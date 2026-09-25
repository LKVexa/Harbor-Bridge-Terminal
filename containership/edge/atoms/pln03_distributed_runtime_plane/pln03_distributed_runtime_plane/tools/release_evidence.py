"""Build the machine-readable release-evidence bundle (MC-048).

Runs every suite, the structural audit, the bench gate and the SBOM check; hashes every
source file; writes evidence/EVIDENCE.json + evidence/SHA256SUMS.  If PK_EVIDENCE_KEY is set
the bundle is HMAC-sealed, otherwise it is explicitly marked UNSEALED.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import pathlib
import platform
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(args: list[str], env=None) -> dict:
    t = time.time()
    p = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    tail = (p.stdout + p.stderr).strip().splitlines()[-6:]
    return {"cmd": " ".join(args), "rc": p.returncode, "seconds": round(time.time() - t, 2), "tail": tail,
            "stdout": p.stdout}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence")
    a = ap.parse_args(argv)
    out = ROOT / a.out
    out.mkdir(exist_ok=True)
    steps = {
        "unit_contract_fault_governance": run(["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-t", "tests"]),
        "optimised_mode": run(["-O", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-t", "tests"]),
        "structural_audit": run(["audit_repository.py"]),
        "bench_gate": run(["tools/bench.py", "--n", "20000", "--out", str(out / "bench.json")]),
        "sbom_check": run(["tools/sbom.py", "--check"]),
    }
    audit = json.loads(steps["structural_audit"]["stdout"] or "{}")
    for s in steps.values():
        s.pop("stdout")
    hashes = {}
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and rel.parts[0] not in {a.out, "__pycache__"} and "__pycache__" not in rel.parts:
            hashes[str(rel).replace("\\", "/")] = hashlib.sha256(p.read_bytes()).hexdigest()
    tree = hashlib.sha256("".join(f"{k}:{v}\n" for k, v in hashes.items()).encode()).hexdigest()
    bundle = {
        "schema": "pk.release-evidence/1", "component": "PLN-03", "version": (ROOT / "VERSION").read_text().strip(),
        "source_tree_sha256": tree, "config_digest": None,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "machine": platform.machine()},
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gates": {k: {"rc": v["rc"], "passed": v["rc"] == 0, "seconds": v["seconds"], "tail": v["tail"]}
                  for k, v in steps.items()},
        "all_gates_passed": all(v["rc"] == 0 for v in steps.values()),
        "release_ready": audit.get("release_ready", False),
        "release_blockers": audit.get("release_blockers", []),
        "pk_core_conformance": "NOT_RUN (pk_core unpinned, MC-055)",
        "file_count": len(hashes),
    }
    from importlib import import_module
    sys.path.insert(0, str(ROOT.parent))
    cfg = import_module("pln03_distributed_runtime_plane.config")
    bundle["config_digest"] = cfg.digest(cfg.DEFAULT)
    raw = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
    key = os.environ.get("PK_EVIDENCE_KEY")
    bundle["seal"] = hmac.new(key.encode(), raw, hashlib.sha256).hexdigest() if key else "UNSEALED"
    (out / "EVIDENCE.json").write_text(json.dumps(bundle, indent=2) + "\n")
    (out / "SHA256SUMS").write_text("".join(f"{v}  {k}\n" for k, v in hashes.items()))
    print(json.dumps({k: bundle[k] for k in ("version", "all_gates_passed", "release_ready", "source_tree_sha256",
                                             "seal")}, indent=2))
    return 0 if bundle["all_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
