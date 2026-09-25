import json, os
import jsonschema
from inv38_kernel_bypass_transport import outcomes as o
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCH = os.path.join(ROOT, "schemas")
GOLD = os.path.join(SCH, "golden")
def _load(p): return json.load(open(p))
_SCHEMA_BY_ID = {
    "PK_BYPASS_MR/1": "pk_bypass_mr_v1.schema.json",
    "PK_BYPASS_POST/1": "pk_bypass_post_v1.schema.json",
    "PK_BYPASS_CQ/1": "pk_bypass_cq_v1.schema.json",
    "PK_BYPASS_ERROR/1": "pk_bypass_error_v1.schema.json",
}
def _schema_for(doc): return _load(os.path.join(SCH, _SCHEMA_BY_ID[doc["schema"]]))
def test_valid_vectors_pass():
    for name in _load(os.path.join(GOLD, "index.json"))["valid"]:
        doc = _load(os.path.join(GOLD, name))
        jsonschema.validate(doc, _schema_for(doc))
def test_invalid_vectors_fail():
    for name in _load(os.path.join(GOLD, "index.json"))["invalid"]:
        doc = _load(os.path.join(GOLD, name))
        try:
            jsonschema.validate(doc, _schema_for(doc)); assert False, name
        except jsonschema.ValidationError:
            pass
def test_cross_version_rejected_by_const():
    for name in _load(os.path.join(GOLD, "index.json"))["cross_version"]:
        doc = _load(os.path.join(GOLD, name))
        # unknown version: schema id lookup would be for /2 which we don't ship -> const mismatch on /1
        s = _load(os.path.join(SCH, "pk_bypass_mr_v1.schema.json"))
        try:
            jsonschema.validate(doc, s); assert False, name
        except jsonschema.ValidationError:
            pass
def test_error_reason_code_in_table_or_pattern():
    doc = _load(os.path.join(GOLD, "error_stale_key.json"))
    assert doc["reason_code"].startswith("PK_BYPASS_")
