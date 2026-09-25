"""M28 - fail-closed production release gate with machine-readable evidence.

    python tools/release_gate.py [--out evidence/RELEASE_GATE.json] [--quick] [--self-test]

Exit codes: 0 GO · 1 FAIL (a technical lane failed) · 3 NO_GO (lanes pass but
human/external blockers remain).  The verdict is computed by the pure
function ``evaluate``; ``--self-test`` is the falsifier proving that a GO is
impossible while any blocker or failing lane exists.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable


def _run(name: str, args: list[str], cwd: pathlib.Path, timeout: int = 1800) -> dict:
    started = time.time()
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        ok, tail = p.returncode == 0, (p.stdout + p.stderr).strip().splitlines()[-3:]
    except subprocess.TimeoutExpired:
        ok, tail = False, ["timeout"]
    return {"lane": name, "status": "PASS" if ok else "FAIL", "seconds": round(time.time() - started, 1), "tail": tail}


def lanes(quick: bool) -> list[dict]:
    tests = str(ROOT / "tests")
    out = [
        _run("compileall", [PY, "-m", "compileall", "-q", str(ROOT)], ROOT),
        _run("unit+integration", [PY, "-m", "unittest", "discover", "-s", tests], ROOT),
        _run("unit+integration (-O)", [PY, "-O", "-m", "unittest", "discover", "-s", tests], ROOT),
        _run("error-doc drift", [PY, "tools/gen_error_doc.py", "--check"], ROOT),
        _run("rtm", [PY, "tools/rtm.py", "--check"], ROOT),
        _run("deps (stdlib-only)", [PY, "tools/sbom.py", "--check-imports"], ROOT),
        _run("fuzz", [PY, "tools/fuzz.py", "--iterations", "500" if quick else "5000", "--seed", "20260923"], ROOT),
        _run("perf gate (PROPOSED thresholds)", [PY, "tools/perf.py", "--mode", "quick", "--seconds", "3", "--gate"], ROOT),
    ]
    return out


def blockers() -> list[str]:
    b = []
    owners = json.loads((ROOT / "ops" / "OWNERS.json").read_text())
    if any(v == "UNASSIGNED" or v == ["UNASSIGNED"] for k, v in owners.items() if k not in ("schema", "component", "note")):
        b.append("M32: owner / security reviewer / on-call UNASSIGNED (ops/OWNERS.json)")
    waivers = json.loads((ROOT / "ops" / "WAIVERS.json").read_text())["waivers"]
    pending = [w["id"] for w in waivers if w["status"] != "APPROVED" or not w.get("approved_by")]
    if pending:
        b.append(f"M33: waivers not approved: {', '.join(pending)}")
    rtm = json.loads((ROOT / "traceability" / "rtm.json").read_text())
    blocked = [i["id"] for i in rtm["items"] if i["status"] == "BLOCKED"]
    if blocked:
        b.append(f"RTM items BLOCKED: {', '.join(blocked)}")
    partial_unwaived = [i["id"] for i in rtm["items"] if i["status"] == "PARTIAL"
                        and not any(i["id"] in w["items"] and w["status"] == "APPROVED" for w in waivers)]
    if partial_unwaived:
        b.append(f"RTM items PARTIAL without an approved waiver: {', '.join(partial_unwaived)}")
    for name, path in (("M22 perf thresholds", "ops/PERF_THRESHOLDS.json"), ("M44 SLO", "ops/SLO.json")):
        if json.loads((ROOT / path).read_text()).get("status") != "APPROVED":
            b.append(f"{name} not APPROVED ({path})")
    if "Status: APPROVED" not in (ROOT / "docs" / "ADR-0001-execution-tier-semantics.md").read_text():
        b.append("M41: ADR-0001 not APPROVED")
    if not (ROOT / "LICENSE").exists():
        b.append("M47: no LICENSE declared by the owner")
    gate = ROOT / "conformance" / "PK_GATE_RESULTS.json"
    if not gate.exists():
        b.append("M02/M48: no pk_core gate result (conformance/PK_GATE_RESULTS.json)")
    if "Status: APPROVED" not in (ROOT / "MASTER.md").read_text():
        b.append("M01: replacement MASTER.md not APPROVED")
    b.append("release approval: no signed human release approval recorded (the gate never mints one)")
    return b


def evaluate(lane_results: list[dict], blocker_list: list[str]) -> str:
    if not lane_results or any(l["status"] != "PASS" for l in lane_results):
        return "FAIL"
    return "NO_GO" if blocker_list else "GO"


def self_test() -> None:
    ok = [{"lane": "x", "status": "PASS"}]
    assert evaluate(ok, []) == "GO"
    assert evaluate(ok, ["anything"]) == "NO_GO"
    assert evaluate([{"lane": "x", "status": "FAIL"}], []) == "FAIL"
    assert evaluate([], []) == "FAIL"
    assert evaluate(ok, blockers()) == "NO_GO", "falsifier: current tree must not be GO"
    print("release gate self-test: PASS")


def main() -> int:
    if "--self-test" in sys.argv:
        self_test()
        return 0
    sys.path.insert(0, str(ROOT / "tools"))
    from build_info import build_info  # noqa: E402
    results = lanes("--quick" in sys.argv)
    bl = blockers()
    verdict = evaluate(results, bl)
    evidence = {"schema": "PK_PLN04_RELEASE_GATE/1", "generated_ns": time.time_ns(), "build": build_info(),
                "verdict": verdict, "lanes": results, "blockers": bl,
                "declared_skip_lanes": ["pk_core certification tests (tests/test_component.py) - M02",
                                        "real wasmtime lane (tests/test_units.py) - wasmtime not installed"]}
    out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else ROOT / "evidence" / "RELEASE_GATE.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2))
    print(json.dumps({"verdict": verdict, "lanes": {l["lane"]: l["status"] for l in results}, "blockers": bl}, indent=2))
    return {"GO": 0, "FAIL": 1, "NO_GO": 3}[verdict]


if __name__ == "__main__":
    sys.exit(main())
