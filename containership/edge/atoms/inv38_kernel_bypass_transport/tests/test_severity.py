import os, yaml
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def test_sev1_covers_isolation_and_sealing():
    s = yaml.safe_load(open(os.path.join(ROOT, "ops", "severity.yaml")))
    trig = s["severities"]["SEV-1"]["triggers"]
    assert "memory_isolation_violation" in trig and "sealing_failure" in trig
def test_containment_actions_present():
    s = yaml.safe_load(open(os.path.join(ROOT, "ops", "severity.yaml")))
    assert "disable_bypass" in s["containment_actions"]
