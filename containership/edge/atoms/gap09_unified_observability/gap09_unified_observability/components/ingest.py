"""The integrated verified-ingest path and the partition/reconnect protocol (40).

Order of checks for one submission (fail-closed at every step, cheapest first):
  1 size/shape bounds          (runtime._prepare via the store)
  2 trusted time               (TimeAuthority: skew + confidence)
  3 quarantine                 (reporter / site / tenant)
  4 admission                  (global, tenant, reporter buckets -> retry_after)
  5 signature + key lifecycle  (Ed25519 over GAP09-CSP/1, KeyRegistry)
  6 attestation (optional)     (AttestationVerifier)
  7 scope + per-tenant quota   (ReporterAuthority, TenantCardinalityQuota)
  8 durable replay             (DurableReplayGuard)
  9 commit                     (SignalStore.submit_verified, atomic batch)
Every refusal lands in the audit ledger with its stable error code.
"""
from __future__ import annotations

import threading
from typing import Any, Mapping, Sequence

from ..runtime import ReplayDetected, ReporterAuthority, Sample, SignalError, SignalStore
from .canonical import PROFILE_ID, canonical_bytes, submission_envelope
from .errors import Throttled


class _PreVerified:
    def __init__(self, authority: ReporterAuthority) -> None:
        self._a = authority

    def verify(self, **_: Any) -> ReporterAuthority:
        return self._a


class VerifiedIngest:
    def __init__(self, *, store: SignalStore, verifier, time_authority, admission, quarantine, quota,
                 replay, audit, wal=None) -> None:
        self.store, self.verifier, self.time, self.admission = store, verifier, time_authority, admission
        self.quarantine, self.quota, self.replay, self.audit, self.wal = quarantine, quota, replay, audit, wal
        self.accepted = self.refused = 0
        self._commit_lock = threading.Lock()  # the store's verifier slot is swapped per call

    def submit(self, *, reporter: str, samples: Sequence[Sample], submission_id: str, issued_at: int,
               signature: str, key_id: str, attestation_evidence: Any = None) -> int:
        admitted = False
        try:
            now = self.time.check_reported(issued_at)
            for s in samples:
                self.quarantine.check(reporter=reporter, site=s.site, tenant=s.tenant, now=now)
            tenants = sorted({s.tenant for s in samples}) or ["-"]
            self.admission.admit(tenant=tenants[0], reporter=reporter, cost=max(1, len(samples)), now=now)
            admitted = True
            env = submission_envelope(reporter, submission_id, issued_at, samples, key_id)
            payload = canonical_bytes(env)
            att = {"key_id": key_id, "profile": PROFILE_ID}
            if attestation_evidence is not None:
                att["evidence"] = attestation_evidence
            authority = self.verifier.verify(reporter=reporter, payload=payload, signature=signature,
                                             attestation=att, now=now)
            for s in samples:
                if not authority.permits(s):
                    from ..runtime import ScopeViolation
                    raise ScopeViolation("sample outside verified reporter scope")
            by_tenant: dict[str, list] = {}
            for s in samples:
                by_tenant.setdefault(s.tenant, []).append((s.environment, s.site, s.workload, s.signal))
            for t, keys in by_tenant.items():
                self.quota.reserve(t, keys, now)
            self.replay.check_and_record(reporter, submission_id, issued_at, now)
            with self._commit_lock:
                self.store.trust_verifier = _PreVerified(authority)
                try:
                    n = self.store.submit_verified(reporter, samples, submission_id=submission_id, issued_at=issued_at,
                                                   signature=signature, attestation={"key_id": key_id}, now=now)
                finally:
                    self.store.trust_verifier = None
            self.accepted += 1
            self.audit.append("ingest", {"outcome": "accept", "reporter": reporter, "submission_id": submission_id,
                                         "samples": len(samples)}, actor="ingest")
            return n
        except SignalError as exc:
            self.refused += 1
            self.audit.append("ingest", {"outcome": "refuse", "reporter": reporter if isinstance(reporter, str) else None,
                                         "code": exc.code}, actor="ingest")
            raise
        finally:
            if admitted:
                self.admission.release()


def reconcile(wal, ingest: VerifiedIngest) -> dict:
    """Replay a site's un-acked WAL entries after reconnect, in order.

    * accepted -> ack
    * ReplayDetected -> the hub already has it (ack was lost): ack, count dup
    * Throttled -> stop, keep the rest pending (retry_after honoured by caller)
    * any other refusal -> ack as *rejected* with the code recorded; a poison
      entry must not block the queue forever, and it is never retried as trusted
    """
    out = {"delivered": 0, "duplicates": 0, "rejected": [], "stopped": None}
    for n, entry in wal.pending():
        samples = [Sample(**s) for s in entry["samples"]]
        try:
            ingest.submit(reporter=entry["reporter"], samples=samples, submission_id=entry["submission_id"],
                          issued_at=entry["issued_at"], signature=entry["signature"], key_id=entry["key_id"])
            out["delivered"] += 1
        except ReplayDetected:
            out["duplicates"] += 1
        except Throttled as exc:
            out["stopped"] = {"seq": n, "retry_after": exc.retry_after}
            break
        except SignalError as exc:
            out["rejected"].append({"seq": n, "code": exc.code})
        wal.ack(n)
    return out
