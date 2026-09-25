"""M76/M75 - run the vendored pk_core W0-W9 workflow + gate for INV-60 and record evidence."""
import json, pathlib, sys
PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent)); sys.dont_write_bytecode = True
from pk_core.evidence import EvidenceLedger
from pk_core.gate import ConformanceGate
from pk_core.workflow import WorkflowEngine
from inv60_wasm_application_fabric import COMPONENT

rel = PKG / "release"; rel.mkdir(exist_ok=True)
ev = rel / "pk_evidence.jsonl"
if ev.exists():
    ev.unlink()
ledger = EvidenceLedger(ev)
res = WorkflowEngine(ledger).run(COMPONENT())
gate = ConformanceGate().evaluate([res]).to_dict()
problems = ledger.verify()
out = {"schema": "inv60.conformance/1", "note": "pk_core conformance answers the 100 checklist items at contract/reference level; it is NOT the production exit gate",
       "workflow": res.to_dict(), "gate": gate, "ledger_problems": problems, "evidence_head": ledger.head,
       "findings": {f.check_id: {"status": f.status.value, "stage": f.stage.name, "artifacts": list(f.artifacts) if hasattr(f, "artifacts") else []} for f in res.findings}}
(rel / "CONFORMANCE.json").write_text(json.dumps(out, indent=1, default=str))
(rel / "PK_GATE_RESULTS.json").write_text(json.dumps(gate, indent=1))
print(json.dumps({"certified": res.certified, "counts": res.counts, "pk_gate": gate["verdict"], "ledger_problems": len(problems)}))
sys.exit(0 if res.certified and not problems else 1)
