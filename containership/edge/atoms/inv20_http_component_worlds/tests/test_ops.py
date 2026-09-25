"""Components 12, 16, 17, 2, 24, 26: health, observability, audit, WIT, reconstruction, packaging."""
import json
import pathlib
import re
import subprocess
import sys
import tomllib
import unittest

try:
    from . import _path  # noqa: F401
except ImportError:
    import _path  # type: ignore # noqa: F401

import inv20_http_component_worlds as pkg
from inv20_http_component_worlds import witgen
from inv20_http_component_worlds.config import bootstrap_default, validate
from inv20_http_component_worlds.health import HealthMonitor, IllegalTransition, Phase
from inv20_http_component_worlds.identity import KeyProvider
from inv20_http_component_worlds.observability import (
    AuditLog, AuditUnavailable, Metrics, StructuredLogger, accept_traceparent, outbound_traceparent, redact,
    verify_audit_stream,
)

PKG = pathlib.Path(pkg.__file__).resolve().parent


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class HealthTest(unittest.TestCase):
    def mk(self):
        c = Clock()
        h = HealthMonitor("4.3.0", clock=c, stall_after_s=5, drain_max_s=10)
        h.transition(Phase.CONFIGURING, "boot")
        return h, c

    def test_healthy_startup_and_dependency_cycle(self):
        h, _ = self.mk()
        self.assertEqual(h.evaluate(), Phase.UNHEALTHY)          # no valid config yet
        h.set_config(1, "sha256:x", True)
        h.set_dependency("policy", True); h.set_dependency("identity", True)
        self.assertEqual(h.evaluate(), Phase.READY)
        h.set_dependency("identity", False)
        self.assertEqual(h.evaluate(), Phase.DEGRADED)
        self.assertEqual(h.snapshot()["reason"], "dependency_unavailable:identity")
        self.assertFalse(h.ready)
        h.set_dependency("identity", True)
        self.assertEqual(h.evaluate(), Phase.READY)

    def test_invalid_config_and_recovery(self):
        h, _ = self.mk()
        h.set_config(1, "d", False); h.set_dependency("policy", True); h.set_dependency("identity", True)
        self.assertEqual(h.evaluate(), Phase.UNHEALTHY)
        h.set_config(2, "d2", True)
        self.assertEqual(h.evaluate(), Phase.READY)

    def test_stall_and_saturation(self):
        h, c = self.mk()
        h.set_config(1, "d", True); h.set_dependency("policy", True); h.set_dependency("identity", True)
        h.evaluate()
        h.progress("r1"); c.t = 6
        self.assertEqual(h.evaluate(), Phase.DEGRADED)
        self.assertEqual(h.reason, "request_stalled")
        h.finished("r1"); h.queue_capacity, h.queue_depth = 10, 9
        self.assertEqual((h.evaluate(), h.reason), (Phase.DEGRADED, "queue_saturated"))

    def test_drain_quarantine_illegal(self):
        h, c = self.mk()
        h.set_config(1, "d", True); h.set_dependency("policy", True); h.set_dependency("identity", True)
        h.evaluate(); h.progress("r"); h.begin_drain()
        self.assertFalse(h.snapshot()["accepts_traffic"])
        c.t = 11
        self.assertEqual((h.evaluate(), h.reason), (Phase.UNHEALTHY, "drain_stuck"))
        h.quarantine("security")
        with self.assertRaises(IllegalTransition):
            h.transition(Phase.READY, "nope")
        snap = h.snapshot()
        self.assertEqual((snap["schema"], snap["phase"]), ("INV20_HEALTH/1", "quarantined"))
        json.dumps(snap)

    def test_liveness_independent_of_traffic(self):
        h, c = self.mk()
        self.assertTrue(h.live)
        c.t = 16
        self.assertFalse(h.live)
        h.beat()
        self.assertTrue(h.live)


class ObservabilityTest(unittest.TestCase):
    def test_metrics_bounded(self):
        m = Metrics()
        m.inc("requests_handled", status_class="2xx")
        for i in range(5000):
            m.inc("egress_denials", reason=f"attacker-{i}.evil")       # collapses to "other"
        self.assertEqual(m.get("egress_denials", reason="other"), 5000)
        m.observe("body_bytes", 1024, direction="in")
        self.assertEqual(m.get("body_bytes", direction="in")["count"], 1)
        with self.assertRaises(KeyError):
            m.inc("undeclared")
        with self.assertRaises(KeyError):
            m.inc("requests_handled")
        self.assertLess(len(m.series), 10)
        json.dumps(m.export())

    def test_redaction_and_bounds(self):
        out = redact({"headers": [["Authorization", "Bearer abc"], ["x-ok", "1"]], "cookie": "s=1",
                      "url": "/cb?code=SECRET&x=1", "note": "A" * 5000})
        s = json.dumps(out)
        for secret in ("Bearer abc", "SECRET", "s=1"):
            self.assertNotIn(secret, s)
        self.assertLessEqual(len(out["note"]), 256)

    def test_structured_log_fields(self):
        lines = []
        log = StructuredLogger("n1", "s1", "prod", "4.3.0", "r7", sink=lines.append, clock=lambda: 1.0)
        rec = log.log("warn", "egress.denied", tenant="acme", workload="billing", reason="loopback",
                      authorization="Bearer x")
        for k in ("ts", "severity", "event", "node", "site", "env", "release", "config_revision", "tenant",
                  "trace_id", "reason"):
            self.assertIn(k, rec)
        self.assertTrue(rec["tenant"].startswith("t_"))
        self.assertNotIn("Bearer", lines[0])

    def test_trace_context_trust(self):
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        self.assertEqual(accept_traceparent(tp, True)[0], "a" * 32)
        self.assertNotEqual(accept_traceparent(tp, False)[0], "a" * 32)       # untrusted: new root
        self.assertNotEqual(accept_traceparent("00-" + "0" * 32 + "-" + "b" * 16 + "-01", True)[0], "0" * 32)
        self.assertIsNone(outbound_traceparent("a" * 32, "b" * 16, False))


class AuditTest(unittest.TestCase):
    def mk(self):
        keys = KeyProvider(); keys.rotate()
        log = AuditLog(keys, clock=lambda: 1.0, release="4.3.0")
        for i in range(5):
            log.emit("workload:acme/billing", "acme", "egress.authorize", f"api{i}.example.com:443", "allow", "allowed")
        return keys, log

    def test_verify_ok(self):
        keys, log = self.mk()
        self.assertTrue(verify_audit_stream(log.records, keys, log.anchor())["ok"])

    def test_tamper_detection(self):
        keys, log = self.mk()
        anchor = log.anchor()
        mod = [dict(r) for r in log.records]; mod[2]["result"] = "deny"
        self.assertFalse(verify_audit_stream(mod, keys, anchor)["ok"])
        self.assertFalse(verify_audit_stream(log.records[:2] + log.records[3:], keys, anchor)["ok"])
        self.assertFalse(verify_audit_stream([log.records[1], log.records[0]] + log.records[2:], keys, anchor)["ok"])
        self.assertFalse(verify_audit_stream(log.records + [log.records[-1]], keys, anchor)["ok"])
        self.assertFalse(verify_audit_stream(log.records[:-1], keys, anchor)["ok"])       # truncation

    def test_key_rotation_preserves_chain(self):
        keys, log = self.mk()
        keys.rotate()
        log.emit("op", "acme", "config.rollback", "rev3", "ok", "operator")
        self.assertTrue(verify_audit_stream(log.records, keys, log.anchor())["ok"])
        self.assertEqual({r["kid"] for r in log.records}, {"k1", "k2"})

    def test_sink_unavailable(self):
        keys, log = self.mk()
        log.available = False
        with self.assertRaises(AuditUnavailable):
            log.emit("op", "t", "egress.disable", "all", "ok", "emergency")
        self.assertIsNone(log.emit("op", "t", "metrics.flush", "-", "ok", "-", critical=False))


class WitTest(unittest.TestCase):
    def test_fresh(self):
        self.assertEqual(witgen.main(["--check"]), 0)

    def test_world_shapes(self):
        from inv20_http_component_worlds._wit_generated import WIT
        self.assertEqual(WIT["worlds"]["service"], {"export": ["handler"], "import": []})
        self.assertEqual(WIT["worlds"]["middleware"], {"export": ["handler"], "import": ["handler"]})
        self.assertIn("outgoing", WIT["worlds"]["service-with-egress"]["import"])

    def test_fixtures(self):
        fx = PKG / "wit" / "fixtures"
        for name in ("valid_service", "valid_middleware", "egress_service"):
            witgen.validate(witgen.parse((fx / f"{name}.wit").read_text()))
        for name in ("invalid_two_handlers", "invalid_ambient_egress", "invalid_syntax"):
            with self.subTest(name=name), self.assertRaises(witgen.WitError):
                witgen.validate(witgen.parse((fx / f"{name}.wit").read_text()))
        with self.assertRaises(witgen.WitError):
            witgen.validate(witgen.parse((fx / "version_skew.wit").read_text()), require_major=4)

    def test_error_variants_match_registry(self):
        from inv20_http_component_worlds.errors import REGISTRY
        text = (PKG / "wit" / "inv20.wit").read_text()
        block = text[text.index("variant error-code"): text.index("}", text.index("variant error-code"))]
        wit_codes = {l.strip().rstrip(",") for l in block.splitlines()[1:] if l.strip() and "(" not in l}
        reg = {c[2:].lower().replace("_", "-") for c in REGISTRY}
        missing = wit_codes - reg
        self.assertEqual(missing, set())


class ReconstructionTest(unittest.TestCase):
    def test_rebuild_from_authoritative_sources(self):
        # Destroyed runtime -> bootstrap from source defaults; policy-equivalent, egress off.
        s1, s2 = bootstrap_default(), bootstrap_default()
        self.assertEqual(s1.provenance.digest, s2.provenance.digest)
        self.assertFalse(s2.active["outgoing_enabled"])


class PackagingTest(unittest.TestCase):
    def test_version_single_source(self):
        v = pkg.__version__
        self.assertEqual((PKG / "VERSION").read_text().strip(), v)
        meta = tomllib.loads((PKG / "pyproject.toml").read_text())
        self.assertEqual(meta["project"]["version"], v)
        self.assertIn(f"## {v}", (PKG / "CHANGELOG.md").read_text())
        self.assertIn(f"**Version:** {v}", (PKG / "README.md").read_text())

    def test_import_without_pk_core(self):
        code = "import inv20_http_component_worlds as p; print(p.__version__)"
        out = subprocess.run([sys.executable, "-c", code], cwd=str(PKG.parent), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_no_sys_path_hacks_in_library(self):
        for f in PKG.glob("*.py"):
            self.assertNotIn("sys.path.insert", f.read_text(), f.name)

    def test_sha256sums_current(self):
        import hashlib
        source_tree = (PKG / ".github").exists()
        for line in (PKG / "SHA256SUMS.txt").read_text().splitlines():
            h, name = line.split("  ", 1)
            if not (PKG / name).exists():
                self.assertFalse(source_tree, f"{name} listed but missing from source tree")
                continue   # installed wheel carries a subset; every present file must still match
            self.assertEqual(hashlib.sha256((PKG / name).read_bytes()).hexdigest(), h, name)


if __name__ == "__main__":
    unittest.main()
