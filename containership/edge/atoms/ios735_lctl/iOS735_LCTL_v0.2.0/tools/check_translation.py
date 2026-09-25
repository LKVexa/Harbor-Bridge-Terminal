#!/usr/bin/env python3
"""Independently back-check canonical LCTL and the translation map against the Swift skeleton.

The checker does not import translate.py. Expected values are re-derived from Swift source,
Evidence/components.json, Evidence/control-ledger.json, and Golden.swift.

  python tools/check_translation.py
  python tools/check_translation.py --falsify
  python tools/check_translation.py --canonical-dir PATH --source-dir PATH --map PATH
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
DEFAULT_SK = PKG / "input" / "iOS735_Skeleton"
PROJECT_COMPONENTS = 735
PROJECT_PHASES = 43
CONTROLS_PER_COMPONENT = 25

EVIDENCE = {
    "SKELETON_DECLARED": "skeletonDeclared",
    "NEEDS_DEVICE_RUN": "deviceRun",
    "NEEDS_HUMAN_REVIEW": "humanReview",
    "NEEDS_PRODUCT_DECISION": "productDecision",
    "NEEDS_CI_RUN": "ciRun",
}
FAMILY_OP = {
    "general": "CHECKPOINT_SCOPE",
    "mlModel": "TENSOR",
    "visualStates": "DEVICE",
    "trustBoundary": "FAILURE_DOMAIN",
    "voiceOver": "DEVICE",
    "capabilityDetection": "DEVICE",
    "dataModel": "MEMORY_DOMAIN",
    "locationAuthorization": "DEVICE",
    "reproducibleBuild": "SCHEDULE_SEAL",
    "wireContract": "CLASSICAL_CHANNEL",
    "syncMerge": "CONSISTENCY_SCOPE",
    "renderBudget": "CAPACITY",
    "backgroundMode": "TIMEOUT",
    "analyticsMinimization": "MESSAGE",
    "testOwnership": "CHECKPOINT",
    "pushPayload": "MESSAGE",
    "mediaSession": "DEVICE",
    "storeKitTruth": "CONSISTENCY_SCOPE",
    "localeFormatting": "DOMAIN",
    "documentationOwnership": "PERSISTENT",
}
COLS = [
    "ROW", "FACE", "LANE", "QSPACE", "OP", "OUT", "CTRL", "A", "B", "PARAM",
    "TYPE", "BASIS", "REGIME", "ASSUME", "ERROR", "RESOURCE", "CONF", "PROOF",
]


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "none"


def _require_match(pattern: str, text: str, label: str):
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f"cannot parse {label}")
    return m


def swift_runtime(sk: Path):
    src = (sk / "Sources/ComponentKit/Runtime.swift").read_text(encoding="utf-8")
    enum_body = _require_match(r"public enum LifecycleState:[^{]+\{([^}]*)\}", src, "LifecycleState").group(1)
    groups = re.findall(r"\bcase\s+([^\n]+)", enum_body)
    lifecycle = [name.strip() for group in groups for name in group.split(",")]
    lifecycle = [name for name in lifecycle if re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name)]
    body = src.split("transitions: [LifecycleState: Set<LifecycleState>] = [", 1)[1].split("\n    ]", 1)[0]
    transitions = {m[0]: re.findall(r"\.(\w+)", m[1]) for m in re.findall(r"\.(\w+): \[([^\]]*)\]", body)}
    body = src.split("public static func classify", 1)[1].split("\n    }", 1)[0]
    error_list = []
    for codes, dom, disp in re.findall(r"case ([^:]+): return \(\.(\w+), \.(\w+)\)", body):
        error_list.extend((code, dom, disp) for code in re.findall(r"\.(\w+)", codes))
    if len(lifecycle) != 9 or len(transitions) != 9 or len(error_list) != 10:
        raise ValueError(
            f"could not read ComponentKit runtime tables ({len(lifecycle)} states, "
            f"{len(transitions)} transition rows, {len(error_list)} error codes)"
        )
    return lifecycle, transitions, error_list


def golden_contracts(sk: Path):
    g = sk / "Tests/VEC1BridgeTests/Golden.swift"
    return dict(re.findall(r'"(C\d{4}\w*)": "([0-9a-f]{64})"', g.read_text(encoding="utf-8"))) if g.exists() else {}


def contract_sha(c):
    rec = {
        "schema": "IOS735/COMPONENT_CONTRACT/1",
        "component": int(c["n"]),
        "type": c["type"],
        "name": c["name"],
        "phase": int(c["phase"]),
        "phase_name": c["phase_name"],
        "layer": c["layer"],
        "family": int(c["family"]),
        "frameworks": list(c["frameworks"]),
        "capabilities": list(c["capabilities"]),
        "donors": list(c["donors"]),
        "user_visible": bool(c["visible"]),
    }
    encoded = json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def expected(sk: Path):
    comps = json.loads((sk / "Evidence/components.json").read_text(encoding="utf-8"))
    ledger = json.loads((sk / "Evidence/control-ledger.json").read_text(encoding="utf-8"))
    if len(comps) != PROJECT_COMPONENTS or len(ledger) != PROJECT_COMPONENTS * CONTROLS_PER_COMPONENT:
        raise ValueError(f"unexpected skeleton size: {len(comps)} components, {len(ledger)} controls")
    by = {}
    for row in ledger:
        by.setdefault(row["component"], []).append(row)
    out = {}
    for c in comps:
        n = c["n"]
        if n in out:
            raise ValueError(f"duplicate component C{n:04d}")
        src_path = sk / "Sources" / c["module"] / (c["type"] + ".swift")
        src = src_path.read_text(encoding="utf-8")
        budgets = re.findall(r'QualityBudget\(metric: "([^"]*)", unit: "([^"]*)", limit: ([0-9.]+)\)', src)
        hw_raw = _require_match(r"requiresHardware: \[([^\]]*)\]", src, f"C{n:04d} requiresHardware").group(1)
        cap_raw = _require_match(r"capabilities: \[([^\]]*)\]", src, f"C{n:04d} capabilities").group(1)
        fallback = _require_match(r'fallback: "((?:[^"\\]|\\.)*)"', src, f"C{n:04d} fallback").group(1)
        family = _require_match(r"\bfamily:\s*\.(\w+)", src, f"C{n:04d} family").group(1)
        hardware = [h.strip().lstrip(".") for h in hw_raw.split(",") if h.strip()]
        capabilities = [x.strip().lstrip(".") for x in cap_raw.split(",") if x.strip()]
        controls = sorted(by.get(n, []), key=lambda r: r["control"])
        expected_controls = [f"{n}.{i:02d}" for i in range(1, CONTROLS_PER_COMPONENT + 1)]
        if [r["control"] for r in controls] != expected_controls:
            raise ValueError(f"C{n:04d}: control ledger does not contain exactly x.01..x.25")
        if capabilities != list(c["capabilities"]):
            raise ValueError(f"C{n:04d}: capabilities differ between Swift and components.json")
        unit = f"P{c['phase']:02d}_{slug(c['phase_name']).replace('-', '_')}.lctlc"
        out[n] = {
            "type": c["type"],
            "name": c["name"],
            "phase": c["phase"],
            "phase_name": c["phase_name"],
            "layer": c["layer"],
            "family": family,
            "budgets": budgets,
            "hardware": hardware,
            "fallback": fallback,
            "capabilities": capabilities,
            "controls": controls,
            "visible": c["visible"],
            "record": c,
            "unit": unit,
        }
    if set(out) != set(range(1, PROJECT_COMPONENTS + 1)):
        raise ValueError("component IDs must be exactly 1..735")
    return out


def parse_canonical(path: Path):
    rows = []
    in_tuple = False
    seen_rows = set()
    text = path.read_text(encoding="utf-8")
    if not text.startswith("LCTL/1.3\n"):
        raise ValueError(f"{path.name}: missing LCTL/1.3 header")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line == "QTUPLE/1.0":
            if in_tuple:
                raise ValueError(f"{path.name}:{lineno}: nested QTUPLE")
            in_tuple = True
            continue
        if line == "END QTUPLE":
            if not in_tuple:
                raise ValueError(f"{path.name}:{lineno}: END QTUPLE without QTUPLE")
            in_tuple = False
            continue
        if not in_tuple or not line.startswith("("):
            continue
        if not line.endswith(")") or line.count("¦") != 17:
            raise ValueError(f"{path.name}:{lineno}: malformed canonical row")
        cells = [x.strip() for x in line[1:-1].split("¦")]
        if len(cells) != len(COLS):
            raise ValueError(f"{path.name}:{lineno}: expected {len(COLS)} cells, found {len(cells)}")
        row = dict(zip(COLS, cells))
        if row["ROW"] in seen_rows:
            raise ValueError(f"{path.name}:{lineno}: duplicate row ID {row['ROW']}")
        seen_rows.add(row["ROW"])
        rows.append(row)
    if in_tuple:
        raise ValueError(f"{path.name}: unterminated QTUPLE")
    if not rows:
        raise ValueError(f"{path.name}: no canonical rows")
    return rows


def kv(param: str):
    out = {}
    for part in param.split(";"):
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"malformed key/value parameter {param!r}")
        key, value = part.split("=", 1)
        if key in out:
            raise ValueError(f"duplicate parameter key {key!r}")
        out[key] = value
    return out


def _int(value, default=-1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _numeric_rows(idx, pattern):
    found = []
    rx = re.compile(pattern)
    for key, row in idx.items():
        m = rx.fullmatch(key)
        if m:
            found.append((int(m.group(1)), row))
    return [row for _, row in sorted(found)]


def check(units, exp, lifecycle, transitions, error_list, golden, source_dir: Path):
    errors = []
    E = errors.append
    expected_units = {Path(x["unit"]).stem for x in exp.values()} | {"IOS735_APP"}
    actual_units = set(units)
    if actual_units != expected_units:
        missing = sorted(expected_units - actual_units)
        extra = sorted(actual_units - expected_units)
        E(f"canonical unit set mismatch: missing={missing[:5]} extra={extra[:5]}")

    errmap = {code: (domain, disp) for code, domain, disp in error_list}
    seen = {}
    boot = []
    for uname, rows in units.items():
        if uname == "IOS735_APP":
            continue
        idx = {r["ROW"]: r for r in rows}
        for r in rows:
            m = re.fullmatch(r"K(\d{4})R", r["ROW"])
            if not m:
                continue
            n = int(m.group(1))
            K = f"K{n:04d}"
            C = f"C{n:04d}"
            if n in seen:
                E(f"{C} translated twice ({seen[n]}, {uname})")
            seen[n] = uname
            x = exp.get(n)
            if not x:
                E(f"{C} not in skeleton")
                continue
            if uname != Path(x["unit"]).stem:
                E(f"{C} is in {uname}, expected {Path(x['unit']).stem}")
            try:
                p = kv(r["PARAM"])
            except ValueError as exc:
                E(f"{C} region parameters malformed: {exc}")
                continue
            status_counts = Counter(c["status"] for c in x["controls"])
            status = ",".join(f"{k.lower()}:{v}" for k, v in sorted(status_counts.items()))
            expected_region = {
                "name": x["type"], "component": str(n), "phase": str(x["phase"]), "layer": slug(x["layer"]),
                "family": x["family"], "visible": str(x["visible"]).lower(), "owner": "UNASSIGNED",
                "controls": str(CONTROLS_PER_COMPONENT),
                "complete": str(sum(1 for c in x["controls"] if c["complete"])), "status": status,
            }
            if r["OP"] != "REGION" or p != expected_region:
                E(f"{C} region metadata differs from skeleton/control ledger")
            sha = contract_sha(x["record"])
            if r["PROOF"] != f"ios735:contract:{sha}":
                E(f"{C} contract hash mismatch")
            if golden and golden.get(x["type"]) != sha:
                E(f"{C} contract hash differs from Golden.swift")

            state_of = {}
            for i, state in enumerate(lifecycle):
                ev = idx.get(f"{K}E{i}")
                if not ev or ev["OP"] != "EVENT":
                    E(f"{C} missing lifecycle event {i}")
                    continue
                try:
                    ep = kv(ev["PARAM"])
                except ValueError as exc:
                    E(f"{C} lifecycle event {i} malformed: {exc}")
                    continue
                if ep != {"id": f"{C}.{state}", "kind": "lifecycle"}:
                    E(f"{C} lifecycle event {i} metadata mismatch")
                state_of[ev["ROW"]] = state
            dep = idx.get(f"{K}L")
            got = set()
            if not dep or dep["OP"] != "DEPENDENCY":
                E(f"{C} lifecycle dependency row missing/wrong op")
            else:
                try:
                    for edge in dep["PARAM"].split(";"):
                        a, b = edge.split("->", 1)
                        got.add((state_of.get(a), state_of.get(b)))
                except ValueError:
                    E(f"{C} lifecycle dependency encoding malformed")
            want = {(a, b) for a, bs in transitions.items() for b in bs}
            if got != want:
                E(f"{C} lifecycle edges differ from Runtime.swift: missing {sorted(want - got)[:3]} extra {sorted(got - want)[:3]}")

            fd = idx.get(f"{K}X")
            gotm = {}
            if not fd or fd["OP"] != "FAILURE_DOMAIN":
                E(f"{C} failure-domain row missing/wrong op")
            else:
                try:
                    for item in fd["PARAM"].split(","):
                        code, dd = item.split(":", 1)
                        domain, disp = dd.split("/", 1)
                        gotm[code] = (domain, disp)
                except ValueError:
                    E(f"{C} failure-domain encoding malformed")
            if gotm != errmap:
                E(f"{C} error map differs from ComponentError.classify")

            mem = idx.get(f"{K}M")
            try:
                mp = kv(mem["PARAM"]) if mem else {}
            except ValueError:
                mp = {}
            if not mem or mem["OP"] != "MEMORY_DOMAIN" or mp != {
                "name": f"{C}.state", "owner": "UNASSIGNED", "source_of_truth": "product-decision"
            }:
                E(f"{C} state memory-domain metadata mismatch")

            bud_rows = _numeric_rows(idx, fr"{K}B(\d+)")
            got_budgets = []
            for br in bud_rows:
                try:
                    bp = kv(br["PARAM"])
                except ValueError:
                    bp = {}
                if br["OP"] != "CAPACITY" or bp.get("approval") != "proposed":
                    E(f"{C} budget row has wrong op/approval")
                got_budgets.append((bp.get("metric"), bp.get("unit"), bp.get("limit")))
            want_budgets = [(slug(m), slug(u), limit) for m, u, limit in x["budgets"]]
            if got_budgets != want_budgets:
                E(f"{C} budgets differ from Swift")

            cap_rows = _numeric_rows(idx, fr"{K}P(\d+)")
            got_caps = []
            for cr in cap_rows:
                try:
                    cp = kv(cr["PARAM"])
                except ValueError:
                    cp = {}
                if cr["OP"] != "DEVICE" or cp.get("gate") != "declared-and-justified-before-request":
                    E(f"{C} capability gate metadata mismatch")
                got_caps.append(cp.get("capability"))
            if got_caps != x["capabilities"]:
                E(f"{C} capabilities differ from Swift")

            hw_rows = _numeric_rows(idx, fr"{K}H(\d+)")
            got_hw = []
            for hr in hw_rows:
                try:
                    hp = kv(hr["PARAM"])
                except ValueError:
                    hp = {}
                if hr["OP"] != "DEVICE" or hp.get("fallback") != slug(x["fallback"]):
                    E(f"{C} hardware fallback metadata mismatch")
                got_hw.append(hp.get("hardware"))
            if got_hw != x["hardware"]:
                E(f"{C} hardware differs from Swift")

            expected_op = FAMILY_OP.get(x["family"])
            if expected_op is None:
                E(f"{C} unknown family {x['family']!r}")
            for ctl in x["controls"][20:]:
                k = ctl["control"].split(".")[1]
                q = idx.get(f"{K}Q{k}")
                if not q:
                    E(f"{C} clause x.{k} missing")
                    continue
                try:
                    qp = kv(q["PARAM"])
                except ValueError:
                    qp = {}
                expected_clause = {
                    "clause": f"x.{k}", "family": x["family"], "evidence": EVIDENCE.get(ctl["status"]),
                    "statement_sha256": hashlib.sha256(ctl["text"].encode("utf-8")).hexdigest()[:16],
                }
                if q["OP"] != expected_op or qp != expected_clause:
                    E(f"{C} clause x.{k} differs from the control ledger/family mapping")

            future = idx.get(f"{K}F")
            if future and future["OP"] == "FUTURE":
                try:
                    fp = kv(future["PARAM"])
                except ValueError:
                    fp = {}
                if fp.get("id") != f"boot.{C}" or "awaits" not in fp:
                    E(f"{C} boot future metadata mismatch")
                else:
                    boot.append((x["phase"], n, fp["awaits"]))
            else:
                E(f"{C} boot future missing/wrong op")

    missing = sorted(set(exp) - set(seen))
    if missing:
        E(f"components not translated: {missing[:10]}")
    extra = sorted(set(seen) - set(exp))
    if extra:
        E(f"unexpected translated components: {extra[:10]}")
    if len(seen) != PROJECT_COMPONENTS:
        E(f"translated component count {len(seen)} != {PROJECT_COMPONENTS}")

    boot.sort()
    for i, (phase, n, awaits) in enumerate(boot):
        want = f"P{phase:02d}.start" if i == 0 or boot[i - 1][0] != phase else f"C{boot[i - 1][1]:04d}.active"
        if awaits != want:
            E(f"C{n:04d} boot future awaits {awaits}, expected {want}")

    app_rows = units.get("IOS735_APP", [])
    app = {r["ROW"]: r for r in app_rows}
    a1 = app.get("A0001")
    try:
        a1p = kv(a1["PARAM"]) if a1 else {}
    except ValueError:
        a1p = {}
    complete_total = sum(c["complete"] for x in exp.values() for c in x["controls"])
    if not a1 or a1["OP"] != "REGION" or a1p != {
        "name": "ios735.app", "phases": str(PROJECT_PHASES), "components": str(PROJECT_COMPONENTS),
        "controls": str(PROJECT_COMPONENTS * CONTROLS_PER_COMPONENT), "complete": str(complete_total),
    }:
        E("app: application region metadata mismatch")
    a2 = app.get("A0002")
    try:
        a2p = kv(a2["PARAM"]) if a2 else {}
    except ValueError:
        a2p = {}
    if not a2 or a2["OP"] != "EVENT" or a2p != {"id": "app.launch", "kind": "application"}:
        E("app: launch event mismatch")

    for phase in range(1, PROJECT_PHASES + 1):
        phase_comps = [x for _, x in sorted(exp.items()) if x["phase"] == phase]
        if not phase_comps:
            E(f"app: phase {phase} has no components")
            continue
        unit_name = phase_comps[0]["unit"]
        module = f"ios735.p{phase:02d}.{slug(phase_comps[0]['phase_name']).replace('-', '_')}"
        first_n = min(n for n, x in exp.items() if x["phase"] == phase)
        last_n = max(n for n, x in exp.items() if x["phase"] == phase)
        reg = app.get(f"M{phase:02d}R")
        try:
            rp = kv(reg["PARAM"]) if reg else {}
        except ValueError:
            rp = {}
        expected_rp = {
            "name": module, "phase": str(phase), "components": str(len(phase_comps)),
            "first": f"C{first_n:04d}", "last": f"C{last_n:04d}",
        }
        if not reg or reg["OP"] != "REGION" or rp != expected_rp:
            E(f"app: phase {phase} region metadata mismatch")
        unit_file = source_dir / unit_name
        if not unit_file.is_file():
            E(f"app: missing source/{unit_name}")
        elif reg and reg["PROOF"] != f"ios735:phase-unit:{hashlib.sha256(unit_file.read_bytes()).hexdigest()}":
            E(f"app: phase {phase} unit seal does not match source/{unit_name}")
        start = app.get(f"M{phase:02d}S")
        end = app.get(f"M{phase:02d}E")
        try:
            sp = kv(start["PARAM"]) if start else {}
            ep = kv(end["PARAM"]) if end else {}
        except ValueError:
            sp, ep = {}, {}
        if not start or start["OP"] != "EVENT" or sp != {"id": f"P{phase:02d}.start", "kind": "phase"}:
            E(f"app: phase {phase} start event mismatch")
        if not end or end["OP"] != "EVENT" or ep != {
            "id": f"P{phase:02d}.end", "kind": "phase", "equals": f"C{last_n:04d}.active"
        }:
            E(f"app: phase {phase} end event mismatch")
        dep = app.get(f"M{phase:02d}D")
        prev = "A0002" if phase == 1 else f"M{phase - 1:02d}E"
        expected_edges = {f"M{phase:02d}S->M{phase:02d}E", f"{prev}->M{phase:02d}S"}
        got_edges = set(dep["PARAM"].split(";")) if dep else set()
        if not dep or dep["OP"] != "DEPENDENCY" or got_edges != expected_edges:
            E(f"app: phase {phase} dependency chain mismatch")
    return errors, len(seen)


def check_map(map_data, exp, lifecycle, transitions, error_list, source_dir: Path):
    errors = []
    E = errors.append
    if map_data.get("schema") != "IOS735_LCTL/MAP/1":
        E("map: schema mismatch")
    if map_data.get("lifecycle") != lifecycle:
        E("map: lifecycle order differs from Runtime.swift")
    if map_data.get("transitions") != transitions:
        E("map: transitions differ from Runtime.swift")
    if map_data.get("error_map") != [list(x) for x in error_list]:
        E("map: error_map differs from Runtime.swift")
    if map_data.get("family_op") != FAMILY_OP:
        E("map: family_op mapping mismatch")

    expected_phases = []
    for phase in range(1, PROJECT_PHASES + 1):
        items = [(n, x) for n, x in sorted(exp.items()) if x["phase"] == phase]
        if not items:
            continue
        first_n, first_x = items[0]
        last_n, _ = items[-1]
        unit = first_x["unit"]
        unit_path = source_dir / unit
        sha = hashlib.sha256(unit_path.read_bytes()).hexdigest() if unit_path.is_file() else None
        expected_phases.append({
            "phase": phase,
            "module": f"ios735.p{phase:02d}.{slug(first_x['phase_name']).replace('-', '_')}",
            "file": unit,
            "count": len(items),
            "first": f"C{first_n:04d}",
            "last": f"C{last_n:04d}",
            "end": f"C{last_n:04d}.active",
            "sha": sha,
        })
    if map_data.get("phases") != expected_phases:
        E("map: phase records/source hashes mismatch")

    expected_components = []
    for n, x in sorted(exp.items()):
        expected_components.append({
            "component": n,
            "type": x["type"],
            "name": x["name"],
            "phase": x["phase"],
            "unit": x["unit"],
            "frame_rows_prefix": f"K{n:04d}",
            "contract_sha256": contract_sha(x["record"]),
            "family": x["family"],
            "clause_op": FAMILY_OP.get(x["family"]),
            "budgets": [{"metric": m, "unit": u, "limit": limit} for m, u, limit in x["budgets"]],
            "capabilities": x["capabilities"],
            "hardware": x["hardware"],
            "controls": [
                {
                    "control": ctl["control"],
                    "status": ctl["status"],
                    "complete": ctl["complete"],
                    "text_sha256": hashlib.sha256(ctl["text"].encode("utf-8")).hexdigest(),
                }
                for ctl in x["controls"]
            ],
        })
    if map_data.get("components") != expected_components:
        E("map: component/control records differ from Swift skeleton or control ledger")
    return errors


def load_units(canonical_dir: Path):
    paths = sorted(canonical_dir.glob("*.lctl"))
    return {p.stem: parse_canonical(p) for p in paths}


def run_falsifiers(units, exp, lifecycle, transitions, error_list, golden, source_dir, map_data):
    cases = []

    def row_of(u, unit, rid):
        return next(r for r in u[unit] if r["ROW"] == rid)

    def mutate_units(desc, fn):
        u = copy.deepcopy(units)
        fn(u)
        errs, _ = check(u, exp, lifecycle, transitions, error_list, golden, source_dir)
        cases.append((desc, bool(errs)))

    mutate_units("drop one lifecycle edge", lambda u: row_of(u, "P01_application_foundation", "K0001L").update(
        PARAM=";".join(row_of(u, "P01_application_foundation", "K0001L")["PARAM"].split(";")[1:])))
    mutate_units("swap an error disposition", lambda u: row_of(u, "P10_security_architecture", next(
        r["ROW"] for r in u["P10_security_architecture"] if r["ROW"].endswith("X"))).update(
        PARAM=row_of(u, "P10_security_architecture", next(
            r["ROW"] for r in u["P10_security_architecture"] if r["ROW"].endswith("X")))["PARAM"].replace("terminal", "retry")))
    mutate_units("claim a completed control", lambda u: row_of(u, "P05_accessibility", next(
        r["ROW"] for r in u["P05_accessibility"] if r["ROW"].endswith("R") and r["ROW"].startswith("K"))).update(
        PARAM=row_of(u, "P05_accessibility", next(
            r["ROW"] for r in u["P05_accessibility"] if r["ROW"].endswith("R") and r["ROW"].startswith("K")))["PARAM"].replace("complete=0", "complete=1")))
    mutate_units("delete a component frame", lambda u: u.__setitem__("P43_documentation", [
        r for r in u["P43_documentation"] if not r["ROW"].startswith("K0735")]))
    mutate_units("reorder boot", lambda u: row_of(u, "P02_software_architecture", "K0012F").update(
        PARAM="id=boot.C0012;awaits=P02.start"))
    mutate_units("approve a budget", lambda u: row_of(u, "P07_networking_and_api_infrastructure", next(
        r["ROW"] for r in u["P07_networking_and_api_infrastructure"] if re.fullmatch(r"K\d{4}B0", r["ROW"]))).update(
        PARAM=row_of(u, "P07_networking_and_api_infrastructure", next(
            r["ROW"] for r in u["P07_networking_and_api_infrastructure"] if re.fullmatch(r"K\d{4}B0", r["ROW"])))["PARAM"].replace("proposed", "approved")))
    mutate_units("change a capability gate", lambda u: row_of(u, "P03_user_interface_platform", next(
        r["ROW"] for r in u["P03_user_interface_platform"] if re.fullmatch(r"K\d{4}P0", r["ROW"]))).update(
        PARAM=row_of(u, "P03_user_interface_platform", next(
            r["ROW"] for r in u["P03_user_interface_platform"] if re.fullmatch(r"K\d{4}P0", r["ROW"])))["PARAM"].replace(
            "declared-and-justified-before-request", "always-allow")))
    mutate_units("change component family metadata", lambda u: row_of(u, "P12_privacy_architecture", next(
        r["ROW"] for r in u["P12_privacy_architecture"] if r["ROW"].endswith("R") and r["ROW"].startswith("K"))).update(
        PARAM=re.sub(r"family=[^;]+", "family=general-corrupt", row_of(u, "P12_privacy_architecture", next(
            r["ROW"] for r in u["P12_privacy_architecture"] if r["ROW"].endswith("R") and r["ROW"].startswith("K")))["PARAM"])))

    m = copy.deepcopy(map_data)
    m["components"][0]["contract_sha256"] = "0" * 64
    cases.append(("corrupt translation map contract hash", bool(check_map(m, exp, lifecycle, transitions, error_list, source_dir))))
    return cases


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--falsify", action="store_true")
    ap.add_argument("--canonical-dir", type=Path, default=PKG / "canonical")
    ap.add_argument("--source-dir", type=Path, default=PKG / "source")
    ap.add_argument("--map", dest="map_path", type=Path, default=PKG / "map" / "TRANSLATION_MAP.json")
    ap.add_argument("--skeleton", type=Path, default=DEFAULT_SK)
    args = ap.parse_args(argv)

    try:
        exp = expected(args.skeleton)
        lifecycle, transitions, error_list = swift_runtime(args.skeleton)
        golden = golden_contracts(args.skeleton)
        units = load_units(args.canonical_dir)
        map_data = json.loads(args.map_path.read_text(encoding="utf-8"))
        errors, n = check(units, exp, lifecycle, transitions, error_list, golden, args.source_dir)
        errors.extend(check_map(map_data, exp, lifecycle, transitions, error_list, args.source_dir))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: checker setup/parse error: {exc}")
        return 1

    print(f"golden contracts available: {len(golden)}")
    if args.falsify:
        cases = run_falsifiers(units, exp, lifecycle, transitions, error_list, golden, args.source_dir, map_data)
        for desc, caught in cases:
            print(f"falsifier {'CAUGHT' if caught else 'MISSED'}: {desc}")
        if not all(caught for _, caught in cases):
            errors.append("a falsifier was not caught")
    for error in errors[:80]:
        print("FAIL", error)
    print(
        f"{'PASS' if not errors else 'FAIL'}: {n}/{PROJECT_COMPONENTS} components round-trip from canonical LCTL "
        f"and map to the Swift skeleton" + (f" ({len(errors)} problems)" if errors else "")
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
