"""Trust-store distribution: signed snapshots/deltas, site agent, propagation SLO.

Objects (all ``PK_SIGNED_CONFIG/1`` signed by a configuration-authority key that
is distinct from any artifact signer):

* ``trust-snapshot`` body = ``PK_TRUST_GENERATION/1`` + ``expires``
* ``trust-delta``    body = ``PK_TRUST_DELTA/1``: namespace, parent_generation,
  generation (= parent + 1), issued_at, expires, urgent, ops[]

``SiteTrustAgent`` accepts only objects that verify locally (signature, scope,
monotonic generation, exact parent, not expired under *trusted* time) - so a
compromised relay or cache can at most withhold updates, never roll a site
back or fork it.  Gaps require a full snapshot.  Every accepted object is
journalled (byte-preserving) and replayed/re-verified at restart.  Activation
is an atomic swap; the prior generation is kept for forensics only.

``PropagationTracker`` (control plane) verifies signed site acknowledgements
and measures publish->activate latency per generation, flagging SLO breaches
(urgent revocations have their own, tighter objective).
"""
from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping, Sequence

from . import algorithms as algs
from .canonical import b64u_decode, b64u_encode, canonical_bytes, exact_fields, ld_encode, strict_loads
from .errors import GapError, fail
from .store import AuthorityKey, TrustState, atomic_write, sign_config, verify_config
from .trust import Anchor, Namespace, SignerAuthz, TrustGeneration, parse_cert

DELTA_SCHEMA = "PK_TRUST_DELTA/1"
ACK_SCHEMA = "PK_TRUST_ACK/1"
DELTA_OPS = {"revoke_serial", "revoke_kid", "revoke_identity", "add_cert", "add_signer", "remove_signer",
             "add_anchor", "retire_anchor", "set_policy_ref"}
MAX_OPS = 1024


def make_snapshot(gen: TrustGeneration, *, expires: int, kid: str, alg: str, signer: Callable[[bytes], bytes]) -> dict[str, Any]:
    body = {"trust": gen.to_dict(), "expires": expires}
    return sign_config("trust-distribution", body, kid=kid, alg=alg, signer=signer)


def make_delta(namespace: Namespace, parent: int, ops: Sequence[Mapping[str, Any]], *, issued_at: int, expires: int, urgent: bool,
               kid: str, alg: str, signer: Callable[[bytes], bytes]) -> dict[str, Any]:
    body = {"schema": DELTA_SCHEMA, "namespace": namespace.as_dict(), "parent_generation": parent, "generation": parent + 1,
            "issued_at": issued_at, "expires": expires, "urgent": urgent, "ops": [dict(o) for o in ops]}
    return sign_config("trust-delta", body, kid=kid, alg=alg, signer=signer)


def apply_ops(gen: TrustGeneration, ops: Sequence[Mapping[str, Any]], new_generation: int, issued_at: int) -> TrustGeneration:
    if len(ops) > MAX_OPS:
        raise fail("INPUT_TOO_LARGE", "delta has too many operations")
    certs = {c["serial"]: c for c in gen.certs}
    signers = {s.identity: s for s in gen.signers}
    anchors = {a.anchor_id: a for a in gen.anchors}
    rs, rk, ri = set(gen.revoked_serials), set(gen.revoked_kids), set(gen.revoked_identities)
    policy_ref = gen.policy_ref
    for op in ops:
        o = exact_fields(op, {"op", "value"}, what="delta op")
        name, v = o["op"], o["value"]
        if name not in DELTA_OPS:
            raise fail("TRUST_CORRUPT", "unknown delta operation", op=str(name)[:32])
        if name in ("revoke_serial", "revoke_kid", "revoke_identity", "remove_signer", "set_policy_ref") and (not isinstance(v, str) or not v or len(v) > 512):
            raise fail("TRUST_CORRUPT", "delta op value must be a non-empty string", op=name)
        if name == "revoke_serial":
            rs.add(str(v))
        elif name == "revoke_kid":
            rk.add(str(v))
        elif name == "revoke_identity":
            ri.add(str(v))
        elif name == "add_cert":
            c = parse_cert(v)
            if c["serial"] in certs:
                raise fail("TRUST_CORRUPT", "delta re-adds existing certificate serial", serial=c["serial"])
            certs[c["serial"]] = c
        elif name == "add_signer":
            s = SignerAuthz.from_dict(v)
            signers[s.identity] = s
        elif name == "remove_signer":
            signers.pop(str(v), None)
        elif name == "add_anchor":
            a = Anchor.from_dict(v)
            if a.anchor_id in anchors:
                raise fail("TRUST_CORRUPT", "delta re-adds existing anchor", anchor=a.anchor_id)
            anchors[a.anchor_id] = a
        elif name == "retire_anchor":
            if not isinstance(v, str) or v not in anchors:
                raise fail("TRUST_CORRUPT", "retiring unknown anchor")
            anchors[v] = replace(anchors[v], state="retired")
        elif name == "set_policy_ref":
            policy_ref = str(v)
    return TrustGeneration(gen.namespace, new_generation, issued_at, gen.max_staleness_s, tuple(anchors.values()), tuple(certs.values()),
                           tuple(signers.values()), frozenset(rs), frozenset(rk), frozenset(ri), policy_ref)


class SiteTrustAgent:
    def __init__(self, namespace: Namespace, authorities: Mapping[str, AuthorityKey], clock: Any, *, journal_dir: str | None = None,
                 state: TrustState | None = None, audit: Any = None, site_signer: tuple[str, str, Callable[[bytes], bytes]] | None = None,
                 profile: str = algs.PROFILE_PRODUCTION):
        self.namespace = namespace
        self._auth = dict(authorities)
        self._clock = clock
        self._dir = journal_dir
        self.state = state or TrustState()
        self._audit = audit
        self._site_signer = site_signer
        self._profile = profile
        self._lock = threading.Lock()
        self.expires: int | None = None
        self.previous: TrustGeneration | None = None
        if journal_dir:
            os.makedirs(journal_dir, exist_ok=True)
            self._replay()

    def _event(self, e: str, **d: Any) -> None:
        if self._audit is not None:
            self._audit.append(e, {"namespace": self.namespace.as_dict(), **d})

    def _journal(self, gen: int, raw: bytes) -> None:
        if self._dir:
            atomic_write(os.path.join(self._dir, f"{gen:010d}.json"), raw)

    def _replay(self) -> None:
        files = sorted(f for f in os.listdir(self._dir) if f.endswith(".json"))  # type: ignore[arg-type]
        for f in files:
            with open(os.path.join(self._dir, f), "rb") as fh:  # type: ignore[arg-type]
                doc = strict_loads(fh.read())
            self._accept(doc, replay=True)

    def active_generation(self) -> int:
        try:
            return self.state.current().generation
        except GapError:
            return 0

    def offer(self, doc: Mapping[str, Any]) -> dict[str, Any]:
        """Offer a snapshot/delta from any (untrusted) channel; returns activation evidence."""
        return self._accept(doc, replay=False)

    def _accept(self, doc: Mapping[str, Any], *, replay: bool) -> dict[str, Any]:
        dtype = doc.get("type") if isinstance(doc, Mapping) else None
        now_r = self._clock.now()
        now = now_r.value
        with self._lock:
            active = self.active_generation()
            if dtype == "trust-distribution":
                body = verify_config(doc, self._auth, expect_type="trust-distribution", profile=self._profile)
                b = exact_fields(body, {"trust", "expires"}, what="snapshot body")
                gen = TrustGeneration.from_dict(b["trust"])
                expires = int(b["expires"])
                parent = None
            elif dtype == "trust-delta":
                body = verify_config(doc, self._auth, expect_type="trust-delta", profile=self._profile)
                b = exact_fields(body, {"schema", "namespace", "parent_generation", "generation", "issued_at", "expires", "urgent", "ops"}, what="delta")
                if b["schema"] != DELTA_SCHEMA or b["generation"] != b["parent_generation"] + 1:
                    raise fail("TRUST_CORRUPT", "delta schema/generation arithmetic invalid")
                if Namespace.from_dict(b["namespace"]) != self.namespace:
                    raise fail("TRUST_SCOPE", "delta scoped to another namespace")
                parent = b["parent_generation"]
                if parent != active:
                    if b["generation"] <= active:
                        raise fail("TRUST_ROLLBACK", "delta generation not above active", active=active, offered=b["generation"])
                    raise fail("TRUST_PARENT_MISMATCH", "delta parent does not match active generation; full snapshot required",
                               active=active, parent=parent)
                gen = apply_ops(self.state.current(), b["ops"], b["generation"], b["issued_at"])
                expires = int(b["expires"])
            else:
                raise fail("TRUST_CORRUPT", "unknown distribution object type")
            if gen.namespace != self.namespace:
                raise fail("TRUST_SCOPE", "snapshot scoped to another namespace")
            if gen.generation <= active:
                self._event("trust.distribution_rejected", code="TRUST_ROLLBACK", offered=gen.generation, active=active)
                raise fail("TRUST_ROLLBACK", "offered generation not above active", active=active, offered=gen.generation)
            if not replay and now > expires:
                raise fail("TRUST_STALE", "distribution object already expired", expires=expires, now=now)
            raw = canonical_bytes(doc)
            if not replay:
                self._journal(gen.generation, raw)
            try:
                self.previous = self.state.current()
            except GapError:
                self.previous = None
            self.state.swap(gen)
            self.expires = expires
        ev = {"generation": gen.generation, "parent": parent, "type": dtype, "digest": gen.digest,
              "object_digest": hashlib.sha256(raw).hexdigest(), "activated_at": now, "time": now_r.evidence(),
              "urgent": bool(dtype == "trust-delta" and b["urgent"])}
        self._event("trust.activate", **{k: v for k, v in ev.items() if k != "time"})
        return ev

    def readiness(self) -> tuple[bool, str]:
        try:
            gen = self.state.current()
            now = self._clock.now().value
        except GapError as exc:
            return False, exc.code
        if self.expires is not None and now > self.expires:
            return False, "TRUST_STALE"
        try:
            gen.check_fresh(now)
        except GapError as exc:
            return False, exc.code
        return True, "ok"

    def reconcile_plan(self, control_plane_generation: int, snapshot_generation: int) -> dict[str, Any]:
        """Minimum safe fetch after reconnect: contiguous deltas or a snapshot."""
        active = self.active_generation()
        if control_plane_generation <= active:
            return {"action": "none", "active": active}
        if active >= snapshot_generation:
            return {"action": "deltas", "from": active + 1, "to": control_plane_generation}
        return {"action": "snapshot", "snapshot_generation": snapshot_generation, "then_deltas_to": control_plane_generation}

    def acknowledge(self, evidence: Mapping[str, Any], site_id: str) -> dict[str, Any]:
        if self._site_signer is None:
            raise fail("POLICY_INVALID", "site has no acknowledgement key")
        kid, alg, sign = self._site_signer
        body = {"schema": ACK_SCHEMA, "site_id": site_id, "namespace": self.namespace.as_dict(), "generation": evidence["generation"],
                "digest": evidence["digest"], "activated_at": evidence["activated_at"], "kid": kid, "alg": alg}
        return {**body, "sig": b64u_encode(sign(_ack_message(body)))}


def _ack_message(b: Mapping[str, Any]) -> bytes:
    return ld_encode("trust-ack/1", [("schema", b["schema"]), ("site_id", b["site_id"]), ("namespace", canonical_bytes(b["namespace"])),
                                     ("generation", b["generation"]), ("digest", b["digest"]), ("activated_at", b["activated_at"]),
                                     ("kid", b["kid"]), ("alg", b["alg"])])


@dataclass(frozen=True)
class PropagationSLO:
    normal_s: int = 3600
    urgent_revocation_s: int = 300


class PropagationTracker:
    """Control-plane view: which sites activated which generation, and how fast."""

    def __init__(self, site_keys: Mapping[str, tuple[str, str, bytes]], slo: PropagationSLO | None = None):
        self._keys = dict(site_keys)  # site_id -> (kid, alg, spki)
        self.slo = slo or PropagationSLO()
        self._published: dict[int, tuple[int, bool, str]] = {}
        self._acks: dict[int, dict[str, int]] = {}

    def published(self, generation: int, at: int, *, urgent: bool, digest: str) -> None:
        self._published[generation] = (at, urgent, digest)

    def ack(self, ack: Mapping[str, Any]) -> int:
        a = exact_fields(ack, {"schema", "site_id", "namespace", "generation", "digest", "activated_at", "kid", "alg", "sig"}, what="ack")
        key = self._keys.get(a["site_id"])
        if key is None or key[0] != a["kid"] or key[1] != a["alg"]:
            raise fail("SIGNER_UNTRUSTED", "acknowledgement from unknown site key")
        algs.verify_raw(key[1], key[2], b64u_decode(a["sig"]), _ack_message(a), profile=algs.PROFILE_PRODUCTION)
        pub = self._published.get(a["generation"])
        if pub is None or pub[2] != a["digest"]:
            raise fail("TRUST_CORRUPT", "acknowledged generation/digest was not published")
        latency = a["activated_at"] - pub[0]
        self._acks.setdefault(a["generation"], {})[a["site_id"]] = latency
        return latency

    def report(self, now: int) -> dict[str, Any]:
        out = []
        for gen, (at, urgent, _) in sorted(self._published.items()):
            budget = self.slo.urgent_revocation_s if urgent else self.slo.normal_s
            acks = self._acks.get(gen, {})
            pending = sorted(set(self._keys) - set(acks))
            worst = max(acks.values(), default=None)
            breach = (worst is not None and worst > budget) or (pending and now - at > budget)
            out.append({"generation": gen, "urgent": urgent, "budget_s": budget, "acked": len(acks), "pending_sites": pending,
                        "worst_latency_s": worst, "slo_breach": bool(breach)})
        return {"schema": "PK_PROPAGATION_REPORT/1", "generations": out, "breaches": sum(1 for g in out if g["slo_breach"])}
