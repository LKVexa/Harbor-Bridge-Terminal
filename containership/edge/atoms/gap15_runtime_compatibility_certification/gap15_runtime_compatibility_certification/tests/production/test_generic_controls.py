"""Per-component generic controls: configuration contract (xx-11), telemetry hooks (xx-12),
threat-model coverage (xx-13), runbook linkage (xx-15); plus policy signing and injection."""
import os
import re
import sys
import unittest

from fixtures import ENV, PART, T0, World, art
from gap15_runtime_compatibility_certification.production import authz, config, policy, signing, observability

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PKG, "tools"))
from threat_rows import ROWS  # noqa: E402

CONFIG_COMPONENTS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17",
                     "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32"]


class ConfigContractTest(unittest.TestCase):
    def test_every_runtime_component_has_a_validated_config_section(self):
        """controls: 01-11 02-11 03-11 04-11 05-11 06-11 07-11 08-11 09-11 10-11 11-11 12-11 13-11 14-11 15-11 16-11 17-11 18-11 19-11 20-11 21-11 22-11 23-11 24-11 25-11 26-11 27-11 28-11 29-11 30-11 31-11 32-11"""
        secs = config.component_sections()
        self.assertEqual(sorted(c for c in CONFIG_COMPONENTS if c not in secs), [])
        base = {"environment": "prod", "partitions": [PART], "signing.key_ref": "kms://k", "authz.policy_ref": "file:///p",
                "api.tls_cert_ref": "file:///t"}
        merged = {**config.defaults(), **base}
        self.assertEqual(config.validate_config(merged), [])
        for key, (typ, default, rng, comp, desc) in config.CONFIG_SCHEMA.items():
            self.assertTrue(desc, key)
            if isinstance(rng, tuple):
                bad = dict(merged, **{key: rng[1] + 1 if typ is int else 2.0})
                self.assertTrue(config.validate_config(bad), key)  # out-of-range rejected


class TelemetryHooksTest(unittest.TestCase):
    """One end-to-end scenario; every component's declared hook must be observed in real output."""

    HOOKS = {
        "01": ("gauge", "gap15_audit_chain_ok"), "02": ("audit", "evidence.accepted"), "03": ("reject", "signature"),
        "04": ("reject", "provenance"), "05": ("reject", "attestation"), "06": ("clock", "freshness_rejections"),
        "07": ("reject", "auth"), "08": ("audit", "authz.denied"), "09": ("reject", "schema"),
        "10": ("counter", "gap15_evidence_accepted_total"), "11": ("counter", "gap15_revision_conflicts_total"),
        "12": ("gauge", "gap15_audit_chain_ok"), "13": ("audit", "revoke"), "14": ("requests", "ingest"),
        "20": ("audit", "lifecycle.mutate"), "21": ("verdict", "incompatible"), "25": ("audit-partition", PART),
        "26": ("exposition", "gap15_certifications_total"), "27": ("log", "evidence.ingested"),
        "28": ("verdict", "certified"), "30": ("audit", "admission.decided"), "31": ("audit", "conflict.opened"),
        "32": ("counter-cat", "capacity"), "24": ("verdict", "untested"), "23": ("policy-trace", "policy"),
    }

    def test_hooks_observed(self):
        """controls: 01-12 02-12 03-12 04-12 05-12 06-12 07-12 08-12 09-12 10-12 11-12 12-12 13-12 14-12 20-12 21-12 23-12 25-12 26-12 27-12 28-12 30-12 31-12 32-12"""
        from gap15_runtime_compatibility_certification.production.service import ServiceError
        from gap15_runtime_compatibility_certification.production.capacity import RateLimiter
        from gap15_runtime_compatibility_certification.production import timepolicy
        w = World()
        r = w.svc.ingest(w.producer(), w.evidence())
        k = w.key_for(r)
        d = w.svc.certify(w.reader(), k)
        w.svc.certify(w.reader(), w.key_for({"profile_id": "profile:none"}))
        w.svc.ingest(w.producer(), w.evidence(digest=art(2), result="incompatible", failure_class="deterministic"))
        w.svc.certify(w.reader(), w.key_for(r, digest=art(2)))
        for bad in (lambda: w.svc.ingest(w.producer(), w.evidence(key_id="producer-b-key")),
                    lambda: w.svc.ingest(w.producer(), w.evidence(prov_kw={"sbom_subject": art(9)})),
                    lambda: w.svc.ingest(w.producer(), w.evidence(quote_kw={"firmware": "1.0.0"})),
                    lambda: w.svc.ingest("bad", w.evidence()),
                    lambda: w.svc.ingest(w.reader(), w.evidence()),
                    lambda: w.svc.ingest(w.producer(), b"{}")):
            with self.assertRaises(ServiceError):
                bad()
        from gap15_runtime_compatibility_certification.production.store import Conflict
        try:
            w.svc.ingest_batch(w.producer(), [w.evidence(digest=art(3))], expected_revision=0)
        except ServiceError:
            pass
        w.svc.revoke(w.operator(), subject_type="artifact", subject_id=art(5), partition=PART, reason="x", severity="low")
        w.svc.lifecycle(w.operator(), partition=PART, runtime="wamr@2.1.0", state="deprecated", effective_at=T0, reason="r", source="s")
        w.svc.admit(w.reader(), {"request_id": "q", "artifact": art(1), "runtime": "wasmtime@21.0.0", "profile_id": k.profile_id,
                                 "partition": PART, "intent": "new"})
        w.advance(1)
        w.svc.ingest(w.producer("producer-b"), w.evidence(producer="producer-b", result="incompatible", failure_class="deterministic"))
        w.svc.limiter = RateLimiter(per_key_rate=0.001, per_key_burst=0.5, global_rate=1, global_burst=1, clock=lambda: 0.0)
        with self.assertRaises(ServiceError):
            w.svc.ingest(w.producer(), w.evidence(digest=art(4)))
        w.svc.readiness()
        bad_clock = timepolicy.TrustedClock([timepolicy.fixed_source([T0], confidence="low")], monotonic=lambda: 0.0)
        with self.assertRaises(timepolicy.TimeError_):
            bad_clock.require()
        audits = w.store.audit_events()
        actions = {a["action"] for a in audits}
        expo = w.svc.metrics.exposition()
        m = w.svc.metrics
        missing = []
        for comp, (kind, name) in self.HOOKS.items():
            ok = {
                "gauge": lambda: f"{name} 1" in expo,
                "audit": lambda: name in actions,
                "reject": lambda: m.get("gap15_evidence_rejections_total", category=name) > 0,
                "clock": lambda: bad_clock.metrics[name] > 0,
                "counter": lambda: m.get(name) > 0,
                "counter-cat": lambda: m.get("gap15_evidence_rejections_total", category=name) > 0,
                "requests": lambda: m.get("gap15_requests_total", op=name, outcome="ok") > 0,
                "verdict": lambda: m.get("gap15_certifications_total", verdict=name) > 0,
                "audit-partition": lambda: any(a["partition"] == name for a in audits),
                "exposition": lambda: name in expo,
                "log": lambda: any(name in line for line in w.svc.log.sink),
                "policy-trace": lambda: any(t.get("rule") == name for t in d["trace"]),
            }[kind]()
            if not ok:
                missing.append((comp, kind, name))
        self.assertEqual(missing, [])


class ThreatModelCoverageTest(unittest.TestCase):
    def test_one_threat_row_per_component(self):
        """controls: 01-13 02-13 03-13 04-13 05-13 06-13 07-13 08-13 09-13 10-13 11-13 12-13 13-13 14-13 15-13 16-13 17-13 18-13 19-13 20-13 21-13 22-13 23-13 24-13 25-13 26-13 27-13 28-13 29-13 30-13 31-13 32-13 33-13 34-13 35-13 36-13 37-13 38-13 39-13 40-13 41-13 42-13 43-13 44-13 45-13 46-13 47-13 48-13 49-13 50-13 51-13"""
        tm = open(os.path.join(PKG, "docs", "THREAT_MODEL.md")).read()
        self.assertEqual([r[0] for r in ROWS], [f"{i:02d}" for i in range(1, 52)])
        for r in ROWS:
            self.assertIn(f'id="tm-{r[0]}"', tm)
            self.assertTrue(all(cell for cell in r))


class RunbookLinkageTest(unittest.TestCase):
    def test_every_component_mapped_to_runbook(self):
        """controls: 01-15 02-15 03-15 04-15 05-15 06-15 07-15 08-15 09-15 10-15 11-15 12-15 13-15 14-15 15-15 16-15 17-15 18-15 19-15 20-15 21-15 22-15 23-15 24-15 25-15 26-15 27-15 28-15 29-15 30-15 31-15 32-15 33-15 34-15 35-15 36-15 37-15 38-15 39-15 40-15 41-15 42-15 43-15 44-15 45-15 46-15 47-15 48-15 49-15 50-15 51-15"""
        rb = open(os.path.join(PKG, "docs", "RUNBOOKS.md")).read()
        table = rb.split("## Component → runbook map", 1)[1]
        covered = set()
        for line in table.splitlines():
            if line.startswith("| ") and "rb-" in line:
                cell = line.split("|")[1]
                for a, b in re.findall(r"(\d\d)-(\d\d)", cell):
                    covered |= {f"{i:02d}" for i in range(int(a), int(b) + 1)}
                covered |= set(re.findall(r"\b(\d\d)\b", cell))
                for anchor in re.findall(r"rb-[a-z0-9-]+", line):
                    self.assertIn(f'id="{anchor}"', rb, anchor)
        self.assertEqual(sorted({f"{i:02d}" for i in range(1, 52)} - covered), [])


class PolicySigningTest(unittest.TestCase):
    def test_policy_bundles_signed_and_verified_before_activation(self):
        """controls: 08-07 23-06"""
        w = World()
        w.trust.add(signing.TrustedKey("policy-key", "policy-admin", w.kp.generate("policy-key"), scopes=frozenset({"policy:sign"})))
        b2 = authz.PolicyBundle("authz:2", list(w.authz.bundle.rules))
        with self.assertRaises(authz.AuthzError):
            w.authz.activate(b2, trust=w.trust, signature=None)
        sig = authz.sign_bundle(w.kp, "policy-key", b2, signed_at=T0)
        w.authz.activate(b2, trust=w.trust, signature=sig)
        self.assertEqual(w.authz.bundle.revision, "authz:2")
        b3 = authz.PolicyBundle("authz:3", list(w.authz.bundle.rules)[:1])
        with self.assertRaises(authz.AuthzError):
            w.authz.activate(b3, trust=w.trust, signature=sig)  # signature for a different bundle
        ps = policy.PolicySet("p:9", [])
        psig = authz.sign_bundle(w.kp, "policy-key", ps, signed_at=T0, kind="precedence-policy")
        self.assertTrue(authz.verify_bundle(w.trust, psig, ps, kind="precedence-policy"))


class InjectionTest(unittest.TestCase):
    def test_sql_and_path_injection_inert(self):
        """controls: 36-05"""
        w = World()
        w.svc.ingest(w.producer(), w.evidence())
        self.assertEqual(w.store.lookup(PART, artifact_digest="x' OR '1'='1"), [])
        self.assertEqual(w.store.lookup("acme/prod/edge-1' OR 1=1 --"), [])
        from gap15_runtime_compatibility_certification.production.partition import Partition, PartitionError
        with self.assertRaises(PartitionError):
            Partition.parse("../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
