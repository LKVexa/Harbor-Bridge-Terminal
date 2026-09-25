"""Integration, security, fault and recovery tests for the 4.3.0 ExecutionPlane
(M03 M07 M08 M09 M11 M12 M13 M14 M16 M26 M30 M37 M38 M39 M40 M45)."""
from __future__ import annotations

import os
import tempfile
import threading
import unittest

from helpers import AUD, FakeClock, dev_plane, pkg, request, secured_plane
from pln04_execution_plane import errors, observability, providers, security, store
from pln04_execution_plane.errors import PlaneError


def code(ctx):
    return ctx.exception.code


class AdmissionLifecycleTest(unittest.TestCase):
    def test_no_active_before_provider_confirms_and_compensation(self):
        pl, provs = dev_plane()
        provs["process"].fail_start = 5
        with self.assertRaises(PlaneError) as ctx:
            pl.admit(request("w1"))
        self.assertEqual(code(ctx), "PLN04-PROV-001")
        self.assertIsNone(pl.store.get("inst/w1"))           # compensated to terminated and removed
        self.assertIsNone(pl.node.instance("w1"))
        self.assertEqual(pl.fair.usage(), {})                # reservation released
        kinds = [r["kind"] for r in pl.audit.records]
        self.assertIn("provider_start_failed", kinds)
        self.assertNotIn("workload_admitted", kinds)

    def test_retry_recovers_transient_provider_failure(self):
        pl, provs = dev_plane()
        provs["process"].fail_start = 1
        self.assertEqual(pl.admit(request("w1"))["tier"], "process")
        self.assertEqual(pl.store.get("inst/w1")[1]["state"], "active")

    def test_unverified_zeroization_withholds_resources(self):
        pl, provs = dev_plane()
        pl.admit(request("w1"))
        provs["process"].zeroize_unverifiable = True
        with self.assertRaises(PlaneError) as ctx:
            pl.teardown("w1", "t1")
        self.assertEqual(code(ctx), "PLN04-PROV-003")
        self.assertEqual(pl.store.get("inst/w1")[1]["state"], "failed")
        self.assertIn("t1", pl.fair.usage())                 # never reused while unproven
        provs["process"].zeroize_unverifiable = False
        self.assertEqual(pl.reap()["reaped"], ["w1"])
        self.assertEqual(pl.fair.usage(), {})

    def test_policy_floor_and_explain(self):
        pl, _ = dev_plane(tiers=("process", "microvm"))
        self.assertEqual(pl.admit(request("w1", trust_class="third-party"))["tier"], "microvm")
        with self.assertRaises(PlaneError) as ctx:
            pl.admit(request("w2", trust_class="hostile"))
        self.assertEqual(code(ctx), "PLN04-POL-001")
        self.assertIn("unikernel", pl.explain("w1")["reason"])

    def test_idempotency_key_replay_and_misuse(self):
        pl, provs = dev_plane()
        a = pl.admit(request("w1", idempotency_key="key-000001"))
        b = pl.admit(request("w1", idempotency_key="key-000001"))
        self.assertEqual(a["epoch"], b["epoch"])
        self.assertEqual([c for c in provs["process"].calls if c[0] == "start"], [("start", "w1")])
        with self.assertRaises(PlaneError) as ctx:
            pl.admit(request("w1", trust_class="first-party", idempotency_key="key-000001"))
        self.assertEqual(code(ctx), "PLN04-CONF-002")

    def test_cross_tenant_and_teardown_ownership(self):
        pl, _ = dev_plane()
        pl.admit(request("w1", tenant="a"))
        with self.assertRaises(PlaneError) as ctx:
            pl.admit(request("w1", tenant="b"))
        self.assertEqual(code(ctx), "PLN04-AUTHZ-002")
        with self.assertRaises(PlaneError) as ctx:
            pl.teardown("w1", "b")
        self.assertEqual(code(ctx), "PLN04-AUTHZ-002")
        with self.assertRaises(PlaneError):
            pl.teardown("w1")
        self.assertTrue(pl.teardown("w1", privileged=True))
        self.assertFalse(pl.teardown("w1", "a"))

    def test_attestation_loss_quarantines_and_expiry_fails_closed(self):
        clock = FakeClock()
        pl, _ = dev_plane(wall=clock)
        pl.admit(request("w1", trust_class="untrusted"))
        clock.advance(10_000)
        self.assertIn("microvm", pl.refresh_attestation())
        self.assertEqual(pl.store.get("inst/w1")[1]["state"], "quarantined")
        with self.assertRaises(PlaneError) as ctx:
            pl.admit(request("w1", trust_class="untrusted"))
        self.assertEqual(code(ctx), "PLN04-ATT-001")
        with self.assertRaises(PlaneError) as ctx:                       # every tier expired: fail closed
            pl.admit(request("w2", trust_class="untrusted"))
        self.assertEqual(code(ctx), "PLN04-POL-001")
        pl.attest_tier("vm")                                             # fresh evidence for vm only
        self.assertEqual(pl.admit(request("w2", trust_class="untrusted"))["tier"], "vm")

    def test_illegal_transition_is_refused(self):
        with self.assertRaises(PlaneError) as ctx:
            providers.check_transition("terminated", "active")
        self.assertEqual(code(ctx), "PLN04-STATE-004")
        with self.assertRaises(PlaneError):
            providers.check_transition("reserved", "active")


class PolicyTest(unittest.TestCase):
    def test_residency(self):
        pl, _ = dev_plane(config={"site": "eu-1", "residency": {"t-eu": ["eu-1"], "t-us": ["us-1"]}})
        pl.admit(request("w1", tenant="t-eu"))
        for req in (request("w2", tenant="t-us"), request("w3", tenant="t-eu", site="us-1")):
            with self.assertRaises(PlaneError) as ctx:
                pl.admit(req)
            self.assertEqual(code(ctx), "PLN04-POL-004")

    def test_coresidency(self):
        pl, _ = dev_plane()
        pl.admit(request("h1", tenant="a", trust_class="hostile"))
        with self.assertRaises(PlaneError) as ctx:
            pl.admit(request("x1", tenant="b", trust_class="trusted"))
        self.assertEqual(code(ctx), "PLN04-POL-005")
        pl.admit(request("x2", tenant="a", trust_class="trusted"))   # same tenant allowed
        pl2, _ = dev_plane()
        pl2.admit(request("u1", tenant="a", trust_class="untrusted"))
        pl2.admit(request("t1", tenant="b", trust_class="trusted"))    # different tier ok
        with self.assertRaises(PlaneError):
            pl2.admit(request("u2", tenant="b", trust_class="untrusted"))

    def test_rollout_and_emergency_disable(self):
        pl, _ = dev_plane(config={"rollout": {"stage": "canary", "canary_tenants": ["c"]}})
        pl.admit(request("w1", tenant="c"))
        with self.assertRaises(PlaneError) as ctx:
            pl.admit(request("w2", tenant="d"))
        self.assertEqual(code(ctx), "PLN04-POL-006")
        self.assertIsNotNone(ctx.exception.retry_after_s)
        pl.enable("full")
        pl.admit(request("w2", tenant="d"))
        pl.emergency_disable("incident 42")
        with self.assertRaises(PlaneError):
            pl.admit(request("w3", tenant="c"))
        self.assertFalse(pl.health()["ready"])
        self.assertTrue(pl.teardown("w1", "c"))                        # drain still possible

    def test_auto_rollback_on_provider_errors(self):
        pl, provs = dev_plane()
        for i in range(10):
            pl.admit(request(f"ok{i}", tenant=f"t{i}"))
        provs["process"].fail_start = 10**6
        for i in range(10):
            with self.assertRaises(PlaneError):
                pl.admit(request(f"bad{i}", tenant=f"u{i}"))
        self.assertIsNone(pl.auto_rollback(max_error_ratio=0.9, min_requests=5))
        self.assertIn("error ratio", pl.auto_rollback(max_error_ratio=0.3, min_requests=5))
        self.assertEqual(pl.rollout.stage, "disabled")

    def test_fair_share_and_capacity(self):
        pl, _ = dev_plane(config={"limits": {"cpu_milli": 4000, "memory_mib": 4096, "headroom": 0.25}})
        res = {"cpu_milli": 1000, "memory_mib": 256}
        pl.admit(request("a1", tenant="a", resources=res))
        pl.admit(request("a2", tenant="a", resources=res))
        pl.admit(request("a3", tenant="a", resources=res))   # borrowing idle capacity up to 75 %
        with self.assertRaises(PlaneError) as ctx:
            pl.admit(request("a4", tenant="a", resources=res))
        self.assertEqual(code(ctx), "PLN04-CAP-001")
        pl.admit(request("b1", tenant="b", resources=res))   # b still has its guaranteed share
        pl2, _ = dev_plane(config={"limits": {"max_instances": 2, "per_tenant_limit": 1}})
        pl2.admit(request("x", tenant="a"))
        with self.assertRaises(PlaneError):
            pl2.admit(request("y", tenant="a"))


class ConcurrencyAndFencingTest(unittest.TestCase):
    def test_at_most_one_active_per_workload_under_contention(self):
        pl, provs = dev_plane()
        provs["process"].start_delay_s = 0.01
        results, barrier = [], threading.Barrier(16)

        def worker(i):
            barrier.wait()
            try:
                results.append(pl.admit(request("same", tenant=f"t{i % 2}"))["tenant"])
            except PlaneError as exc:
                results.append(type(exc).__name__)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        starts = [c for c in provs["process"].calls if c[0] == "start"]
        self.assertEqual(len(starts), 1)
        self.assertEqual(len(provs["process"].list_instances()), 1)

    def test_stale_epoch_is_rejected_by_provider(self):
        prov = providers.ReferenceProvider("microvm")
        mk = lambda e: providers.ProviderRequest("w", "t", "microvm", "sha256:" + "0" * 64, "sha256:" + "0" * 64,
                                                 f"key-{e:08d}", 10**20, e)
        prov.start(mk(2))
        with self.assertRaises(PlaneError) as ctx:
            prov.stop("w", 1)
        self.assertEqual(code(ctx), "PLN04-STATE-002")
        self.assertEqual(prov.start(mk(2)).epoch, 2)  # idempotent same key
        with self.assertRaises(PlaneError):
            prov.start(providers.ProviderRequest("w", "t", "vm", "sha256:" + "0" * 64, "sha256:" + "0" * 64, "k" * 8, 10**20, 3))

    def test_lease_partition_pause_and_resume(self):
        clock = FakeClock(0)
        st = store.MemoryStateStore()
        seen = []
        lm = store.LeaseManager(st, clock=clock, on_split_brain=lambda *a: seen.append(a))
        a = lm.acquire("w", "ctrl-a", 10)
        with self.assertRaises(PlaneError):
            lm.acquire("w", "ctrl-b", 10)
        self.assertTrue(seen)
        clock.advance(11)                                   # ctrl-a paused past expiry
        b = lm.acquire("w", "ctrl-b", 10)
        self.assertGreater(b.epoch, a.epoch)
        with self.assertRaises(PlaneError):
            lm.renew(a, 10)                                  # resumed stale owner is fenced
        with self.assertRaises(PlaneError):
            lm.validate(a)
        lm.release(b)
        self.assertGreater(lm.acquire("w", "ctrl-a", 10).epoch, b.epoch)  # epochs never go back


class DurabilityAndRecoveryTest(unittest.TestCase):
    def test_restart_recovery_never_resumes_blindly(self):
        with tempfile.TemporaryDirectory() as d:
            st = store.FileStateStore(os.path.join(d, "s"), fsync=False)
            pl, provs = dev_plane(store=st)
            pl.admit(request("alive", tenant="a"))
            pl.admit(request("dead", tenant="a", trust_class="first-party"))
            provs["wasm"].resources.clear()                  # provider lost this instance
            st.close()
            st2 = store.FileStateStore(os.path.join(d, "s"), fsync=False)
            pl2, _ = dev_plane(store=st2)
            pl2.registry._providers["process"] = provs["process"]
            pl2.registry._providers["wasm"] = provs["wasm"]
            summary = pl2.recover()
            self.assertEqual(summary, {"active": 1, "orphaned": 1})
            self.assertEqual(st2.get("inst/alive")[1]["state"], "active")
            self.assertEqual(st2.get("inst/dead")[1]["state"], "orphaned")
            with self.assertRaises(PlaneError):                  # ownership survives restart
                pl2.admit(request("alive", tenant="b"))
            self.assertIn("dead", pl2.reap()["reaped"])
            st2.close()

    def test_crash_mid_start_is_orphaned_then_reaped(self):
        with tempfile.TemporaryDirectory() as d:
            st = store.FileStateStore(os.path.join(d, "s"), fsync=False)
            pl, provs = dev_plane(store=st)
            original = provs["process"]._do_start

            def crash(req):
                original(req)
                raise SystemExit("simulated controller crash after provider start")

            provs["process"]._do_start = crash
            with self.assertRaises(SystemExit):
                pl.admit(request("w1"))
            st.close()
            st2 = store.FileStateStore(os.path.join(d, "s"), fsync=False)
            pl2, _ = dev_plane(store=st2)
            pl2.registry._providers["process"] = provs["process"]
            pl2.recover()
            self.assertIn(st2.get("inst/w1")[1]["state"], ("orphaned", "failed"))
            pl2.reap()
            self.assertIsNone(st2.get("inst/w1"))
            self.assertEqual(provs["process"].resources, {})
            st2.close()

    def test_store_outage_fails_closed(self):
        pl, provs = dev_plane()
        pl.store.fail_writes = True
        with self.assertRaises(PlaneError) as ctx:
            pl.admit(request("w1"))
        self.assertEqual(code(ctx), "PLN04-DEP-001")
        self.assertEqual(list(provs["process"].calls), [])
        self.assertFalse(pl.health()["ready"])
        self.assertEqual(pl.fair.usage(), {})

    def test_drain(self):
        pl, _ = dev_plane()
        for i in range(5):
            pl.admit(request(f"w{i}", tenant=f"t{i}", trust_class="first-party"))
        out = pl.drain("maintenance")
        self.assertEqual(len(out["drained"]), 5)
        self.assertEqual(list(pl.store.items("inst/")), [])


class SecuredProductionTest(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.clock = FakeClock()
        self.pl, self.signer, self.arts = secured_plane(self._d.name, self.clock)
        self.digest = security.sha256_digest(b"module")
        self.arts.register(security.issue_provenance(self.signer, digest=self.digest, builder="ci", source="git:abc", tiers=pkg.TIERS))

    def tearDown(self):
        self.pl.store.close()
        self.pl.audit.close()
        self._d.cleanup()

    def token(self, tenant="t1", caps=("admission:create", "admission:teardown")):
        return security.issue_actor_token(self.signer, subject="svc", tenant=tenant, caps=caps, audience=AUD, now=self.clock())

    def cls(self, workload="w1", tenant="t1", trust_class="untrusted"):
        return security.issue_classification(self.signer, issuer="sec-plane", workload=workload, tenant=tenant,
                                             trust_class=trust_class, policy_digest="sha256:" + "a" * 64, now=self.clock())

    def req(self, **kw):
        base = dict(trust_class="untrusted", artifact_digest=self.digest, classification_token=self.cls())
        base.update(kw)
        return request("w1", **base)

    def test_production_refuses_missing_controls(self):
        from pln04_execution_plane import plane as plane_mod, policy
        reg = providers.ProviderRegistry(allow_reference=True)
        reg.register(providers.ReferenceProvider("process"))
        with self.assertRaises(PlaneError):
            plane_mod.ExecutionPlane(policy.PlaneConfig.load({"profile": "production"}), reg)
        with self.assertRaises(PlaneError):
            providers.ProviderRegistry(allow_reference=False).register(providers.ReferenceProvider("vm"))

    def test_full_secured_admission(self):
        d = self.pl.admit(self.req(), token=self.token())
        self.assertEqual(d["tier"], "microvm")
        rec = self.pl.store.get("inst/w1")[1]
        self.assertEqual(rec["policy_digest"], "sha256:" + "a" * 64)
        ok, seq, _, _ = observability.verify_audit_file(os.path.join(self._d.name, "audit.jsonl"))
        self.assertTrue(ok)
        self.assertGreater(seq, 5)
        self.assertTrue(self.pl.teardown("w1", "t1", token=self.token()))

    def test_authn_authz_failures(self):
        cases = [
            (None, "PLN04-AUTHN-001"),
            ("garbage.token.value", "PLN04-AUTHN-001"),
            (self.token(tenant="t2"), "PLN04-AUTHZ-001"),
            (self.token(caps=("catalogue:read",)), "PLN04-AUTHZ-001"),
        ]
        for tok, expected in cases:
            with self.assertRaises(PlaneError) as ctx:
                self.pl.admit(self.req(), token=tok)
            self.assertEqual(code(ctx), expected)
        other = security.HmacKeyring()
        other.add("k1", b"z" * 32)
        forged = security.issue_actor_token(other.signer("k1"), subject="x", tenant="t1", caps=["admission:create"], audience=AUD, now=self.clock())
        with self.assertRaises(PlaneError):
            self.pl.admit(self.req(), token=forged)
        stale = self.token()
        self.clock.advance(3600)
        with self.assertRaises(PlaneError):
            self.pl.admit(self.req(classification_token=self.cls()), token=stale)

    def test_classification_binding(self):
        for bad in (None, self.cls(workload="other"), self.cls(trust_class="trusted")):
            with self.assertRaises(PlaneError) as ctx:
                self.pl.admit(self.req(classification_token=bad) if bad else request("w1", trust_class="untrusted", artifact_digest=self.digest), token=self.token())
            self.assertEqual(code(ctx), "PLN04-POL-002")

    def test_artifact_policy(self):
        with self.assertRaises(PlaneError) as ctx:
            self.pl.admit(self.req(artifact_digest=security.sha256_digest(b"unknown")), token=self.token())
        self.assertEqual(code(ctx), "PLN04-POL-003")
        self.arts.revoke(self.digest)
        with self.assertRaises(PlaneError):
            self.pl.admit(self.req(), token=self.token())
        with self.assertRaises(PlaneError):
            self.arts.register(security.issue_provenance(self.signer, digest=self.digest, builder="evil", source="x", tiers=["vm"]))

    def test_attestation_replay_and_nonce_binding(self):
        att = self.pl.attestor
        nonce = att.challenge("n1")
        ev = security.issue_attestation(self.signer, node_id="n1", tier="vm", nonce=nonce, measurement="m-good", now=self.clock())
        self.pl.attest_tier("vm", ev)
        with self.assertRaises(PlaneError) as ctx:
            self.pl.attest_tier("vm", ev)
        self.assertEqual(code(ctx), "PLN04-ATT-002")
        for bad in (
            security.issue_attestation(self.signer, node_id="n1", tier="vm", nonce="never-issued", measurement="m-good", now=self.clock()),
            security.issue_attestation(self.signer, node_id="n2", tier="vm", nonce=att.challenge("n1"), measurement="m-good", now=self.clock()),
            security.issue_attestation(self.signer, node_id="n1", tier="vm", nonce=att.challenge("n1"), measurement="m-evil", now=self.clock()),
            security.issue_attestation(self.signer, node_id="n1", tier="vm", nonce=att.challenge("n1"), measurement="m-good", now=self.clock() - 10_000),
        ):
            with self.assertRaises(PlaneError):
                self.pl.attest_tier("vm", bad)

    def test_audit_tamper_and_truncation_detected(self):
        self.pl.admit(self.req(), token=self.token())
        path = os.path.join(self._d.name, "audit.jsonl")
        anchor = observability.FileAnchor(os.path.join(self._d.name, "anchor.jsonl"))
        anchor.anchor(self.pl.audit.sequence, self.pl.audit.head)
        lines = open(path).read().splitlines()
        with open(path, "w") as fh:
            fh.write("\n".join(lines[:-2]) + "\n")
        ok, _, _, reason = observability.verify_audit_file(path, anchor.anchors())
        self.assertFalse(ok)
        self.assertIn("truncation", reason)
        with open(path, "w") as fh:
            fh.write("\n".join([lines[0].replace('"kind":"', '"kind":"x')] + lines[1:]) + "\n")
        self.assertFalse(observability.verify_audit_file(path)[0])


if __name__ == "__main__":
    unittest.main()
