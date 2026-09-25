"""Security-control mutation harness (Section 9 threat-coverage verification).

Each mutant disables one control in a scratch copy of the package and runs the
security suites against it.  A mutant that *survives* (all tests still pass)
proves a vacuous test and fails this tool.  Output: evidence/mutation.json.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
SUITES = ["test_primitives.py", "test_contracts.py", "test_properties.py", "test_subsystems.py", "test_races.py"]

# (id, threat, file, original, replacement)
MUTANTS = [
    ("M01", "T-FORGE", "capabilities.py", "if _guard is not _MINT_GUARD:\n            raise Forged(\"Reference objects",
     "if False:\n            raise Forged(\"Reference objects"),
    ("M02", "T-FORGE", "capabilities.py", "if not hmac.compare_digest(self._signature, expected):", "if False:"),
    ("M03", "T-WIDEN", "capabilities.py", "if not requested <= self._operations:", "if False:"),
    ("M04", "T-WIDEN", "capabilities.py", "if not requested <= allowed:", "if False:"),
    ("M05", "T-XAUTH", "capabilities.py",
     "if self._authority_id != authority_id or not hmac.compare_digest(self._authority_seal, authority_seal):",
     "if self._authority_id != authority_id:"),
    ("M06", "T-REVOKE", "capabilities.py", "            if self._revoked:\n                raise Revoked(f\"{resource}:",
     "            if False:\n                raise Revoked(f\"{resource}:"),
    ("M07", "T-REVOKE", "capabilities.py", "    for membrane in membranes:\n        membrane._register(reference)",
     "    for membrane in membranes[:1]:\n        membrane._register(reference)"),
    ("M08", "T-LEAK", "capabilities.py", "token='<redacted>'", "token={self._token!r}"),
    # M09: strip every serialization guard from Reference (removing only one is an equivalent mutant: the
    # guards are layered, which the first run of this harness showed when M09b survived).
    ("M09", "T-SERIAL", "capabilities.py",
     "    def __reduce__(self):\n        raise TypeError(\"capability references are process-local and intentionally non-serializable\")\n\n"
     "    __reduce_ex__ = _no_serialize\n    __copy__ = _no_serialize\n    __deepcopy__ = _no_serialize\n\n    def __repr__(self) -> str:\n        return (",
     "    def __repr__(self) -> str:\n        return ("),
    ("M10", "T-DOS", "capabilities.py", "if len(chain) > MAX_MEMBRANE_DEPTH:", "if False:"),
    ("M11", "T-INPUT", "capabilities.py", "if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):", "if False:"),
    ("M12", "T-AUDIT", "audit.py", "errors.append(f\"#{n}: prev link broken (deleted/reordered)\")", "pass"),
    ("M13", "T-AUDIT", "audit.py", "if not hmac.compare_digest(mac, str(event.get(\"mac\"))):", "if False:"),
    ("M14", "T-CFG", "config.py", "if not hmac.compare_digest(expected, str(sig.get(\"mac\"))):", "if False:"),
    ("M15", "T-CFG", "config.py", "if self._active is not None and cfg[\"config_version\"] <= self._active.config[\"config_version\"]:", "if False:"),
    ("M16", "T-REPLAY", "identity.py", "if claims[\"nonce\"] in self._seen_nonces:", "if False:"),
    ("M17", "T-AUTHN", "identity.py", "if aud != self.audience:", "if False:"),
    ("M18", "T-AUDIT", "broker.py", "            if raised is None:\n                raised = Degraded(\"audit unavailable; action denied\")",
     "            if False:\n                raised = Degraded(\"audit unavailable; action denied\")"),
    ("M19", "T-LEAK", "telemetry.py", "(\"<redacted>\" if k.lower() in REDACT_KEYS else redact(v))", "redact(v)"),
    ("M20", "T-RETRY", "resilience.py", "            else:\n                raise\n        except retry_on", "            else:\n                last = exc\n        except retry_on"),
]


def run_mutant(mid, file, old, new):
    with tempfile.TemporaryDirectory() as td:
        dst = pathlib.Path(td) / PKG.name
        shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns("__pycache__", "evidence", "dist"))
        target = dst / file
        src = target.read_text()
        if src.count(old) != 1:
            return {"id": mid, "status": "INVALID", "detail": f"anchor found {src.count(old)} times"}
        target.write_text(src.replace(old, new))
        killed_by = []
        for suite in SUITES:
            p = subprocess.run([sys.executable, "-B", suite], cwd=dst / "tests", capture_output=True, text=True,
                               timeout=600, env={"INV41_ITER": "120", "INV41_RACE_ROUNDS": "8", "PATH": "/usr/bin:/bin"})
            if p.returncode != 0:
                killed_by.append(suite)
        return {"id": mid, "status": "KILLED" if killed_by else "SURVIVED", "killed_by": killed_by}


def main() -> int:
    t0 = time.time()
    results = []
    for mid, threat, file, old, new in MUTANTS:
        r = run_mutant(mid, file, old, new)
        r.update(threat=threat, file=file)
        results.append(r)
        print(mid, threat, r["status"], r.get("killed_by", r.get("detail")), flush=True)
    out = {"schema": "INV41_MUTATION/1", "mutants": len(results),
           "killed": sum(r["status"] == "KILLED" for r in results),
           "survived": [r["id"] for r in results if r["status"] == "SURVIVED"],
           "invalid": [r["id"] for r in results if r["status"] == "INVALID"],
           "duration_s": round(time.time() - t0, 1), "results": results}
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "mutation.json").write_text(json.dumps(out, indent=1))
    return 0 if not out["survived"] and not out["invalid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
