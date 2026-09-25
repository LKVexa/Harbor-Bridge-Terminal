"""Bootstrap controller (1), release-integrity boot phase (19), inventory and
pressure adapter (2, 22), and schema conformance fixtures (52)."""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import KEYS

from gap01_edge_node_supervisor import bootstrap, inventory
from gap01_edge_node_supervisor.schemas import validate


def ns(tmp, **kw):
    base = dict(node="b1", state_dir=str(tmp / "s"), socket=str(tmp / "r" / "c.sock"), probe_port=0,
                config=None, config_key=None, node_key=None, signals=None, caller_key=[], bind=[],
                simulate=True, release_key=None, require_manifest=False, allow_unsigned_config=False,
                manifest=str(tmp / "no-manifest.json"))
    base.update(kw)
    return argparse.Namespace(**base)


def no_sleep_build(args):
    orig = bootstrap.run_phases
    bootstrap.run_phases = lambda steps, **kw: orig(steps, sleep=lambda s: None, **kw)
    try:
        return bootstrap.build(args)
    finally:
        bootstrap.run_phases = orig


class BootstrapTest(unittest.TestCase):
    def test_phase_order_and_retry_then_recovery_mode(self):
        calls, sleeps = [], []
        flaky = {"n": 0}

        def flaky_runtime():
            flaky["n"] += 1
            if flaky["n"] < 2:
                raise OSError("transient")

        steps = {p: (lambda p=p: calls.append(p)) for p in bootstrap.PHASES}
        steps["runtime"] = flaky_runtime
        rec = bootstrap.run_phases(steps, retries=2, sleep=sleeps.append)
        self.assertFalse(rec.recovery_mode)
        self.assertEqual([x["phase"] for x in rec.phases if x["ok"]], list(bootstrap.PHASES))
        self.assertEqual(sleeps, [0.2])

        def broken():
            raise OSError("disk gone")
        steps["state_dir"] = broken
        rec = bootstrap.run_phases(steps, retries=1, sleep=sleeps.append)
        self.assertTrue(rec.recovery_mode)
        self.assertEqual(rec.failed_phase, "state_dir")
        self.assertNotIn("identity", [x["phase"] for x in rec.phases])

    def test_build_in_process_with_attestation(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        (tmp / "cp.key").write_bytes(KEYS["cp"]); os.chmod(tmp / "cp.key", 0o600)
        (tmp / "node.key").write_bytes(b"n" * 32); os.chmod(tmp / "node.key", 0o600)
        (tmp / "signals.json").write_text(json.dumps([{"name": "runtime", "required": True},
                                                      {"name": "disk", "required": False}]))
        rec, ctx = bootstrap.build(ns(tmp, node_key=str(tmp / "node.key"), signals=str(tmp / "signals.json"),
                                      caller_key=[f"cp={tmp / 'cp.key'}"], bind=["cp=control-plane"]))
        try:
            self.assertFalse(rec.recovery_mode, rec.phases)
            att = json.loads((tmp / "s" / "boot_attestation.json").read_text())
            self.assertTrue(ctx["identity"].verify(att))
            self.assertEqual(set(ctx["health"].specs), {"runtime", "disk"})
        finally:
            ctx["control"].shutdown(); ctx["probe"].shutdown()
            ctx["control"].server_close(); ctx["probe"].server_close()

    def test_bad_caller_key_permissions_enter_recovery_mode(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        (tmp / "cp.key").write_bytes(KEYS["cp"]); os.chmod(tmp / "cp.key", 0o644)
        rec, _ = no_sleep_build(ns(tmp, caller_key=[f"cp={tmp / 'cp.key'}"]))
        self.assertTrue(rec.recovery_mode)
        self.assertEqual(rec.failed_phase, "recover")

    def test_unsigned_config_refused_by_default(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        (tmp / "c.json").write_text(json.dumps({"config": {"max_workloads": 5}}))
        rec, _ = no_sleep_build(ns(tmp, config=str(tmp / "c.json")))
        self.assertEqual((rec.recovery_mode, rec.failed_phase), (True, "config"))
        rec, ctx = no_sleep_build(ns(tmp, config=str(tmp / "c.json"), allow_unsigned_config=True))
        try:
            self.assertFalse(rec.recovery_mode, rec.phases)
            self.assertEqual(ctx["cfg"].max_workloads, 5)
        finally:
            ctx["control"].shutdown(); ctx["probe"].shutdown()
            ctx["control"].server_close(); ctx["probe"].server_close()


class IntegrityPhaseTest(unittest.TestCase):
    def test_tampered_install_refuses_boot(self):
        src = pathlib.Path(__file__).resolve().parents[1]
        tmp = pathlib.Path(tempfile.mkdtemp())
        pkg = tmp / "gap01_edge_node_supervisor"
        shutil.copytree(src, pkg, ignore=shutil.ignore_patterns("__pycache__", "evidence"))
        files = {p.relative_to(pkg).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in pkg.rglob("*.py")}
        (pkg / "RELEASE_MANIFEST.json").write_text(json.dumps({"files": files}))
        code = (f"import sys, json; sys.path.insert(0, {str(tmp)!r}); sys.path.insert(0, {str(pkg / 'tests')!r}); "
                "from test_bootstrap_inventory import ns, no_sleep_build; import pathlib; "
                f"r, c = no_sleep_build(ns(pathlib.Path({str(tmp)!r}), require_manifest=True, "
                f"manifest={str(pkg / 'RELEASE_MANIFEST.json')!r})); "
                "print(json.dumps([r.recovery_mode, r.failed_phase]))")
        env = dict(os.environ, GAP01_LOG_LEVEL="CRITICAL")
        ok = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(json.loads(ok.stdout.strip().splitlines()[-1])[1], None, ok.stderr[-2000:])
        (pkg / "controller.py").write_text((pkg / "controller.py").read_text() + "\n# tampered\n")
        bad = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(json.loads(bad.stdout.strip().splitlines()[-1]), [True, "integrity"], bad.stderr[-2000:])


class InventoryTest(unittest.TestCase):
    def test_snapshot_shape_and_digest(self):
        s = inventory.snapshot(("/",))
        for k in ("cpu", "memory", "numa_nodes", "accelerators", "disks", "nics", "firmware", "digest"):
            self.assertIn(k, s)
        self.assertGreaterEqual(s["cpu"]["logical"] or 1, 1)
        self.assertEqual(len(s["digest"]), 64)

    def test_pressure_thresholds(self):
        p = inventory.pressure(50, 50, "/")
        self.assertIn("under_pressure", p)
        missing = inventory.pressure(99, 99, "/nonexistent-path-xyz")
        self.assertIsNone(missing["disk_pct"])

    def test_pressure_detects_threshold_crossing(self):
        p = inventory.pressure(50, 50, "/")
        forced = inventory.pressure(50, 50, "/") if p["disk_pct"] is None else inventory.pressure(99, 1, "/")
        if forced["disk_pct"] is not None:
            self.assertTrue(forced["under_pressure"])
            self.assertTrue(any(r.startswith("disk") for r in forced["reasons"]))


class SchemaFixtureTest(unittest.TestCase):
    """Schema conformance fixtures (52): every example is valid or invalid as named."""

    def test_fixtures(self):
        root = pathlib.Path(__file__).resolve().parents[1] / "examples" / "fixtures"
        files = sorted(root.glob("*.json"))
        self.assertGreater(len(files), 10)
        for f in files:
            doc = json.loads(f.read_text())
            problems = validate(doc["schema_name"], doc["document"])
            if doc["expect"] == "valid":
                self.assertEqual(problems, [], f.name)
            else:
                self.assertTrue(problems, f"{f.name} should be invalid")


if __name__ == "__main__":
    unittest.main()
