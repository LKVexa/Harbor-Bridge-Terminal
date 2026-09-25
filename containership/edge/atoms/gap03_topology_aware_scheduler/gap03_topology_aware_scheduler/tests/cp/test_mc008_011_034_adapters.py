import json
import os
import unittest

from gap03_topology_aware_scheduler import FairShare, Topology, score_candidates
from gap03_topology_aware_scheduler.controlplane import identity
from gap03_topology_aware_scheduler.controlplane.adapters import gap02, gap14, pln05, sch01
from gap03_topology_aware_scheduler.controlplane.errors import SchedulerError
from gap03_topology_aware_scheduler.controlplane.ledger_store import LedgerStore
from gap03_topology_aware_scheduler.controlplane.transactions import PlacementCoordinator, TxnJournal
from gap03_topology_aware_scheduler.tests.cp._util import TmpCase, covers

FX = os.path.join(os.path.dirname(gap02.__file__), "..", "fixtures")
T0 = 1_000_000.0


def fx(name):
    with open(os.path.join(FX, name), encoding="utf-8") as fh:
        return json.load(fh)


def topo():
    t = Topology()
    for n, p in {"a": ("eu", "dub", "r1"), "b": ("eu", "dub", "r2"), "c": ("eu", "ams", "r1"), "d": ("us", "iad", "r1")}.items():
        t.place(n, *p)
    return t


class SCH01(TmpCase):
    def coord(self, faults, tag):
        led = LedgerStore(self.d("l" + tag), clock=self.clock)
        led.submit({"type": "set_capacity", "capacity": 4})
        led.submit({"type": "set_reservations", "reserved": {"a": 2}, "entitlement_generation": 1})
        down = sch01.SCH01Harness(faults=faults)
        pc = PlacementCoordinator(journal=TxnJournal(self.d("j" + tag), clock=self.clock), ledger=led,
                                  topology_snapshot=topo().snapshot, downstream=down, fence=lambda: 1, clock=self.clock)
        return pc, led, down

    @covers("MC-008", 6, 7, 8, 25)
    def test_mc008_lossless_request_mapping_and_operation_id(self):
        t = topo()
        fs = FairShare(reserved={"a": 1}, capacity=4)
        res = score_candidates(t, "a", ["d", "b", "c"], fair_share=fs, tenant="a")
        req = sch01.to_request(txn="tx1", version="1.1", scoring_result=res, tenant="a", slots=1, fence=3, trace="00-x")
        self.assertEqual([r["node"] for r in req["ranked"]], res.ranked_nodes())
        self.assertEqual(req["fairness"]["state_token"], res.fairness.state_token)
        self.assertEqual(req["topology_generation"], res.topology_generation)
        out = sch01.SCH01Harness().place(dict(req, node="b"))
        self.assertTrue(out["operation_id"].startswith("sch01-"))

    @covers("MC-008", 9, 17, 27)
    def test_mc008_sch01_cannot_bypass_hard_constraints(self):
        """SCH-01 selection guard: an infeasible node needs an explicit override policy."""
        t = topo()
        res = score_candidates(t, "a", ["b"], fair_share=FairShare(capacity=4), tenant="a")
        req = sch01.to_request(txn="x", version="1.1", scoring_result=res, tenant="a", slots=1, fence=1,
                               infeasible={"d": "tee_unverified"})
        with self.assertRaises(SchedulerError):
            sch01.check_selection(req, "d")
        sch01.check_selection(req, "d", override_policy="POL-7")
        with self.assertRaises(SchedulerError):
            sch01.check_selection(req, "zzz")

    @covers("MC-008", 10, 11, 12, 14, 26, 27)
    def test_mc008_end_to_end_fixture_suite(self):
        """end-to-end fixtures: success, no feasible node, policy denial, stale, lost response (idempotent retry via status), timeout, busy."""
        for i, case in enumerate(fx("sch01.json")["cases"]):
            with self.subTest(case=case["name"]):
                pc, led, down = self.coord(list(case["faults"]), str(i))
                r = pc.place(txn=f"t{i}", workload={"id": "w"}, anchor="a", candidates=["b", "c"], tenant="a")
                self.assertEqual(r["state"], case["expect_state"])
                if r["state"] == "ABORTED":
                    self.assertNotEqual(led.state["claims"].get(f"t{i}", {}).get("state"), "pending")

    @covers("MC-008", 18)

    @covers("MC-008", 13, 26)
    def test_mc008_version_negotiation_before_side_effects(self):
        """untrusted-input validation: unsupported protocol versions are rejected before side effects."""
        self.assertEqual(sch01.negotiate(["1.0", "1.1", "2.0"]), "1.1")
        with self.assertRaises(SchedulerError):
            sch01.negotiate(["2.0"])
        h = sch01.SCH01Harness(versions=("2.0",))
        with self.assertRaises(SchedulerError) as cm:
            h.place({"txn": "x", "version": "1.1", "fence": 1, "node": "b"})
        self.assertEqual(cm.exception.code, "UNSUPPORTED_VERSION")
        self.assertEqual(h.placements, {})

    @covers("MC-008", 12)
    def test_mc008_error_taxonomy_complete(self):
        for native, (code, comp) in sch01.SCH_ERRORS.items():
            e = sch01.map_error(native)
            self.assertEqual(e.code, code)
            self.assertEqual(e.detail["compensation"], comp)
        self.assertEqual(sch01.map_error("E_WHATEVER").code, "INTERNAL")


class GAP02(TmpCase):
    @covers("MC-009", 6, 7, 15, 25, 26)
    def test_mc009_fixture_suite(self):
        for case in fx("gap02.json")["cases"]:
            with self.subTest(case=case["name"]):
                if "error" in case:
                    with self.assertRaises(SchedulerError) as cm:
                        gap02.normalize(case["input"])
                    self.assertEqual(cm.exception.code, case["error"])
                else:
                    rec = gap02.normalize(case["input"])
                    for k, v in case["expect"].items():
                        self.assertEqual(rec[k], v)

    @covers("MC-009", 12, 14, 27)
    def test_mc009_binding_duplicates_conflicts_and_hot_remove(self):
        """adversarial/fault: duplicate device identity, older generation replay, conflicting discovery sources and hot-removed accelerators."""
        inv = gap02.Inventory()
        base = fx("gap02.json")["cases"][0]["input"]
        inv.ingest(base)
        with self.assertRaises(SchedulerError):
            inv.ingest(dict(base, node="n9"))  # same device bound to two nodes
        with self.assertRaises(SchedulerError):
            inv.ingest(dict(base, generation=2))  # older generation
        with self.assertRaises(SchedulerError):
            inv.ingest(dict(base, source="gap02-b", cpus=8))  # conflicting source at same gen
        inv.ingest(dict(base, generation=4, accelerators=[]))  # accelerator removed
        self.assertEqual(inv.by_node["n1"]["accelerators"], [])
        ev = inv.reconcile({"n1", "n7"}, {"n1"}, T0)
        self.assertIn({"event": "topology_node_without_inventory", "node": "n7"}, ev)
        self.assertIn("inventory_digest", inv.snapshot_meta())

    @covers("MC-009", 10, 13, 27)
    def test_mc009_stale_unknown_never_sufficient_and_hard_predicates(self):
        """fault: stale or missing inventory is never treated as sufficient capability (fail closed)."""
        inv = gap02.Inventory(ttl_s=300)
        inv.ingest(fx("gap02.json")["cases"][0]["input"])
        self.assertEqual(inv.feasible("n1", {"accelerators": ["gpu.h100"]}, T0), (True, "ok"))
        self.assertEqual(inv.feasible("n1", {"accelerators": ["gpu.a100"]}, T0)[0], False)
        self.assertEqual(inv.feasible("n1", {"isa": "arm64"}, T0)[1], "isa")
        self.assertEqual(inv.feasible("n1", {}, T0 + 301)[1], "inventory_stale_or_missing")
        self.assertEqual(inv.feasible("ghost", {}, T0)[1], "inventory_stale_or_missing")

    @covers("MC-009", 11, 16, 27)
    def test_mc009_tee_claim_requires_attestation(self):
        """adversarial/authorization: an unattested TEE claim is not honoured; only a verified attestation enables it."""
        t, key = self.trust()
        base = dict(fx("gap02.json")["cases"][0]["input"], tee=True)
        inv = gap02.Inventory(trust=t, measurement_allowlist={"m1"})
        self.assertFalse(inv.ingest(base)["claims"]["tee"])
        claims = {"tee": True, "secure_boot": True, "measurement": "m1"}
        att = {"claims": claims, "envelope": identity.sign_artifact(key, "attestation", claims, clock=self.clock)}
        self.assertTrue(inv.ingest(dict(base, generation=5, attestation=att))["claims"]["tee"])


class GAP14(TmpCase):
    @covers("MC-010", 6, 7, 10, 15, 25, 26)
    def test_mc010_fixture_suite(self):
        snap = topo().snapshot()
        for case in fx("gap14.json")["cases"]:
            with self.subTest(case=case["name"]):
                g = gap14.Gravity()
                if "error" in case:
                    with self.assertRaises(SchedulerError) as cm:
                        g.ingest(case["input"], snap)
                    self.assertEqual(cm.exception.code, case["error"])
                else:
                    r = g.ingest(case["input"], snap)
                    self.assertEqual(g.contribution(r["id"], case["candidate"], snap, T0)["value"], case["expect_value"])

    @covers("MC-034", 13)

    @covers("MC-010", 8, 27)
    def test_mc010_authenticity_revision_staleness(self):
        """adversarial/fault: unsigned anchors, older revisions, conflicting provenance and stale anchors are rejected or flagged."""
        t, key = self.trust()
        snap = topo().snapshot()
        g = gap14.Gravity(trust=t)
        body = {"version": "1.0", "tenant": "t", "dataset": "d", "replicas": [{"node": "d", "bytes": 10**12}], "revision": 2,
                "observed_at": T0, "source": "gap14"}
        with self.assertRaises(SchedulerError):
            g.ingest(body, snap)  # unsigned
        rec = g.ingest(dict(body, envelope=identity.sign_artifact(key, "gravity_anchor", body)), snap)
        far = g.contribution(rec["id"], "a", snap, T0)
        near = g.contribution(rec["id"], "d", snap, T0)
        self.assertGreater(far["value"], near["value"])
        self.assertEqual(far["revision"], 2)
        self.assertEqual(g.contribution(rec["id"], "a", snap, T0 + 10_000)["status"], "stale")
        self.assertEqual(g.contribution(None, "a", snap, T0)["status"], "absent")
        old = dict(body, revision=1)
        with self.assertRaises(SchedulerError):
            g.ingest(dict(old, envelope=identity.sign_artifact(key, "gravity_anchor", old)), snap)
        conflict = dict(body, replicas=[{"node": "c", "bytes": 1}])
        with self.assertRaises(SchedulerError):
            g.ingest(dict(conflict, envelope=identity.sign_artifact(key, "gravity_anchor", conflict)), snap)

    @covers("MC-010", 12, 13, 20)
    def test_mc010_scoped_ids_and_soft_unless_hard_residency(self):
        snap = topo().snapshot()
        g = gap14.Gravity(salt=b"s")
        r = g.ingest({"version": "1.0", "tenant": "t", "dataset": "secret-orders", "replicas": [{"node": "d", "bytes": 5}],
                      "revision": 1, "observed_at": T0, "source": "x"}, snap)
        view = g.telemetry_view(r["id"])
        self.assertNotIn("secret-orders", json.dumps(view))
        self.assertNotIn("d", [v for v in view.values() if isinstance(v, str)])
        self.assertTrue(g.hard_residency_ok(r["id"], "a", snap))  # soft by default
        r2 = g.ingest({"version": "1.0", "tenant": "t", "dataset": "eu-only", "replicas": [{"node": "a", "bytes": 5}],
                       "revision": 1, "observed_at": T0, "source": "x", "residency_hard": True}, snap)
        self.assertFalse(g.hard_residency_ok(r2["id"], "d", snap))


class PLN05(TmpCase):
    @covers("MC-011", 6, 7, 9, 15, 25, 26)
    def test_mc011_fixture_suite(self):
        """fixtures for demand spike, low confidence, stale forecast, bad unit and unsupported version."""
        for case in fx("pln05.json")["cases"]:
            with self.subTest(case=case["name"]):
                d = pln05.Demand()
                if "error" in case:
                    with self.assertRaises(SchedulerError) as cm:
                        d.ingest(case["input"], T0)
                    self.assertEqual(cm.exception.code, case["error"])
                else:
                    self.assertEqual(d.ingest(case["input"], T0), case["expect"])

    @covers("MC-011", 8, 10, 11, 12, 27)
    def test_mc011_advisory_debounce_fallback_no_double_count(self):
        d = pln05.Demand()
        sig = {"version": "1.0", "request_id": "r1", "tenant": "t", "resource_class": "slots", "unit": "slot", "quantity": 10,
               "confidence": 0.9, "observed_at": T0, "revision": 1}
        self.assertEqual(d.ingest(sig, T0), "accepted")
        self.assertEqual(d.ingest(sig, T0), "duplicate")
        self.assertEqual(d.ingest(dict(sig, request_id="r2", quantity=100, revision=2), T0 + 1), "debounced")
        self.assertEqual(d.ingest(dict(sig, request_id="r3", quantity=10, revision=3), T0 + 60), "within_hysteresis")
        self.assertEqual(d.ingest(dict(sig, request_id="r0", revision=0), T0 + 90), "discarded_out_of_order")
        d.note_placement("t", 4)
        adv = d.advisory("t", T0 + 10)
        self.assertEqual(adv["slots"], 6)
        self.assertEqual(adv["request_id"], "r1")
        self.assertEqual(d.advisory("t", T0 + pln05.TTL_S + 10)["status"], "last_known_good")
        self.assertEqual(d.advisory("t", T0 + pln05.TTL_S + pln05.LKG_TTL_S + 10)["status"], "baseline")

    @covers("MC-011", 14, 27)
    def test_mc011_outage_cannot_cause_unbounded_retries(self):
        from gap03_topology_aware_scheduler.controlplane.retry import Policy, Retrier
        r = Retrier("pln05", Policy(max_attempts=3), seed=1, sleep=lambda s: None)
        calls = []

        def down(**kw):
            calls.append(1)
            raise SchedulerError("DEPENDENCY_UNAVAILABLE", "pln05 down")
        with self.assertRaises(SchedulerError):
            r.run(down, op_class="read_only", deadline_s=5)
        self.assertEqual(len(calls), 3)


class Fixtures034(unittest.TestCase):
    @covers("MC-034", 6, 7, 9, 13, 15)
    def test_mc034_fixture_sets_cover_required_classes(self):
        need = {"positive", "boundary", "malformed", "unsupported_version"}
        for name in ("gap02.json", "gap14.json", "pln05.json"):
            f = fx(name)
            self.assertTrue(need <= {c["class"] for c in f["cases"]}, name)
            for k in ("adapter", "schema", "versions_tested", "owner_repo"):
                self.assertIn(k, f)
        s = {c["class"] for c in fx("sch01.json")["cases"]}
        self.assertTrue({"positive", "dependency_error", "authorization_failure", "stale_revision"} <= s)

    @covers("MC-034", 8, 12, 14)
    def test_mc034_harness_is_deterministic_and_correlated(self):
        """fault injection (E_BUSY) with deterministic replay; correlation by txn id across retries."""
        a, b = sch01.SCH01Harness(faults=["E_BUSY"]), sch01.SCH01Harness(faults=["E_BUSY"])
        for h in (a, b):
            with self.assertRaises(SchedulerError):
                h.place({"txn": "t", "node": "x", "fence": 1, "version": "1.0"})
            h.place({"txn": "t", "node": "x", "fence": 1, "version": "1.0"})
        self.assertEqual(a.placements, b.placements)
        self.assertEqual(a.status("t")["txn"], "t")
