"""MC-06/15/24/25/33 fault, recovery, partition and adjacent-layer integration tests.

Adjacent layers (PLN-01, INV-65, PLN-03, SCH-01, INV-11, GAP-04) are exercised
through contract-faithful in-process mocks. These are *mock* integrations:
they prove this package honours its side of each contract, not that a live
peer does. The traceability matrix records them as ``verified-mock``.
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import threading
import time
import unittest

from helpers import APP, CONFIG, catalogue_doc, provider, ring, token

from pln02_application_plane import wit
from pln02_application_plane.audit import AuditLedger, verify as verify_audit
from pln02_application_plane.catalogue import AutonomyLease, CatalogueClient
from pln02_application_plane.context import RequestContext
from pln02_application_plane.errors import PlaneError
from pln02_application_plane.resolver import verify_revision
from pln02_application_plane.service import ApplicationPlaneService
from pln02_application_plane.store import RevisionStore


def code_of(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except Exception as exc:  # noqa: BLE001
        return getattr(exc, "code", type(exc).__name__)
    return None


class Inv65Mock:
    """INV-65 capability-provider catalogue publisher (mock)."""

    def __init__(self, r):
        self.r, self.gen, self.up, self.providers = r, 1, True, None

    def __call__(self):
        if not self.up:
            raise ConnectionError("INV-65 unreachable")
        return catalogue_doc(self.r, generation=self.gen, providers=self.providers)


class Plane(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.tmp.name)
        self.r = ring()
        self.inv65 = Inv65Mock(self.r)
        self.cat = CatalogueClient(self.inv65, self.r, environment="prod", site="eu-1", cache_path=d / "cat.json",
                                   max_age_seconds=0.0)
        self.store = RevisionStore(d / "store")
        self.audit = AuditLedger(d / "audit.jsonl", self.r, "aud-1")
        self.svc = ApplicationPlaneService(ring=self.r, catalogue=self.cat, store=self.store, audit=self.audit, config=CONFIG)
        self.d = d

    def tearDown(self):
        self.tmp.cleanup()

    def ctx(self, **kw):
        return RequestContext.create("acme", "prod", "eu-1", **kw)

    def submit(self, doc=APP, tok=None, **kw):
        return self.svc.submit(self.ctx(**kw), tok or token(self.r), "shop", json.dumps(doc).encode())


class MC15Integration(Plane):
    def test_pln01_to_pln03_and_sch01(self):
        """PLN-01 submits -> PLN-02 publishes -> PLN-03/SCH-01 consume a verifiable revision."""
        out = self.submit()
        self.assertTrue(out["ok"], out)
        rev_id = out["publication"]["revision"]
        # PLN-03 / SCH-01 side: fetch by address and verify before executing/classifying
        fetched = self.store.get("acme", "prod", rev_id)
        self.assertTrue(verify_revision(fetched))
        self.assertEqual(fetched["bindings"]["api:state"], "redis-b")  # cheapest eligible, explained
        self.assertEqual(sorted(c["name"] for c in fetched["component_specs"]), ["api", "store"])
        self.assertEqual(out["provenance"]["catalogue_generation"], 1)
        self.assertEqual(verify_audit(self.d / "audit.jsonl", self.r)["seq"], 1)

    def test_inv11_wit_versions_feed_resolver(self):
        src = "package pk:store@1.2.0; interface kv { get: func(k: string) -> option<string>; }"
        pkg = wit.parse(src)
        v = wit.interface_version(pkg, "kv")
        app = {"schema": "PK_APPLICATION/1",
               "components": [{"name": "api", "requires": {"state": True}, "imports": {"kv": v}},
                              {"name": "store", "requires": {"state": True}, "exports": {"kv": v}}],
               "edges": [["store", "api", "kv"]]}
        self.assertTrue(self.submit(app)["ok"])

    def test_residency_constraint_from_application(self):
        doc = {**APP, "constraints": {"residency": ["us"]}}
        out = self.submit(doc)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"]["code"], "NO_ELIGIBLE_PROVIDER")  # state only in eu

    def test_optional_capability_dropped_under_policy(self):
        doc = {**APP, "constraints": {"residency": ["eu"]}}
        out = self.submit(doc)
        self.assertTrue(out["ok"], out)
        self.assertIn("api:tracing", out["revision"]["dropped_optional"])

    def test_authn_authz_errors_are_public_documents(self):
        out = self.svc.submit(self.ctx(), "garbage", "shop", b"{}")
        self.assertEqual(out["error"]["code"], "UNAUTHENTICATED")
        out = self.submit(tok=token(self.r, tenant="evil"))
        self.assertEqual(out["error"]["code"], "PERMISSION_DENIED")
        records = self.audit.export()
        self.assertEqual([r["event"]["action"] for r in records], ["authn_failure", "authz_denied"])

    def test_idempotent_replay(self):
        a = self.submit(idempotency_key="req-000001")
        b = self.submit(idempotency_key="req-000001")
        self.assertEqual(a["publication"], b["publication"])
        c = self.submit({**APP, "edges": []}, idempotency_key="req-000001")
        self.assertEqual(c["error"]["code"], "IDEMPOTENCY_CONFLICT")

    def test_metrics_and_health(self):
        self.submit()
        self.assertEqual(self.svc.metrics.value("application_revisions_total", {"tenant": "acme", "environment": "prod", "site": "eu-1"}), 1)
        self.assertIn("resolution_seconds_bucket", self.svc.metrics.prometheus())
        h = self.svc.health.report(config_digest=self.svc.config_digest)
        self.assertTrue(h["ready"])


class MC06MC33Disconnected(Plane):
    def test_partition_without_lease_fails_closed(self):
        self.assertTrue(self.submit()["ok"])
        self.inv65.up = False
        out = self.submit({**APP, "edges": [["store", "api", "store"]], "components": APP["components"]}, idempotency_key=None)
        self.assertEqual(out["error"]["code"], "CATALOGUE_STALE")
        self.assertFalse(self.svc.health.report()["ready"])

    def test_partition_with_gap04_lease_degrades_then_reconnects(self):
        self.assertTrue(self.submit()["ok"])
        self.inv65.up = False
        self.cat.lease = AutonomyLease("GAP-04", time.time() + 60)
        out = self.submit()
        self.assertTrue(out["ok"])
        self.assertTrue(out["provenance"]["catalogue_degraded"])
        self.assertEqual(self.svc.health.report()["status"], "degraded")
        # reconnect: newer generation accepted, rollback refused
        self.inv65.up, self.inv65.gen = True, 5
        self.assertEqual(self.cat.refresh().generation, 5)
        self.inv65.gen = 4
        self.assertEqual(code_of(self.cat.refresh), "CATALOGUE_UNTRUSTED")

    def test_offline_window_bound(self):
        self.submit()
        self.inv65.up = False
        self.cat.lease = AutonomyLease("GAP-04", time.time() + 60)
        self.cat.max_offline = 0.0
        time.sleep(0.01)
        self.assertEqual(self.submit()["error"]["code"], "CATALOGUE_STALE")

    def test_cache_survives_restart_and_tampered_cache_ignored(self):
        self.submit()
        c2 = CatalogueClient(self.inv65, self.r, environment="prod", site="eu-1", cache_path=self.d / "cat.json")
        self.assertIsNotNone(c2._current)
        raw = json.loads((self.d / "cat.json").read_text())
        raw["doc"]["providers"]["state"][0]["id"] = "hostile"
        (self.d / "cat.json").write_text(json.dumps(raw))
        c3 = CatalogueClient(self.inv65, self.r, environment="prod", site="eu-1", cache_path=self.d / "cat.json")
        self.assertIsNone(c3._current)

    def test_poisoned_catalogue_rejected(self):
        doc = catalogue_doc(self.r)
        doc["providers"]["state"].append(provider("hostile", cost=0))
        self.inv65.__call__ = None
        c = CatalogueClient(lambda: doc, self.r, environment="prod", site="eu-1")
        self.assertEqual(code_of(c.refresh), "CATALOGUE_UNTRUSTED")
        wrong_site = catalogue_doc(self.r, site="us-1")
        c = CatalogueClient(lambda: wrong_site, self.r, environment="prod", site="eu-1")
        self.assertEqual(code_of(c.refresh), "CATALOGUE_UNTRUSTED")


class MC24MC25Store(Plane):
    def test_split_brain_fencing(self):
        rev = self.submit()["revision"]
        stale_epoch = self.svc.epoch
        new_epoch = self.store.acquire_epoch("controller-b")  # failover to B
        self.assertEqual(code_of(self.store.publish, tenant="acme", environment="prod", application="shop",
                                 revision=rev, epoch=stale_epoch), "FENCED")
        self.store.publish(tenant="acme", environment="prod", application="shop", revision=rev, epoch=new_epoch)
        self.assertEqual(self.submit({**APP, "edges": APP["edges"]}, idempotency_key=None)["error"]["code"], "FENCED")

    def test_freeze_disable_quarantine(self):
        admin = token(self.r, roles=("plane-admin",), sub="ops")
        self.assertEqual(code_of(self.svc.admin, token(self.r), "freeze", "acme"), "PERMISSION_DENIED")
        self.svc.admin(admin, "freeze", "acme")
        self.assertEqual(self.submit()["error"]["code"], "PLANE_FROZEN")
        self.svc.admin(admin, "unfreeze", "acme")
        out = self.submit()
        self.assertTrue(out["ok"])
        rid = out["publication"]["revision"]
        self.svc.admin(admin, "quarantine", rid)
        self.assertEqual(code_of(self.store.get, "acme", "prod", rid), "REVISION_QUARANTINED")
        self.svc.admin(admin, "release", rid)
        self.svc.admin(admin, "disable")
        self.assertEqual(self.submit()["error"]["code"], "PLANE_DISABLED")
        self.assertFalse(self.svc.health.report()["ready"])

    def test_supersession_and_rollback(self):
        a = self.submit()["publication"]["revision"]
        v2 = json.loads(json.dumps(APP))
        v2["components"][0]["requires"]["tracing"] = True
        b = self.submit(v2)["publication"]["revision"]
        self.assertNotEqual(a, b)
        head = self.store.head("acme", "prod", "shop")
        self.assertEqual(head["current"], b)
        self.assertEqual(head["history"][-1], {**head["history"][-1], "revision": a, "superseded_by": b})
        self.assertEqual(self.store.rollback(tenant="acme", environment="prod", application="shop", epoch=self.svc.epoch), a)

    def test_crash_leftovers_and_corruption_recovered(self):
        rid = self.submit()["publication"]["revision"]
        root = self.d / "store"
        (root / "revisions" / "acme" / "prod" / ".tmp-crash").write_text("partial")
        path = root / "revisions" / "acme" / "prod" / f"{rid}.json"
        data = json.loads(path.read_text())
        data["revision"]["bindings"]["api:state"] = "hostile"
        path.write_text(json.dumps(data))
        s2 = RevisionStore(root)  # restart
        self.assertEqual(s2.recovery_report["tmp_removed"], 1)
        self.assertEqual(s2.recovery_report["corrupt_quarantined"], [rid])
        self.assertEqual(code_of(s2.get, "acme", "prod", rid), "REVISION_QUARANTINED")

    def test_backup_restore_fences_old_holders(self):
        rid = self.submit()["publication"]["revision"]
        b = self.store.backup(self.d / "bak")
        restored = RevisionStore.restore(b, self.d / "restored")
        self.assertEqual(restored.get("acme", "prod", rid)["revision"], rid)
        self.assertGreater(restored.status()["epoch"], self.svc.epoch)

    def test_concurrent_submissions_consistent(self):
        errs, oks = [], []

        def worker(i):
            doc = json.loads(json.dumps(APP))
            doc["components"][1]["exports"]["store"] = doc["components"][0]["imports"]["store"] = f"1.{i}"
            out = self.svc.submit(self.ctx(), token(self.r), f"app{i}", json.dumps(doc).encode())
            (oks if out["ok"] else errs).append(out)
        ts = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(oks) + len(errs), 6)
        for e in errs:
            self.assertIn(e["error"]["code"], {"QUOTA_EXCEEDED", "OVERLOADED"})
        self.assertEqual(verify_audit(self.d / "audit.jsonl", self.r)["seq"], 6)


class MC30Observability(unittest.TestCase):
    def test_trace_cardinality_logs(self):
        from pln02_application_plane.observability import MAX_SERIES_PER_METRIC, Metrics, StructuredLogger, TraceContext, Watchdog
        t = TraceContext.from_header("00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual(t.child().trace_id, "a" * 32)
        self.assertNotEqual(TraceContext.from_header("bogus").trace_id, "a" * 32)
        m = Metrics()
        for i in range(MAX_SERIES_PER_METRIC + 50):
            m.inc("x", {"k": str(i)})
        self.assertEqual(m.dropped_series, 50)
        log = StructuredLogger()
        rec = log.log("info", "e", password="p", nested={"token": "t"})
        self.assertNotIn("p", json.dumps(rec["password"]).strip('"*REDACT'))
        now = [0.0]
        w = Watchdog(stall_after=1, clock=lambda: now[0])
        w.start("op")
        now[0] = 2
        self.assertEqual(len(w.stalled()), 1)


if __name__ == "__main__":
    unittest.main()
