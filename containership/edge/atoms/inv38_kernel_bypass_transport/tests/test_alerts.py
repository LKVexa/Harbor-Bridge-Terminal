import os, yaml
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def test_zero_budget_safety_pages_immediately():
    a = yaml.safe_load(open(os.path.join(ROOT, "observability", "alerts", "inv38-alerts.yaml")))["alerts"]
    safety = [x for x in a if x["id"] in ("A-SAFETY","A-SEAL")]
    assert safety and all(x["severity"]=="SEV-1" and x["page"]=="immediate" for x in safety)
def test_stall_is_multisignal():
    a = yaml.safe_load(open(os.path.join(ROOT, "observability", "alerts", "inv38-alerts.yaml")))["alerts"]
    stall = next(x for x in a if x["id"]=="A-STALL")
    assert "completion_delta" in stall["expr"] and "oldest_inflight" in stall["expr"]
