import datetime as dt
import json
import os
import shutil
import tarfile
import unittest

from gap03_topology_aware_scheduler.controlplane import (alerts, backup, exitgate, governance, identity, rollout, supply_chain,
                                                         waivers)
from gap03_topology_aware_scheduler.controlplane.errors import SchedulerError
from gap03_topology_aware_scheduler.controlplane.ledger_store import LedgerStore
from gap03_topology_aware_scheduler.controlplane.topology_store import TopologyStore
from gap03_topology_aware_scheduler.tests.cp._util import TmpCase, covers

ROOT = governance.ROOT
TODAY = dt.date(2026, 9, 22)


class Ownership(unittest.TestCase):
    @covers("MC-036", 26, 27)
    @covers("MC-036", 9, 12, 15, 25)
    def test_mc036_metadata_complete_and_check_blocks_placeholders(self):
        o = json.load(open(os.path.join(ROOT, "governance/OWNERS.json")))
        for k in ("service_owner", "oncall", "escalation", "raci", "service_catalog", "transfer_procedure", "high_risk_change_review"):
            self.assertIn(k, o)
        for area in ("architecture", "code", "security", "operations", "schema_contracts", "state_stores", "adjacent_integrations", "release"):
            self.assertIn(area, o["raci"])
        b = governance.ownership_blockers()
        self.assertIn("no accountable service owner", b)  # honest: owners are not assigned
        self.assertIn("CODEOWNERS uses placeholder handles", b)

    @covers("MC-036", 8, 10, 11)
    def test_mc036_escalation_codeowners_transfer(self):
        o = json.load(open(os.path.join(ROOT, "governance/OWNERS.json")))
        self.assertEqual([e["severity"] for e in o["escalation"]], ["SEV1", "SEV2", "SEV3", "SEV4"])
        co = open(os.path.join(ROOT, "governance/CODEOWNERS")).read()
        for crit in ("identity.py", "ledger_store.py", "coordination.py", "wire.py", "policy/", "WAIVERS.json", "ci/"):
            self.assertIn(crit, co)
        self.assertIn("revoked", o["transfer_procedure"])


class ADR(unittest.TestCase):
    @covers("MC-037", 6, 7, 8, 9, 10, 11, 12, 14, 15)
    def test_mc037_adr_sections_and_honest_status(self):
        """ADR completeness (all sections, supersession rule, diagram) and honest Proposed status."""
        st = governance.adr_status()
        self.assertEqual(st["missing_sections"], [])
        self.assertTrue(st["has_supersession_rule"])
        self.assertTrue(st["has_mermaid"])
        self.assertEqual(st["status"], "Proposed")
        self.assertFalse(st["approved"])  # CHK-013 stays blocked until three named approvals exist


class Provenance(unittest.TestCase):
    @covers("MC-039", 7, 11, 13)
    def test_mc039_absence_recorded_not_fabricated(self):
        """the missing MASTER.md is recorded with search evidence and digests; nothing fabricated."""
        p = governance.provenance_status()
        self.assertEqual(p["status"], "BLOCKED")
        self.assertGreaterEqual(len(p["searched"]), 2)
        self.assertTrue(any("sha256" in s for s in p["searched"]))
        for root, _, files in os.walk(ROOT):
            self.assertNotIn("MASTER.md", files)


class Supply(TmpCase):
    def pkg(self):
        d = os.path.join(self.tmp, "pkg")
        os.makedirs(os.path.join(d, "sub"))
        open(os.path.join(d, "a.py"), "w").write("x=1\n")
        open(os.path.join(d, "sub", "b.txt"), "w").write("b\n")
        return d

    @covers("MC-040", 6, 7, 8, 25)
    def test_mc040_manifest_sbom_provenance(self):
        d = self.pkg()
        m = supply_chain.manifest(d)
        self.assertEqual(sorted(m), ["a.py", "sub/b.txt"])
        text = supply_chain.manifest_text(m)
        self.assertEqual(supply_chain.verify_manifest(d, text), [])
        open(os.path.join(d, "a.py"), "a").write("#")
        open(os.path.join(d, "c.py"), "w").write("")
        probs = supply_chain.verify_manifest(d, text)
        self.assertIn("modified: a.py", probs)
        self.assertIn("unlisted: c.py", probs)
        sb = supply_chain.sbom("4.3.0", m)
        self.assertEqual(sb["bomFormat"], "CycloneDX")
        self.assertEqual(sb["properties"][0]["value"], "0")
        pv = supply_chain.provenance("4.3.0", m, builder_id="local:unverified", source_uri="file://x")
        self.assertEqual(pv["subject"][0]["digest"]["sha256"], supply_chain.artifact_digest(m))

    @covers("MC-040", 9, 10, 17, 27)
    def test_mc040_release_signature_bound_to_digest(self):
        """adversarial: a tampered signature, a downgraded algorithm or a signature for a different artifact digest are all rejected."""
        key = identity.SigningKey.generate("rel1", "spiffe://prod.example/issuer/release")
        m = supply_chain.manifest(self.pkg())
        stmt = supply_chain.provenance("4.3.0", m, builder_id="b", source_uri="s")
        env = supply_chain.sign_release(key, stmt)
        supply_chain.verify_release(env, key.public, expected_digest=supply_chain.artifact_digest(m))
        with self.assertRaises(SchedulerError):
            supply_chain.verify_release(env, key.public, expected_digest="0" * 64)
        bad = dict(env, signature=env["signature"][:-4] + "AAAA")
        with self.assertRaises(SchedulerError):
            supply_chain.verify_release(bad, key.public, expected_digest=supply_chain.artifact_digest(m))
        with self.assertRaises(SchedulerError):
            supply_chain.verify_release(dict(env, alg="none"), key.public, expected_digest=supply_chain.artifact_digest(m))

    @covers("MC-040", 11, 12, 13)
    def test_mc040_vulnerability_scan_never_fakes_clean(self):
        sb = supply_chain.sbom("4.3.0", {"a": "b"})
        self.assertEqual(supply_chain.vulnerability_scan(sb, {"items": []})["status"], "INDETERMINATE")
        adv = {"source": "osv-snapshot", "fetched_at": "2026-09-22", "items": [{"package": "cpython", "affected": [sb["components"][0]["version"]]}]}
        self.assertEqual(supply_chain.vulnerability_scan(sb, adv)["status"], "VULNERABLE")


class Rollout(unittest.TestCase):
    def obs(self, bad_at=None):
        def observe(digest, pct):
            o = {"error_ratio": 0.0001, "p99_ms": 8.0, "fencing_rejections": 0, "readiness": 1.0, "audit_write_failures": 0}
            if bad_at is not None and pct == bad_at and digest == "new":
                o["error_ratio"] = 0.05
            return o
        return observe

    @covers("MC-041", 26)

    @covers("MC-041", 6, 7, 8, 9, 25)
    def test_mc041_promotes_through_stages(self):
        shifts, rec = [], []
        r = rollout.run(candidate="new", previous="old", gate_result={"decision": "GO", "artifact_digest": "new"},
                        observe=self.obs(), shift=lambda d, p: shifts.append((d, p)), record=rec.append)
        self.assertEqual(r["result"], "PROMOTED")
        self.assertEqual([p for _, p in shifts], [1, 10, 50, 100])

    @covers("MC-041", 10, 11, 12, 13, 27)
    def test_mc041_automatic_rollback_and_gate_binding(self):
        """fault injection: an error-ratio breach at 10% triggers automatic rollback; promotion without a GO for the exact digest is refused."""
        shifts, rec = [], []
        r = rollout.run(candidate="new", previous="old", gate_result={"decision": "GO", "artifact_digest": "new"},
                        observe=self.obs(bad_at=10), shift=lambda d, p: shifts.append((d, p)), record=rec.append)
        self.assertEqual(r["result"], "ROLLED_BACK")
        self.assertEqual(shifts[-1], ("old", 100))
        self.assertEqual(rec[-1]["event"], "rollback")
        for gate in ({"decision": "NO_GO", "artifact_digest": "new"}, {"decision": "GO", "artifact_digest": "other"}):
            with self.assertRaises(SchedulerError):
                rollout.run(candidate="new", previous="old", gate_result=gate, observe=self.obs(), shift=lambda *a: None,
                            record=lambda *a: None)


class Backup(TmpCase):
    def stores(self):
        t = TopologyStore(self.d("s/topology"))
        t.submit({"type": "batch", "expected_generation": 0, "mutations": [{"op": "create", "id": "eu", "node_type": "region", "parent": None}]})
        led = LedgerStore(self.d("s/ledger"))
        led.submit({"type": "set_capacity", "capacity": 3})
        return {"topology": t, "ledger": led}

    @covers("MC-042", 26)

    @covers("MC-042", 6, 7, 8, 10, 25, 28)
    def test_mc042_backup_restore_round_trip_with_rto(self):
        """integration with real stores: backup -> restore -> invariants, head match and measured RTO."""
        st = self.stores()
        arc = os.path.join(self.tmp, "b.tgz")
        man = backup.backup(st, arc)
        self.assertEqual(set(man["stores"]), {"topology", "ledger"})
        out = backup.restore(arc, os.path.join(self.tmp, "restored"), {"topology": TopologyStore, "ledger": LedgerStore})
        self.assertEqual(out["stores"]["ledger"].state["capacity"], 3)
        self.assertEqual(out["stores"]["topology"].generation, 1)
        self.assertLess(out["rto_s"], 5)

    @covers("MC-042", 11, 12, 13, 15, 27)
    def test_mc042_tampered_or_unsafe_restore_refused(self):
        """adversarial: a tampered backup member fails checksum validation before activation; restore into a non-empty target is refused."""
        st = self.stores()
        arc = os.path.join(self.tmp, "b.tgz")
        backup.backup(st, arc)
        with self.assertRaises(SchedulerError):
            backup.restore(arc, self.d("s"), {"topology": TopologyStore, "ledger": LedgerStore})  # non-empty target
        bad = os.path.join(self.tmp, "bad.tgz")
        tampered = []
        with tarfile.open(arc) as src, tarfile.open(bad, "w:gz") as dst:
            for m in src.getmembers():
                data = src.extractfile(m).read()
                if m.name.startswith("ledger") and b'"capacity":3' in data:
                    data = data.replace(b'"capacity":3', b'"capacity":9')
                    tampered.append(m.name)
                import io
                m.size = len(data)
                dst.addfile(m, io.BytesIO(data))
        self.assertTrue(tampered)
        with self.assertRaises(SchedulerError):
            backup.restore(bad, os.path.join(self.tmp, "r2"), {"topology": TopologyStore, "ledger": LedgerStore})


class Incident(unittest.TestCase):
    @covers("MC-043", 26)
    @covers("MC-043", 6, 7, 8, 9, 10, 11, 12)
    def test_mc043_runbook_content_and_alert_links(self):
        """integration with the real alert catalog: every alert's runbook exists; severity, paging, containment, forensics, recovery and escalation sections present."""
        text = open(os.path.join(ROOT, "runbooks/incident-response.md")).read()
        for needle in ("SEV1", "SEV2", "Page", "Contain", "Forensics", "Recover", "Post-incident", "Escalation"):
            self.assertIn(needle, text)
        for a in alerts.ALERTS:
            self.assertTrue(os.path.exists(os.path.join(ROOT, a["runbook"])), a["runbook"])
        self.assertIn("NOT EXERCISED", text)


class Support(unittest.TestCase):
    @covers("MC-044", 6, 7, 8, 9, 10, 11)
    def test_mc044_policy_machine_readable_and_honest(self):
        """policy machine-readable, status PROPOSED: supported releases/branches with end-of-support dates and a
        maintenance window, vulnerability SLAs incl. actively-exploited emergency handling, patch qualification
        requirements, runtime upgrade cadence, EOL dates consistent with the compatibility matrix."""
        p = governance.support_policy()
        self.assertEqual(p["status"], "PROPOSED")
        self.assertEqual(p["vuln_sla_hours"]["critical"], 72)
        self.assertEqual(p["vuln_sla_hours"]["actively_exploited"], 24)  # emergency handling for exploited vulnerabilities
        self.assertEqual({r["status"] for r in p["supported_releases"]}, {"current", "security-fixes-only", "end-of-life"})
        self.assertIn("maintenance_window", p)
        for q in ("regression", "security verification", "compatibility matrix", "benchmark", "canary"):
            self.assertTrue(any(q in x for x in p["patch_qualification"]), q)
        self.assertIn("6 months", p["runtime_upgrade_cadence"])
        from gap03_topology_aware_scheduler.controlplane import compat
        for py, eol in p["runtime_eol"].items():
            self.assertEqual(compat.MATRIX["python"]["eol"][py], eol)


class Waivers(unittest.TestCase):
    def w(self, **kw):
        base = {"id": "W-1", "control_ids": ["MC-031-CHK-010"], "severity": "P1", "scope": "benchmarks", "owner": "alice",
                "created": "2026-09-01", "expires": "2026-10-15", "compensating_controls": ["local proposed thresholds"],
                "approval": {"approver": "bob", "record": "CHG-9"}, "status": "approved", "rationale": "no pinned runner",
                "residual_risk": "latency regressions detected late", "links": {"work_items": ["GAP03-12"], "rtm": ["MC-031-CHK-010"]},
                "applies_to_version": "4.3.0"}
        base.update(kw)
        return base

    @covers("MC-045", 6, 7, 8, 9, 10, 25, 27)
    def test_mc045_validation_expiry_and_coverage(self):
        """adversarial waivers: expired, ownerless, over-long and unapproved waivers cover nothing; compensating controls required."""
        self.assertEqual(waivers.validate(self.w(), today=TODAY), [])
        self.assertIn("expired", waivers.validate(self.w(expires="2026-09-01"), today=TODAY))
        self.assertIn("no accountable owner", waivers.validate(self.w(owner="UNASSIGNED"), today=TODAY))
        self.assertIn("expiry exceeds severity maximum", waivers.validate(self.w(severity="P0"), today=TODAY))
        self.assertIn("no approval record", waivers.validate(self.w(approval={}), today=TODAY))
        reg = [self.w(), self.w(id="W-2", status="draft")]
        self.assertEqual(waivers.covers(reg, "MC-031-CHK-010", today=TODAY)["id"], "W-1")
        self.assertIsNone(waivers.covers(reg, "MC-001-CHK-001", today=TODAY))
        self.assertEqual(waivers.expiring([self.w(expires="2026-09-30")], today=TODAY), ["W-1"])

    @covers("MC-045", 26)

    @covers("MC-045", 11, 12)
    def test_mc045_shipped_registry_is_empty_and_valid(self):
        self.assertEqual(waivers.load(os.path.join(ROOT, "WAIVERS.json")), [])


class ExitGate(TmpCase):
    def bundle(self, digest, t, keys):
        now = self.clock()
        ev = {c: {"artifact_digest": digest, "produced_at": now, "status": "PASS"} for c in exitgate.EVIDENCE_CLASSES}
        signs = {r: identity.sign_artifact(keys[r], "signoff", {"role": r, "artifact_digest": digest}, clock=self.clock)
                 for r in exitgate.SIGNOFF_ROLES}
        return {"artifact_digest": digest, "evidence": ev, "mandatory_checks": [{"id": "MC-001-CHK-001", "status": "SATISFIED"}],
                "signoffs": signs, "defects": [{"id": "DEF-01", "severity": "P1", "status": "FIXED"}], "waivers": [],
                "release_candidate": {"version": "4.3.0", "source_commit": "abc123", "config_digest": "c" * 64,
                                      "schema_digests": {"PK_TOPOLOGY/1.1": "s" * 64}}}

    def keys(self, t):
        ks = {}
        for r in exitgate.SIGNOFF_ROLES:
            k = identity.SigningKey.generate("k", f"spiffe://prod.example/issuer/{r}")
            t.add_key(k.issuer, k.kid, k.public)
            ks[r] = k
        return ks

    @covers("MC-046", 6, 7, 14, 15, 25, 26)
    def test_mc046_go_only_with_complete_independent_evidence(self):
        """integration/contract: a complete bundle with four independent Ed25519 sign-offs yields a signed GO verifiable by deployment automation only for the same digest."""
        t, _ = self.trust()
        ks = self.keys(t)
        b = self.bundle("d1", t, ks)
        r = exitgate.evaluate(b, artifact_digest="d1", trust=t, now=self.clock())
        self.assertEqual(r["decision"], "GO", r["reasons"])
        signed = exitgate.sign_result(r, ks["release"])
        self.assertTrue(exitgate.verify_result(t, signed, artifact_digest="d1"))
        self.assertFalse(exitgate.verify_result(t, signed, artifact_digest="d2"))

    @covers("MC-046", 8, 9, 10, 11, 12, 13, 17, 27)
    def test_mc046_fail_closed_matrix(self):
        """adversarial/fault: wrong digest, missing/stale/failed evidence, blocked checks, missing or duplicated (same-issuer) sign-offs and an absent trust store each force NO_GO."""
        t, _ = self.trust()
        ks = self.keys(t)
        cases = {}
        b = self.bundle("d1", t, ks); b["artifact_digest"] = "d2"; cases["wrong digest"] = b
        b = self.bundle("d1", t, ks); del b["evidence"]["sbom"]; cases["missing"] = b
        b = self.bundle("d1", t, ks); b["evidence"]["tests"]["produced_at"] = self.clock() - 15 * 86400; cases["stale"] = b
        b = self.bundle("d1", t, ks); b["evidence"]["security"]["status"] = "FAIL"; cases["failed"] = b
        b = self.bundle("d1", t, ks); b["mandatory_checks"][0]["status"] = "BLOCKED"; cases["blocked check"] = b
        b = self.bundle("d1", t, ks); del b["signoffs"]["security"]; cases["no signoff"] = b
        b = self.bundle("d1", t, ks); b["signoffs"]["sre"] = b["signoffs"]["technical"]; cases["same signer"] = b
        for name, bundle in cases.items():
            r = exitgate.evaluate(bundle, artifact_digest="d1", trust=t, now=self.clock())
            self.assertEqual(r["decision"], "NO_GO", f"{name}: {r}")
        self.assertEqual(exitgate.evaluate(self.bundle("d1", t, ks), artifact_digest="d1", trust=None)["decision"], "NO_GO")
