"""C035 / C036 / C037 configuration tests."""
import importlib
import unittest

import _path
cfg = importlib.import_module(_path.PKG + ".config")
sec = importlib.import_module(_path.PKG + ".security")


class Overlays(unittest.TestCase):
    def test_layers_and_effective_values(self):
        c, layers = cfg.resolve("edge", {"_site": "store-12", "fuel": 500})
        self.assertEqual(layers, ["base", "env:edge", "site:store-12"])
        self.assertEqual((c["fuel"], c["max_concurrent"]), (500, 8))

    def test_every_environment_resolves(self):
        for env in cfg.ENVIRONMENTS:
            cfg.resolve(env)

    def test_rejections(self):
        bad = [{"nope": 1}, {"fuel": "10"}, {"fuel": 0}, {"fuel": True}, {"max_value_bytes": 10**8},
               {"isolation": "none"}, {"per_tenant_concurrent": 100}, {"residency": []},
               {"host_call_timeout_ms": 5000}]
        for o in bad:
            with self.subTest(o=o), self.assertRaises(cfg.ConfigError):
                cfg.resolve("prod", o)
        with self.assertRaises(cfg.ConfigError):
            cfg.resolve("prod", {"isolation": "inline-dev"})
        with self.assertRaises(cfg.ConfigError):
            cfg.resolve("mars")


class Activation(unittest.TestCase):
    def test_provenance_and_atomicity(self):
        log = sec.AuditLog(b"k" * 32)
        s = cfg.ConfigStore("prod", audit=log)
        d0 = s.active_digest
        rec = s.activate({"_site": "s1", "fuel": 2000}, actor="david", reason="raise fuel")
        self.assertEqual((rec["previous"], rec["actor"], rec["layers"][-1]), (d0, "david", "site:s1"))
        self.assertEqual(s.active["fuel"], 2000)
        before = (dict(s.active), s.active_digest, len(s.history))
        for bad, kw in (({"fuel": -1}, {}), ({"fuel": 5}, {"precheck": lambda c: False}), ({"fuel": 5}, {"actor": ""})):
            with self.assertRaises(cfg.ConfigError):
                s.activate(bad, actor=kw.get("actor", "d"), reason="r", precheck=kw.get("precheck"))
        self.assertEqual((dict(s.active), s.active_digest, len(s.history)), before)
        rb = s.rollback(actor="david", reason="bad canary")
        self.assertEqual(rb["digest"], d0)
        self.assertEqual(s.active["fuel"], cfg.BASE["fuel"])
        self.assertTrue(sec.AuditLog.verify(log.entries, b"k" * 32)[0])
        self.assertEqual(sum(1 for e in log.entries if e["event"] == "config.activated"), 3)

    def test_audit_failure_aborts_activation(self):
        class Boom:
            def append(self, *a, **k):
                raise sec.AuthError("audit unavailable")
        s = cfg.ConfigStore.__new__(cfg.ConfigStore)
        cfg.ConfigStore.__init__(s, "prod")
        s.audit = Boom()
        before = s.active_digest
        with self.assertRaises(sec.AuthError):
            s.activate({"fuel": 7}, actor="a", reason="r")
        self.assertEqual(s.active_digest, before)
        self.assertNotEqual(s.active["fuel"], 7)

    def test_frozen_in_degraded_control_plane(self):
        s = cfg.ConfigStore("prod")
        s.frozen = True
        with self.assertRaisesRegex(cfg.ConfigError, "frozen"):
            s.activate({"fuel": 7}, actor="a", reason="r")


if __name__ == "__main__":
    unittest.main()
