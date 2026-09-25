"""Component 36 - artifact / policy verification, fail-closed (contract ``PK_DYN_ARTIFACT/1``).

Release manifest (canonical JSON)::

  {"schema": "PK_DYN_ARTIFACT/1", "name": str, "digest": "sha256:<64 hex>",
   "chain": [<delegation cert>, ...],          # anchor -> ... -> leaf, len 0..MAX_CHAIN
   "signature": <core.TrustRoot signature by leaf kid over envelope(name, digest, scope)>,
   "scope": "artifact"|"policy",
   "provenance": <PK_DYN_PROVENANCE/1 statement>,
   "policy_bundle": <PK_DYN_POLICY/1 object, only when scope == "policy">}

Delegation cert: {"statement": {"schema": "PK_DYN_DELEGATION/1", "issuer": kid,
"subject": kid, "scopes": [...], "not_before": t, "not_after": t}, "signature": sig}.

Every check fails closed: any exception or unknown field is a rejection, every
rejection is written to the audit log before ``Inv08Error`` is raised.

Limitation: signatures are HMAC-SHA256 (symmetric) because the stdlib has no
asymmetric primitive; the verifier therefore holds every signing key.  Asymmetric
signing (Ed25519/Sigstore/Rekor transparency) is BLOCKED on a vetted crypto library
and a production KMS-backed release key.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any

from .core import Inv08Error, Outcome, TrustRoot, canonical

SCHEMA = "PK_DYN_ARTIFACT/1"
DELEGATION = "PK_DYN_DELEGATION/1"
PROVENANCE = "PK_DYN_PROVENANCE/1"
POLICY = "PK_DYN_POLICY/1"
MAX_CHAIN = 4
MAX_ARTIFACT_BYTES = 256 * 1024 * 1024
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
POOL_KEYS = {"min_nodes", "max_nodes", "per_node", "lease_ttl"}


class VerificationError(Inv08Error):
    pass


def _fail(reason: str, msg: str) -> VerificationError:
    return VerificationError(f"INV08.ARTIFACT.{reason.upper()}", msg, outcome=Outcome.TERMINAL_FAILURE,
                             severity="critical", remediation="do not deploy; re-fetch or re-sign artifact",
                             details={"reason": reason})


def verify_digest(data: bytes, expected: str) -> None:
    if not isinstance(expected, str) or not _DIGEST_RE.match(expected):
        raise _fail("bad_digest_format", f"unsupported digest {expected!r}")
    if not isinstance(data, (bytes, bytearray)) or len(data) > MAX_ARTIFACT_BYTES:
        raise _fail("bad_artifact", "artifact missing or too large")
    got = "sha256:" + hashlib.sha256(data).hexdigest()
    if not hmac.compare_digest(got, expected):
        raise _fail("digest_mismatch", "artifact digest mismatch")


def envelope(name: str, digest: str, scope: str) -> dict:
    return {"schema": SCHEMA + "#envelope", "name": name, "digest": digest, "scope": scope}


def make_delegation(trust: TrustRoot, issuer: str, subject: str, scopes: list[str],
                    not_before: float, not_after: float) -> dict:
    st = {"schema": DELEGATION, "issuer": issuer, "subject": subject, "scopes": sorted(scopes),
          "not_before": not_before, "not_after": not_after}
    return {"statement": st, "signature": trust.sign(issuer, st)}


def verify_chain(trust: TrustRoot, anchors: set[str], chain: list, payload: dict, sig: dict,
                 *, scope: str, now: float) -> None:
    """Anchor kid -> delegations -> leaf kid that signed ``payload``."""
    if not isinstance(chain, list) or len(chain) > MAX_CHAIN:
        raise _fail("chain_too_long", "delegation chain missing or too long")
    if not isinstance(sig, dict):
        raise _fail("bad_signature", "signature missing")
    current: str | None = None
    for i, cert in enumerate(chain):
        try:
            st, csig = cert["statement"], cert["signature"]
            if st["schema"] != DELEGATION:
                raise KeyError
        except (KeyError, TypeError):
            raise _fail("bad_chain", f"malformed delegation {i}")
        issuer = st["issuer"]
        if (i == 0 and issuer not in anchors) or (i > 0 and issuer != current):
            raise _fail("broken_chain", f"delegation {i} issuer {issuer!r} not trusted")
        if csig.get("kid") != issuer or not trust.verify(st, csig):
            raise _fail("bad_chain_signature", f"delegation {i} signature invalid or revoked")
        if not (st["not_before"] <= now <= st["not_after"]):
            raise _fail("expired_delegation", f"delegation {i} outside validity window")
        if scope not in st["scopes"]:
            raise _fail("scope_violation", f"delegation {i} does not grant scope {scope!r}")
        current = st["subject"]
    leaf = current
    if leaf is None:
        if sig.get("kid") not in anchors:
            raise _fail("untrusted_signer", "signer is not an anchor and no chain given")
    elif sig.get("kid") != leaf:
        raise _fail("signer_mismatch", "artifact not signed by chain leaf")
    if not trust.verify(payload, sig):
        raise _fail("bad_signature", "artifact signature invalid or key revoked")


def verify_provenance(stmt: Any, digest: str, name: str, allowed_builders: set[str]) -> None:
    try:
        ok = (stmt["schema"] == PROVENANCE
              and any(s["name"] == name and s["digest"] == digest for s in stmt["subject"])
              and isinstance(stmt["builder"]["id"], str)
              and isinstance(stmt["materials"], list))
        builder = stmt["builder"]["id"]
        mats_ok = all(_DIGEST_RE.match(m["digest"]) for m in stmt["materials"])
    except (KeyError, TypeError):
        raise _fail("bad_provenance", "malformed provenance statement")
    if not ok or not mats_ok:
        raise _fail("provenance_subject", "provenance does not cover this artifact")
    if builder not in allowed_builders:
        raise _fail("untrusted_builder", f"builder {builder!r} not allowed")


def validate_policy_bundle(bundle: Any, *, current_version: int = 0, max_nodes_ceiling: int = 10000) -> dict:
    """Schema, bounds, anti-rollback, and acceptance by the real ``model.Pool``."""
    from ..model import Pool
    if not isinstance(bundle, dict) or set(bundle) != {"schema", "version", "pool"}:
        raise _fail("bad_policy", "policy bundle keys must be exactly schema/version/pool")
    if bundle["schema"] != POLICY:
        raise _fail("bad_policy", "unsupported policy schema")
    v = bundle["version"]
    if isinstance(v, bool) or not isinstance(v, int) or v <= current_version:
        raise _fail("policy_rollback", f"policy version {v!r} must exceed {current_version}")
    pool = bundle["pool"]
    if not isinstance(pool, dict) or set(pool) != POOL_KEYS:
        raise _fail("bad_policy", "pool section keys invalid")
    if isinstance(pool["max_nodes"], int) and pool["max_nodes"] > max_nodes_ceiling:
        raise _fail("policy_bounds", "max_nodes exceeds ceiling")
    try:
        Pool(**pool)
    except (ValueError, TypeError) as exc:
        raise _fail("policy_bounds", f"rejected by Pool: {exc}")
    canonical(bundle)
    return pool


class ArtifactGate:
    """Runs all checks; writes audit evidence for accept and reject; fails closed."""

    def __init__(self, trust: TrustRoot, anchors: set[str], allowed_builders: set[str], audit,
                 clock, *, current_policy_version: int = 0) -> None:
        self.trust, self.anchors, self.builders = trust, set(anchors), set(allowed_builders)
        self.audit, self.clock, self.policy_version = audit, clock, current_policy_version

    def verify_release(self, data: bytes, manifest: Any) -> dict:
        name = manifest.get("name", "?") if isinstance(manifest, dict) else "?"
        try:
            if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
                raise _fail("bad_manifest", "unsupported manifest")
            scope = manifest["scope"]
            if scope not in ("artifact", "policy"):
                raise _fail("bad_manifest", "unknown scope")
            verify_digest(data, manifest["digest"])
            verify_chain(self.trust, self.anchors, manifest["chain"],
                         envelope(name, manifest["digest"], scope), manifest["signature"],
                         scope=scope, now=self.clock())
            verify_provenance(manifest["provenance"], manifest["digest"], name, self.builders)
            result = {"name": name, "digest": manifest["digest"], "scope": scope}
            if scope == "policy":
                import json
                bundle = json.loads(data.decode("utf-8"))
                if bundle != manifest.get("policy_bundle"):
                    raise _fail("bad_policy", "embedded bundle differs from signed bytes")
                result["pool"] = validate_policy_bundle(bundle, current_version=self.policy_version)
                self.policy_version = bundle["version"]
        except VerificationError as exc:
            self.audit.append("artifact-gate", "verify", name, "DENY", exc.to_dict())
            raise
        except Exception as exc:  # fail closed on anything unexpected
            err = _fail("internal", f"{type(exc).__name__}")
            self.audit.append("artifact-gate", "verify", name, "DENY", err.to_dict())
            raise err from exc
        self.audit.append("artifact-gate", "verify", name, "SUCCESS", result)
        return result
