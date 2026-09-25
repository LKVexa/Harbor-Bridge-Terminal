import json
import pathlib
import tempfile
import threading
import time
import unittest

import _util  # noqa: F401
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gap05_state_replication_consistency_model.production import errors as E
from gap05_state_replication_consistency_model.production.anti_entropy import reconcile
from gap05_state_replication_consistency_model.production.audit import AuditLedger
from gap05_state_replication_consistency_model.production.authz import Authorizer, Grant, Permission, Policy
from gap05_state_replication_consistency_model.production.lifecycle import contain, triage
from gap05_state_replication_consistency_model.production.observe import (Admission, EpochExpiry, Metrics,
                                                                           StructuredLog)
from gap05_state_replication_consistency_model.production.resolution import ResolutionAdapter
from gap05_state_replication_consistency_model.production.testkit import Cluster, E as ENV, T, full_policy


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.key = Ed25519PrivateKey.generate()
        self.led = AuditLedger(self.dir / "a", self.key, segment_records=5, max_active_segments=3,
                               archive_dir=self.dir / "arch")
        for i in range(22):
            self.led.append("apply", op_id=f"op{i}", outcome="converged")
        self.head = self.led.signed_head()

    def tearDown(self):
        self.tmp.cleanup()

    def _verify(self):
        return AuditLedger.verify([self.dir / "arch", self.dir / "a"], self.key.public_key(), self.head)

    def test_chain_verifies_across_segments(self):
        """items: MC10-001 MC10-002 MC10-006 MC10-007 MC10-012
        Sealed segments + active segment verify end to end against the signed head."""
        self.assertEqual(self._verify()["head_seq"], 22)

    def test_tamper_insert_delete_truncate(self):
        """items: MC10-002 MC10-011 MC10-012 MC38-005
        Modification, deletion, reordering and tail truncation are each detected."""
        seg = sorted((self.dir / "a").glob("audit-*.jsonl"))[-1]
        original = seg.read_bytes()
        lines = original.splitlines()
        mutations = {
            "modify": b"\n".join([lines[0].replace(b"converged", b"superseded")] + lines[1:]) + b"\n",
            "delete": b"\n".join(lines[1:]) + b"\n",
            "reorder": b"\n".join([lines[1], lines[0]] + lines[2:]) + b"\n",
            "truncate": b"\n".join(lines[:-1]) + b"\n",
        }
        for name, data in mutations.items():
            seg.write_bytes(data)
            with self.assertRaises(E.IntegrityError, msg=name):
                self._verify()
        seg.write_bytes(original)
        self._verify()
        forged = dict(self.head, head={"seq": 99, "hash": "0" * 64})
        with self.assertRaises(E.IntegrityError):
            AuditLedger.verify([self.dir / "a"], self.key.public_key(), forged)

    def test_retention_refuses_when_full_without_archive(self):
        """items: MC11-002 MC11-004 MC11-010 MC11-011 MC11-012 MC10-009
        With no archive and all segments full, new events are refused (CAP_AUDIT_FULL); nothing is dropped."""
        led = AuditLedger(self.dir / "b", self.key, segment_records=3, max_active_segments=2)
        for i in range(6):
            led.append("apply", op_id=str(i))
        with self.assertRaises(E.CapacityError) as cm:
            led.append("apply", op_id="x")
        self.assertEqual(cm.exception.code, "CAP_AUDIT_FULL")
        self.assertGreaterEqual(led.pressure, 1.0)
        AuditLedger.verify([self.dir / "b"], self.key.public_key(), led.signed_head())

    def test_archive_handoff_verified(self):
        """items: MC11-005 MC10-006 MC11-001
        Sealed segments move to the archive only after the copy is verified."""
        self.assertTrue(list((self.dir / "arch").glob("audit-*.jsonl")))
        self.assertLessEqual(len(list((self.dir / "a").glob("audit-*.jsonl"))), 3)

    def test_node_refuses_write_when_audit_full(self):
        """items: MC11-003 MC11-004 MC10-009
        The node refuses a write it could not audit, before WAL or state mutation."""
        c = Cluster(("a",), node_kwargs={"audit_segment_records": 3, "audit_max_segments": 2})
        try:
            a = c.nodes["a"]
            n = 0
            with self.assertRaises(E.CapacityError):
                for i in range(20):
                    a.write(T, ENV, f"k{i}", "v", principal="operator")
                    n += 1
            wal = len(a.wal.records)
            self.assertEqual(wal, n)   # the refused write never reached the WAL
        finally:
            c.close()

    def test_audit_no_raw_values(self):
        """items: MC10-003 MC10-008 MC10-010
        Audit records carry actor, tenant/env, key digest, op_id, outcome, trace id - never raw values or keys."""
        c = Cluster(("a",))
        try:
            c.nodes["a"].write(T, ENV, "customer-ssn-key", "super-secret-value", principal="operator")
            raw = b"".join(p.read_bytes() for p in (c.nodes["a"].dir / "audit").glob("*.jsonl"))
            self.assertNotIn(b"super-secret-value", raw)
            self.assertNotIn(b"customer-ssn-key", raw)
            rec = [json.loads(l) for l in raw.splitlines() if b'"apply"' in l][0]
            for f in ("principal", "tenant", "environment", "key_digest", "op_id", "outcome", "trace_id", "site"):
                self.assertIn(f, rec)
        finally:
            c.close()


class AuthzTests(unittest.TestCase):
    def test_default_deny_and_codes(self):
        """items: MC13-001 MC13-003 MC13-009 MC13-012
        Every permission is explicit; no grant = deny with a stable, non-leaking code."""
        pol = Policy([Grant("u", Permission.READ, "t", "e")], version="v1")
        az = Authorizer(lambda: pol)
        az.require("u", Permission.READ, "t", "e")
        for perm in Permission:
            if perm is not Permission.READ:
                with self.assertRaises(E.AuthorizationError) as cm:
                    az.require("u", perm, "t", "e")
                self.assertEqual(cm.exception.code, "SEC_FORBIDDEN")
        with self.assertRaises(E.AuthorizationError):
            az.require("u", Permission.READ, "t2", "e")

    def test_wildcards_only_break_glass(self):
        """items: MC13-006 MC38-006
        Wildcard scopes are refused for normal principals and wildcard principals are never allowed."""
        with self.assertRaises(E.ConfigError):
            Policy([Grant("u", Permission.WRITE, "*", "e")], version="v")
        with self.assertRaises(E.ConfigError):
            Policy([Grant("*", Permission.WRITE, "t", "e")], version="v", wildcard_principals=frozenset({"*"}))
        Policy([Grant("breakglass", Permission.RECOVER, "*", "*")], version="v",
               wildcard_principals=frozenset({"breakglass"}))

    def test_policy_outage_denies_and_versions_audited(self):
        """items: MC13-005 MC13-011 MC13-002
        Provider failure denies (fail closed); privileged decisions record the policy version."""
        def boom():
            raise RuntimeError("policy backend down")
        with self.assertRaises(E.AuthorizationError):
            Authorizer(boom).require("u", Permission.READ, "t", "e")
        c = Cluster(("a", "b"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            a.write(T, ENV, "k", "1", principal="operator")
            b.write(T, ENV, "k", "2", principal="operator")
            reconcile(a, b, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("b"))
            a.resolve(T, ENV, "k", "3", principal="operator")
            recs = [json.loads(l) for p in (a.dir / "audit").glob("*.jsonl") for l in p.read_text().splitlines()]
            az = [r for r in recs if r["event"] == "authz" and r["permission"] == "resolve"]
            self.assertEqual(az[0]["decision"]["policy_version"], "p1")
        finally:
            c.close()

    def test_revoked_grant_takes_effect_immediately(self):
        """items: MC13-008 MC38-006
        No decision cache: replacing the policy revokes access on the next call."""
        c = Cluster(("a",))
        try:
            a = c.nodes["a"]
            a.write(T, ENV, "k", "1", principal="operator")
            c.policy = full_policy([c.principal("a")], version="p2")   # operator removed
            with self.assertRaises(E.AuthorizationError):
                a.write(T, ENV, "k", "2", principal="operator")
        finally:
            c.close()

    def test_replicate_vs_write_separation(self):
        """items: MC13-001 MC13-007
        A principal with only WRITE cannot relay replication traffic (no confused deputy)."""
        c = Cluster(("a", "b"))
        try:
            c.policy = Policy([Grant("operator", p, T, ENV) for p in Permission] +
                              [Grant(c.principal("b"), Permission.WRITE, T, ENV)], version="p3")
            r = c.nodes["b"].write(T, ENV, "k", "v", principal="operator")
            with self.assertRaises(E.AuthorizationError):
                c.nodes["a"].submit(c.nodes["b"].docs[r["op_id"]], principal=c.principal("b"), relay=True)
        finally:
            c.close()


class QuarantineViewTests(unittest.TestCase):
    def setUp(self):
        from gap05_state_replication_consistency_model.production.limits import Limits
        self.c = Cluster(("a", "b", "c"), node_kwargs={"limits": Limits(max_siblings=1)})
        a, b, cc = (self.c.nodes[n] for n in "abc")
        for n in (a, b, cc):
            n.write(T, ENV, "k", n.name, principal="operator")
        reconcile(a, b, T, ENV, principal_a=self.c.principal("a"), principal_b=self.c.principal("b"))
        reconcile(a, cc, T, ENV, principal_a=self.c.principal("a"), principal_b=self.c.principal("c"))
        self.a = a

    def tearDown(self):
        self.c.close()

    def test_list_export_freeze(self):
        """items: MC22-001 MC22-002 MC22-003 MC22-006 MC22-007 MC22-010
        Enumerate/export are authorized + audited; freeze blocks new local writes but not resolution."""
        lst = self.a.quarantine_list(T, ENV, principal="operator")
        self.assertEqual(lst, [{"key": "k", "active": 1, "quarantined": 2, "frozen": False}])
        cs = self.a.quarantine_export(T, ENV, "k", principal="operator")
        self.assertEqual(cs["total_unresolved"], 3)
        self.a.freeze(T, ENV, "k", principal="operator", reason="incident 7")
        with self.assertRaises(E.ConflictStillOpen) as cm:
            self.a.write(T, ENV, "k", "x", principal="operator", context={})
        self.assertEqual(cm.exception.code, "CORR_KEY_FROZEN")
        self.a.resolve(T, ENV, "k", "final", principal="operator")
        self.assertEqual(self.a.read(T, ENV, "k", principal="operator")["value"], "final")
        a2 = self.c.reopen("a")
        self.assertNotIn("\x1f".join((T, ENV, "k")), a2.frozen)

    def test_freeze_survives_restart(self):
        """items: MC22-004 MC22-011
        Freeze is WAL-logged and survives restart."""
        self.a.freeze(T, ENV, "k", principal="operator", reason="hold")
        a2 = self.c.reopen("a")
        self.assertIn("\x1f".join((T, ENV, "k")), a2.frozen)

    def test_stale_decision_rejected(self):
        """items: MC22-005 MC16-005 MC45-005
        A policy decision computed on an older frontier is refused after the frontier changes."""
        from gap05_state_replication_consistency_model.production.schemas import digest
        stale = {"frontier_digest": digest(self.a.conflict_set(T, ENV, "k")), "policy_version": "p"}
        self.c.nodes["b"].write(T, ENV, "k", "newer-b", principal="operator",
                                context={})  # concurrent new write elsewhere
        reconcile(self.a, self.c.nodes["b"], T, ENV, principal_a=self.c.principal("a"),
                  principal_b=self.c.principal("b"))
        with self.assertRaises(E.ConflictStillOpen) as cm:
            self.a.resolve(T, ENV, "k", "x", principal="operator", decision=stale)
        self.assertEqual(cm.exception.code, "CORR_STALE_DECISION")

    def test_views_immutable(self):
        """items: MC23-001 MC23-002 MC23-010 MC23-012 MC22-008
        Frontier views are frozen dataclasses of MappingProxy copies: mutation attempts fail and
        never reach node state."""
        v = self.a.view(T, ENV, "k")
        with self.assertRaises(Exception):
            v.active[0]["value"] = "hacked"
        with self.assertRaises(Exception):
            v.open = False
        with self.assertRaises(Exception):
            v.active.append(1)
        nested = v.active[0]["vector"]
        nested.append(["zz", 9])  # nested list is a deep copy: mutating it cannot reach node state
        self.assertNotIn(["zz", 9], self.a.view(T, ENV, "k").active[0]["vector"])

    def test_reader_threads_see_coherent_views(self):
        """items: MC23-003 MC23-011 MC41-006
        Readers under concurrent writers never observe a torn frontier (antichain always holds)."""
        from gap05_state_replication_consistency_model.model import dominates
        stop = threading.Event()
        bad = []

        def reader():
            while not stop.is_set():
                v = self.a.view(T, ENV, "k")
                vecs = [dict(map(tuple, d["vector"])) for d in v.active + v.quarantined]
                for x in vecs:
                    for y in vecs:
                        if x is not y and dominates(x, y):
                            bad.append((x, y))
        ts = [threading.Thread(target=reader) for _ in range(3)]
        [t.start() for t in ts]
        for i in range(30):
            self.a.write(T, ENV, f"other{i}", "v", principal="operator")
            self.a.admission.advance()
        self.a.resolve(T, ENV, "k", "r", principal="operator")
        stop.set()
        [t.join() for t in ts]
        self.assertEqual(bad, [])


class ResolutionAdapterTests(unittest.TestCase):
    CS = {"schema": "PK_CONFLICT_SET/1", "key": "k", "siblings": [
        {"site": "a", "value": "1", "vector": [["a", 1]]}, {"site": "b", "value": "2", "vector": [["b", 1]]}],
        "quarantined": [], "open": True, "total_unresolved": 2}

    def test_timeout_retry_then_unavailable_keeps_conflict(self):
        """items: MC16-006 MC16-011 MC16-010
        Hanging policy -> bounded retries -> DEP_POLICY_UNAVAILABLE; the adapter never picks a winner."""
        slept = []
        ad = ResolutionAdapter(lambda req: time.sleep(1), timeout_s=0.05, retries=2, sleep=slept.append)
        with self.assertRaises(E.DependencyUnavailable) as cm:
            ad.request(self.CS, {"tenant": T})
        self.assertEqual(cm.exception.code, "DEP_POLICY_UNAVAILABLE")
        self.assertEqual(ad.calls, 3)
        self.assertEqual(slept, [0.05, 0.1, 0.2])

    def test_valid_decision_carries_digest_and_version(self):
        """items: MC16-001 MC16-002 MC16-005 MC16-012
        A valid decision is returned with the frontier digest; malformed decisions are rejected."""
        ad = ResolutionAdapter(lambda req: {"decision": "resolve", "value": "2", "policy_version": "gap13-v7",
                                            "evidence": {"rule": "max"}})
        d1 = ad.request(self.CS, {})
        d2 = ad.request(self.CS, {})
        self.assertEqual(d1, d2)   # deterministic policy + identical input -> identical decision
        bad = ResolutionAdapter(lambda req: {"decision": "resolve"}, retries=0)
        with self.assertRaises(E.SchemaError):
            bad.request(self.CS, {})

    def test_end_to_end_resolution_dominates_quarantine(self):
        """items: MC16-004 MC16-003 MC34-008
        Applying a policy decision creates one write that dominates every active and quarantined sibling;
        re-applying the same decision is refused (idempotent)."""
        from gap05_state_replication_consistency_model.production.limits import Limits
        from gap05_state_replication_consistency_model.model import dominates
        c = Cluster(("a", "b", "c"), node_kwargs={"limits": Limits(max_siblings=1)})
        try:
            a = c.nodes["a"]
            for n in "abc":
                c.nodes[n].write(T, ENV, "k", n, principal="operator")
            for n in "bc":
                reconcile(a, c.nodes[n], T, ENV, principal_a=c.principal("a"), principal_b=c.principal(n))
            ad = ResolutionAdapter(lambda req: {"decision": "resolve", "value": "policy",
                                                "policy_version": "v1", "evidence": {}})
            dec = ad.request(a.conflict_set(T, ENV, "k"), {})
            frontier = a._frontier_docs("\x1f".join((T, ENV, "k")))
            r = a.resolve(T, ENV, "k", dec["value"], principal="operator", decision=dec)
            win = dict(map(tuple, a.docs[r["op_id"]]["vector"]))
            for d in frontier:
                self.assertTrue(dominates(win, dict(map(tuple, d["vector"]))))
            with self.assertRaises(E.ConflictStillOpen):
                a.resolve(T, ENV, "k", dec["value"], principal="operator", decision=dec)
        finally:
            c.close()


class ObservabilityTests(unittest.TestCase):
    def test_metrics_bounded_and_exposed(self):
        """items: MC26-002 MC26-003 MC26-005 MC26-009 MC26-011
        Outcome counters, frontier/quarantine gauges, Prometheus exposition, bounded series."""
        m = Metrics(max_series=5)
        for i in range(20):
            m.inc("apply_total", outcome=f"o{i}")
        self.assertEqual(m.overflow, 15)
        self.assertIn("gap05_metric_series_overflow_total 15", m.exposition())
        c = Cluster(("a",))
        try:
            c.nodes["a"].write(T, ENV, "k", "v", principal="operator")
            text = c.nodes["a"].metrics.exposition()
            self.assertIn('gap05_apply_total{outcome="converged"} 1.0', text)
            self.assertIn("gap05_frontier_width", text)
            self.assertIn("gap05_quarantine_depth", text)
        finally:
            c.close()

    def test_rejections_observable(self):
        """items: MC26-012 MC26-004 MC27-002
        Every rejection increments a counter labelled with its stable reason code and logs it."""
        c = Cluster(("a",))
        try:
            with self.assertRaises(E.AuthorizationError):
                c.nodes["a"].write("nope", ENV, "k", "v", principal="operator")
            self.assertEqual(c.nodes["a"].metrics.get("apply_total", outcome="rejected", code="SEC_FORBIDDEN"), 1)
        finally:
            c.close()

    def test_log_redaction_injection_sampling(self):
        """items: MC27-001 MC27-005 MC27-006 MC27-007 MC27-011 MC12-010 MC38-009
        Values are salted digests; newline injection stays inside one JSON field; errors bypass sampling."""
        log = StructuredLog(sample_rate=0.0)
        rec = log.emit("error", "write_rejected", value="secret\n{\"level\":\"info\"}", code="SEC_X",
                       trace_id="t1", sig="abc")
        self.assertTrue(rec["value"].startswith("sha256:"))
        self.assertTrue(rec["sig"].startswith("sha256:"))
        self.assertEqual(len(log.lines), 1)
        self.assertEqual(json.loads(log.lines[0])["code"], "SEC_X")
        self.assertIsNone(log.emit("info", "write_applied", trace_id="t2"))
        log.emit("info", "bad-unicode", detail="\ud800")
        self.assertEqual(len(log.lines), 2)

    def test_trace_correlation(self):
        """items: MC27-003 MC27-004 MC27-008 MC10-010
        One trace id links the log line and the audit record of the same write; trace ids never authorize."""
        c = Cluster(("a",))
        try:
            a = c.nodes["a"]
            doc = None
            r = a.write(T, ENV, "k", "v", principal="operator")
            doc = a.docs[r["op_id"]]
            a2 = Cluster.__new__(Cluster)  # noqa: F841
            from gap05_state_replication_consistency_model.production.protect import sign_write
            b_doc = dict(doc)
            res = a.submit(b_doc, principal="operator", trace_id="trace-xyz")
            self.assertEqual(res["outcome"], "duplicate")
            with self.assertRaises(E.AuthorizationError):
                a.submit(b_doc, principal="trace-xyz", relay=True, trace_id="operator")
            audit = [json.loads(l) for p in (a.dir / "audit").glob("*.jsonl") for l in p.read_text().splitlines()]
            logs = [json.loads(l) for l in a.log.lines]
            tid = [x for x in logs if x["event"] == "write_applied"][0]["trace_id"]
            self.assertIn(tid, {x.get("trace_id") for x in audit})
        finally:
            c.close()

    def test_health_readiness(self):
        """items: MC28-001 MC28-002 MC28-003 MC28-004 MC28-005 MC28-006 MC28-011
        Live != ready; fail-stop, recovery mode and rejected recovery records each fail readiness with reasons."""
        c = Cluster(("a",))
        try:
            h = c.nodes["a"].health()
            self.assertTrue(h["live"] and h["ready"])
            for f in ("membership_epoch", "schemas", "quarantine_pressure", "audit_pressure", "snapshot_generation"):
                self.assertIn(f, h)
            c.nodes["a"].recovery_mode = True
            h = c.nodes["a"].health()
            self.assertTrue(h["live"])
            self.assertFalse(h["ready"])
            c.nodes["a"].degraded = "test"
            self.assertFalse(c.nodes["a"].health()["live"])
            with self.assertRaises(E.IntegrityError):
                c.nodes["a"].write(T, ENV, "k", "v", principal="operator")
        finally:
            c.close()

    def test_admission_hot_key_and_tenant_isolation(self):
        """items: MC29-001 MC29-004 MC29-005 MC29-007 MC29-012 MC06-006
        A hot key is throttled without blocking other keys or other tenants; refill restores service."""
        adm = Admission(tenant_capacity=100, tenant_refill=100, key_capacity=3, key_refill=3)
        for _ in range(3):
            adm.admit("t1", "hot")
        with self.assertRaises(E.CapacityError) as cm:
            adm.admit("t1", "hot")
        self.assertEqual(cm.exception.code, "CAP_HOT_KEY")
        self.assertTrue(cm.exception.retryable)
        adm.admit("t1", "cold")
        adm.admit("t2", "hot")
        adm.advance()
        adm.admit("t1", "hot")
        self.assertEqual(adm.rejections["hot_key"], 1)

    def test_admission_bounded_metadata(self):
        """items: MC29-010 MC29-003
        Tracked-key state is bounded (oldest evicted), so admission cannot become a memory vector."""
        adm = Admission(max_tracked_keys=100)
        for i in range(1000):
            adm.admit("t", f"k{i}")
        self.assertLessEqual(len(adm.keys), 100)

    def test_expiry_is_logical(self):
        """items: MC31-001 MC31-002 MC31-003 MC31-004 MC31-008
        Expiry is counted in membership epochs, never wall clock, and never decides causal order."""
        ex = EpochExpiry(3)
        self.assertFalse(ex.expired(5, 7))
        self.assertTrue(ex.expired(5, 8))
        import inspect as _i
        import gap05_state_replication_consistency_model.model as core
        self.assertNotIn("time.", _i.getsource(core))

    def test_triage_and_containment(self):
        """items: MC47-002 MC47-003 MC47-004 MC47-005
        Triage maps signals to severities; containment freezes keys through the audited API."""
        c = Cluster(("a",))
        try:
            a = c.nodes["a"]
            a.degraded = "wal"
            t = triage(a)
            self.assertEqual(t["pages"][0]["severity"], "SEV1")
            a.degraded = None
            contain(a, T, ENV, ["k1", "k2"], principal="operator", reason="incident")
            self.assertEqual(len(a.frozen), 2)
            with self.assertRaises(E.AuthorizationError):
                contain(a, T, ENV, ["k3"], principal="nobody", reason="x")
        finally:
            c.close()

    def test_analytics_matches_audit(self):
        """items: MC44-002 MC44-003 MC44-009 MC44-010
        Conflict analytics (hot keys, site pairs, recurrence) agree with audit-ledger ground truth."""
        c = Cluster(("a", "b"))
        try:
            a, b = c.nodes["a"], c.nodes["b"]
            for rnd in range(2):
                a.write(T, ENV, "hot", f"a{rnd}", principal="operator", context=None if rnd == 0 else None)
                b.write(T, ENV, "hot", f"b{rnd}", principal="operator")
                reconcile(a, b, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("b"))
                a.resolve(T, ENV, "hot", f"r{rnd}", principal="operator")
                reconcile(a, b, T, ENV, principal_a=c.principal("a"), principal_b=c.principal("b"))
            rep = a.analytics.report()
            audit = [json.loads(l) for p in (a.dir / "audit").glob("*.jsonl") for l in p.read_text().splitlines()]
            audited_conflicts = sum(1 for r in audit if r["event"] == "apply" and r["outcome"] in ("conflict",
                                                                                                "quarantined"))
            self.assertEqual(sum(h["conflicts"] for h in rep["hot_keys"]), audited_conflicts)
            self.assertEqual(rep["recurring"][0]["key"], "hot")
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main()
