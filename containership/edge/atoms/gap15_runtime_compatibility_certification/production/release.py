"""Release governance: RTM (41), release evidence bundle (40), formal exit gate (50),
canary/staged rollout (46), supply-chain SBOM/provenance (45), bootstrap preflight (44).

The exit gate consumes *signed* evidence bound to an exact build digest and
never treats checklist text or a manually entered 'pass' as evidence
(MC-50-03). It returns NO_GO whenever any mandatory row is missing, stale,
mismatched, unsigned, or only waived by an expired/unauthorised waiver.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import sqlite3
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

from .canonical import canonical_bytes, digest, sha256_hex
from .signing import KeyProvider, TrustStore, sign_payload, verify_payload

GATE_POLICY_REVISION = "GAP15-GATE-POLICY/1.0.0"


def tree_digest(root: str, *, exclude=("__pycache__", ".pyc", "evidence/", ".db")) -> dict:
    """Deterministic per-file SHA-256 and a root digest over the shipped tree."""
    files = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if d not in ("__pycache__",))
        for f in sorted(fn):
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if any(x in rel for x in exclude):
                continue
            files[rel] = sha256_hex(open(p, "rb").read())
    return {"files": files, "root": "sha256:" + sha256_hex(canonical_bytes(files))}


def sbom(root: str, name: str, version: str) -> dict:
    """CycloneDX-shaped SBOM: stdlib-only, so components are the files themselves + the Python runtime."""
    td = tree_digest(root)
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": name, "version": version,
                                       "purl": f"pkg:generic/{name}@{version}"}, "subject": td["root"]},
            "components": [{"type": "file", "name": k, "hashes": [{"alg": "SHA-256", "content": v}]} for k, v in td["files"].items()],
            "dependencies": [{"ref": "python", "note": f"CPython >= 3.10 standard library only; built with {platform.python_version()}"}]}


def build_provenance(root: str, *, builder: str, source_revision: str, invocation: list) -> dict:
    td = tree_digest(root)
    return {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": os.path.basename(os.path.abspath(root)), "digest": {"sha256": td["root"][7:]}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "gap15/local-package", "externalParameters": {"invocation": invocation},
                                              "resolvedDependencies": [{"uri": source_revision}]},
                          "runDetails": {"builder": {"id": builder},
                                         "metadata": {"python": sys.version.split()[0], "host": platform.platform()}}}}


# ------------------------------------------------------------------ RTM
@dataclass
class RtmRow:
    control_id: str
    text: str
    component: str
    priority: str
    status: str  # LOCALLY_VERIFIED | ARTIFACT_PRESENT_UNREVIEWED | BLOCKED | NOT_IMPLEMENTED | NOT_APPLICABLE
    implementation: list = field(default_factory=list)
    tests: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    blocker: Optional[str] = None
    owner: Optional[str] = None
    reviewer: Optional[str] = None
    waiver: Optional[str] = None
    na_rationale: Optional[str] = None


def rtm_problems(rows: list) -> list:
    """Orphans, untested implementation, N/A without rationale, verified without evidence (MC-41-06/07)."""
    out = []
    for r in rows:
        if r.status == "LOCALLY_VERIFIED" and (not r.tests or not r.evidence):
            out.append(f"{r.control_id}: verified without test+evidence")
        if r.status == "NOT_APPLICABLE" and not r.na_rationale:
            out.append(f"{r.control_id}: N/A without rationale")
        if r.status == "BLOCKED" and not r.blocker:
            out.append(f"{r.control_id}: blocked without a named blocker")
        if r.implementation and not r.tests and r.status not in ("BLOCKED", "ARTIFACT_PRESENT_UNREVIEWED"):
            out.append(f"{r.control_id}: implementation with no test")
    return out


# ------------------------------------------------------------------ gate
@dataclass
class GateInput:
    kind: str  # tests | rtm | sbom | provenance | security | performance | restore | dr | review | approval
    build_digest: str
    produced_at: int
    body: dict
    signature: Optional[dict] = None


def sign_input(kp: KeyProvider, key_id: str, inp: GateInput, environment: str = "release") -> GateInput:
    payload = {"kind": inp.kind, "build_digest": inp.build_digest, "produced_at": inp.produced_at, "body": inp.body}
    inp.signature = sign_payload(kp, key_id, message_type="gate-input", environment=environment, payload=payload,
                                 signed_at=inp.produced_at)
    return inp


MANDATORY_INPUTS = ("tests", "rtm", "sbom", "provenance", "security", "performance", "restore", "dr", "review", "approval")


def exit_gate(inputs: list, *, build_digest: str, trust: TrustStore, now: int, max_age_s: int = 7 * 86400,
              environment: str = "release", reviewer_denylist: frozenset = frozenset()) -> dict:
    """Machine-enforced GO/NO_GO (component 50)."""
    results, blockers = {}, []
    by_kind = {}
    for inp in inputs:
        by_kind.setdefault(inp.kind, []).append(inp)
    for kind in MANDATORY_INPUTS:
        cands = by_kind.get(kind, [])
        if not cands:
            results[kind] = "MISSING"
            blockers.append(f"{kind}: no evidence supplied")
            continue
        inp = max(cands, key=lambda i: i.produced_at)
        payload = {"kind": inp.kind, "build_digest": inp.build_digest, "produced_at": inp.produced_at, "body": inp.body}
        v = verify_payload(trust, inp.signature, message_type="gate-input", environment=environment, payload=payload,
                           required_scope="gate:sign" if kind not in ("review", "approval") else f"gate:{kind}")
        if not v.ok:
            results[kind] = "UNVERIFIABLE:" + v.code
            blockers.append(f"{kind}: signature {v.code}")
        elif inp.build_digest != build_digest:
            results[kind] = "MISMATCHED_BUILD"
            blockers.append(f"{kind}: evidence is for {inp.build_digest[:19]}…, not this build")
        elif now - inp.produced_at > max_age_s:
            results[kind] = "STALE"
            blockers.append(f"{kind}: evidence older than {max_age_s}s")
        elif kind in ("review", "approval") and v.signer in reviewer_denylist:
            results[kind] = "SELF_REVIEW"
            blockers.append(f"{kind}: signer {v.signer} may not review its own output")
        elif inp.body.get("status") != "pass":
            results[kind] = "FAILED"
            blockers.append(f"{kind}: status {inp.body.get('status')!r}")
        else:
            results[kind] = "PASS"
    decision = "GO" if not blockers else "NO_GO"
    return {"schema": "GAP15_GATE_DECISION/1", "decision": decision, "build_digest": build_digest,
            "gate_policy_revision": GATE_POLICY_REVISION, "evaluated_at": now, "inputs": results, "blockers": blockers}


# ------------------------------------------------------------------ rollout
STAGES = ("dev", "test", "canary", "site-subset", "pct-25", "global")


@dataclass
class RolloutController:
    """Staged promotion with automatic halt/rollback triggers (component 46)."""

    thresholds: dict = field(default_factory=lambda: {"error_rate": 0.01, "incorrect_verdicts": 0, "sig_failures": 5,
                                                      "replication_lag_s": 30, "saturation": 0.85, "audit_gaps": 0})
    stage_index: int = 0
    history: list = field(default_factory=list)
    halted: bool = False

    @property
    def stage(self) -> str:
        return STAGES[self.stage_index]

    def evaluate(self, observed: dict, *, observation_s: int, min_observation_s: int = 600) -> dict:
        breaches = [k for k, lim in self.thresholds.items() if observed.get(k, float("inf")) > lim]
        missing = [k for k in self.thresholds if k not in observed]
        if breaches or missing:
            self.halted = True
            action = "rollback"
            prev = self.stage_index
            self.stage_index = max(0, self.stage_index - 1)
            rec = {"action": action, "from": STAGES[prev], "to": self.stage, "breaches": breaches, "missing_signals": missing}
        elif observation_s < min_observation_s:
            rec = {"action": "hold", "stage": self.stage, "reason": "observation window not complete"}
        elif self.stage_index < len(STAGES) - 1:
            self.stage_index += 1
            rec = {"action": "promote", "to": self.stage}
        else:
            rec = {"action": "complete", "stage": self.stage}
        self.history.append(rec)
        return rec


# ------------------------------------------------------------------ bootstrap
def preflight(*, data_dir: str, config: dict, trust: TrustStore, clock_ok: bool, min_free_bytes: int = 64 << 20) -> dict:
    """Day-0 bootstrap validator (MC-44-04): permissions, config, trust roots, clock, headroom."""
    checks = {}
    checks["python"] = "ok" if sys.version_info >= (3, 10) else "E_PYTHON_TOO_OLD"
    checks["sqlite"] = "ok" if sqlite3.sqlite_version_info >= (3, 35, 0) else "E_SQLITE_TOO_OLD"
    try:
        os.makedirs(data_dir, exist_ok=True)
        probe = os.path.join(data_dir, ".preflight")
        with open(probe, "w") as fh:
            fh.write("ok")
        os.remove(probe)
        mode = os.stat(data_dir).st_mode & 0o777
        checks["data_dir"] = "ok" if os.name == "nt" or not mode & 0o007 else "E_DATA_DIR_WORLD_ACCESSIBLE"
    except OSError:
        checks["data_dir"] = "E_DATA_DIR_UNWRITABLE"
    st = os.statvfs(data_dir) if hasattr(os, "statvfs") else None
    checks["headroom"] = "ok" if st is None or st.f_bavail * st.f_frsize >= min_free_bytes else "E_LOW_DISK"
    from .config import validate_config
    problems = validate_config(config)
    checks["config"] = "ok" if not problems else "E_CONFIG: " + "; ".join(problems)
    checks["trust_roots"] = "ok" if trust.keys() else "E_NO_TRUST_ROOTS"
    checks["clock"] = "ok" if clock_ok else "E_CLOCK_UNTRUSTED"
    return {"ok": all(v == "ok" for v in checks.values()), "checks": checks}
