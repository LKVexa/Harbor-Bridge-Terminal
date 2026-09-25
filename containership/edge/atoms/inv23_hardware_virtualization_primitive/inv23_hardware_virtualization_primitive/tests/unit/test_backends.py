"""MC-03: classification branches for every backend, with mocked platform APIs."""

import os
import tempfile
import threading
import time
import unittest

from tests._boot import mod

base = mod("backends.base")
lk = mod("backends.linux_kvm")
win = mod("backends.windows_whpx")
mac = mod("backends.macos_hvf")
probe = mod("probe")
tel = mod("telemetry")

INTEL = "vendor_id\t: GenuineIntel\nflags\t\t: fpu vme vmx ept sse2\n"
INTEL_GUEST = "vendor_id\t: GenuineIntel\nflags\t\t: fpu vmx ept hypervisor\n"
AMD = "vendor_id\t: AuthenticAMD\nflags\t\t: fpu svm npt\n"
NOVT = "vendor_id\t: GenuineIntel\nflags\t\t: fpu sse2\n"
NOVT_GUEST = "vendor_id\t: GenuineIntel\nflags\t\t: fpu sse2 hypervisor\n"


def fake_root(cpuinfo, kvm=True, nested=None):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "proc"))
    if cpuinfo is not None:
        with open(os.path.join(d, "proc", "cpuinfo"), "w") as fh:
            fh.write(cpuinfo)
    if kvm:
        os.makedirs(os.path.join(d, "dev"))
        open(os.path.join(d, "dev", "kvm"), "w").close()
    if nested is not None:
        p = os.path.join(d, "sys", "module", "kvm_intel", "parameters")
        os.makedirs(p)
        with open(os.path.join(p, "nested"), "w") as fh:
            fh.write(nested + "\n")
    return d


def linux(cpuinfo, *, kvm=True, api=12, opener=None, nested=None, ioctl=None):
    return lk.LinuxKvmBackend(fake_root(cpuinfo, kvm, nested), ioctl=ioctl or (lambda fd: api), opener=opener or os.open)


class LinuxBackendTest(unittest.TestCase):
    def setUp(self):
        self._m = lk._platform.machine
        lk._platform.machine = lambda: "x86_64"

    def tearDown(self):
        lk._platform.machine = self._m

    def test_bare_metal_intel_usable(self):
        r = linux(INTEL, nested="Y").probe("h")
        self.assertEqual((r.state, r.reason, r.cpu_vendor, r.slat), ("usable", "ok", "GenuineIntel", True))
        self.assertTrue(r.bare_metal)
        self.assertEqual(r.nesting_depth, 0)
        self.assertTrue(r.nested_enabled)
        self.assertEqual(r.evidence["kvm_api"], 12)

    def test_amd_npt(self):
        r = linux(AMD).probe("h")
        self.assertEqual((r.state, r.slat, r.cpu_vendor), ("usable", True, "AuthenticAMD"))

    def test_guest_never_bare_metal_and_depth_unknown(self):
        r = linux(INTEL_GUEST).probe("h")
        self.assertEqual(r.state, "usable")
        self.assertIsNone(r.nesting_depth)
        self.assertFalse(r.bare_metal)
        self.assertFalse(r.to_report()["bare_metal"])

    def test_capability_absent(self):
        self.assertEqual(linux(NOVT).probe("h").state, "absent")
        g = linux(NOVT_GUEST).probe("h")
        self.assertEqual((g.state, g.reason, g.virtualized), ("absent", "capability_absent", True))

    def test_device_absent(self):
        r = linux(INTEL, kvm=False).probe("h")
        self.assertEqual((r.state, r.reason), ("present-disabled", "device_absent"))

    def test_permission_denied_is_not_absent(self):
        def deny(*a, **k):
            raise PermissionError(13, "denied")

        r = linux(INTEL, opener=deny).probe("h")
        self.assertEqual((r.state, r.reason), ("present-disabled", "permission_denied"))

    def test_ioctl_failure_and_bad_api(self):
        def boom(fd):
            raise OSError(25, "ENOTTY")

        self.assertEqual(linux(INTEL, ioctl=boom).probe("h").reason, "kernel_api_unavailable")
        self.assertEqual(linux(INTEL, api=11).probe("h").state, "present-disabled")
        r = linux(INTEL, ioctl=lambda fd: "12").probe("h")
        self.assertEqual((r.state, r.reason), ("indeterminate", "malformed_probe_response"))

    def test_malformed_cpuinfo(self):
        with self.assertRaises(base.ProbeError):
            linux("garbage without colon").probe("h")
        r = linux(None).probe("h")
        self.assertEqual(r.state, "indeterminate")

    def test_unsupported_architecture(self):
        lk._platform.machine = lambda: "riscv64"
        r = linux(INTEL).probe("h")
        self.assertEqual((r.state, r.reason), ("indeterminate", "unsupported_architecture"))

    def test_repeated_probes_do_not_leak_fds(self):
        b = linux(INTEL)
        before = len(os.listdir("/proc/self/fd")) if os.path.isdir("/proc/self/fd") else 0
        for _ in range(200):
            b.probe("h")
        after = len(os.listdir("/proc/self/fd")) if os.path.isdir("/proc/self/fd") else 0
        self.assertLessEqual(after - before, 2)


class ProbeResultInvariantTest(unittest.TestCase):
    def test_usable_requires_positive_evidence(self):
        with self.assertRaises(ValueError):
            base.ProbeResult(
                host="h", backend="b", backend_version="1", platform="linux", architecture="x86_64", state="usable", reason="ok"
            )

    def test_virtualized_cannot_be_depth_zero(self):
        with self.assertRaises(ValueError):
            base.ProbeResult(
                host="h",
                backend="b",
                backend_version="1",
                platform="linux",
                architecture="x86_64",
                state="absent",
                reason="capability_absent",
                virtualized=True,
                nesting_depth=0,
            )


class WindowsMacTest(unittest.TestCase):
    def test_windows_branches(self):
        W = win.WindowsWhpxBackend
        self.assertEqual(W(feature=lambda pf: False, whv=lambda: True).probe("h").state, "usable")
        self.assertEqual(W(feature=lambda pf: True, whv=lambda: False).probe("h").state, "present-disabled")
        self.assertEqual(W(feature=lambda pf: False, whv=lambda: None, cpu_capable=lambda: False).probe("h").state, "absent")
        r = W(feature=lambda pf: False, whv=lambda: None).probe("h")
        self.assertEqual((r.state, r.reason), ("indeterminate", "firmware_disabled"))
        u = W(feature=lambda pf: False, whv=lambda: True).probe("h")
        self.assertIsNone(u.nesting_depth)  # never fabricated
        self.assertFalse(u.to_report()["bare_metal"])

    def test_mac_branches(self):
        M = mac.MacosHvfBackend
        vals = {"kern.hv_support": 1, "kern.hv_vmm_present": 0}
        r = M(sysctl=vals.get).probe("h")
        self.assertEqual((r.state, r.nesting_depth, r.bare_metal), ("usable", 0, True))
        vals["kern.hv_vmm_present"] = 1
        self.assertFalse(M(sysctl=vals.get).probe("h").bare_metal)
        self.assertEqual(M(sysctl={"kern.hv_support": 0}.get).probe("h").state, "absent")
        self.assertEqual(M(sysctl={}.get).probe("h").state, "indeterminate")


class Boom:
    name, version = "linux-kvm", "t"

    def __init__(self, exc=None, sleep=0.0, ret=None):
        self.exc, self.sleep, self.ret = exc, sleep, ret

    def supports(self, p, a):
        return True

    def probe(self, host):
        time.sleep(self.sleep)
        if self.exc:
            raise self.exc
        return self.ret


class ProberTest(unittest.TestCase):
    def P(self, b, **kw):
        return probe.Prober([b], host="h", platform="linux", architecture="x86_64", **kw)

    def test_exceptions_never_become_usable(self):
        for exc, reason in ((RuntimeError("x"), "backend_error"), (base.ProbeError("permission_denied"), "permission_denied")):
            r = self.P(Boom(exc)).probe()
            self.assertEqual((r.state, r.reason), ("indeterminate", reason))
        self.assertEqual(self.P(Boom(ret="junk")).probe().reason, "malformed_probe_response")

    def test_timeout(self):
        r = self.P(Boom(sleep=0.5), timeout_s=0.05).probe()
        self.assertEqual((r.state, r.reason), ("indeterminate", "probe_timeout"))

    def test_unsupported_platform(self):
        r = probe.Prober([], host="h", platform="sunos", architecture="sparc").probe()
        self.assertEqual((r.state, r.reason), ("indeterminate", "unsupported_platform"))

    def test_cache_ttl_and_invalidation(self):
        lk_backend = Boom(ret=None)
        seq = []

        class Flip(Boom):
            def probe(s, host):
                seq.append(1)
                st = "usable" if len(seq) == 1 else "present-disabled"
                return base.ProbeResult(
                    host=host,
                    backend="linux-kvm",
                    backend_version="t",
                    platform="linux",
                    architecture="x86_64",
                    state=st,
                    reason="ok" if st == "usable" else "firmware_disabled",
                    facility_usable=st == "usable",
                    virtualized=False,
                    nesting_depth=0,
                )

        del lk_backend
        p = self.P(Flip(), cache_ttl_s=60)
        self.assertEqual(p.probe().state, "usable")
        self.assertEqual(p.probe().state, "usable")  # cached
        p.invalidate()
        self.assertEqual(p.probe().state, "present-disabled")  # firmware change observed
        p2 = self.P(Flip(), cache_ttl_s=0)
        seq.clear()
        p2.probe()
        self.assertEqual(p2.probe().state, "present-disabled")  # TTL 0 -> no stale verdict

    def test_concurrent_probes_and_telemetry(self):
        sink = tel.MemorySink()
        p = self.P(Boom(RuntimeError()), telemetry=tel.Telemetry(sink), cache_ttl_s=0)
        ts = [threading.Thread(target=p.probe) for _ in range(16)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        key = ("inv23_probe_failures_total", (("backend", "linux-kvm"), ("reason", "backend_error")))
        self.assertEqual(sink.counters[key], 16)
        self.assertEqual(len(sink.histograms[("inv23_probe_latency_seconds", (("backend", "linux-kvm"),))]), 16)


if __name__ == "__main__":
    unittest.main()
