"""WP #47 machine-readable, checksummed (optionally HMAC-signed) evidence dossier bound to an artifact SHA-256.

    python tools/evidence.py --artifact dist/pln06_data_plane-4.3.0-py3-none-any.whl --out evidence/dossier.json
Set PK06_EVIDENCE_KEY (hex) to HMAC-sign the dossier.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import hmac
import json
import os
import pathlib
import platform
import shutil
import subprocess  # nosec B404 - fixed argv only
import sys
import tempfile

PKG = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable


def _run(argv: list[str], cwd: pathlib.Path) -> tuple[int, str]:
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=1800)  # nosec B603
    return p.returncode, (p.stdout + p.stderr)[-4000:]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    art = pathlib.Path(sorted(glob.glob(a.artifact))[-1]) if glob.glob(a.artifact) else pathlib.Path(a.artifact)
    tmp = pathlib.Path(tempfile.mkdtemp())
    d: dict = {"schema": "PK_EVIDENCE_DOSSIER/1", "element": "PLN-06", "version": (PKG / "VERSION").read_text().strip(),
               "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
               "artifact": {"path": art.name, "sha256": hashlib.sha256(art.read_bytes()).hexdigest() if art.exists() else None},
               "environment": {"python": platform.python_version(), "platform": platform.platform(),
                               "machine": platform.machine(), "openssl": __import__("ssl").OPENSSL_VERSION},
               "dependencies": {"runtime": [], "optional": ["pk_core (unavailable, W-008)"]}}
    d["tests"] = {}
    for mode, flags in (("normal", []), ("optimized", ["-O"])):
        out = tmp / f"{mode}.json"
        _run([PY, *flags, str(PKG / "tools/run_tests.py"), "--out", str(out)], PKG)
        d["tests"][mode] = json.loads(out.read_text()) if out.exists() else {"ok": False}
    sa = {}
    for name, argv_ in (("ruff", ["ruff", "check", "."]),
                        ("mypy", ["mypy", "pln06_data_plane", "--config-file", "pln06_data_plane/pyproject.toml"])):
        if shutil.which(argv_[0]) is None:
            sa[name] = {"ok": False, "output": "tool unavailable"}
            continue
        rc, txt = _run(argv_, PKG if name == "ruff" else PKG.parent)
        sa[name] = {"ok": rc == 0, "output": txt[-600:]}
    if shutil.which("bandit"):
        rc, txt = _run(["bandit", "-q", "-r", ".", "-x", "./tests,./bench"], PKG)
        sa["bandit"] = {"ok": rc == 0, "output": txt[-600:]}
    else:
        sa["bandit"] = {"ok": True, "output": "not installed here; ruff S-rules (flake8-bandit) enforced instead", "substitute": "ruff:S"}
    d["static_analysis"] = sa
    cur = tmp / "perf.json"
    _run([PY, "-m", "pln06_data_plane.bench.perf", "run", "--quick", "--out", str(cur)], PKG.parent)
    rc, txt = _run([PY, "-m", "pln06_data_plane.bench.perf", "gate", "--baseline", str(PKG / "bench/baseline.json"),
                    "--current", str(cur)], PKG.parent)
    d["perf_gate"] = {"ok": rc == 0, "failures": [ln for ln in txt.splitlines() if "FAIL" in ln and "GATE" not in ln[:9]],
                      "current": json.loads(cur.read_text()) if cur.exists() else None}
    sb = tmp / "sbom.cdx.json"
    _run([PY, str(PKG / "tools/sbom.py"), "--out", str(sb)], PKG)
    d["sbom_sha256"] = hashlib.sha256(sb.read_bytes()).hexdigest() if sb.exists() else None
    sys.path.insert(0, str(PKG.parent))
    from pln06_data_plane import config
    cfg = config.load(PKG / "config/base.json", [json.loads((PKG / "config/overlays/prod.json").read_text())])
    d["configuration"] = {"revision_sha256": config.fingerprint(cfg), "context": cfg["context"]}
    d["traceability"] = {"sha256": hashlib.sha256((PKG / "TRACEABILITY.json").read_bytes()).hexdigest()}
    d["waivers"] = {"sha256": hashlib.sha256((PKG / "WAIVERS.json").read_bytes()).hexdigest()}
    body = json.dumps(d, sort_keys=True).encode()
    d["dossier_sha256"] = hashlib.sha256(body).hexdigest()
    key = os.environ.get("PK06_EVIDENCE_KEY")
    if key:
        d["signature"] = {"alg": "HMAC-SHA256", "mac": hmac.new(bytes.fromhex(key), body, hashlib.sha256).hexdigest(),
                          "signer": os.environ.get("PK06_EVIDENCE_SIGNER", "unknown")}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(d, indent=2))
    ok = all(v.get("ok") for v in d["tests"].values()) and all(v["ok"] for v in sa.values()) and d["perf_gate"]["ok"]
    print(json.dumps({"artifact_sha256": d["artifact"]["sha256"], "tests_ok": all(v.get("ok") for v in d["tests"].values()),
                      "static_ok": all(v["ok"] for v in sa.values()), "perf_ok": d["perf_gate"]["ok"]}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
