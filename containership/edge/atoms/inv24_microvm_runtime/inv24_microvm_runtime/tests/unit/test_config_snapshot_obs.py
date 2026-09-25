"""MC-013, MC-015, MC-004, MC-040..MC-044, MC-047: config, snapshots, telemetry, schema contracts."""
import io
import json
import os
import pathlib
import unittest

from inv24_microvm_runtime.tests.helpers import tmpdir

from inv24_microvm_runtime import MicroVM
from inv24_microvm_runtime.config import ConfigStore
from inv24_microvm_runtime.errors import ERROR_CODES, Inv24Error
from inv24_microvm_runtime.observability import EventLogger, Tracer, bind, parse_traceparent, standard_registry
from inv24_microvm_runtime.observability.metrics import MAX_SERIES_PER_METRIC, OVERFLOW_LABEL
from inv24_microvm_runtime.schemas import SCHEMA_FILES, load_schema, validate
from inv24_microvm_runtime.snapshot import SnapshotStore

REPO = pathlib.Path(__file__).resolve().parents[3]
BASE = json.loads((REPO / "config/base.json").read_text())
OVERLAYS = json.loads((REPO / "config/overlays.json").read_text())["environments"]


class ConfigTest(unittest.TestCase):
    def test_shipped_config_and_overlays_validate(self):
        validate(BASE)
        s = ConfigStore(tmpdir())
        for env, ov in OVERLAYS.items():
            with self.subTest(env=env):
                s.propose(BASE, environment=ov, author="ci")

    def test_site_cannot_widen(self):
        s = ConfigStore(tmpdir())
        for site in [{"boot_budget_ms": 200}, {"max_instances": 10_000},
                     {"permitted_devices": ["virtio-net", "pci"]}]:
            with self.subTest(site=site), self.assertRaises(Inv24Error):
                s.propose(BASE, site=site, author="x")

    def test_transactional_activate_rollback_and_restart(self):
        d = tmpdir()
        s = ConfigStore(d)
        seen = []
        s.subscribe(seen.append)
        r1 = s.activate(s.propose(BASE, author="alice"))
        r2 = s.activate(s.propose(BASE, site={"max_instances": 100}, author="bob"))
        self.assertEqual((r1["revision"], r2["revision"]), (1, 2))

        def reject(cfg):
            if cfg["max_instances"] == 50:
                raise RuntimeError("listener refuses")
        s.subscribe(reject)
        with self.assertRaises(Inv24Error):
            s.activate(s.propose(BASE, site={"max_instances": 50}, author="eve"))
        self.assertEqual(s.active["revision"], 2)
        rb = s.rollback(author="ops")
        self.assertEqual(s.active["max_instances"], 512)
        self.assertEqual(rb["revision"], 3)
        self.assertEqual(ConfigStore(d).active["revision"], 3)
        with self.assertRaises(Inv24Error) as cm:
            stale = dict(s.active, revision=2)
            s.activate(stale)
        self.assertEqual(cm.exception.code, "STALE_EPOCH")

    def test_inline_secret_rejected(self):
        s = ConfigStore(tmpdir())
        with self.assertRaises(Inv24Error):
            s.activate(dict(BASE, author="ghp_" + "a" * 40))


class SnapshotTest(unittest.TestCase):
    H = "a" * 64

    def _store(self, **kw):
        args = dict(runtime_version="4.3.0", firecracker_version="1.0.0-test",
                    supported_firecracker=frozenset({"1.0.0-test"}), arch="x86_64",
                    cpu_features=frozenset({"avx2", "sse4_2"}))
        args.update(kw)
        return SnapshotStore(self.root, **args)

    def setUp(self):
        self.root = tmpdir()

    def _snap(self, store, sid="snap-1", epoch=3):
        p = store.begin(sid)
        (p / "memory.bin").write_bytes(os.urandom(4096))
        (p / "vmstate.bin").write_bytes(os.urandom(512))
        return store.commit(sid, tenant="t1", workload="w1", devices=["serial"], kernel_sha256=self.H,
                            rootfs_sha256=self.H, ownership_epoch=epoch)

    def test_roundtrip_and_repeat_restore(self):
        s = self._store()
        self._snap(s)
        for _ in range(3):
            s.validate_for_restore("snap-1", tenant="t1", workload="w1", current_epoch=3, device_model=frozenset({"serial"}))
        # clean restart: a new store object sees the committed snapshot
        self._store().validate_for_restore("snap-1", tenant="t1", workload="w1", current_epoch=3, device_model=frozenset({"serial"}))

    def test_rejections(self):
        s = self._store()
        self._snap(s)
        dm = frozenset({"serial"})
        cases = [
            (dict(tenant="t2", workload="w1", current_epoch=3, device_model=dm), "TENANT_MISMATCH"),
            (dict(tenant="t1", workload="w1", current_epoch=4, device_model=dm), "STALE_EPOCH"),
            (dict(tenant="t1", workload="w1", current_epoch=3, device_model=frozenset()), "SNAPSHOT_INCOMPATIBLE"),
        ]
        for kw, code in cases:
            with self.subTest(code=code), self.assertRaises(Inv24Error) as cm:
                s.validate_for_restore("snap-1", **kw)
            self.assertEqual(cm.exception.code, code)
        for other, code in [(dict(arch="aarch64"), "SNAPSHOT_INCOMPATIBLE"),
                            (dict(supported_firecracker=frozenset({"2.0"})), "SNAPSHOT_INCOMPATIBLE"),
                            (dict(cpu_features=frozenset({"sse4_2"})), "SNAPSHOT_INCOMPATIBLE")]:
            with self.subTest(other=other), self.assertRaises(Inv24Error) as cm:
                self._store(**other).validate_for_restore("snap-1", tenant="t1", workload="w1", current_epoch=3, device_model=dm)
            self.assertEqual(cm.exception.code, code)

    def test_truncated_corrupt_missing_and_partial(self):
        s = self._store()
        dm = frozenset({"serial"})
        for i, damage in enumerate(["truncate", "corrupt_meta", "missing"]):
            sid = f"s{i}"
            self._snap(s, sid)
            d = pathlib.Path(self.root) / sid
            if damage == "truncate":
                (d / "memory.bin").write_bytes(b"x")
            elif damage == "corrupt_meta":
                (d / "meta.json").write_text("{not json")
            else:
                (d / "vmstate.bin").unlink()
            with self.subTest(damage=damage), self.assertRaises(Inv24Error) as cm:
                s.validate_for_restore(sid, tenant="t1", workload="w1", current_epoch=0, device_model=dm)
            self.assertEqual(cm.exception.code, "SNAPSHOT_INVALID")
        # crash mid-snapshot: partial dir exists, is not loadable, and is garbage-collected
        p = s.begin("crashy")
        (p / "memory.bin").write_bytes(b"x" * 10)
        with self.assertRaises(Inv24Error):
            s.validate_for_restore("crashy", tenant="t1", workload="w1", current_epoch=0, device_model=dm)
        self.assertEqual(s.gc_partials(), ["crashy.partial"])
        with self.assertRaises(Inv24Error):
            s.begin("../escape")


class TelemetryTest(unittest.TestCase):
    def test_metrics_exposition_and_cardinality_cap(self):
        reg, m = standard_registry()
        m["boot"].observe(0.04, environment="dc")
        m["device_refusals"].inc(device="pci")
        m["instances"].set(1, state="running", tenant="t1")
        for i in range(MAX_SERIES_PER_METRIC + 50):
            m["instances"].set(1, state="running", tenant=f"t{i}")
        self.assertEqual(m["instances"].overflowed, 50)  # t1 reused; 1000 cap
        text = reg.expose()
        self.assertIn('microvm_boot_seconds_bucket{environment="dc",le="0.05"} 1', text)
        self.assertIn("microvm_device_refusals_total", text)
        self.assertIn(OVERFLOW_LABEL, text)
        with self.assertRaises(Inv24Error):
            m["device_refusals"].inc(-1, device="x")
        with self.assertRaises(Inv24Error):
            m["device_refusals"].inc(device="x", tenant="y")

    def test_structured_log_correlation_and_redaction(self):
        buf = io.StringIO()
        log = EventLogger(node="n1", stream=buf)
        with bind(tenant="t1", operation="op-1", trace_id="abc"):
            log.info("admitted", capability_token="eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sig", vcpus=2)
        rec = json.loads(buf.getvalue())
        self.assertEqual((rec["tenant"], rec["operation"], rec["node"]), ("t1", "op-1", "n1"))
        self.assertEqual(rec["fields"]["capability_token"], "[REDACTED]")
        self.assertIsNone(log.log("debug", "noise"))

    def test_trace_propagation(self):
        tr = Tracer()
        tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        with tr.span("admit", traceparent=tp) as s1:
            with tr.span("launch") as s2:
                pass
        self.assertEqual(s1.trace_id, "0af7651916cd43dd8448eb211c80319c")
        self.assertEqual((s2.trace_id, s2.parent_id), (s1.trace_id, s1.span_id))
        for bad in ["", "garbage", "00-" + "0" * 32 + "-b7ad6b7169203331-01"]:
            self.assertIsNone(parse_traceparent(bad))


class SchemaContractTest(unittest.TestCase):
    """Framework-independent consumer contract tests: domain output must satisfy published schemas."""

    def test_all_schemas_load(self):
        for name in SCHEMA_FILES:
            self.assertEqual(load_schema(name)["title"], name)

    def test_domain_records_conform(self):
        vm = MicroVM("vm1", "t1", vcpus=2, memory_mib=256, devices={"serial", "virtio-net"})
        validate(vm.create_record())
        validate(vm.status())
        validate(vm.boot(elapsed_ms=10))
        validate(vm.status())
        validate(vm.stop())

    def test_error_records_conform(self):
        for code in ERROR_CODES:
            validate(Inv24Error(code, "m" * 1000).to_dict())

    def test_unknown_error_code_is_never_silently_accepted(self):
        self.assertEqual(Inv24Error("NOPE").code, "CONFIG_REJECTED")


if __name__ == "__main__":
    unittest.main()
