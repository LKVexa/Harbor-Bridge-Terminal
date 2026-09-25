"""WS 1 -- hypervisor adapter boundary, live-state fencing and provider fault handling."""
from __future__ import annotations

import json
import unittest

from _support import E, FakeHypervisor, Rig
from inv32_elastic_virtualization.adapters import GuestLifecycle
from inv32_elastic_virtualization.adapters.hyperflux import HyperFluxAdapter


class AdapterContractTest(unittest.TestCase):
    def setUp(self):
        self.r = Rig()
        self.r.guest()
        self.t = self.r.tenant_token()

    def tearDown(self):
        self.r.close()

    def h(self, req, tok=None):
        return self.r.ctl.handle(req, tok or self.t)

    def test_grow_reclaim_uses_hypervisor_confirmed_values(self):
        res = self.h(self.r.mem("a", 2048))
        ev = res["event"]
        self.assertEqual((ev["from_mib"], ev["applied_mib"], ev["reversible_to"]), (1024, 2048, 1024))
        self.assertEqual(self.r.fake.get_guest("g1").memory_mib, 2048)
        self.assertIsNotNone(ev["provider_request_id"])

    def test_block_alignment(self):
        ev = self.h(self.r.mem("a", 2000))["event"]  # grow aligns down to 1920
        self.assertEqual(ev["applied_mib"], 1920)
        self.assertEqual(ev["rule"], "aligned_to_block")
        ev = self.h(self.r.mem("b", 1100))["event"]  # reclaim aligns up to 1152
        self.assertEqual(ev["applied_mib"], 1152)

    def test_floor_ceiling_boundaries(self):
        self.assertEqual(self.h(self.r.mem("a", 256))["outcome"], "success")
        self.assertEqual(self.h(self.r.mem("b", 255))["error"]["code"], "floor_breach")
        ev = self.h(self.r.mem("c", 4096))["event"]
        self.assertEqual(ev["applied_mib"], 4096)
        ev = self.h(self.r.mem("d", 10**6))["event"]
        self.assertEqual((ev["applied_mib"], ev["rule"]), (4096, "clamped_to_ceiling"))

    def test_reserve_boundary_uses_confirmed_capacity_including_overhead(self):
        fake = FakeHypervisor(8192, overhead_mib=1024, reserved_pool_mib=512, fragmentation_mib=256, block_mib=128)
        r = Rig(fake=fake)
        r.guest(mem=1024, ceiling=8192)
        usable = 8192 - 1024 - 512 - 256
        reserve = r.ctl.reserve_mib(usable)
        free = usable - reserve - 1024
        ok_target = 1024 + (free // 128) * 128
        self.assertEqual(r.ctl.handle(r.mem("a", ok_target), r.tenant_token())["outcome"], "success")
        res = r.ctl.handle(r.mem("b", ok_target + 128), r.tenant_token())
        self.assertEqual(res["error"]["code"], "reserve_breach")
        r.close()

    def test_guest_refusal_is_first_class(self):
        self.r.fake.inject("refuse")
        res = self.h(self.r.mem("a", 512))
        self.assertEqual(res["outcome"], "rejected")
        self.assertEqual(res["event"]["applied_mib"], 1024)
        self.assertEqual(res["event"]["provider_status"], "refused")

    def test_partial_balloon_records_actual(self):
        self.r.fake.inject("partial")
        res = self.h(self.r.mem("a", 3072))
        self.assertEqual(res["outcome"], "partial_success")
        self.assertEqual(res["event"]["applied_mib"], 2048)
        self.assertEqual(res["event"]["target_mib"], 3072)

    def test_partial_vcpu_is_compensated(self):
        self.r.fake.inject("partial")
        res = self.h(self.r.cpu("a", 4))
        self.assertEqual(res["outcome"], "rolled_back")
        self.assertEqual(self.r.fake.get_guest("g1").vcpus, 1)

    def test_stale_expected_state_rejected(self):
        v = self.r.fake.get_guest("g1").state_version
        self.r.fake.external_resize("g1", 1152)
        res = self.h(self.r.mem("a", 2048, expected_version=v))
        self.assertEqual(res["error"]["code"], "stale_expected_state")
        self.assertEqual(self.r.fake.get_guest("g1").memory_mib, 1152)

    def test_concurrent_external_change_between_read_and_write(self):
        self.r.fake.inject("external_change")
        res = self.h(self.r.mem("a", 2048))
        self.assertEqual(res["error"]["code"], "stale_expected_state")

    def test_identifier_reuse_detected(self):
        self.r.fake.recreate_guest("g1", "t1")
        res = self.h(self.r.mem("a", 2048))
        self.assertEqual(res["error"]["code"], "identity_mismatch")

    def test_tenant_ownership_checked_against_provider(self):
        self.r.fake.create_guest("g2", "t2", 1024)
        self.r.ctl.register_guest("g2", tenant="t2", floor_mib=256, ceiling_mib=2048, vcpu_max=2)
        res = self.h(self.r.mem("a", 2048, guest="g2"))  # t1 token names t2's guest with tenant t1
        self.assertEqual(res["error"]["code"], "authorization_denied")

    def test_lifecycle_blocks_mutation(self):
        for state in (GuestLifecycle.PAUSED, GuestLifecycle.MIGRATING, GuestLifecycle.SNAPSHOTTING,
                      GuestLifecycle.CRASHED, GuestLifecycle.BOOTING, GuestLifecycle.SHUTTING_DOWN):
            self.r.fake.set_lifecycle("g1", state)
            res = self.h(self.r.mem(f"op-{state.value}", 2048))
            self.assertEqual(res["error"]["code"], "guest_state_incompatible", state)

    def test_capability_negotiation_fails_before_mutation(self):
        self.r.fake.bump_capabilities(vcpu_hotplug=False)
        res = self.h(self.r.cpu("a", 2))
        self.assertEqual(res["error"]["code"], "capability_unsupported")
        self.assertEqual(self.r.fake.calls, [])

    def test_capability_change_invalidates_cache_and_is_audited(self):
        before = len(self.r.store.audit_events)
        self.r.fake.bump_capabilities(provider_version="fake-hyperflux-1.1")
        self.h(self.r.mem("a", 2048))
        kinds = [e.get("reason") for e in self.r.store.audit_events[before:]]
        self.assertTrue(any("capabilities changed" in (k or "") for k in kinds))

    def test_non_balloonable_and_boot_vcpu_constraints(self):
        r = Rig()
        r.guest(mem=1024, vcpus=2, floor=128, non_balloonable_mib=768, min_boot_vcpus=2)
        tok = r.tenant_token()
        self.assertEqual(r.ctl.handle(r.mem("a", 512), tok)["error"]["code"], "floor_breach")
        self.assertEqual(r.ctl.handle(r.cpu("b", 1), tok)["error"]["code"], "validation_failed")
        r.close()

    def test_provider_invariant_violation_quarantines(self):
        self.r.fake.inject("lie_floor")
        res = self.h(self.r.mem("a", 2048))
        self.assertIn(res["error"]["code"], ("provider_invariant_violation",))
        self.assertIn("guest:g1", self.r.ctl.quarantine.active())
        self.assertEqual(self.h(self.r.mem("b", 1024))["error"]["code"], "quarantined")

    def test_untrusted_capacity_fails_closed(self):
        self.r.fake.inject("capacity_untrusted")
        self.assertEqual(self.h(self.r.mem("a", 2048))["error"]["code"], "capacity_untrusted")

    def test_transient_rpc_failure_is_retried_once_mutated_once(self):
        self.r.fake.inject("unavailable", times=1)
        res = self.h(self.r.mem("a", 2048))
        self.assertEqual(res["outcome"], "success")
        self.assertEqual(len([c for c in self.r.fake.calls if c[0] == "memory"]), 1)

    def test_provider_restart_mid_request(self):
        self.r.fake.inject("restart")
        res = self.h(self.r.mem("a", 2048))
        self.assertEqual(res["outcome"], "success")  # idempotency key + CAS make the retry safe

    def test_raw_provider_error_text_never_exposed(self):
        self.r.fake.inject("unavailable", times=None)
        res = self.h(self.r.mem("a", 2048))
        blob = json.dumps(res)
        self.assertNotIn("/var/", blob)
        self.assertNotIn("token=abc123", blob)
        self.assertEqual(res["error"]["code"], "provider_unavailable")

    def test_cancellation_before_mutation(self):
        self.r.ctl.cancel("a")
        self.assertEqual(self.h(self.r.mem("a", 2048))["error"]["code"], "cancelled")
        self.assertEqual(self.r.fake.calls, [])

    def test_drain_blocks_new_mutations(self):
        self.assertTrue(self.r.ctl.drain(timeout_s=0.1))
        self.assertEqual(self.h(self.r.mem("a", 2048))["error"]["code"], "shutting_down")

    def test_vcpu_add_remove_and_revert(self):
        ev = self.h(self.r.cpu("a", 3))["event"]
        self.assertEqual(ev["applied_vcpus"], 3)
        op = self.r.operator_token()
        res = self.r.ctl.handle(self.r.revert("b", ev["event_hash"], kind="vcpu"), op)
        self.assertEqual(res["outcome"], "success")
        self.assertEqual(self.r.fake.get_guest("g1").vcpus, 1)
        self.assertEqual(self.h(self.r.cpu("c", 5))["error"]["code"], "validation_failed")

    def test_hyperflux_shell_fails_closed_without_pinned_spec(self):
        with self.assertRaises(E.CapabilityUnsupported):
            HyperFluxAdapter(transport=object())


if __name__ == "__main__":
    unittest.main()
