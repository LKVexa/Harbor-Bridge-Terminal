"""Regenerate conformance fixtures + digest manifest (INV-63-C029).  Run: python tools/gen_fixtures.py"""
import json, pathlib, sys
PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
schema = __import__(PKG.name + ".schema", fromlist=["x"])
FIX = PKG / "fixtures"
FIX.mkdir(exist_ok=True)
SIG = "ab" * 64
DIG = "sha256:" + "0" * 64
cases = [
 ("desired_v1_valid", "PK_DEPLOY_DESIRED/1", {"schema":"PK_DEPLOY_DESIRED/1","tenant":"acme","component":"api","version":"v1","count":3,"spread":True}, "valid", None),
 ("desired_v2_valid", "PK_DEPLOY_DESIRED/2", {"schema":"PK_DEPLOY_DESIRED/2","tenant":"acme","component":"api","version":"v1","count":3,"artifact":{"digest":DIG,"signature":SIG,"key_id":"rel-1"},"residency":["eu"],"priority":"critical"}, "valid", None),
 ("desired_v2_missing_artifact", "PK_DEPLOY_DESIRED/2", {"schema":"PK_DEPLOY_DESIRED/2","tenant":"acme","component":"api","version":"v1","count":3}, "invalid", "INV63-E-SCHEMA"),
 ("desired_negative_count", "PK_DEPLOY_DESIRED/1", {"schema":"PK_DEPLOY_DESIRED/1","tenant":"acme","component":"api","version":"v1","count":-1}, "invalid", "INV63-E-SCHEMA"),
 ("desired_bool_count", "PK_DEPLOY_DESIRED/1", {"schema":"PK_DEPLOY_DESIRED/1","tenant":"acme","component":"api","version":"v1","count":True}, "invalid", "INV63-E-SCHEMA"),
 ("desired_bad_tenant", "PK_DEPLOY_DESIRED/1", {"schema":"PK_DEPLOY_DESIRED/1","tenant":"Acme Corp","component":"api","version":"v1","count":1}, "invalid", "INV63-E-SCHEMA"),
 ("desired_unknown_field", "PK_DEPLOY_DESIRED/1", {"schema":"PK_DEPLOY_DESIRED/1","tenant":"acme","component":"api","version":"v1","count":1,"x":1}, "invalid", "INV63-E-SCHEMA"),
 ("diff_valid", "PK_DEPLOY_DIFF/1", {"schema":"PK_DEPLOY_DIFF/1","start":[["acme/api","v1","h1"]],"stop":[]}, "valid", None),
 ("diff_short_instance", "PK_DEPLOY_DIFF/1", {"schema":"PK_DEPLOY_DIFF/1","start":[["acme/api","v1"]],"stop":[]}, "invalid", "INV63-E-SCHEMA"),
 ("rollout_valid", "PK_DEPLOY_ROLLOUT/1", {"schema":"PK_DEPLOY_ROLLOUT/1","tenant":"acme","component":"api","version":"v2","max_unavailable":1,"canary":1}, "valid", None),
 ("rollout_zero_unavailable", "PK_DEPLOY_ROLLOUT/1", {"schema":"PK_DEPLOY_ROLLOUT/1","tenant":"acme","component":"api","version":"v2","max_unavailable":0}, "invalid", "INV63-E-SCHEMA"),
 ("error_valid", "PK_DEPLOY_ERROR/1", {"schema":"PK_DEPLOY_ERROR/1","code":"INV63-E-QUOTA","message":"m","retryable":False,"outcome":"TERMINAL","details":{}}, "valid", None),
 ("event_valid", "PK_DEPLOY_EVENT/1", {"schema":"PK_DEPLOY_EVENT/1","sequence":1,"kind":"reconcile","ts":1.0,"tenant":"acme","trace_id":"0"*31+"1","reason":"r"}, "valid", None),
 ("request_valid", "PK_DEPLOY_REQUEST/1", {"schema":"PK_DEPLOY_REQUEST/1","op":"reconcile","token":"t.s","idempotency_key":"abcdefgh","body":{},"traceparent":"00-"+"1"*32+"-"+"2"*16+"-01"}, "valid", None),
 ("request_unknown_op", "PK_DEPLOY_REQUEST/1", {"schema":"PK_DEPLOY_REQUEST/1","op":"delete_everything","token":"t.s","idempotency_key":"abcdefgh","body":{}}, "invalid", "INV63-E-SCHEMA"),
 ("config_valid", "PK_DEPLOY_CONFIG/1", {"schema":"PK_DEPLOY_CONFIG/1","environment":"prod","site":"eu-1","tier":"near-edge"}, "valid", None),
 ("config_bad_env", "PK_DEPLOY_CONFIG/1", {"schema":"PK_DEPLOY_CONFIG/1","environment":"yolo","site":"x"}, "invalid", "INV63-E-SCHEMA"),
 ("desired_v9_unsupported", "PK_DEPLOY_DESIRED/9", {"schema":"PK_DEPLOY_DESIRED/9"}, "invalid", "INV63-E-UNSUPPORTED-VERSION"),
]
out = []
for name, ref, payload, expect, code in cases:
    (FIX / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    out.append({"file": f"{name}.json", "schema": ref, "expect": expect, "expect_code": code})
(FIX / "FIXTURES.json").write_text(json.dumps({"schema": "INV63_FIXTURES/1", "schema_digests": schema.all_schema_digests(), "fixtures": out}, indent=2) + "\n")
print(len(out), "fixtures")
