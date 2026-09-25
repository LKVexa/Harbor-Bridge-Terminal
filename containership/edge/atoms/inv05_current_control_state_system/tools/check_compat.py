"""Fail on wire-schema or error-catalog breaking changes (MC-012-06, MC-013-01)."""
import json, sys
import _path  # noqa: F401
from inv05_current_control_state_system import tools_check as tc
from inv05_current_control_state_system.errors import ERROR_CATALOG
from inv05_current_control_state_system.schema import schema_lock

problems = tc.schema_breaking_changes(tc.load_json("conformance/schema_lock.json"), schema_lock())
for code, spec in tc.load_json("conformance/error_catalog_lock.json").items():
    cur = ERROR_CATALOG.get(code)
    if cur is None or (cur.category, cur.retryable, cur.http_status) != (spec["category"], spec["retryable"], spec["http_status"]):
        problems.append(f"error code {code} removed or changed")
print(json.dumps({"ok": not problems, "problems": problems}))
sys.exit(1 if problems else 0)
