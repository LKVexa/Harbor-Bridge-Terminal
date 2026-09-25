import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def test_layout_schema_has_three_classes():
    s = json.load(open(os.path.join(ROOT, "config", "layout.schema.json")))
    for k in ("immutable", "config", "state"):
        assert k in s["properties"]
    assert s["required"] == ["immutable", "config", "state"]
