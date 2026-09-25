"""GAP-02 v4.3.0 production-layer tests. Test class names carry the MC id they evidence."""
import base64, json, os, random, sys, tempfile, threading, time, unittest, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from gap02_hardware_capability_discovery.capabilities import CapabilityReport
from gap02_hardware_capability_discovery.production import (
    accelerators as acc, cpu, topology, storage, nic, virt, confidential, securedev, envelope, replay,
    timepolicy, config, sweep, executor, publisher, errors, broker, authz, provenance, integration, compat,
    cache, hotplug, health, observability, audit, explain, breaker, quarantine, limits)
from gap02_hardware_capability_discovery.production.errors import Code, Gap02Error
from gap02_hardware_capability_discovery.production.evidence import ProbeEvidence, promote, Host
import fixtures as fx

KEY = b"k" * 32


class FakeClock:
    def __init__(self, t=1_000_000.0):
        self.t = t
    def wall(self): return self.t
    def mono(self): return self.t
    def tick(self, s): self.t += s


def synced_clock():
    c = FakeClock()
    tc = timepolicy.TrustedClock(wall=c.wall, mono=c.mono)
    tc.sync(c.t, "ntp")
    return c, tc


# ---------------------------------------------------------------- invariant
class TestInvariant_MC00(unittest.TestCase):
    def test_observations_never_promote(self):
        for k in ("observation", "name-match", "driver-presence", "heuristic", "cache"):
            self.assertEqual(promote(ProbeEvidence("x", True, k, "s")), "unprobed")
    def test_error_blocks_promotion(self):
        self.assertEqual(promote(ProbeEvidence("x", True, "runtime-call", "s", error="GAP02-E004")), "unprobed")
    def test_non_bool_rejected(self):
        with self.assertRaises(ValueError):
            ProbeEvidence("x", 1, "runtime-call", "s")


# ---------------------------------------------------------------- MC-01 GPU
class TestGpu_MC01(unittest.TestCase):
    def cfg(self, **k): return {"cuda_runtime_version": "12.4", **k}
    def test_positive(self):
        d, ev = acc._nvidia(fx.nvidia(), self.cfg())
        self.assertEqual(promote(ev), "present"); self.assertTrue(d[0].schedulable)
        self.assertEqual(d[0].memory_total_bytes, 81920 * acc.MIB)
    def test_runtime_unknown_is_unproven(self):
        d, ev = acc._nvidia(fx.nvidia(), {})
        self.assertIsNone(d[0].compatible); self.assertNotEqual(promote(ev), "present")
    def test_driver_mismatch(self):
        d, ev = acc._nvidia(fx.nvidia(q="GPU-a, 0, 470.1.1, 100, 50, Disabled, 0\n"), self.cfg())
        self.assertFalse(d[0].compatible); self.assertIn("minimum", d[0].incompatibility)
        self.assertNotEqual(promote(ev), "present")
    def test_runtime_missing(self):
        _, ev = acc._nvidia(fx.linux(), self.cfg())
        self.assertEqual(ev.error, Code.PROBE_UNAVAILABLE.value); self.assertEqual(promote(ev), "unprobed")
    def test_driver_unreachable(self):
        _, ev = acc._nvidia(fx.nvidia(rc=9, q="NVIDIA-SMI has failed because it couldn't communicate"), self.cfg())
        self.assertEqual(ev.error, Code.DRIVER_ERROR.value)
    def test_permission_denied(self):
        h = fx.linux(denied=["/sys/class/kfd/kfd/topology/nodes/1/properties"],
                     files={"/sys/class/kfd/kfd/topology/nodes/1/properties": "simd_count 64"})
        _, ev = acc._amd(h, {})
        self.assertEqual(ev.error, Code.PRIVILEGE_DENIED.value)
    def test_timeout(self):
        _, ev = acc._nvidia(fx.linux(timeout_paths=[acc.NVSMI]), self.cfg())
        self.assertEqual(ev.error, Code.TIMEOUT.value)
    def test_unhealthy(self):
        d, ev = acc._nvidia(fx.nvidia(q="GPU-a, 0, 550.1.1, 100, 50, Disabled, 3\n"), self.cfg())
        self.assertEqual(d[0].health, "unhealthy"); self.assertFalse(ev.result)
    def test_health_unavailable_fails_closed(self):
        d, ev = acc._nvidia(fx.nvidia(q="GPU-a, 0, 550.1.1, 100, 50, Disabled, [N/A]\n"), self.cfg())
        self.assertEqual(d[0].health, "unknown"); self.assertFalse(d[0].schedulable)
    def test_partitioned_no_double_count(self):
        d, _ = acc._nvidia(fx.nvidia(q=fx.NV_MIG, lst=fx.NV_LIST_MIG), self.cfg())
        units = integration.allocation_units(d)
        self.assertEqual([u["unit_id"] for u in units], ["MIG-bbbb-1", "MIG-bbbb-2"])
        self.assertEqual(d[0].children, ["MIG-bbbb-1", "MIG-bbbb-2"])
    def test_malformed(self):
        _, ev = acc._nvidia(fx.nvidia(q="garbage\n"), self.cfg())
        self.assertEqual(ev.error, Code.MALFORMED_RESPONSE.value)
    def test_index_not_identity(self):
        d, _ = acc._nvidia(fx.nvidia(), self.cfg())
        self.assertTrue(d[0].stable_id.startswith("GPU-")); self.assertEqual(d[0].enum_index, 0)
    def test_platform_not_supported(self):
        _, ev = acc._amd(Host(files={}, commands={}, system="Darwin"), {})
        self.assertEqual(ev.error, Code.UNSUPPORTED_PLATFORM.value)
    def test_display_adapter_not_compute(self):
        h = fx.linux(files={"/sys/class/drm/card0/device/vendor": "0x10de"})
        out = acc.probe_accelerators(h, {})
        self.assertTrue(all(promote(e) != "present" for e in out["evidence"]))
    def test_apple_never_schedulable(self):
        h = Host(files={}, commands={(acc.SYSPROF, "SPDisplaysDataType", "-json"):
                 (0, json.dumps({"SPDisplaysDataType": [{"spdisplays_mtlgpufamilysupport": "metal3"}]}))}, system="Darwin")
        d, ev = acc._apple(h, {})
        self.assertFalse(d[0].schedulable); self.assertFalse(ev.result)
    def test_amd_positive(self):
        h = fx.linux(files={"/sys/class/kfd/kfd/topology/nodes/1/properties": "simd_count 64\nunique_id 77",
                            "/opt/rocm/.info/version": "6.1.0"},
                     commands={(acc.ROCM_SMI, "--showuniqueid", "--showhealth", "--json"):
                               (0, json.dumps({"card0": {"Unique ID": "77", "Health": "OK"}}))})
        d, ev = acc._amd(h, {})
        self.assertEqual(promote(ev), "present"); self.assertEqual(d[0].stable_id, "AMD-77")


# ---------------------------------------------------------------- MC-02 NPU
class TestNpu_MC02(unittest.TestCase):
    CHK = ("/opt/vendor/npu-check",)
    def test_driver_alone_is_not_proof(self):
        h = fx.linux(files={"/sys/class/accel/accel0/device/driver_name": "intel_vpu"})
        _, ev = acc._npu(h, {})
        self.assertEqual(promote(ev), "unprobed"); self.assertEqual(ev.facts.get("detail", "")[:9], "no NPU ru")
    def test_runtime_usable(self):
        h = fx.linux(commands={self.CHK: (0, json.dumps({"usable": True, "device_id": "npu-1", "health": "healthy"}))})
        d, ev = acc._npu(h, {"npu_runtime_checks": {"intel": self.CHK}})
        self.assertEqual(promote(ev), "present"); self.assertTrue(d[0].schedulable)
    def test_runtime_unusable(self):
        h = fx.linux(commands={self.CHK: (0, json.dumps({"usable": False, "device_id": "npu-1"}))})
        _, ev = acc._npu(h, {"npu_runtime_checks": {"intel": self.CHK}})
        self.assertEqual(promote(ev), "absent")
    def test_malformed(self):
        h = fx.linux(commands={self.CHK: (0, json.dumps({"usable": "yes"}))})
        _, ev = acc._npu(h, {"npu_runtime_checks": {"intel": self.CHK}})
        self.assertEqual(ev.error, Code.MALFORMED_RESPONSE.value)
    def test_apple_unsupported(self):
        _, ev = acc._npu(Host(files={}, commands={}, system="Darwin"), {})
        self.assertEqual(ev.error, Code.UNSUPPORTED_PLATFORM.value)


# ---------------------------------------------------------------- MC-03 CPU
class TestCpu_MC03(unittest.TestCase):
    def test_x86(self):
        r = cpu.probe_cpu(fx.linux(files={"/proc/cpuinfo": fx.CPUINFO_X86}))
        self.assertIn("avx2", r["features"]); self.assertIn("virt.slat", r["features"])
        states = {e.capability: promote(e) for e in cpu.feature_evidence(r)}
        self.assertEqual(states["cpu.x86.avx2"], "present"); self.assertEqual(states["cpu.x86.avx512f"], "absent")
    def test_arm(self):
        r = cpu.probe_cpu(fx.linux(files={"/proc/cpuinfo": fx.CPUINFO_ARM}, machine="aarch64"))
        self.assertEqual(r["arch"], "arm64"); self.assertIn("sve", r["features"]); self.assertIn("lse", r["features"])
    def test_riscv(self):
        r = cpu.probe_cpu(fx.linux(files={"/proc/cpuinfo": "isa\t: rv64imafdcv_zicsr\n"}, machine="riscv64"))
        self.assertIn("rvv", r["features"])
    def test_unknown_arch(self):
        r = cpu.probe_cpu(fx.linux(machine="mips"))
        self.assertEqual(r["evidence"].error, Code.UNSUPPORTED_PLATFORM.value)
        self.assertEqual(cpu.feature_evidence(r), [])
    def test_darwin_partial_source_never_claims_absent(self):
        h = Host(files={}, commands={("/usr/sbin/sysctl", "-n", "hw.optional.neon"): (0, "1\n")}, system="Darwin", machine="arm64")
        r = cpu.probe_cpu(h)
        states = {e.capability: promote(e) for e in cpu.feature_evidence(r)}
        self.assertEqual(states, {"cpu.arm64.neon": "present"})
    def test_missing_cpuinfo(self):
        self.assertEqual(cpu.probe_cpu(fx.linux())["evidence"].error, Code.PROBE_UNAVAILABLE.value)


# ---------------------------------------------------------------- MC-04..09
class TestNuma_MC04(unittest.TestCase):
    def test_two_nodes(self):
        r = topology.probe_numa(fx.linux(files=fx.NUMA2))
        self.assertEqual(promote(r["evidence"]), "present"); self.assertEqual(r["nodes"][1]["mem_total_bytes"], 2048 * 1024)
        self.assertEqual(promote(r["hugepage_evidence"]), "present"); self.assertEqual(promote(r["ecc_evidence"]), "unprobed")
    def test_unsupported(self):
        self.assertEqual(topology.probe_numa(Host(files={}, system="Windows"))["evidence"].error, Code.UNSUPPORTED_PLATFORM.value)


class TestStorage_MC05(unittest.TestCase):
    def test_nvme(self):
        f = {"/sys/block/nvme0n1/size": "2000", "/sys/block/nvme0n1/queue/rotational": "0",
             "/sys/block/nvme0n1/queue/discard_max_bytes": "2199023255040", "/sys/block/loop0/size": "8"}
        r = storage.probe_storage(fx.linux(files=f))
        self.assertEqual(len(r["devices"]), 1); self.assertEqual(r["devices"][0]["capacity_bytes"], 2000 * 512)
        self.assertTrue(all(promote(e) == "present" for e in r["derived"]))
        self.assertNotIn("serial", json.dumps(r["devices"]))


class TestNic_MC06(unittest.TestCase):
    def test_physical_virtual_and_no_addresses(self):
        f = {"/sys/class/net/eth0/device/vendor": "x", "/sys/class/net/eth0/speed": "25000",
             "/sys/class/net/eth0/mtu": "9000", "/sys/class/net/eth0/queues/rx-0/x": "",
             "/sys/class/net/eth0/queues/rx-1/x": "", "/sys/class/net/eth0/device/sriov_totalvfs": "8",
             "/sys/class/net/eth0/address": "aa:bb:cc:dd:ee:ff", "/sys/class/net/lo/mtu": "65536"}
        r = nic.probe_nics(fx.linux(files=f))
        e0 = next(x for x in r["nics"] if x["name"] == "eth0")
        self.assertTrue(e0["physical"]); self.assertEqual(e0["speed_mbps"], 25000)
        self.assertFalse(next(x for x in r["nics"] if x["name"] == "lo")["physical"])
        self.assertNotIn("aa:bb", json.dumps(r["nics"]))
        st = {e.capability: promote(e) for e in r["derived"]}
        self.assertEqual(st["network.sriov"], "present"); self.assertEqual(st["network.rss"], "present")


class TestVirt_MC07(unittest.TestCase):
    def test_kvm_iommu(self):
        f = {"/proc/cpuinfo": "flags : vmx ept", "/dev/kvm": "", "/sys/kernel/iommu_groups/0/x": "",
             "/sys/module/kvm_intel/parameters/nested": "Y"}
        r = virt.probe_virt(fx.linux(files=f))
        self.assertEqual(promote(r["evidence"]), "present")
        self.assertEqual({e.capability: promote(e) for e in r["derived"]},
                         {"virtualization.iommu": "present", "virtualization.nested": "present"})
    def test_extension_without_kvm_is_absent_for_host(self):
        r = virt.probe_virt(fx.linux(files={"/proc/cpuinfo": "flags : vmx"}))
        self.assertEqual(promote(r["evidence"]), "absent")
    def test_darwin_malformed(self):
        h = Host(files={}, commands={("/usr/sbin/sysctl", "-n", "kern.hv_support"): (0, "maybe")}, system="Darwin")
        self.assertEqual(virt.probe_virt(h)["evidence"].error, Code.MALFORMED_RESPONSE.value)


class TestConfidential_MC08(unittest.TestCase):
    F = {"/sys/module/kvm_amd/parameters/sev_snp": "Y"}
    def test_enabled_but_unattested(self):
        ev = {e.capability: promote(e) for e in confidential.probe_confidential(fx.linux(files=self.F))["evidence"]}
        self.assertEqual(ev["cc.sev-snp.enabled"], "present"); self.assertEqual(ev["cc.sev-snp.attested"], "unprobed")
    def test_attested_with_verifier_and_nonce(self):
        ev = {e.capability: promote(e) for e in confidential.probe_confidential(
            fx.linux(files=self.F), nonce=os.urandom(16), verifier=lambda t, n: True)["evidence"]}
        self.assertEqual(ev["cc.sev-snp.attested"], "present")
    def test_short_nonce_refused(self):
        ev = {e.capability: promote(e) for e in confidential.probe_confidential(
            fx.linux(files=self.F), nonce=b"x", verifier=lambda t, n: True)["evidence"]}
        self.assertEqual(ev["cc.sev-snp.attested"], "unprobed")
    def test_verifier_crash(self):
        def boom(t, n): raise RuntimeError
        ev = [e for e in confidential.probe_confidential(fx.linux(files=self.F), nonce=os.urandom(16), verifier=boom)["evidence"]
              if e.capability == "cc.sev-snp.attested"][0]
        self.assertEqual(ev.error, Code.DEPENDENCY_FAILURE.value)


class TestSecureDevice_MC09(unittest.TestCase):
    def test_tpm2_usable(self):
        f = {"/sys/class/tpm/tpm0/tpm_version_major": "2", "/sys/class/tpm/tpm0/pcr-sha256/0": "", "/dev/tpmrm0": ""}
        r = securedev.probe_tpm(fx.linux(files=f))
        self.assertEqual(promote(r["evidence"]), "present"); self.assertEqual(r["pcr_banks"], ["sha256"])
    def test_tpm_denied(self):
        f = {"/sys/class/tpm/tpm0/tpm_version_major": "2", "/dev/tpmrm0": ""}
        r = securedev.probe_tpm(fx.linux(files=f, denied=["/dev/tpmrm0"]))
        self.assertEqual(r["evidence"].error, Code.PRIVILEGE_DENIED.value)
    def test_tpm12_absent_for_tpm2(self):
        r = securedev.probe_tpm(fx.linux(files={"/sys/class/tpm/tpm0/tpm_version_major": "1"}))
        self.assertEqual(promote(r["evidence"]), "absent")
    def test_none(self):
        self.assertEqual(promote(securedev.probe_tpm(fx.linux())["evidence"]), "absent")


# ---------------------------------------------------------------- MC-10/11/12
def make_report(node="n1", now=1_000_000):
    r = CapabilityReport(node); r.record("cpu", "present", now); r.record("gpu", "unprobed", now); return r


IDENT = {"attested": True, "identity_id": "dev-1", "evidence_digest": "e" * 64}


class TestEnvelope_MC10(unittest.TestCase):
    def setUp(self):
        self.c, self.clock = synced_clock()
        self.s = envelope.HmacSigner("k1", KEY)
        self.seq = replay.Sequencer("boot-1")
    def seal(self):
        now = int(self.c.t)
        return envelope.seal(make_report(now=now), now, self.s, identity=IDENT, sequence=self.seq.next("t"), generation="g")
    def open(self, env, **kw):
        return envelope.open_envelope(env, verifier=self.s, identity_check=lambda i: True, clock=self.clock,
                                      guard=kw.pop("guard", replay.ReplayGuard()), **kw)
    def test_roundtrip(self):
        self.assertEqual(self.open(self.seal())["present"], ["cpu"])
    def test_tamper(self):
        env = self.seal(); b = json.loads(json.dumps(env.body)); b["facts"]["present"].append("gpu")
        with self.assertRaises(Gap02Error) as cm:
            self.open(envelope.SignedEnvelope(b, env.key_id, env.alg, env.signature))
        self.assertEqual(cm.exception.code, Code.SIGNATURE_FAILURE)
    def test_unattested_refused(self):
        with self.assertRaises(Gap02Error):
            envelope.seal(make_report(), 1_000_000, self.s, identity={"attested": False}, sequence={}, generation="g")
    def test_identity_rejected(self):
        with self.assertRaises(Gap02Error) as cm:
            envelope.open_envelope(self.seal(), verifier=self.s, identity_check=lambda i: False,
                                   clock=self.clock, guard=replay.ReplayGuard())
        self.assertEqual(cm.exception.code, Code.UNATTESTED)
    def test_revoked(self):
        with self.assertRaises(Gap02Error):
            self.open(self.seal(), revoked=frozenset({"k1"}))
    def test_stale(self):
        env = self.seal(); self.c.tick(120)
        with self.assertRaises(Gap02Error) as cm: self.open(env)
        self.assertEqual(cm.exception.code, Code.STALE_DATA)
    def test_schema(self):
        with self.assertRaises(Gap02Error): envelope.SignedEnvelope.from_dict({"schema": "X/9"})
    def test_zeroize(self):
        self.s.zeroize(); self.assertEqual(bytes(self.s._key), b"\0" * 32)


class TestReplay_MC11(unittest.TestCase):
    def test_replay_rejected(self):
        g, s = replay.ReplayGuard(), replay.Sequencer("b")
        a = s.next("t1"); g.admit("n", a)
        with self.assertRaises(Gap02Error): g.admit("n", a)
    def test_old_sequence_rejected(self):
        g, s = replay.ReplayGuard(), replay.Sequencer("b")
        a, b = s.next("t1"), s.next("t1"); g.admit("n", b)
        with self.assertRaises(Gap02Error): g.admit("n", a)
    def test_topology_change_invalidates_old_epoch(self):
        g, s = replay.ReplayGuard(), replay.Sequencer("b")
        old = s.next("t1"); new = s.next("t2")
        g.topology_changed("n", "b", new["epoch"])
        with self.assertRaises(Gap02Error): g.admit("n", old)
        g.admit("n", new)
    def test_malformed(self):
        with self.assertRaises(Gap02Error): replay.ReplayGuard().admit("n", {"epoch": "x"})


class TestTrustedTime_MC12(unittest.TestCase):
    def test_unsynced(self):
        with self.assertRaises(Gap02Error): timepolicy.TrustedClock().now()
    def test_rollback_detected(self):
        c, tc = synced_clock(); tc.now(); c.t -= 0  # mono and wall move together normally
        c2 = FakeClock(); tc2 = timepolicy.TrustedClock(wall=lambda: c2.t - 600, mono=c2.mono); tc2.sync(c2.t, "ntp")
        with self.assertRaises(Gap02Error) as cm: tc2.now()
        self.assertEqual(cm.exception.code, Code.CLOCK_UNTRUSTED)
    def test_low_quality(self):
        c = FakeClock(); tc = timepolicy.TrustedClock(wall=c.wall, mono=c.mono); tc.sync(c.t, "local-rtc")
        with self.assertRaises(Gap02Error): tc.now()
    def test_sync_expiry(self):
        c, tc = synced_clock(); c.tick(4000)
        with self.assertRaises(Gap02Error): tc.now()
    def test_future_signature(self):
        c, tc = synced_clock()
        with self.assertRaises(Gap02Error): tc.check_signed_at(int(c.t) + 100, int(c.t), 60)


# ---------------------------------------------------------------- MC-13/14/15
class TestConfig_MC13(unittest.TestCase):
    def test_defaults_secure(self):
        c = config.ProbeConfig(); self.assertFalse(c.allow_reference_signer)
    def test_unknown_key(self):
        with self.assertRaises(Gap02Error): config.ProbeConfig.from_dict({"intervall": 5}, env={})
    def test_env_allowlist(self):
        self.assertEqual(config.ProbeConfig.from_dict({}, env={"GAP02_INTERVAL_SECONDS": "30"}).interval_seconds, 30)
        with self.assertRaises(Gap02Error):
            config.ProbeConfig.from_dict({}, env={"GAP02_ALLOW_REFERENCE_SIGNER": "1"})
    def test_ranges(self):
        for bad in ({"interval_seconds": 0}, {"max_concurrency": 99}, {"enabled_probes": ["x"]},
                    {"npu_runtime_checks": {"v": ["rel/path"]}}, {"schema": "GAP02_PROBE_CONFIG/2"}):
            with self.assertRaises(Gap02Error): config.ProbeConfig.from_dict(bad, env={})
    def test_deny_list(self):
        c = config.ProbeConfig.from_dict({"denied_probes": ["accelerators"]}, env={})
        self.assertNotIn("accelerators", c.active_probes)


def ev(cap, r=True): return ProbeEvidence(cap, r, "kernel-attribute", "t")


class TestExecutor_MC14(unittest.TestCase):
    def test_wedged_probe_cannot_stall(self):
        block = threading.Event()
        probes = {"fast": (lambda: [ev("a")], ("a",)),
                  "wedged": (lambda: (block.wait(5), [ev("b")])[1], ("b",))}
        ex = executor.ProbeExecutor("n", probes, probe_timeout=0.2, sweep_deadline=1.0, clock=lambda: 100)
        t0 = time.monotonic(); snap = ex.sweep(); took = time.monotonic() - t0
        block.set(); ex.stop()
        self.assertLess(took, 1.5)
        self.assertEqual(snap.report.state("a"), "present"); self.assertEqual(snap.report.state("b"), "unprobed")
    def test_queued_probes_not_falsely_timed_out(self):
        probes = {f"p{i}": (lambda i=i: (time.sleep(0.1), [ev(f"c{i}")])[1], (f"c{i}",)) for i in range(8)}
        ex = executor.ProbeExecutor("n", probes, max_concurrency=2, probe_timeout=0.3, sweep_deadline=5, clock=lambda: 1)
        s = ex.sweep(); ex.stop()
        self.assertEqual(sorted(s.report.present()), [f"c{i}" for i in range(8)])
    def test_crash_is_unprobed(self):
        ex = executor.ProbeExecutor("n", {"p": (lambda: 1 / 0, ("a",))}, clock=lambda: 100)
        self.assertEqual(ex.sweep().report.state("a"), "unprobed"); ex.stop()
    def test_hotplug_wakes_loop(self):
        n = []
        ex = executor.ProbeExecutor("n", {"p": (lambda: (n.append(1), [ev("a")])[1], ("a",))}, clock=lambda: 100 + len(n))
        th = threading.Thread(target=ex.run, args=(30,), kwargs={"max_sweeps": 2}); th.start()
        time.sleep(0.2); ex.notify_hotplug(["p"]); th.join(3); ex.stop()
        self.assertEqual(len(n), 2)


class TestAtomicSweep_MC15(unittest.TestCase):
    def test_all_declared_present_in_snapshot(self):
        b = sweep.SweepBuilder("n", ("a", "b"), 10, 1); b.add(ev("a"))
        s = b.seal(); self.assertEqual(s.report.state("b"), "unprobed")
        with self.assertRaises(Gap02Error): b.add(ev("b"))
    def test_older_cannot_replace_newer(self):
        st = sweep.SnapshotStore()
        st.publish(sweep.SweepBuilder("n", ("a",), 10, 2).seal())
        with self.assertRaises(Gap02Error): st.publish(sweep.SweepBuilder("n", ("a",), 11, 1).seal())
    def test_generation_changes_with_topology(self):
        b1 = sweep.SweepBuilder("n", ("a",), 10, 1); b1.add(ev("a"))
        b2 = sweep.SweepBuilder("n", ("a",), 10, 1); b2.add(ev("a", False))
        self.assertNotEqual(b1.seal().generation, b2.seal().generation)


# ---------------------------------------------------------------- MC-16..20
class FlakyTransport:
    def __init__(self, fails=0, bad_ack=False): self.fails, self.sent, self.bad = fails, [], bad_ack
    def send(self, key, payload, timeout):
        if self.fails: self.fails -= 1; raise OSError("down")
        self.sent.append(key); return {"ack": True, "key": "other" if self.bad else key}


class TestPublisher_MC16(unittest.TestCase):
    def pub(self, t, **k): return publisher.Publisher(t, sleep=lambda s: None, rng=random.Random(0), **k)
    def test_retry_then_ack(self):
        p = self.pub(FlakyTransport(fails=2)); p.enqueue("g1", {}); self.assertEqual(p.flush(), 1)
        self.assertEqual(p.stats.retries, 2)
    def test_idempotent(self):
        t = FlakyTransport(); p = self.pub(t); p.enqueue("g1", {}); p.enqueue("g1", {}); p.flush(); p.enqueue("g1", {}); p.flush()
        self.assertEqual(t.sent, ["g1"])
    def test_backpressure_drops_oldest(self):
        p = self.pub(FlakyTransport(fails=999), buffer_size=2)
        for k in "abc": p.enqueue(k, {})
        self.assertEqual([k for k, _ in p.buf], ["b", "c"]); self.assertEqual(p.stats.dropped, 1)
    def test_wrong_ack_not_delivered(self):
        p = self.pub(FlakyTransport(bad_ack=True), max_attempts=2); p.enqueue("g", {}); self.assertEqual(p.flush(), 0)
    def test_cancel(self):
        p = self.pub(FlakyTransport()); p.enqueue("g", {}); p.cancel(); self.assertEqual(p.flush(), 0)
    def test_offline_then_reconnect(self):
        t = FlakyTransport(fails=10); p = self.pub(t, max_attempts=3); p.enqueue("g", {})
        self.assertEqual(p.flush(), 0); t.fails = 0; self.assertEqual(p.flush(), 1)


class TestErrorTaxonomy_MC17(unittest.TestCase):
    def test_codes_unique_and_stable(self):
        vals = [c.value for c in Code]; self.assertEqual(len(vals), len(set(vals)))
        self.assertEqual(Code.TIMEOUT.value, "GAP02-E004")
        self.assertFalse(set(vals) & errors.RESERVED)
    def test_classify(self):
        import subprocess
        self.assertEqual(errors.classify(PermissionError()), Code.PRIVILEGE_DENIED)
        self.assertEqual(errors.classify(subprocess.TimeoutExpired("x", 1)), Code.TIMEOUT)
        self.assertEqual(errors.classify(RuntimeError()), Code.INTERNAL)
    def test_bounded_detail(self):
        self.assertEqual(len(Gap02Error(Code.INTERNAL, "x" * 9999).detail), 512)
        self.assertIn("runbook", Gap02Error(Code.TIMEOUT).to_dict())


class TestBroker_MC18(unittest.TestCase):
    def test_unknown_op_denied(self):
        self.assertEqual(broker.handle({"op": "cat /etc/shadow"})["code"], Code.POLICY_DENIED.value)
    def test_param_injection_rejected(self):
        self.assertEqual(broker.handle({"op": "smart.health", "dev": "sda; rm -rf /"})["code"], Code.CONFIG_INVALID.value)
        self.assertEqual(broker.handle({"op": "efi.secureboot", "dev": "x"})["code"], Code.CONFIG_INVALID.value)
    def test_client_requires_authz(self):
        c = broker.BrokerClient(authz.AuthzPolicy(bindings={"svc": {"scheduler"}}), "svc")
        with self.assertRaises(Gap02Error): c.call("efi.secureboot")
    def test_process_boundary(self):
        c = broker.BrokerClient(authz.AuthzPolicy(bindings={"sec": {"security-admin"}}), "sec")
        r = c.call("nope"); self.assertEqual(r["code"], Code.POLICY_DENIED.value)


class TestAuthz_MC19(unittest.TestCase):
    def test_deny_default(self):
        p = authz.AuthzPolicy(bindings={"s": {"scheduler"}})
        self.assertTrue(p.allowed("s", "read.scheduling_facts"))
        for a in ("read.detailed_inventory", "probe.deep", "probe.force", "control.freeze", "bogus"):
            self.assertFalse(p.allowed("s", a))
        self.assertFalse(p.allowed("stranger", "read.scheduling_facts"))
    def test_bad_role(self):
        with self.assertRaises(Gap02Error): authz.AuthzPolicy(roles={"x": {"root"}})


class TestProvenance_MC20(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.path = os.path.join(self.d, "plug.py")
        open(self.path, "w").write("VALUE = 42\n")
        self.s = envelope.HmacSigner("rel", KEY)
    def manifest(self, **over):
        e = {"sha256": provenance.sha256_file(self.path), "version": "1.0", "approved_versions": ["1.0"],
             "license": "MIT", "dependencies": [], "provenance": {"builder": "ci"}}; e.update(over)
        plugins = {"plug": e}
        body = json.dumps(plugins, sort_keys=True, separators=(",", ":")).encode()
        return {"plugins": plugins, "key_id": "rel", "alg": self.s.alg, "signature": base64.b64encode(self.s.sign(body)).decode()}
    def test_ok(self):
        self.assertEqual(provenance.ProvenancePolicy(self.manifest(), verifier=self.s).load("plug", self.path).VALUE, 42)
    def test_tampered_file(self):
        p = provenance.ProvenancePolicy(self.manifest(), verifier=self.s)
        open(self.path, "a").write("X=1\n")
        with self.assertRaises(Gap02Error): p.load("plug", self.path)
    def test_bad_manifest_sig(self):
        m = self.manifest(); m["plugins"]["plug"]["version"] = "2.0"
        with self.assertRaises(Gap02Error): provenance.ProvenancePolicy(m, verifier=self.s)
    def test_policy_failures(self):
        for over in ({"approved_versions": ["0.9"]}, {"license": "GPL-3.0"}, {"provenance": {}}):
            with self.assertRaises(Gap02Error):
                provenance.ProvenancePolicy(self.manifest(**over), verifier=self.s).load("plug", self.path)
        with self.assertRaises(Gap02Error):
            provenance.ProvenancePolicy(self.manifest(dependencies=["evil"]), verifier=self.s,
                                        forbidden_deps=frozenset({"evil"})).load("plug", self.path)
    def test_unapproved(self):
        with self.assertRaises(Gap02Error): provenance.ProvenancePolicy(self.manifest(), verifier=self.s).load("x", self.path)


# ---------------------------------------------------------------- MC-21..26 (contract fakes)
class FakeIdp:
    def __init__(self, ok=True, bind=True): self.ok, self.bind = ok, bind
    def attest(self, node, nonce):
        return {"attested": self.ok, "identity_id": "id-" + node, "evidence_digest": "d" * 64,
                "nonce": nonce.hex() if self.bind else "00"}
    def check(self, ident): return ident.get("identity_id", "").startswith("id-")


class TestGap06Contract_MC21(unittest.TestCase):
    def test_bind(self):
        n = os.urandom(16); self.assertEqual(integration.bind_identity(FakeIdp(), "n1", n)["identity_id"], "id-n1")
    def test_failures(self):
        n = os.urandom(16)
        for idp, code in ((FakeIdp(ok=False), Code.UNATTESTED), (FakeIdp(bind=False), Code.REPLAY_DETECTED)):
            with self.assertRaises(Gap02Error) as cm: integration.bind_identity(idp, "n1", n)
            self.assertEqual(cm.exception.code, code)
        class Down:
            def attest(self, *a): raise ConnectionError
        with self.assertRaises(Gap02Error) as cm: integration.bind_identity(Down(), "n1", n)
        self.assertEqual(cm.exception.code, Code.DEPENDENCY_FAILURE)


class TestGap07Contract_MC22(unittest.TestCase):
    def test_rotation_revocation_unavailable(self):
        c, clock = synced_clock(); ring = integration.KeyRing()
        k1, k2 = envelope.HmacSigner("k1", KEY), envelope.HmacSigner("k2", b"z" * 32)
        ring.provision(k1); now = int(c.t)
        e1 = envelope.seal(make_report(now=now), now, ring.signer(), identity=IDENT,
                           sequence=replay.Sequencer("b").next("t"), generation="g")
        ring.rotate(k2)
        g = replay.ReplayGuard()
        envelope.open_envelope(e1, verifier=ring, identity_check=lambda i: True, clock=clock, guard=g)  # old key still verifies
        ring.revoke("k1")
        with self.assertRaises(Gap02Error):
            envelope.open_envelope(e1, verifier=ring, identity_check=lambda i: True, clock=clock, guard=replay.ReplayGuard())
        ring.revoke("k2")
        with self.assertRaises(Gap02Error) as cm: ring.signer()
        self.assertEqual(cm.exception.code, Code.SIGNATURE_FAILURE)


class TestGap01Contract_MC23(unittest.TestCase):
    def test_readiness_quarantine_hotplug(self):
        ex = executor.ProbeExecutor("n", {"p": (lambda: [ev("a")], ("a",))}, clock=lambda: 100)
        link = integration.SupervisorLink(ex)
        self.assertEqual(link.readiness(100)["reason"], "no sweep")
        ex.sweep(); self.assertTrue(link.readiness(100)["ready"])
        self.assertEqual(link.readiness(1000)["reason"], "stale")
        link.route_hotplug(["p", "unknown"]); self.assertEqual(ex._hot, {"p"})
        link.disable("ops", "incident"); self.assertEqual(link.readiness(100)["reason"], "frozen")
        self.assertEqual(ex.sweep().report.state("a"), "unprobed"); ex.stop()


class TestSch01Contract_MC24(unittest.TestCase):
    def test_unprobed_never_matches(self):
        facts = {"present": ["cpu"], "unprobed": ["gpu.compute.nvidia"], "absent": []}
        ok, why = integration.placement_match({"capabilities": ["gpu.compute.nvidia"]}, facts)
        self.assertFalse(ok); self.assertIn("unprobed", why)
    def test_quantitative(self):
        d, _ = acc._nvidia(fx.nvidia(), {"cuda_runtime_version": "12.4"})
        facts = {"present": ["gpu.compute.nvidia"]}
        self.assertTrue(integration.placement_match({"capabilities": ["gpu.compute.nvidia"], "min": {"gpu.memory_bytes": 10}}, facts, d)[0])
        self.assertFalse(integration.placement_match({"min": {"gpu.memory_bytes": 10**15}}, facts, d)[0])
        self.assertFalse(integration.placement_match({"min": {"gpu.count": 2}}, facts, d)[0])


class TestPln04Contract_MC25(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(integration.tier_catalog({"present": []}), ["process"])
        self.assertEqual(integration.tier_catalog({"present": ["virtualization.host", "virtualization.iommu", "cc.sev-snp.enabled"]}),
                         ["microvm", "passthrough-vm", "process"])  # enabled-but-unattested ≠ confidential tier


class TestGap11Contract_MC26(unittest.TestCase):
    def test_units_only_schedulable(self):
        d, _ = acc._nvidia(fx.nvidia(q="GPU-a, 0, 550.1.1, 100, 50, Disabled, 1\n"), {"cuda_runtime_version": "12.4"})
        self.assertEqual(integration.allocation_units(d), [])


# ---------------------------------------------------------------- MC-27..40
class TestCompat_MC27(unittest.TestCase):
    def test_negotiate(self):
        self.assertEqual(compat.negotiate("PK_NODE_CAPABILITIES", [1, 2]), 1)
        with self.assertRaises(Gap02Error): compat.negotiate("PK_NODE_CAPABILITIES", [2])
    def test_unknown_fields(self):
        clean, unk = compat.accept({"schema": "PK_NODE_CAPABILITIES/1", "node": "n", "extra": 1})
        self.assertEqual(unk, ["extra"]); self.assertNotIn("extra", clean)
        with self.assertRaises(Gap02Error):
            compat.accept({"schema": "PK_NODE_CAPABILITIES/1", "critical": ["newthing"], "newthing": 1})
    def test_migration(self):
        compat.MIGRATIONS[("PK_NODE_CAPABILITIES", 0)] = lambda p: {**p, "schema": "PK_NODE_CAPABILITIES/1"}
        try:
            self.assertEqual(compat.accept({"schema": "PK_NODE_CAPABILITIES/0", "node": "n"})[0]["schema"], "PK_NODE_CAPABILITIES/1")
        finally:
            compat.MIGRATIONS.clear()
        with self.assertRaises(Gap02Error): compat.accept({"schema": "PK_NODE_CAPABILITIES/0"})


class TestCache_MC28(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "c.json"); self.s = envelope.HmacSigner("c", KEY)
        b = sweep.SweepBuilder("n", ("a",), 100, 1); b.add(ev("a")); self.snap = b.seal()
        self.ident = {"boot_id": "B1", "kernel": "6", "firmware": "F"}
    def test_hint_only(self):
        c = cache.ProbeCache(self.path, self.s); c.store(self.snap, self.ident, 100)
        hints = c.load(self.ident, 110)
        self.assertEqual(len(hints), 1); self.assertEqual(promote(hints[0]), "unprobed")
    def test_invalidation(self):
        c = cache.ProbeCache(self.path, self.s, max_age=60); c.store(self.snap, self.ident, 100)
        self.assertEqual(c.load({**self.ident, "boot_id": "B2"}, 110), [])
        self.assertEqual(c.load({**self.ident, "firmware": "G"}, 110), [])
        self.assertEqual(c.load(self.ident, 1000), [])
        d = json.load(open(self.path)); d["body"]["states"]["a"] = "absent"; json.dump(d, open(self.path, "w"))
        self.assertEqual(c.load(self.ident, 110), [])


class TestHotplug_MC29(unittest.TestCase):
    def test_detect_and_debounce(self):
        got = []; h = Host(files={"/sys/block/sda/size": "1"}, system="Linux"); files = h._files
        w = hotplug.PollingWatcher(got.append, h, debounce=5)
        files["/sys/block/sdb/size"] = "1"; self.assertEqual(w.poll(100), ["storage"])
        files["/sys/block/sdc/size"] = "1"; self.assertEqual(w.poll(101), [])
        self.assertEqual(w.poll(106), ["storage"])


class TestHealth_MC30(unittest.TestCase):
    def test_endpoints(self):
        import urllib.request, urllib.error
        ex = executor.ProbeExecutor("n", {"p": (lambda: [ev("a")], ("a",))}, clock=lambda: int(time.time()))
        m = observability.Metrics(["a"], ["p"])
        srv = health.serve(ex, m)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        try:
            with self.assertRaises(urllib.error.HTTPError) as cm: urllib.request.urlopen(base + "/readyz")
            self.assertEqual(cm.exception.code, 503)
            ex.sweep()
            self.assertTrue(json.load(urllib.request.urlopen(base + "/readyz"))["ready"])
            self.assertEqual(json.load(urllib.request.urlopen(base + "/explain?capability=a"))["state"], "present")
        finally:
            srv.shutdown(); ex.stop()
    def test_loopback_only(self):
        with self.assertRaises(ValueError): health.serve(None, host="0.0.0.0")


class TestMetrics_MC31(unittest.TestCase):
    def test_bounded_cardinality(self):
        m = observability.Metrics(["a"], ["p"])
        for i in range(5000): m.set_state(f"attacker{i}", "present"); m.probe_result(f"x{i}", f"E{i}", 0.1)
        out = m.render()
        self.assertIn('capability="other"', out); self.assertLess(out.count("\n"), 50)
    def test_changes_counter(self):
        m = observability.Metrics(["a"], ["p"]); m.set_state("a", "present"); m.set_state("a", "unprobed")
        self.assertIn("gap02_capability_changes_total", m.render())


class TestLogging_MC32(unittest.TestCase):
    def test_json_and_allowlist(self):
        import logging
        r = logging.LogRecord("gap02", 20, "", 0, "hello", None, None); r.code = "GAP02-E004"; r.secret = "s3cr3t"
        d = json.loads(observability.JsonFormatter().format(r))
        self.assertEqual(d["code"], "GAP02-E004"); self.assertNotIn("secret", d)


class TestTracing_MC33(unittest.TestCase):
    def test_span_records(self):
        t = observability.Tracer()
        if t._otel is not None: self.skipTest("otel present")
        with self.assertRaises(ZeroDivisionError):
            with t.span("probe", probe="p", obj=object()): 1 / 0
        s = t.spans[-1]; self.assertEqual(s["error"], "ZeroDivisionError"); self.assertNotIn("obj", s["attrs"])


class TestAudit_MC34(unittest.TestCase):
    def test_chain_and_tamper(self):
        p = os.path.join(tempfile.mkdtemp(), "a.jsonl"); a = audit.AuditLog(p, clock=lambda: 1)
        for i in range(5): a.append("x", {"i": i})
        self.assertTrue(audit.verify(p, a.head)[0])
        lines = open(p).read().splitlines(); lines[2] = lines[2].replace('"i": 2', '"i": 9')
        open(p, "w").write("\n".join(lines) + "\n"); self.assertFalse(audit.verify(p)[0])
    def test_truncation_needs_head(self):
        p = os.path.join(tempfile.mkdtemp(), "a.jsonl"); a = audit.AuditLog(p, clock=lambda: 1)
        for i in range(3): a.append("x", {"i": i})
        head = a.head; lines = open(p).read().splitlines()[:2]; open(p, "w").write("\n".join(lines) + "\n")
        self.assertTrue(audit.verify(p)[0]); self.assertFalse(audit.verify(p, head)[0])


class TestExplain_MC35(unittest.TestCase):
    def test_reasons(self):
        b = sweep.SweepBuilder("n", ("a", "b", "c"), 10, 1)
        b.add(ev("a")); b.add(errors_ev := ProbeEvidence("b", None, "observation", "s", error=Code.PRIVILEGE_DENIED.value))
        b.add(ProbeEvidence("c", True, "name-match", "s")); s = b.seal()
        self.assertIn("proven", explain.explain(s, "a")["why"])
        e = explain.explain(s, "b"); self.assertIn("PRIVILEGE_DENIED", e["why"]); self.assertIn("runbook", e)
        self.assertIn("cannot promote", explain.explain(s, "c")["why"])


class TestAlerts_MC36(unittest.TestCase):
    def test_alert_rules_reference_real_metrics(self):
        base = pathlib.Path(__file__).resolve().parents[1] / "ops"
        rules = json.load(open(base / "alerts.json")); dash = json.load(open(base / "dashboard.json"))
        m = observability.Metrics(["a"], ["p"]); m.set_state("a", "present"); m.set_state("a", "absent")
        m.probe_result("p", "GAP02-E004", 0.1); m.report_age(1); rendered = m.render()
        for r in rules["rules"]:
            self.assertIn(r["metric"], rendered, r["alert"]); self.assertTrue(r["runbook"].startswith("RUNBOOKS.md#"))
        for p in dash["panels"]: self.assertIn(p["metric"], rendered)


class TestBreaker_MC37(unittest.TestCase):
    def test_open_halfopen_close(self):
        b = breaker.CircuitBreaker("p", failure_threshold=2, cooldown=10)
        b.record(False, 0); self.assertTrue(b.allow(0)); b.record(False, 1); self.assertFalse(b.allow(2))
        self.assertTrue(b.allow(12)); self.assertEqual(b.state, "half-open"); b.record(False, 12); self.assertFalse(b.allow(13))
        self.assertTrue(b.allow(30)); b.record(True, 30); self.assertEqual(b.state, "closed")
    def test_executor_skips_open(self):
        ex = executor.ProbeExecutor("n", {"p": (lambda: 1 / 0, ("a",))}, clock=iter(range(100, 200)).__next__)
        for _ in range(3): ex.sweep()
        s = ex.sweep(); self.assertEqual(s.evidence[-1]["error"], Code.CIRCUIT_OPEN.value); ex.stop()
    def test_shedder(self):
        s = breaker.LoadShedder(1); self.assertTrue(s.try_acquire()); self.assertFalse(s.try_acquire()); s.release()


class TestRestart_MC38(unittest.TestCase):
    def test_resume_sequence_same_boot_resets_new_boot(self):
        p = os.path.join(tempfile.mkdtemp(), "st.json"); probes = {"p": (lambda: [ev("a")], ("a",))}
        ex = executor.ProbeExecutor("n", probes, state=executor.StateFile(p), boot_id="B1", clock=lambda: 1)
        ex.sweep(); ex.sweep(); ex.stop()
        ex2 = executor.ProbeExecutor("n", probes, state=executor.StateFile(p), boot_id="B1", clock=lambda: 2)
        self.assertEqual(ex2.sweep().sequence, 3); ex2.stop()
        ex3 = executor.ProbeExecutor("n", probes, state=executor.StateFile(p), boot_id="B2", clock=lambda: 3)
        self.assertEqual(ex3.sequence, 0); ex3.stop()
    def test_corrupt_state(self):
        p = os.path.join(tempfile.mkdtemp(), "st.json"); open(p, "w").write("{garbage")
        self.assertEqual(executor.StateFile(p).load()["sequence"], 0)


class TestQuarantine_MC39(unittest.TestCase):
    def test_quarantine_and_audit(self):
        log = []; q = quarantine.QuarantineRegistry(lambda k, d: log.append(k))
        with self.assertRaises(Gap02Error): q.quarantine("p", "", "")
        q.quarantine("p", "ops", "bad driver"); self.assertTrue(q.is_quarantined("p"))
        q.release("p", "ops"); self.assertFalse(q.is_quarantined("p"))
        self.assertEqual(log, ["quarantine.set", "quarantine.release"])


class TestResourceCeilings_MC40(unittest.TestCase):
    def test_apply_in_subprocess(self):
        import subprocess
        code = ("import sys;sys.path.insert(0,%r);from gap02_hardware_capability_discovery.production import limits as l;"
                "import json;print(json.dumps(l.apply(l.Ceilings())))") % str(ROOT)
        out = json.loads(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=20).stdout)
        if out["enforced"]: self.assertLessEqual(out["applied"]["RLIMIT_NOFILE"], 256)
    def test_budget(self):
        self.assertFalse(limits.sweep_cpu_ok(9, limits.Ceilings()))


# ---------------------------------------------------------------- MC-44/45/46
class TestPropertyFuzz_MC44(unittest.TestCase):
    def test_random_evidence_never_promotes_without_proof(self):
        rng = random.Random(44)
        kinds = sorted(ProbeEvidence.__init__.__globals__["PROOF_KINDS"] | ProbeEvidence.__init__.__globals__["OBSERVATION_KINDS"])
        for _ in range(5000):
            e = ProbeEvidence("x", rng.choice([True, False, None]), rng.choice(kinds), "s",
                              error=rng.choice([None, "GAP02-E001"]))
            st = promote(e)
            if st == "present":
                self.assertTrue(e.result is True and e.error is None and e.kind in ("runtime-call", "kernel-attribute", "api-bit", "attested"))
    def test_fuzz_parsers_fail_closed(self):
        rng = random.Random(7); alphabet = "GPU-,0123456789 .\n[]N/AEnabled"
        for _ in range(1500):
            q = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 80)))
            d, e = acc._nvidia(fx.nvidia(q=q), {"cuda_runtime_version": "12.4"})
            if promote(e) == "present":
                self.assertTrue(any(x.schedulable for x in d))
    def test_fuzz_envelope_decode(self):
        rng = random.Random(3)
        for _ in range(500):
            junk = {rng.choice(["schema", "body", "x"]): rng.choice([None, 1, "PK_SIGNED_CAPABILITIES/1", {}])}
            try: envelope.SignedEnvelope.from_dict(junk)
            except Gap02Error: pass


class TestConcurrency_MC45(unittest.TestCase):
    def test_readers_never_see_mixed_generation(self):
        st = sweep.SnapshotStore(); stop = threading.Event(); bad = []
        def writer():
            for i in range(1, 300):
                b = sweep.SweepBuilder("n", ("a", "b"), i, i)
                b.add(ev("a", i % 2 == 0)); b.add(ev("b", i % 2 == 0)); st.publish(b.seal())
            stop.set()
        def reader():
            while not stop.is_set():
                s = st.current()
                if s and s.report.state("a") != s.report.state("b"): bad.append(s.sequence)
        ts = [threading.Thread(target=reader) for _ in range(4)] + [threading.Thread(target=writer)]
        [t.start() for t in ts]; [t.join(10) for t in ts]
        self.assertEqual(bad, [])
    def test_replay_guard_concurrent_admission(self):
        g = replay.ReplayGuard(); s = replay.Sequencer("b"); seq = s.next("t"); ok = []
        def go():
            try: g.admit("n", dict(seq)); ok.append(1)
            except Gap02Error: pass
        ts = [threading.Thread(target=go) for _ in range(16)]; [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(len(ok), 1)


class TestFaultInjection_MC46(unittest.TestCase):
    FAULTS = {"timeout": dict(timeout_paths=[acc.NVSMI]), "denied": dict(denied=["/proc/cpuinfo"])}
    def test_every_fault_yields_unprobed_never_present(self):
        for name, kw in self.FAULTS.items():
            h = fx.linux(files={"/proc/cpuinfo": fx.CPUINFO_X86}, commands={}, **kw)
            evs = [acc._nvidia(h, {"cuda_runtime_version": "12.4"})[1], cpu.probe_cpu(h)["evidence"]]
            for e in evs:
                if e.error: self.assertEqual(promote(e), "unprobed", name)
    def test_publisher_permanent_error(self):
        class T:
            def send(self, *a): raise Gap02Error(Code.POLICY_DENIED, "no")
        p = publisher.Publisher(T(), sleep=lambda s: None); p.enqueue("g", {}); self.assertEqual(p.flush(), 0)
        self.assertEqual(p.stats.retries, 0)
    def test_audit_open_refuses_corrupt(self):
        p = os.path.join(tempfile.mkdtemp(), "a.jsonl"); open(p, "w").write('{"seq":1}\n')
        with self.assertRaises(RuntimeError): audit.AuditLog(p)


if __name__ == "__main__":
    unittest.main()
