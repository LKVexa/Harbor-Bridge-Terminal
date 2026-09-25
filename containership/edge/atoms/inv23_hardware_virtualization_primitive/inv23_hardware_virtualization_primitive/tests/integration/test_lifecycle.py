"""MC-11: fault injection and adjacent-layer admission (in-process parts).

Hardware/lab scenarios (host reboot, firmware toggling, L1/L2 nested guests, Windows and
macOS hosts) cannot run in this sandbox; they live in tests/hardware and in the
hardware-conformance workflow and are recorded as outstanding in COMPATIBILITY.md.
"""

import unittest

from tests._boot import mod

base = mod("backends.base")
probe = mod("probe")
claim = mod("claim")
own = mod("ownership")
tel = mod("telemetry")
adm = mod("admission")
model = mod("model")


def result(state="usable", reason="ok", depth=0, virt=False):
    return base.ProbeResult(
        host="h",
        backend="linux-kvm",
        backend_version="t",
        platform="linux",
        architecture="x86_64",
        state=state,
        reason=reason,
        facility_usable=state == "usable",
        virtualized=virt,
        nesting_depth=depth,
        cpu_capable=True,
    )


class Scripted:
    name, version = "linux-kvm", "t"

    def __init__(self, seq):
        self.seq = list(seq)

    def supports(self, p, a):
        return True

    def probe(self, host):
        x = self.seq.pop(0) if len(self.seq) > 1 else self.seq[0]
        if isinstance(x, Exception):
            raise x
        return x


def manager(seq, clock=None, sink=None):
    t = tel.Telemetry(sink or tel.MemorySink())
    pr = probe.Prober([Scripted(seq)], host="h", platform="linux", architecture="x86_64", telemetry=t)
    kw = {"telemetry": t}
    if clock:
        kw["clock"] = clock
    return claim.ClaimManager(pr, own.MemoryClaimProvider(**kw))


class FaultInjection(unittest.TestCase):
    def test_device_disappears_between_probe_and_claim(self):
        m = manager([result(), result("present-disabled", "device_absent")])
        self.assertEqual(m.prober.probe().state, "usable")  # cached earlier verdict
        with self.assertRaises(model.PrimitiveUnavailable):
            m.claim("vmm")  # fresh probe refuses

    def test_permission_revoked_and_timeout(self):
        for bad in (result("present-disabled", "permission_denied"), TimeoutError()):
            with self.assertRaises(model.PrimitiveUnavailable):
                manager([bad]).claim("vmm")

    def test_nested_policy_and_unknown_depth(self):
        with self.assertRaises(model.PrimitiveUnavailable):
            manager([result(depth=None, virt=True)]).claim("vmm")
        resp, c = manager([result(depth=None, virt=True)]).claim("vmm", allow_unknown_depth=True)
        self.assertFalse(resp["bare_metal"])
        self.assertIsNone(resp["nesting_depth"])

    def test_claim_response_and_fencing_roundtrip(self):
        m = manager([result()])
        resp, c = m.claim("vmm")
        self.assertEqual((resp["schema"], resp["generation"], resp["bare_metal"]), ("PK_VIRT_CLAIM/2", 1, True))
        self.assertEqual(m.fence(c), 1)
        m.release(c)
        with self.assertRaises(own.FencingRejected):
            m.fence(c)

    def test_clock_jump_forward_fences_owner(self):
        now = [1e6]
        m = manager([result()], clock=lambda: now[0])
        _, c = m.claim("vmm", lease_s=30)
        now[0] += 3600  # wall clock jumps an hour
        with self.assertRaises(own.LeaseLost):
            m.renew(c)
        _, c2 = m.claim("other")
        with self.assertRaises(own.FencingRejected):
            m.fence(c)
        self.assertEqual(c2.generation, 2)

    def test_telemetry_backend_failure_does_not_change_decision(self):
        class Broken(tel.Sink):
            def metric(self, *a):
                raise OSError("down")

        resp, _ = manager([result()], sink=Broken()).claim("vmm")
        self.assertEqual(resp["generation"], 1)


class AdjacentAdmission(unittest.TestCase):
    """The contract every downstream consumer (GAP-02, INV-24, INV-40, INV-43) must honour."""

    def test_inv24_refuses_when_unavailable_with_reason_preserved(self):
        for st, rs in (("absent", "capability_absent"), ("present-disabled", "permission_denied"), ("indeterminate", "probe_timeout")):
            with self.assertRaises(adm.NotAdmitted) as cm:
                adm.require_usable(result(st, rs).to_report())
            self.assertEqual((cm.exception.state, cm.exception.reason), (st, rs))

    def test_inv24_accepts_usable(self):
        self.assertEqual(adm.require_usable(result().to_report())["state"], "usable")

    def test_schema_version_checked_at_boundary(self):
        legacy = model.VirtPrimitive("h", True, True, True).report()
        with self.assertRaises(adm.NotAdmitted) as cm:
            adm.require_usable(legacy)
        self.assertEqual(cm.exception.reason, "schema_version_rejected")
        forged = result().to_report()
        forged["reason"] = "permission_denied"
        with self.assertRaises(adm.NotAdmitted):
            adm.require_usable(forged)

    def test_nesting_policy_at_consumer(self):
        with self.assertRaises(adm.NotAdmitted):
            adm.require_usable(result(depth=None, virt=True).to_report(), require_known_depth=True)


if __name__ == "__main__":
    unittest.main()
