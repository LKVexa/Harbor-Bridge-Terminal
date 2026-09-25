"""P1/P2 operations: provenance verification hook (MC-17), supported-version
matrix (MC-18), pk_core dependency contract (MC-22), telemetry (MC-29),
tamper-evident audit events (MC-30), ownership metadata (MC-40)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from typing import Any

from . import NORMALIZATION_VERSION, POLICY_VERSION, TOOL_VERSION, WIT_FEATURE_LEVEL
from .normalize import canonical_json

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- MC-17 provenance verification hook -------------------------------------
class ProvenanceError(Exception):
    pass


def ed25519_verify(pubkey_pem: str, data_path: str, sig_path: str) -> bool:
    exe = shutil.which("openssl")
    if exe is None:
        raise ProvenanceError("BLOCKED: openssl not available; signature cannot be verified (fail closed)")
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as fh:
        fh.write(pubkey_pem)
        kp = fh.name
    try:
        r = subprocess.run([exe, "pkeyutl", "-verify", "-pubin", "-inkey", kp, "-rawin", "-in", data_path,
                            "-sigfile", sig_path], capture_output=True, timeout=30)
        return r.returncode == 0
    finally:
        os.unlink(kp)


def verify_import(package_dir: str, policy: dict[str, Any]) -> dict[str, Any]:
    """Verify an imported contract package before it is parsed.

    Expects `package_dir/PROVENANCE.json` = {"files": {rel: sha256}, "sbom": rel,
    "provenance": {...}, "signature": rel-of-sig-over-PROVENANCE.json-bytes?}.
    policy = {"require_signature": bool, "trusted_keys": {key_id: pem}}.
    Every failure raises ProvenanceError: nothing unverified reaches the parser."""
    manifest = os.path.join(package_dir, "PROVENANCE.json")
    if not os.path.isfile(manifest):
        raise ProvenanceError("missing PROVENANCE.json")
    with open(manifest, "rb") as fh:
        raw = fh.read()
    doc = json.loads(raw)
    files = doc.get("files") or {}
    on_disk = sorted(os.path.relpath(os.path.join(dp, f), package_dir).replace(os.sep, "/")
                     for dp, _, fs in os.walk(package_dir) for f in fs if f.endswith(".wit"))
    if sorted(k for k in files if k.endswith(".wit")) != on_disk:
        raise ProvenanceError(f"file set mismatch: listed {sorted(files)} vs present {on_disk}")
    for rel, digest in sorted(files.items()):
        p = os.path.normpath(os.path.join(package_dir, rel))
        if not p.startswith(os.path.abspath(package_dir)):
            raise ProvenanceError(f"path escapes package: {rel}")
        if not os.path.isfile(p) or sha256_file(p) != digest:
            raise ProvenanceError(f"digest mismatch: {rel}")
    if not doc.get("sbom") or doc["sbom"] not in files:
        raise ProvenanceError("SBOM missing or not digest-covered")
    if not isinstance(doc.get("provenance"), dict) or not doc["provenance"].get("builder"):
        raise ProvenanceError("provenance statement missing builder")
    signed = False
    if policy.get("require_signature"):
        sig = os.path.join(package_dir, "PROVENANCE.json.sig")
        kid = doc.get("key_id")
        key = (policy.get("trusted_keys") or {}).get(kid)
        if key is None:
            raise ProvenanceError(f"untrusted or missing key id {kid!r}")
        if not os.path.isfile(sig) or not ed25519_verify(key, manifest, sig):
            raise ProvenanceError("signature invalid")
        signed = True
    return {"verified": True, "files": len(files), "signed": signed, "manifest_sha256": hashlib.sha256(raw).hexdigest()}


# ---- MC-18 supported-version matrix -----------------------------------------
MATRIX: dict[str, Any] = {
    "tool_version": TOOL_VERSION,
    "wit_feature_level": WIT_FEATURE_LEVEL,
    "normalization": NORMALIZATION_VERSION,
    "policy": POLICY_VERSION,
    "python": {"supported": ["3.10", "3.11", "3.12", "3.13"], "tested_here": None},
    "reference_toolchain": {"name": "wasm-tools", "pinned": "1.219.1",
                            "sha256_linux_x86_64_tgz": "4b7a764bf421fb33de78a45a94d5d832b29befe3d4977f935db4bdab09b17fd1"},
    "component_model": {"supported": "0.2 (WASI p2 era, sync)", "gated": ["async (future/stream/async func)"],
                        "unsupported": ["error-context", "fixed-size lists (off by default)", "nested namespaces", "named results"]},
    "adjacent": {"INV-09": "portable compute ISA — consumes nothing from INV-11",
                 "INV-10": "composition — consumes PK_INTERFACE_DIFF/1 linkable flag",
                 "INV-12": "language interoperability — consumes PK_INTERFACE/1 exports",
                 "GAP-15": "runtime certification — consumes release evidence bundle"},
    "pk_core": {"distribution": "pk-core", "specifier": ">=4.0,<5", "import": "pk_core",
                "source": "internal estate index (not on PyPI)", "status_here": None},
}


def matrix(python_version: str | None = None) -> dict[str, Any]:
    import platform
    m = json.loads(json.dumps(MATRIX))
    pv = python_version or ".".join(platform.python_version_tuple()[:2])
    m["python"]["tested_here"] = pv
    m["python"]["in_support_range"] = pv in m["python"]["supported"]
    return m


# ---- MC-22 pk_core dependency contract --------------------------------------
def pk_core_status() -> dict[str, Any]:
    """Resolve pk_core against the declared specifier; absence is BLOCKED."""
    import importlib
    import importlib.util
    path = os.environ.get("PK_CORE_PATH")
    found = (importlib.util.find_spec("pk_core") is not None) if not path else os.path.isdir(os.path.join(path, "pk_core"))
    if not found:
        return {"status": "BLOCKED", "reason": "pk_core not importable (declared: pk-core>=4.0,<5 from the estate index; or set PK_CORE_PATH)"}
    try:
        import sys
        if path and path not in sys.path:
            sys.path.insert(0, path)
        mod = importlib.import_module("pk_core")
        ver = getattr(mod, "__version__", None)
    except Exception as exc:  # pragma: no cover - depends on estate
        return {"status": "FAILED", "reason": f"import error: {exc}"}
    ok = ver is not None and ver.split(".")[0] == "4"
    return {"status": "OK" if ok else "FAILED", "version": ver}


# ---- MC-29 structured telemetry --------------------------------------------
class Telemetry:
    """In-process counters + fixed-bucket latency histograms, exportable as a
    Prometheus text snapshot.  No network: an exporter reads `snapshot()`.
    Labels are a closed set so hostile input cannot create cardinality."""
    BUCKETS_MS = (0.1, 0.5, 1, 2, 5, 10, 50, 100, 1000)
    COUNTERS = ("definitions_parsed", "parse_failures", "classifications", "breaking", "additive",
                "compatible", "link_refusals", "limit_breaches", "resolution_failures")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.counters = {c: 0 for c in self.COUNTERS}
        self.hist = {"compare_ms": [0] * (len(self.BUCKETS_MS) + 1), "parse_ms": [0] * (len(self.BUCKETS_MS) + 1)}
        self.sums = {"compare_ms": 0.0, "parse_ms": 0.0}
        self.saturation = 0.0

    def inc(self, name: str, n: int = 1) -> None:
        if name not in self.counters:
            raise KeyError(f"unknown counter {name}")
        with self._lock:
            self.counters[name] += n

    def observe(self, hist: str, ms: float) -> None:
        with self._lock:
            idx = next((i for i, b in enumerate(self.BUCKETS_MS) if ms <= b), len(self.BUCKETS_MS))
            self.hist[hist][idx] += 1
            self.sums[hist] += ms

    def timed(self, hist: str, fn: Callable[..., Any], *a: Any, **kw: Any) -> Any:
        t = time.perf_counter()
        try:
            return fn(*a, **kw)
        finally:
            self.observe(hist, (time.perf_counter() - t) * 1000)

    def prometheus(self) -> str:
        out = []
        for k, v in sorted(self.counters.items()):
            out.append(f"# TYPE inv11_{k}_total counter\ninv11_{k}_total {v}")
        for h, counts in sorted(self.hist.items()):
            out.append(f"# TYPE inv11_{h} histogram")
            cum = 0
            for b, c in zip(list(self.BUCKETS_MS) + ["+Inf"], counts, strict=True):
                cum += c
                out.append(f'inv11_{h}_bucket{{le="{b}"}} {cum}')
            out.append(f"inv11_{h}_sum {self.sums[h]:.6f}\ninv11_{h}_count {cum}")
        out.append(f"inv11_saturation_ratio {self.saturation:.6f}")
        return "\n".join(out) + "\n"


# ---- MC-30 tamper-evident audit events -------------------------------------
class AuditLog:
    """Append-only JSONL hash chain.  Each event carries prev hash; `verify`
    detects edits, deletions and reordering; the head hash must be recorded
    externally to detect tail truncation (documented limitation)."""

    GENESIS = "0" * 64

    def __init__(self, path: str) -> None:
        self.path = path

    def head(self) -> tuple[int, str]:
        n, h = 0, self.GENESIS
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        ev = json.loads(line)
                        n, h = ev["seq"], ev["hash"]
        return n, h

    def append(self, kind: str, subject: str, decision: str, fingerprints: dict[str, str], detail: dict[str, Any] | None = None) -> dict[str, Any]:
        seq, prev = self.head()
        body = {"seq": seq + 1, "prev": prev, "kind": kind, "subject": subject, "decision": decision,
                "fingerprints": fingerprints, "detail": detail or {}, "tool_version": TOOL_VERSION,
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        body["hash"] = hashlib.sha256(canonical_json(body).encode()).hexdigest()
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(canonical_json(body) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return body

    def verify(self, expected_head: str | None = None) -> dict[str, Any]:
        prev, n = self.GENESIS, 0
        with open(self.path, encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                ev = json.loads(line)
                h = ev.pop("hash")
                if ev["prev"] != prev or ev["seq"] != i:
                    return {"ok": False, "at": i, "reason": "chain link broken"}
                if hashlib.sha256(canonical_json(ev).encode()).hexdigest() != h:
                    return {"ok": False, "at": i, "reason": "event hash mismatch"}
                prev, n = h, i
        if expected_head is not None and expected_head != prev:
            return {"ok": False, "at": n, "reason": "head differs from externally recorded head (truncation?)"}
        return {"ok": True, "events": n, "head": prev}


# ---- MC-40 ownership / escalation ------------------------------------------
OWNERSHIP_REQUIRED = ("component", "accountable_owner", "review_cadence_days", "escalation", "end_of_life_policy", "last_reviewed")


def load_ownership(path: str = os.path.join(PKG, "OWNERSHIP.json")) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    missing = [k for k in OWNERSHIP_REQUIRED if not doc.get(k)]
    status = "INCOMPLETE" if missing else "COMPLETE"
    placeholder = [k for k, v in doc.items() if isinstance(v, str) and "UNASSIGNED" in v]
    if placeholder:
        status = "BLOCKED"
    return {"status": status, "missing": missing, "placeholders": placeholder, "doc": doc}
