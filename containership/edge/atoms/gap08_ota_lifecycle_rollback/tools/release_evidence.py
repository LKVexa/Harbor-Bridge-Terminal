"""Components 37/38: release acceptance evidence bundle + SBOM.

    python tools/release_evidence.py build  [--sign-key-env GAP08_RELEASE_KEY] [--skip-long]
    python tools/release_evidence.py verify

``build`` runs the full test suite (and the short benchmark + soak unless
``--skip-long``), writes ``release/SBOM.cdx.json``, regenerates
``RELEASE_MANIFEST.sha256`` over every shipped file, and writes
``release/EVIDENCE_BUNDLE.json`` binding checklist sections -> test ids ->
results -> the exact file digests.  The bundle digest is HMAC-signed when a
release key is supplied (production: replace with the release signing
service / Sigstore); otherwise it is marked ``unsigned`` and the release gate
must treat it as not releasable.

``verify`` recomputes every digest and fails if any shipped file differs from
the bundle — evidence can never be silently reused after a code/config change.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REL = PKG / "release"
EXCLUDE_DIRS = {"__pycache__", "release", ".pytest_cache"}
EXCLUDE_FILES = {"RELEASE_MANIFEST.sha256"}

# checklist section -> test modules/classes that exercise it (see docs/CHECKLIST_STATUS.md)
TRACE = {
    "01 durable store": ["test_store_lease.StoreTest", "test_chaos.ChaosCampaign"],
    "02 lease/fencing": ["test_store_lease.LeaseTest", "test_controller.FencingRecovery", "test_chaos.Concurrency"],
    "03 conflict detector": ["test_controller.PolicyControls.test_conflicting_rollout_blocked",
                             "test_dod_drills.Section03OverlapSameInstant"],
    "04 health adapter": ["test_components.HealthEvidence"],
    "05 audit sink": ["test_controller.DependencyFailClosed", "test_dod_drills.Section05TamperDrill"],
    "06 artifact verifier": ["test_components.ArtifactVerification", "test_dod_drills.Section06OneByteMutation"],
    "07 A/B installer": ["test_installer_powerloss"],
    "08 rollback executor": ["test_controller.HappyPathAndRollback", "test_controller.DeferredAndIdempotency"],
    "09 blast radius": ["test_controller.PolicyControls.test_topology_blast_radius_denies_whole_domain"],
    "10 emergency freeze": ["test_controller.PolicyControls.test_freeze_blocks_forward_not_rollback_and_unfreeze_needs_second_person"],
    "11 authorization": ["test_controller.PolicyControls.test_authorization_enforced",
                         "test_dod_drills.Section11ScopedAuthorization"],
    "12 identity/attestation": ["test_components.Identity"],
    "13 deferred scheduler": ["test_controller.DeferredAndIdempotency.test_offline_node_deferred_then_retried_behind_gate"],
    "14 idempotent transport": ["test_controller.DeferredAndIdempotency.test_lost_ack_and_duplicate_delivery_execute_once"],
    "15 fail-closed deps": ["test_controller.DependencyFailClosed", "test_dod_drills.Section15DependencyMatrix"],
    "16 retry/backoff": ["test_components.RetryBreakerAdmission"],
    "17 admission": ["test_components.RetryBreakerAdmission", "test_controller.PolicyControls.test_backpressure_limits"],
    "18 windows": ["test_components.Windows", "test_controller.PolicyControls.test_maintenance_window"],
    "19 distribution": ["test_components.Distribution"],
    "20 schemas": ["test_components.ErrorsAndSchemas"],
    "21 error taxonomy": ["test_components.ErrorsAndSchemas.test_error_envelope"],
    "22 observability": ["test_controller.ExplainTelemetry"],
    "23 explain view": ["test_controller.ExplainTelemetry"],
    "24 backup/restore": ["test_store_lease.StoreTest.test_backup_restore_verified", "test_chaos.ChaosCampaign"],
    "25 compatibility": ["test_components.ConfigSecretsCompat.test_compat_matrix"],
    "26 config provenance": ["test_components.ConfigSecretsCompat.test_config_provenance_and_rollback"],
    "27 secrets boundary": ["test_components.ConfigSecretsCompat.test_secrets_boundary"],
    "28 cancellation": ["test_controller.Cancellation"],
    "29 quarantine recovery": ["test_controller.HappyPathAndRollback"],
    "30 reconciliation": ["test_controller.DeferredAndIdempotency.test_unknown_outcome_is_never_success"],
    "31 property/fuzz": ["test_property_fuzz"],
    "32 concurrency": ["test_chaos.Concurrency", "test_store_lease.StoreTest"],
    "33 fault injection": ["test_chaos.ChaosCampaign"],
    "36 power loss (simulated)": ["test_installer_powerloss"],
}


def shipped_files():
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and not (set(p.relative_to(PKG).parts) & EXCLUDE_DIRS) and p.name not in EXCLUDE_FILES \
                and not p.name.endswith(".pyc"):
            yield p


def digests():
    return {str(p.relative_to(PKG)): hashlib.sha256(p.read_bytes()).hexdigest() for p in shipped_files()}


def run_tests():
    sys.path.insert(0, str(PKG / "tests"))
    sys.path.insert(0, str(PKG.parent))
    loader = unittest.TestLoader()
    suite = loader.discover(str(PKG / "tests"), pattern="test_*.py", top_level_dir=str(PKG / "tests"))
    buf = io.StringIO()

    class R(unittest.TextTestResult):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.outcomes = {}

        def addSuccess(self, t):
            super().addSuccess(t)
            self.outcomes[t.id()] = "pass"

        def addFailure(self, t, e):
            super().addFailure(t, e)
            self.outcomes[t.id()] = "fail"

        def addError(self, t, e):
            super().addError(t, e)
            self.outcomes[t.id()] = "error"

        def addSkip(self, t, r):
            super().addSkip(t, r)
            self.outcomes[t.id()] = f"skip: {r}"
    res = unittest.TextTestRunner(stream=buf, verbosity=0, resultclass=R).run(suite)
    return res.outcomes, res.wasSuccessful()


def sbom(version):
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         "component": {"type": "library", "name": "gap08_ota_lifecycle_rollback", "version": version,
                                       "description": "GAP-08 OTA lifecycle/rollback control plane",
                                       "licenses": [{"license": {"name": "UNDECLARED - see docs/OWNERS.md"}}]}},
            "components": [{"type": "platform", "name": "cpython", "version": ">=3.10",
                            "description": "runtime; standard library only, no third-party packages"},
                           {"type": "library", "name": "pk_core", "version": "4.x", "scope": "optional",
                            "description": "Post-Kubernetes checklist framework; only component.py/contract.py import it"}],
            "dependencies": [{"ref": "gap08_ota_lifecycle_rollback", "dependsOn": ["cpython"]}]}


def build(a):
    version = (PKG / "VERSION").read_text().strip()
    REL.mkdir(exist_ok=True)
    outcomes, ok = run_tests()
    extra = {}
    if not a.skip_long:
        for tool, args in (("benchmark.py", ["--sizes", "50", "200", "1000", "--out", str(REL / "benchmark.json")]),
                           ("soak.py", ["--cycles", "40", "--seed", "11", "--out", str(REL / "soak.json")])):
            r = subprocess.run([sys.executable, str(PKG / "tools" / tool), *args], capture_output=True, text=True)
            extra[tool] = {"returncode": r.returncode}
            ok = ok and r.returncode == 0
    (REL / "SBOM.cdx.json").write_text(json.dumps(sbom(version), indent=2) + "\n")
    files = digests()
    (PKG / "RELEASE_MANIFEST.sha256").write_text("".join(f"{d}  ./{f}\n" for f, d in files.items()))
    trace = {}
    for section, ids in TRACE.items():
        hits = {t: o for t, o in outcomes.items() if any(t.startswith(i) or t.startswith("test_" + i) or
                                                         (i in t) for i in ids)}
        trace[section] = {"tests": len(hits), "all_pass": bool(hits) and all(o == "pass" for o in hits.values())}
    body = {"schema": "PK_RELEASE_EVIDENCE/1", "package": "gap08_ota_lifecycle_rollback", "version": version,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "python": sys.version.split()[0],
            "tests": {"total": len(outcomes), "passed": sum(o == "pass" for o in outcomes.values()),
                      "skipped": sum(o.startswith("skip") for o in outcomes.values()),
                      "failed": sorted(t for t, o in outcomes.items() if o in ("fail", "error")),
                      "outcomes": outcomes},
            "long_runs": extra, "section_trace": trace, "files": files,
            "open_items_ref": "docs/CHECKLIST_STATUS.md", "releasable": False}
    body["bundle_digest"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    key = os.environ.get(a.sign_key_env or "", "")
    body["signature"] = (hmac.new(key.encode(), body["bundle_digest"].encode(), hashlib.sha256).hexdigest()
                         if key else "unsigned")
    (REL / "EVIDENCE_BUNDLE.json").write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    print(f"tests {body['tests']['passed']}/{body['tests']['total']} pass, {body['tests']['skipped']} skipped; "
          f"long runs {extra}; files {len(files)}; signature {body['signature'][:12]}")
    return 0 if ok else 1


def verify(_a):
    b = json.loads((REL / "EVIDENCE_BUNDLE.json").read_text())
    now = digests()
    changed = sorted(f for f in set(now) | set(b["files"]) if now.get(f) != b["files"].get(f))
    changed = [f for f in changed if not f.startswith("release/")]
    if changed:
        print("EVIDENCE STALE - files differ from bundle:", changed[:20])
        return 1
    print(f"evidence bundle matches all {len(now)} shipped files (version {b['version']})")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "verify"])
    ap.add_argument("--sign-key-env")
    ap.add_argument("--skip-long", action="store_true")
    a = ap.parse_args()
    sys.exit(build(a) if a.cmd == "build" else verify(a))
