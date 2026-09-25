"""MC-002-03/04: validate every MASTER.md reference and, if present, its schema/provenance."""
import json, sys
import _path  # noqa: F401
from inv05_current_control_state_system import tools_check as tc
p = tc.check_master_md()
print(json.dumps({"ok": not p, "problems": p}))
sys.exit(1 if p else 0)
