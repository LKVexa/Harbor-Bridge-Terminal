#!/usr/bin/env python3
"""Translate the iOS735 skeleton (Swift, L3 of the iOS735_VEC1 stack) into LCTL.

Output: 43 LCTL-C 1.0 phase modules (one @frame per component, chained by tick/prev in boot order)
plus one application unit that composes the 43 phases. Every unit is then lowered to canonical
LCTL/1.3 by the LCTL 1.6.1 compiler and verified by both the 1.6.1 and the 1.6.0 runtimes.

Inputs (read-only): the skeleton's Swift component sources, Evidence/components.json,
Evidence/control-ledger.json. Nothing is guessed that the skeleton does not state.
Deterministic: same inputs -> byte-identical LCTL-C."""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
UNIT_VERSION = "1.6.1"
PROFILE = "lctl.quantum.parallel.distributed"
PROJECT_COMPONENTS = 735
PROJECT_PHASES = 43
CONTROLS_PER_COMPONENT = 25

LIFECYCLE = ["uninitialized", "initializing", "active", "suspended", "restoring", "upgrading", "tearingDown", "terminated", "failed"]
# ComponentKit Lifecycle.transitions, verbatim
TRANSITIONS = {
    "uninitialized": ["initializing", "restoring", "upgrading"],
    "initializing": ["active", "failed", "tearingDown"],
    "restoring": ["active", "failed", "initializing"],
    "upgrading": ["initializing", "failed"],
    "active": ["suspended", "tearingDown", "failed"],
    "suspended": ["active", "tearingDown", "failed"],
    "tearingDown": ["terminated", "failed"],
    "failed": ["tearingDown", "initializing"],
    "terminated": [],
}
# ComponentKit ComponentError.classify, verbatim
ERROR_MAP = [("invalidTransition", "runtime", "terminal"), ("inputTooLarge", "data", "userAction"),
             ("inputMalformed", "data", "userAction"), ("inputEmpty", "data", "userAction"),
             ("dependencyUnavailable", "dependency", "retry"), ("permissionNotYetJustified", "permission", "escalate"),
             ("capabilityUndeclared", "permission", "escalate"), ("cancelled", "runtime", "fallback"),
             ("budgetExceeded", "runtime", "escalate"), ("notImplemented", "configuration", "fallback")]
FAMILIES = ["general", "mlModel", "visualStates", "trustBoundary", "voiceOver", "capabilityDetection", "dataModel",
            "locationAuthorization", "reproducibleBuild", "wireContract", "syncMerge", "renderBudget", "backgroundMode",
            "analyticsMinimization", "testOwnership", "pushPayload", "mediaSession", "storeKitTruth", "localeFormatting",
            "documentationOwnership"]
# LCTL carrier op for each family's x.21..x.25 clauses (all verifier-accepted metadata ops)
FAMILY_OP = {"general": "CHECKPOINT_SCOPE", "mlModel": "TENSOR", "visualStates": "DEVICE", "trustBoundary": "FAILURE_DOMAIN",
             "voiceOver": "DEVICE", "capabilityDetection": "DEVICE", "dataModel": "MEMORY_DOMAIN",
             "locationAuthorization": "DEVICE", "reproducibleBuild": "SCHEDULE_SEAL", "wireContract": "CLASSICAL_CHANNEL",
             "syncMerge": "CONSISTENCY_SCOPE", "renderBudget": "CAPACITY", "backgroundMode": "TIMEOUT",
             "analyticsMinimization": "MESSAGE", "testOwnership": "CHECKPOINT", "pushPayload": "MESSAGE",
             "mediaSession": "DEVICE", "storeKitTruth": "CONSISTENCY_SCOPE", "localeFormatting": "DOMAIN",
             "documentationOwnership": "PERSISTENT"}
EVIDENCE = {"SKELETON_DECLARED": "skeletonDeclared", "NEEDS_DEVICE_RUN": "deviceRun", "NEEDS_HUMAN_REVIEW": "humanReview",
            "NEEDS_PRODUCT_DECISION": "productDecision", "NEEDS_CI_RUN": "ciRun"}
CONTROL_STATUSES = set(EVIDENCE) | {"WRITTEN_NOT_RUN", "DECLARED_NOT_USER_VISIBLE"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "none"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def contract_sha(r):
    """Same record and canonical rule as the stack's VEC1 identity (L4 skeleton.contract_record)."""
    rec = {"schema": "IOS735/COMPONENT_CONTRACT/1", "component": int(r["n"]), "type": r["type"], "name": r["name"],
           "phase": int(r["phase"]), "phase_name": r["phase_name"], "layer": r["layer"], "family": int(r["family"]),
           "frameworks": list(r["frameworks"]), "capabilities": list(r["capabilities"]), "donors": list(r["donors"]),
           "user_visible": bool(r["visible"])}
    return hashlib.sha256(canonical(rec)).hexdigest()


def _required_match(pattern: str, src: str, label: str):
    m = re.search(pattern, src)
    if not m:
        raise ValueError(f"cannot parse {label} from Swift component source")
    return m


def swift_facts(src: str):
    """Budgets, capabilities, hardware and fallback exactly as the Swift contract states them."""
    budgets = [{"metric": m, "unit": u, "limit": l} for m, u, l in
               re.findall(r'QualityBudget\(metric: "([^"]*)", unit: "([^"]*)", limit: ([0-9.]+)\)', src)]
    caps = _required_match(r"capabilities: \[([^\]]*)\]", src, "capabilities").group(1)
    capabilities = [c.strip().lstrip(".") for c in caps.split(",") if c.strip()]
    hw = _required_match(r"requiresHardware: \[([^\]]*)\]", src, "requiresHardware").group(1)
    hardware = [h.strip().lstrip(".") for h in hw.split(",") if h.strip()]
    fallback = _required_match(r'fallback: "((?:[^"\\]|\\.)*)"', src, "fallback").group(1)
    return budgets, capabilities, hardware, fallback


def runtime_facts(skeleton: Path):
    src = (skeleton / "Sources/ComponentKit/Runtime.swift").read_text(encoding="utf-8")
    enum_body = _required_match(r"public enum LifecycleState:[^{]+\{([^}]*)\}", src, "LifecycleState").group(1)
    lifecycle = re.findall(r"\bcase\s+([^\n]+)", enum_body)
    lifecycle = [name.strip() for group in lifecycle for name in group.split(",")]
    lifecycle = [name for name in lifecycle if re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name)]
    trans_body = src.split("transitions: [LifecycleState: Set<LifecycleState>] = [", 1)[1].split("\n    ]", 1)[0]
    transitions = {m[0]: re.findall(r"\.(\w+)", m[1]) for m in re.findall(r"\.(\w+): \[([^\]]*)\]", trans_body)}
    classify = src.split("public static func classify", 1)[1].split("\n    }", 1)[0]
    error_map = []
    for codes, dom, disp in re.findall(r"case ([^:]+): return \(\.(\w+), \.(\w+)\)", classify):
        error_map.extend((code, dom, disp) for code in re.findall(r"\.(\w+)", codes))
    return lifecycle, transitions, error_map


def validate_runtime_constants(skeleton: Path):
    lifecycle, transitions, error_map = runtime_facts(skeleton)
    if lifecycle != LIFECYCLE:
        raise ValueError(f"LifecycleState drift: translator={LIFECYCLE!r}, Swift={lifecycle!r}")
    if transitions != TRANSITIONS:
        raise ValueError("Lifecycle.transitions drift between translate.py and Runtime.swift")
    if error_map != ERROR_MAP:
        raise ValueError("ComponentError.classify drift between translate.py and Runtime.swift")


def arg(**kv):
    for k, v in kv.items():
        if any(ch in str(v) for ch in "│\n;="):
            raise ValueError(f"unsafe ARG value {k}={v!r}")
    return ";".join(f"{k}={v}" for k, v in kv.items())


def row(rid, lane, op, a, meta="_"):
    return f"{rid}│{lane}│{op}│_│_│_│{a}│{meta}"


def load(skeleton: Path):
    validate_runtime_constants(skeleton)
    comps = json.loads((skeleton / "Evidence/components.json").read_text(encoding="utf-8"))
    ledger = json.loads((skeleton / "Evidence/control-ledger.json").read_text(encoding="utf-8"))
    if not isinstance(comps, list) or not isinstance(ledger, list):
        raise ValueError("components.json and control-ledger.json must both contain JSON arrays")
    if len(comps) != PROJECT_COMPONENTS:
        raise ValueError(f"expected {PROJECT_COMPONENTS} components, found {len(comps)}")
    ids = [c.get("n") for c in comps]
    if any(type(n) is not int or n <= 0 for n in ids) or len(set(ids)) != len(ids):
        raise ValueError("component IDs must be unique positive integers")
    if set(ids) != set(range(1, PROJECT_COMPONENTS + 1)):
        raise ValueError("component IDs must be exactly 1..735")
    phases = sorted({c.get("phase") for c in comps})
    if phases != list(range(1, PROJECT_PHASES + 1)):
        raise ValueError(f"phases must be exactly 1..{PROJECT_PHASES}; found {phases!r}")
    by = {}
    for r in ledger:
        n = r.get("component")
        if n not in set(ids):
            raise ValueError(f"control ledger references unknown component {n!r}")
        by.setdefault(n, []).append(r)
    if len(ledger) != PROJECT_COMPONENTS * CONTROLS_PER_COMPONENT:
        raise ValueError(f"expected {PROJECT_COMPONENTS * CONTROLS_PER_COMPONENT} controls, found {len(ledger)}")
    for c in comps:
        n = c["n"]
        fam = c.get("family")
        if type(fam) is not int or not 0 <= fam < len(FAMILIES):
            raise ValueError(f"C{n:04d}: invalid family index {fam!r}")
        if not re.fullmatch(r"[A-Za-z0-9_]+", str(c.get("module", ""))) or not re.fullmatch(r"[A-Za-z0-9_]+", str(c.get("type", ""))):
            raise ValueError(f"C{n:04d}: unsafe module/type path component")
        controls = sorted(by.get(n, []), key=lambda r: r.get("control", ""))
        expected_controls = [f"{n}.{i:02d}" for i in range(1, CONTROLS_PER_COMPONENT + 1)]
        got_controls = [r.get("control") for r in controls]
        if got_controls != expected_controls:
            raise ValueError(f"C{n:04d}: controls must be exactly x.01..x.25")
        for r in controls:
            if r.get("status") not in CONTROL_STATUSES:
                raise ValueError(f"{r.get('control')}: unsupported control status {r.get('status')!r}")
            if type(r.get("complete")) is not bool or not isinstance(r.get("text"), str):
                raise ValueError(f"{r.get('control')}: malformed complete/text fields")
        for r in controls[20:]:
            if r["status"] not in EVIDENCE:
                raise ValueError(f"{r['control']}: clause status cannot be represented in LCTL: {r['status']!r}")
        path = skeleton / "Sources" / c["module"] / (c["type"] + ".swift")
        if not path.is_file():
            raise ValueError(f"C{n:04d}: missing Swift source {path.relative_to(skeleton)}")
        src = path.read_text(encoding="utf-8")
        c["budgets"], capabilities, c["hardware"], c["fallback"] = swift_facts(src)
        if capabilities != list(c.get("capabilities", [])):
            raise ValueError(f"C{n:04d}: capabilities drift between components.json and Swift source")
        c["controls"] = controls
        c["sha"] = contract_sha(c)
    return sorted(comps, key=lambda c: (c["phase"], c["n"]))


def component_frame(c, fid, prev_fid, tick, module, prev_active):
    n = c["n"]; K = f"K{n:04d}"; C = f"C{n:04d}"
    st = {}
    for r in c["controls"]:
        st[r["status"]] = st.get(r["status"], 0) + 1
    status = ",".join(f"{k.lower()}:{v}" for k, v in sorted(st.items()))
    rows = [row(f"{K}R", "meta", "REG", arg(name=c["type"], component=n, phase=c["phase"], layer=slug(c["layer"]),
                family=FAMILIES[c["family"]], visible=str(c["visible"]).lower(), owner="UNASSIGNED",
                controls=len(c["controls"]), complete=sum(1 for r in c["controls"] if r["complete"]), status=status),
                f't=parallel_region;p="ios735:contract:{c["sha"]}"')]
    ev = {s: f"{K}E{i}" for i, s in enumerate(LIFECYCLE)}
    rows += [row(ev[s], "lifecycle", "EVENT", arg(id=f"{C}.{s}", kind="lifecycle")) for s in LIFECYCLE]
    edges = [f"{ev[a]}->{ev[b]}" for a in LIFECYCLE for b in TRANSITIONS[a]]
    rows.append(row(f"{K}L", "lifecycle", "DEP", ";".join(edges), "t=dependency;p=ios735:lifecycle-table"))
    rows.append(row(f"{K}F", "boot", "FUTURE", arg(id=f"boot.{C}", awaits=prev_active)))
    rows.append(row(f"{K}M", "state", "MEMORY_DOMAIN", arg(name=f"{C}.state", owner="UNASSIGNED", source_of_truth="product-decision")))
    rows.append(row(f"{K}X", "errors", "FAILURE_DOMAIN", ",".join(f"{a}:{d}/{p}" for a, d, p in ERROR_MAP)))
    for i, b in enumerate(c["budgets"]):
        rows.append(row(f"{K}B{i}", "budget", "CAPACITY", arg(metric=slug(b["metric"]), unit=slug(b["unit"]), limit=b["limit"], approval="proposed")))
    for i, cap in enumerate(c["capabilities"]):
        rows.append(row(f"{K}P{i}", "permission", "DEVICE", arg(capability=cap, gate="declared-and-justified-before-request")))
    for i, h in enumerate(c["hardware"]):
        rows.append(row(f"{K}H{i}", "hardware", "DEVICE", arg(hardware=h, fallback=slug(c["fallback"]))))
    op = FAMILY_OP[FAMILIES[c["family"]]]
    for r in c["controls"][20:]:
        k = r["control"].split(".")[1]
        rows.append(row(f"{K}Q{k}", "clause", op, arg(clause=f"x.{k}", family=FAMILIES[c["family"]],
                    evidence=EVIDENCE[r["status"]], statement_sha256=hashlib.sha256(r["text"].encode()).hexdigest()[:16])))
    head = f"@frame id={fid} parent=F0000 module={module} tick={tick} prev={prev_fid}"
    return [head, "ID│LANE│OP│OUT│CTRL│IN│ARG│META"] + rows + ["@end"], ev["active"], f"{C}.active"


def unit_header(uid, module, entry_row):
    return ["LCTLC/1.0",
            f"@unit id={uid} version={UNIT_VERSION} profile={PROFILE} entry=F0000:{entry_row} target=local-reference "
            f"error_budget=0.05 resource_ceiling=q<=12;distributed=logical;physical=false proof=ios735-lctl:0.1",
            "@defaults qspace=H basis=computational regime=exact assume=finite_dimension error=exact conf=1.0"]


def phase_unit(num, name, comps, prev_phase_end):
    module = f"ios735.p{num:02d}.{slug(name).replace('-', '_')}"
    L = unit_header(module, module, "C9999")
    L += [f"@frame id=F0000 parent=ROOT module={module} proof=ios735-lctl:0.1", "ID│LANE│OP│OUT│CTRL│IN│ARG│META",
          # LCTL requires one declared quantum register; the translation never touches it (inert anchor).
          'D0001│alloc│Q│q│_│_│1│res="logical_qubits=1";p=ios735:inert-anchor']
    L += ['D0002│alloc│C│c│_│_│1│res="classical_bits=1";p=ios735:inert-anchor',
          row("G0001", "meta", "REG", arg(name=module, phase=num, components=len(comps)), "t=parallel_region;p=ios735:phase"),
          row("G0002", "boot", "EVENT", arg(id=f"P{num:02d}.start", kind="phase")),
          row("G0003", "boot", "FUTURE", arg(id=f"boot.P{num:02d}", awaits=prev_phase_end)),
          "C9999│lane0│.│_│_│_│_│p=lctl:nop", "@end"]
    prev_fid, prev_active = "F0000", f"P{num:02d}.start"
    for t, c in enumerate(comps, start=1):
        fid = f"F{t:04d}"
        fr, _, active = component_frame(c, fid, prev_fid, t, module, prev_active)
        L += fr
        prev_fid, prev_active = fid, active
    return module, "\n".join(L) + "\n", prev_active


def app_unit(phases):
    module = "ios735.app"
    L = unit_header(module, module, "C9999")
    L += [f"@frame id=F0000 parent=ROOT module={module} proof=ios735-lctl:0.1", "ID│LANE│OP│OUT│CTRL│IN│ARG│META",
          'D0001│alloc│Q│q│_│_│1│res="logical_qubits=1";p=ios735:inert-anchor',
          'D0002│alloc│C│c│_│_│1│res="classical_bits=1";p=ios735:inert-anchor',
          row("A0001", "meta", "REG", arg(name=module, phases=len(phases), components=sum(p["count"] for p in phases),
              controls=sum(p["count"] for p in phases) * 25, complete=0), "t=parallel_region;p=ios735:application"),
          row("A0002", "boot", "EVENT", arg(id="app.launch", kind="application")),
          "C9999│lane0│.│_│_│_│_│p=lctl:nop", "@end"]
    for i, p in enumerate(phases, start=1):
        n = p["phase"]
        L += [f"@frame id=F{i:04d} parent=F0000 module={module} tick={i} prev=F{i-1:04d}", "ID│LANE│OP│OUT│CTRL│IN│ARG│META",
              row(f"M{n:02d}R", "meta", "REG", arg(name=p["module"], phase=n, components=p["count"], first=p["first"], last=p["last"]),
                  f't=parallel_region;p="ios735:phase-unit:{p["sha"]}"'),
              row(f"M{n:02d}S", "boot", "EVENT", arg(id=f"P{n:02d}.start", kind="phase")),
              row(f"M{n:02d}E", "boot", "EVENT", arg(id=f"P{n:02d}.end", kind="phase", equals=p["end"])),
              row(f"M{n:02d}D", "boot", "DEP", f"M{n:02d}S->M{n:02d}E" + (f";M{n-1:02d}E->M{n:02d}S" if i > 1 else ";A0002->M01S"),
                  "t=dependency;p=ios735:boot-order"),
              "@end"]
    return module, "\n".join(L) + "\n"


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def translate(skeleton: Path, out: Path):
    skeleton = skeleton.resolve()
    out = out.resolve()
    comps = load(skeleton)
    phases, prev_end, tmap, generated = [], "app.launch", [], {}
    for num in sorted({c["phase"] for c in comps}):
        cs = [c for c in comps if c["phase"] == num]
        phase_names = {c["phase_name"] for c in cs}
        if len(phase_names) != 1:
            raise ValueError(f"phase {num}: inconsistent phase_name values {sorted(phase_names)!r}")
        module, text, end = phase_unit(num, cs[0]["phase_name"], cs, prev_end)
        fname = f"P{num:02d}_{slug(cs[0]['phase_name']).replace('-', '_')}.lctlc"
        generated[fname] = text
        phases.append({"phase": num, "module": module, "file": fname, "count": len(cs), "first": f"C{cs[0]['n']:04d}",
                       "last": f"C{cs[-1]['n']:04d}", "end": end, "sha": hashlib.sha256(text.encode()).hexdigest()})
        prev_end = f"P{num:02d}.end"
        for c in cs:
            tmap.append({"component": c["n"], "type": c["type"], "name": c["name"], "phase": num, "unit": fname,
                         "frame_rows_prefix": f"K{c['n']:04d}", "contract_sha256": c["sha"],
                         "family": FAMILIES[c["family"]], "clause_op": FAMILY_OP[FAMILIES[c["family"]]],
                         "budgets": c["budgets"], "capabilities": c["capabilities"], "hardware": c["hardware"],
                         "controls": [{"control": r["control"], "status": r["status"], "complete": r["complete"],
                                       "text_sha256": hashlib.sha256(r["text"].encode()).hexdigest()} for r in c["controls"]]})
    _, app_text = app_unit(phases)
    generated["IOS735_APP.lctlc"] = app_text
    map_text = json.dumps({"schema": "IOS735_LCTL/MAP/1", "phases": phases,
        "components": tmap, "lifecycle": LIFECYCLE, "transitions": TRANSITIONS, "error_map": ERROR_MAP,
        "family_op": FAMILY_OP}, indent=1, ensure_ascii=False) + "\n"

    src = out / "source"
    src.mkdir(parents=True, exist_ok=True)
    for fname, text in generated.items():
        atomic_write(src / fname, text)
    expected = set(generated)
    for path in src.glob("*.lctlc"):
        if path.name not in expected and (path.name == "IOS735_APP.lctlc" or re.fullmatch(r"P\d{2}_.+\.lctlc", path.name)):
            path.unlink()
    atomic_write(out / "map" / "TRANSLATION_MAP.json", map_text)
    return phases


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("skeleton", nargs="?", type=Path, default=PKG / "input" / "iOS735_Skeleton")
    ap.add_argument("--out", type=Path, default=PKG, help="repository/output root (default: repository root)")
    args = ap.parse_args(argv)
    ph = translate(args.skeleton, args.out)
    print(f"translated {sum(p['count'] for p in ph)} components into {len(ph)} phase units + IOS735_APP.lctlc")
    return 0


if __name__ == "__main__":
    sys.exit(main())
