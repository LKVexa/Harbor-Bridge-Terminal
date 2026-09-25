"""MC-01 / MC-32 / MC-33: the hardware-evidence verification pipeline.

``Verifier.verify_tpm_quote`` runs, in order and fail-closed:
  size/parse -> signature (enrolled AK, allow-listed profile) -> nonce binding
  -> AK name binding -> clockInfo monotonicity -> PCR composite recompute ->
  event-log replay -> IMA policy -> measurement policy -> relay/duplicate checks
and returns a ``Decision`` carrying the reason code and an evidence record
(01.14 / 01.15).  TEE reports go through ``TeeAdapter`` subclasses; the only
adapter shipped is ``GenericSignedReportAdapter``.  Vendor adapters (SEV-SNP,
TDX, Nitro, Apple/Android key attestation) are BLOCKED: no vendor vectors.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

from . import algorithms as alg
from . import tpm
from .errors import Gap06Error, fail

VERIFIER_VERSION = "gap06-verifier/5.0.0"

SUPPORTED_ATTESTERS = {
    # 01.01 supported-attester matrix (status is evidence-backed, not aspirational)
    "tpm2-discrete": {"status": "format-supported", "vectors": "software-simulated only", "min_spec": "TPM 2.0 rev 1.38"},
    "tpm2-firmware": {"status": "format-supported", "vectors": "none", "min_spec": "TPM 2.0 rev 1.38"},
    "vtpm": {"status": "format-supported", "vectors": "none", "note": "requires host-binding evidence (not implemented)"},
    "tee-generic-signed-report": {"status": "supported", "vectors": "software-simulated only"},
    "amd-sev-snp": {"status": "unsupported", "reason": "no adapter, no vendor test vectors"},
    "intel-tdx": {"status": "unsupported", "reason": "no adapter, no vendor test vectors"},
    "tpm1.2": {"status": "unsupported", "reason": "SHA-1 only; explicitly out of scope"},
}


@dataclass(frozen=True)
class Decision:
    ok: bool
    code: str
    node: str
    level: str
    record: dict = field(default_factory=dict)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse_ima(text: str, *, allowed_templates=("ima-ng",), policy=alg.DEFAULT_POLICY):
    """01.07: ASCII IMA measurement list, ima-ng template only.
    Returns [(path, 'alg:hex')]; unknown templates are rejected (policy-controlled)."""
    out = []
    lines = text.splitlines()
    if len(lines) > 100_000:
        raise fail("E_MALFORMED_EVIDENCE", "IMA list too long")
    for n, line in enumerate(lines):
        parts = line.split(" ", 4)
        if len(parts) != 5 or parts[0] != "10":
            raise fail("E_MALFORMED_EVIDENCE", f"IMA line {n} malformed")
        if parts[2] not in allowed_templates:
            raise fail("E_MEASUREMENT_REJECTED", f"IMA template {parts[2]} not allowed")
        algname, _, hexd = parts[3].partition(":")
        policy.check_digest(algname)
        if len(hexd) != 2 * alg.DIGEST_SIZE[algname] or any(c not in "0123456789abcdef" for c in hexd):
            raise fail("E_MALFORMED_EVIDENCE", f"IMA line {n} digest")
        out.append((parts[4], f"{algname}:{hexd}"))
    return out


@dataclass
class EnrolledAK:
    node: str
    ak_public: bytes  # PEM/DER SPKI
    ak_name: bytes
    device_id: str
    tenant: str = "estate"
    active: bool = True


@dataclass
class Verifier:
    policy: alg.AlgorithmPolicy = field(default_factory=alg.AlgorithmPolicy)
    trust_anchor_set: str = "anchors-v1"
    clocks: tpm.ClockTracker = field(default_factory=tpm.ClockTracker)
    last_quote_by_device: dict = field(default_factory=dict)

    def verify_tpm_quote(self, *, ak: EnrolledAK, expected_nonce: bytes, attest: bytes, signature: bytes,
                         pcr_values: dict, event_log: bytes | None, allowed_pcrs: dict,
                         required_pcrs=(0, 7), policy_version: str, ima: str | None = None,
                         ima_allowed: set | None = None, channel_binding: bytes | None = None,
                         expected_channel_binding: bytes | None = None, decided_at: str = "") -> Decision:
        raw_digest = _sha(attest + b"|" + signature)
        claims: dict = {}
        try:
            if not ak.active:
                raise fail("E_REVOKED", "attestation key is not active")
            quote = tpm.parse_attest(attest)
            profile, sig = tpm.parse_signature(signature)
            key = alg.load_public_key(ak.ak_public)
            alg.verify(key, profile, sig, attest, self.policy)
            if quote.extra_data != expected_nonce:
                raise fail("E_NONCE_MISMATCH", "quote extraData does not equal the issued challenge")
            if quote.qualified_signer != ak.ak_name:
                raise fail("E_UNKNOWN_KEY", "qualifiedSigner does not match enrolled AK name")
            if channel_binding is not None or expected_channel_binding is not None:
                if channel_binding != expected_channel_binding:
                    raise fail("E_NONCE_MISMATCH", "channel binding mismatch (possible relay)")
            self.clocks.check(ak.node, quote.clock_info)
            banks = {b for b, _ in quote.pcr_selection}
            if banks != {"sha256"}:
                raise fail("E_UNSUPPORTED_ALG", f"unexpected PCR bank selection {sorted(banks)}")
            selected = set(quote.pcr_selection[0][1])
            if not set(required_pcrs) <= selected:
                raise fail("E_PCR_MISMATCH", f"quote omits required PCRs {sorted(set(required_pcrs) - selected)}")
            if set(pcr_values) != selected:
                raise fail("E_PCR_MISMATCH", "supplied PCR values do not match quoted selection")
            comp = tpm.pcr_composite(quote.pcr_selection, {("sha256", p): v for p, v in pcr_values.items()})
            if comp != quote.pcr_digest:
                raise fail("E_PCR_MISMATCH", "recomputed PCR composite differs from quote")
            if event_log is not None:
                events = tpm.parse_event_log(event_log)
                div = tpm.first_divergence(events, "sha256", pcr_values)
                if div is not None:
                    raise fail("E_EVENTLOG_MISMATCH", f"event log diverges at event index {div}")
                claims["event_log_sha256"] = _sha(event_log)
                claims["events"] = len(events)
            for p in sorted(selected):
                allowed = allowed_pcrs.get(p)
                if allowed is not None and pcr_values[p].hex() not in allowed:
                    raise fail("E_MEASUREMENT_REJECTED", f"PCR{p} value not in accepted set")
            if ima is not None:
                entries = parse_ima(ima, policy=self.policy)
                bad = [p for p, d in entries if ima_allowed is None or d not in ima_allowed]
                if bad:
                    raise fail("E_MEASUREMENT_REJECTED", f"{len(bad)} IMA entries not allowed")
                claims["ima_entries"] = len(entries)
            prev = self.last_quote_by_device.get(ak.device_id)
            if prev is not None and prev != ak.node:
                raise fail("E_DUPLICATE_IDENTITY", "device identity already active under another node")
            self.last_quote_by_device[ak.device_id] = ak.node
            claims.update(pcrs={str(p): v.hex() for p, v in sorted(pcr_values.items())},
                          reset=quote.clock_info.reset_count, restart=quote.clock_info.restart_count,
                          firmware=f"{quote.firmware_version:016x}")
            return self._decide(True, "OK", ak.node, "hardware", raw_digest, claims, policy_version, decided_at)
        except Gap06Error as e:
            return self._decide(False, e.code, ak.node, "untrusted", raw_digest, claims, policy_version, decided_at)
        except Exception as e:  # internal error never yields trust
            return self._decide(False, "E_INTERNAL", ak.node, "untrusted", raw_digest, claims, policy_version, decided_at)

    def _decide(self, ok, code, node, level, raw_digest, claims, policy_version, decided_at) -> Decision:
        claims_digest = _sha(json.dumps(claims, sort_keys=True).encode())
        record = {"schema": "GAP06-EVIDENCE/1", "verifier_version": VERIFIER_VERSION,
                  "trust_anchor_set": self.trust_anchor_set, "policy_version": policy_version,
                  "raw_evidence_sha256": raw_digest, "claims_sha256": claims_digest,
                  "decision": "trusted" if ok else "rejected", "reason_code": code,
                  "node": node, "level": level, "decided_at": decided_at}
        return Decision(ok, code, node, level, record)


class TeeAdapter:
    platform = "abstract"

    def verify(self, report: bytes, signature: bytes, *, expected_report_data: bytes) -> dict:  # pragma: no cover
        raise fail("E_UNSUPPORTED_PLATFORM", self.platform)


@dataclass
class GenericSignedReportAdapter(TeeAdapter):
    """01.10 for a generic signed JSON report: checks vendor signature, SVN floor,
    debug state, TCB status and report_data binding."""
    vendor_key_pem: bytes
    min_svn: int
    platform: str = "tee-generic-signed-report"
    policy: alg.AlgorithmPolicy = field(default_factory=alg.AlgorithmPolicy)

    def verify(self, report: bytes, signature: bytes, *, expected_report_data: bytes) -> dict:
        key = alg.load_public_key(self.vendor_key_pem)
        alg.verify(key, alg.profile_of(key), signature, report, self.policy)
        try:
            doc = json.loads(report.decode("utf-8"))
        except Exception as exc:
            raise fail("E_MALFORMED_EVIDENCE", "report is not JSON") from exc
        if not isinstance(doc, dict) or set(doc) != {"svn", "debug", "tcb_status", "report_data", "measurement"}:
            raise fail("E_SCHEMA", "report fields")
        if doc["debug"] is not False:
            raise fail("E_DEBUG_ENABLED", "TEE debug mode enabled")
        if not isinstance(doc["svn"], int) or doc["svn"] < self.min_svn:
            raise fail("E_TCB_OUT_OF_DATE", "SVN below floor")
        if doc["tcb_status"] != "UpToDate":
            raise fail("E_TCB_OUT_OF_DATE", f"tcb_status {doc['tcb_status']}")
        if doc["report_data"] != expected_report_data.hex():
            raise fail("E_NONCE_MISMATCH", "report_data does not bind the challenge")
        return doc
