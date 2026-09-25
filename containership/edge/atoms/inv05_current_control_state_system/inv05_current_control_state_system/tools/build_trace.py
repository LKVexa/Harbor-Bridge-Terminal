"""Render traceability/TRACE_MATRIX.md from trace_matrix.json and validate it (MC-003-05/06)."""
import json, os, sys
import _path  # noqa: F401
from inv05_current_control_state_system import tools_check as tc
m = tc.load_json("traceability/trace_matrix.json")
problems = tc.check_trace(m)
with open(os.path.join(tc.PKG, "traceability", "TRACE_MATRIX.md"), "w", encoding="utf-8") as fh:
    fh.write(tc.render_trace_md(m))
print(json.dumps({"ok": not problems, "rows": len(m["rows"]), "problems": problems[:50]}))
sys.exit(1 if problems else 0)
