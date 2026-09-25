"""Persistence, idempotency, lifecycle, reconciliation, revocation, rollback,
emergency disable, backup/restore and disaster recovery (MC059-MC066, MC039)."""
import json
import pathlib
import tempfile
import unittest

import _fixtures as F
from inv29_hybrid_wasm_unikernel import lifecycle as L


class LifecycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kr = F.keyring()
        self.clock = F.Clock()
        self.a = F.admitter(self.kr, clock=self.clock)
        self.lc = L.Lifecycle(self.a, L.Store(pathlib.Path(self.tmp.name) / "store"), clock=self.clock)

    def tearDown(self):
        self.tmp.cleanup()

    def test_idempotent_submit(self):
        req = F.request(self.kr)
        first = self.lc.submit(req)
        second = self.lc.submit(req)  # would be a replay if it reached admission again
        self.assertEqual(first["state"], L.ADMITTED)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(self.lc.counts(), {L.ADMITTED: 1})

    def test_refusal_is_persisted_with_code(self):
        doc = self.lc.submit(F.request(self.kr, tenant="mallory"))
        self.assertEqual(doc["state"], L.REFUSED)
        self.assertEqual(doc["error"]["code"], "INV29-E-POLICY")

    def test_state_machine(self):
        cid = self.lc.submit(F.request(self.kr))["id"]
        self.lc.mark_running(cid)
        self.lc.retire(cid)
        with self.assertRaises(L.IllegalTransition):
            self.lc.mark_running(cid)
        with self.assertRaises(L.IllegalTransition):
            self.lc.revoke(cid, "late")

    def test_reconcile_revokes_on_key_revocation_and_is_idempotent(self):
        cid = self.lc.submit(F.request(self.kr))["id"]
        self.lc.mark_running(cid)
        self.assertEqual(self.lc.reconcile()["ok"], 1)
        self.kr.revoke(F.ATTEST_KEY)
        self.assertEqual(self.lc.reconcile()["revoked"], 1)
        self.assertEqual(self.lc.reconcile()["checked"], 0)
        self.assertEqual(self.lc.store.get(cid)["state"], L.REVOKED)

    def test_reconcile_on_tenant_deauthorisation_and_disable(self):
        c1 = self.lc.submit(F.request(self.kr))["id"]
        self.lc.mark_running(c1)
        self.a.set_policy(F.policy(generation=2, allowed_tenants=frozenset({"other"})))
        self.assertEqual(self.lc.reconcile()["revoked"], 1)
        self.a.rollback_policy(F.policy(generation=1))
        c2 = self.lc.submit(F.request(self.kr))["id"]
        self.lc.mark_running(c2)
        self.a.disable("SEV1-drill")
        self.assertEqual(self.lc.reconcile()["revoked"], 1)

    def test_expiry_of_unstarted_admission(self):
        cid = self.lc.submit(F.request(self.kr))["id"]
        self.clock.t += 10_000
        self.assertEqual(self.lc.reconcile()["expired"], 1)
        self.assertEqual(self.lc.store.get(cid)["state"], L.EXPIRED)

    def test_store_integrity_check(self):
        cid = self.lc.submit(F.request(self.kr))["id"]
        p = self.lc.store._p(cid)
        doc = json.loads(p.read_text())
        doc["tenant"] = "mallory"
        p.write_text(json.dumps(doc))
        with self.assertRaises(L.StoreCorrupt):
            self.lc.store.get(cid)
        self.assertEqual(self.lc.reconcile()["corrupt"], 1)

    def test_path_traversal_ids_refused(self):
        for bad in ("../../etc/passwd", "", "A" * 64):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.lc.store.get(bad)

    def test_backup_restore_disaster_recovery(self):
        ids = [self.lc.submit(F.request(self.kr))["id"] for _ in range(5)]
        bpath = pathlib.Path(self.tmp.name) / "backup.json"
        info = self.lc.store.backup(bpath)
        self.assertEqual(info["documents"], 5)
        # disaster: primary store is lost entirely
        fresh = L.Store(pathlib.Path(self.tmp.name) / "rebuilt")
        self.assertEqual(fresh.restore(bpath)["restored"], 5)
        self.assertEqual(sorted(fresh.ids()), sorted(ids))
        # reconstruction: reconcile over the restored store reaches the same verdicts
        lc2 = L.Lifecycle(self.a, fresh, clock=self.clock)
        self.assertEqual(lc2.reconcile()["ok"], 5)

    def test_tampered_backup_refused(self):
        self.lc.submit(F.request(self.kr))
        bpath = pathlib.Path(self.tmp.name) / "backup.json"
        self.lc.store.backup(bpath)
        payload = json.loads(bpath.read_text())
        next(iter(payload["documents"].values()))["tenant"] = "mallory"
        bpath.write_text(json.dumps(payload))
        with self.assertRaises(L.StoreCorrupt):
            L.Store(pathlib.Path(self.tmp.name) / "x").restore(bpath)



class ControlFileTest(unittest.TestCase):
    def test_disable_enable_and_corrupt_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            kr = F.keyring()
            a = F.admitter(kr)
            ctl = L.ControlFile(pathlib.Path(d) / "control.json")
            self.assertIsNone(ctl.apply(a))
            ctl.write("SEV1-drill", "oncall")
            ctl.apply(a)
            with self.assertRaises(PermissionError):
                a.admit(F.request(kr))
            ctl.write(None, "oncall")
            ctl.apply(a)
            a.admit(F.request(kr))
            (pathlib.Path(d) / "control.json").write_text("{not json")
            self.assertIn("failing closed", ctl.apply(a))
            self.assertIsNotNone(a.disabled)

    def test_cli_roundtrip(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("inv29ctl", pathlib.Path(__file__).parents[1] / "tools" / "inv29ctl.py")
        ctl = importlib.util.module_from_spec(spec); spec.loader.exec_module(ctl)
        with tempfile.TemporaryDirectory() as d:
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ctl.main(["disable", "--state", d, "--reason", "drill"]), 0)
                self.assertEqual(ctl.main(["status", "--state", d]), 0)
                self.assertEqual(ctl.main(["enable", "--state", d]), 0)
                self.assertEqual(ctl.main(["backup", "--state", d, "--out", d + "/b.json"]), 0)
                self.assertEqual(ctl.main(["restore", "--state", d, "--src", d + "/b.json"]), 0)


if __name__ == "__main__":
    unittest.main()
