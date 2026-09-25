"""Component 8: configuration subsystem."""
import copy
import threading
import unittest

try:
    from . import _path  # noqa: F401
except ImportError:
    import _path  # type: ignore # noqa: F401

from inv20_http_component_worlds.config import (
    DEFAULTS, ConfigAuthority, ConfigInvalid, ConfigStore, apply_overlays, bootstrap_default, digest, validate,
)


def egress_cfg(**kw):
    c = {"schema": "INV20_CONFIG/1", "outgoing_enabled": True, "capability_ref": "secret://inv20/cap",
         "allowed_authorities": ["api.example.com:443", "b.example.com"]}
    c.update(kw)
    return c


class ValidateTest(unittest.TestCase):
    def test_secure_defaults(self):
        v = validate({"schema": "INV20_CONFIG/1"})
        self.assertFalse(v["outgoing_enabled"])
        self.assertEqual(v["allowed_authorities"], [])
        self.assertFalse(v["observability"]["log_bodies"])

    def test_normalises_authorities(self):
        self.assertEqual(validate(egress_cfg())["allowed_authorities"], ["api.example.com:443", "b.example.com:443"])

    def test_rejections(self):
        bad = [
            {}, None, {"schema": "INV20_CONFIG/2"}, {"schema": "INV20_CONFIG/1", "surprise": 1},
            {"schema": "INV20_CONFIG/1", "limits": {"body_bytes": -1}},
            {"schema": "INV20_CONFIG/1", "limits": {"body_bytes": True}},
            {"schema": "INV20_CONFIG/1", "limits": {"nope": 1}},
            {"schema": "INV20_CONFIG/1", "outgoing_enabled": "yes"},
            {"schema": "INV20_CONFIG/1", "allowed_authorities": ["x.com"]},       # without outgoing
            egress_cfg(capability_ref=None), egress_cfg(capability_ref="plaintext"),
            egress_cfg(allowed_authorities=["user@x.com"]),
            {"schema": "INV20_CONFIG/1", "limits": {"per_tenant_concurrency": 1000, "max_concurrency": 10}},
            {"schema": "INV20_CONFIG/1", "observability": {"log_bodies": True}},
            {"schema": "INV20_CONFIG/1", "features": {"api_token": "hunter2"}},
            {"schema": "INV20_CONFIG/1", "allowed_address_classes": ["everything"]},
        ]
        for cfg in bad:
            with self.subTest(cfg=cfg), self.assertRaises(ConfigInvalid):
                validate(cfg)

    def test_digest_canonical(self):
        a = validate(egress_cfg())
        b = validate(dict(reversed(list(egress_cfg().items()))))
        self.assertEqual(digest(a), digest(b))


class OverlayTest(unittest.TestCase):
    def test_narrowing_allowed(self):
        out = apply_overlays(egress_cfg(), [("workload", {"allowed_authorities": ["b.example.com"]}),
                                            ("environment", {"limits": {"body_bytes": 1024}})])
        self.assertEqual(out["allowed_authorities"], ["b.example.com:443"])
        self.assertEqual(out["limits"]["body_bytes"], 1024)

    def test_expansion_refused(self):
        base_off = {"schema": "INV20_CONFIG/1"}
        cases = [
            (base_off, ("tenant", {"outgoing_enabled": True, "capability_ref": "secret://x"})),
            (egress_cfg(), ("site", {"allowed_authorities": ["api.example.com", "evil.com"]})),
            (egress_cfg(), ("tenant", {"allowed_address_classes": ["public", "private"]})),
            (egress_cfg(), ("workload", {"allow_ip_literals": True})),
            (egress_cfg(), ("workload", {"limits": {"body_bytes": 1 << 21}})),
            (egress_cfg(), ("workload", {"schema": "INV20_CONFIG/1"})),
        ]
        for base, ov in cases:
            with self.subTest(ov=ov), self.assertRaises(ConfigAuthority):
                apply_overlays(base, [ov])
        with self.assertRaises(ConfigInvalid):
            apply_overlays(egress_cfg(), [("galaxy", {})])

    def test_precedence_deterministic(self):
        o1 = [("workload", {"limits": {"body_bytes": 10}}), ("environment", {"limits": {"body_bytes": 100}})]
        self.assertEqual(apply_overlays(egress_cfg(), o1)["limits"]["body_bytes"], 10)
        self.assertEqual(apply_overlays(egress_cfg(), list(reversed(o1)))["limits"]["body_bytes"], 10)


class StoreTest(unittest.TestCase):
    def test_bootstrap(self):
        s = bootstrap_default()
        self.assertFalse(s.active["outgoing_enabled"])
        self.assertEqual(s.provenance.digest, digest(validate(copy.deepcopy(DEFAULTS))))

    def test_stage_activate_rollback_with_audit(self):
        events = []
        s = ConfigStore(audit=lambda a, d: events.append(a))
        s.stage({"schema": "INV20_CONFIG/1"}, "ci", "git:abc")
        p1 = s.activate()
        with self.assertRaises(ConfigInvalid):
            s.stage(egress_cfg(), "ci", "git:def")         # needs approver
        s.stage(egress_cfg(), "ci", "git:def", approver="sec-lead")
        p2 = s.activate()
        self.assertEqual((p2.revision, p2.approver), (p1.revision + 1, "sec-lead"))
        self.assertTrue(s.active["outgoing_enabled"])
        self.assertEqual(s.rollback("oncall").revision, p1.revision)
        self.assertFalse(s.active["outgoing_enabled"])
        self.assertIn("config.rollback", events)

    def test_invalid_never_active(self):
        s = bootstrap_default()
        before = s.provenance.revision
        with self.assertRaises(ConfigInvalid):
            s.stage({"schema": "INV20_CONFIG/1", "limits": {"body_bytes": -5}}, "x", "y")
        self.assertEqual(s.provenance.revision, before)

    def test_auto_rollback_on_failed_readiness(self):
        events = []
        s = ConfigStore(audit=lambda a, d: events.append(a))
        s.stage({"schema": "INV20_CONFIG/1"}, "a", "b"); good = s.activate()
        s.stage({"schema": "INV20_CONFIG/1", "limits": {"body_bytes": 5}}, "a", "b")
        with self.assertRaises(ConfigInvalid):
            s.activate(readiness=lambda c: False)
        self.assertEqual(s.provenance.revision, good.revision)
        s.stage({"schema": "INV20_CONFIG/1", "limits": {"body_bytes": 6}}, "a", "b")

        def boom(c):
            raise RuntimeError("interrupted activation")
        with self.assertRaises(ConfigInvalid):
            s.activate(readiness=boom)
        self.assertEqual(s.provenance.revision, good.revision)
        self.assertEqual(events.count("config.auto_rollback"), 2)

    def test_concurrent_updates_serialised(self):
        s = bootstrap_default()
        errs = []

        def work(i):
            try:
                s.stage({"schema": "INV20_CONFIG/1", "limits": {"body_bytes": 100 + i}}, f"w{i}", "t")
            except Exception as e:  # pragma: no cover
                errs.append(e)
        ts = [threading.Thread(target=work, args=(i,)) for i in range(20)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertFalse(errs)
        p = s.activate()
        self.assertEqual(p.revision, 21)

    def test_export_never_resolves_secrets(self):
        s = ConfigStore(require_approval=False)
        s.stage(egress_cfg(), "a", "b"); s.activate()
        self.assertEqual(s.export()["config"]["capability_ref"], "secret://inv20/cap")

    def test_rollback_without_history(self):
        with self.assertRaises(ConfigInvalid):
            bootstrap_default().rollback("x")


if __name__ == "__main__":
    unittest.main()
