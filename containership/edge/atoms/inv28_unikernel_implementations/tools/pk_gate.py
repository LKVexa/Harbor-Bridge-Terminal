"""Run the vendored pk_core workflow W0-W9 + conformance gate over INV-28 (MC-002, MC-076 framework lane).

    python -B -m inv28_unikernel_implementations.tools.pk_gate [--out evidence/PK_GATE_RESULTS.json]
                                                               [--ledger evidence/pk_evidence.jsonl]

pk_core measures conformance of the declared contract plus exercised findings against the 100-item
checklist.  It is necessary but never sufficient: the exercised/declared split is reported and the MC-level
implementation status lives in evidence/MC_STATUS.json - the two axes are never merged.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from importlib import import_module

from ._common import EVIDENCE, ROOT, ensure_path, write_json


def run(ledger_path=None) -> dict:
    ensure_path()
    warnings.simplefilter("ignore", DeprecationWarning)
    from pk_core.evidence import EvidenceLedger
    from pk_core.gate import ConformanceGate
    from pk_core.workflow import WorkflowEngine
    comp = import_module(ROOT.name).COMPONENT()
    if ledger_path is not None and ledger_path.exists():
        ledger_path.unlink()
    ledger = EvidenceLedger(ledger_path) if ledger_path is not None else None
    engine = WorkflowEngine(ledger=ledger) if ledger is not None else WorkflowEngine()
    result = engine.run(comp)
    gate = ConformanceGate().evaluate([result]).to_dict()
    mod = import_module(ROOT.name + ".component")
    gate["workflow"] = {"certified": result.certified, "counts": result.counts, "coverage": result.coverage}
    gate["exercised_findings"] = len(mod.EXERCISED_BANDS)
    gate["declaration_derived_findings"] = sum(result.counts.values()) - len(mod.EXERCISED_BANDS)
    gate["ledger"] = None
    if ledger is not None:
        gate["ledger"] = {"path": ledger_path.relative_to(ROOT).as_posix(), "records": len(ledger),
                          "head": ledger.head, "verify_problems": ledger.verify()}
    gate["axis_note"] = ("framework conformance only: pk_core's default band handlers derive most findings from the "
                         "contract's declarations; 'satisfied' there is not implementation evidence. MC-level status: "
                         "evidence/MC_STATUS.json")
    return gate


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(EVIDENCE / "PK_GATE_RESULTS.json"))
    ap.add_argument("--ledger", default=str(EVIDENCE / "pk_evidence.jsonl"))
    a = ap.parse_args(argv)
    from pathlib import Path
    g = run(Path(a.ledger))
    write_json(Path(a.out), g)
    print("PK_GATE", g["verdict"], json.dumps(g["workflow"]["counts"]), f"exercised={g['exercised_findings']}")
    return 0 if g["verdict"] == "GO" else 1


if __name__ == "__main__":
    sys.exit(main())
