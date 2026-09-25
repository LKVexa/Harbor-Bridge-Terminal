"""Run the vendored pk_core workflow + conformance gate over INV-27 (MC-021, MC-087).

    python -B -m inv27_unikernel_execution.tools.pk_gate

pk_core measures conformance of the *declared contract and exercised checks* to the 100-item checklist.
It is one input to the release gate and never a substitute for evidence/RTM.json or evidence/MC_STATUS.json.
"""
from __future__ import annotations

import json
import sys
from importlib import import_module

from ._refs import ROOT

VENDOR = ROOT / "_vendor"


def run() -> dict:
    for p in (str(VENDOR), str(ROOT.parent)):
        if p not in sys.path:
            sys.path.insert(0, p)
    from pk_core.gate import ConformanceGate
    from pk_core.workflow import WorkflowEngine
    comp = import_module(ROOT.name).COMPONENT()
    result = WorkflowEngine().run(comp)
    gate = ConformanceGate().evaluate([result]).to_dict()
    gate["workflow"] = {"certified": result.certified, "counts": result.counts, "coverage": result.coverage}
    mod = import_module(ROOT.name + ".component")
    gate["optimized_mode"] = not __debug__
    gate["exercised_findings"] = list(mod.EXERCISED_BANDS)
    gate["axis_note"] = ("framework conformance only; most findings derive from contract declarations. "
                         "Implementation status: evidence/MC_STATUS.json and evidence/RTM.json")
    return gate


def main(argv=None) -> int:
    g = run()
    if "--check" not in (sys.argv[1:] if argv is None else argv):
        (ROOT / "evidence" / "PK_GATE_RESULTS.json").write_text(json.dumps(g, indent=1, default=str))
    print("PK_GATE", g["verdict"], json.dumps(g["workflow"]["counts"]), "optimized" if g["optimized_mode"] else "")
    return 0 if g["verdict"] == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
