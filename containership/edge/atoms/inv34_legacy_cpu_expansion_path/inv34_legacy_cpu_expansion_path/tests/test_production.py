"""Tests for the 5.1.0 production overlay. Each class names the MC items it evidences."""
from __future__ import annotations

import io
import json
import os
import pathlib
import random
import sys
import tempfile
import threading
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv34_legacy_cpu_expansion_path.expansion import (IdempotencyConflict, ShrinkNotSupported,  # noqa: E402
                                                      GuestLimitExceeded, StaleGeneration, HostCapacityExceeded)
from inv34_legacy_cpu_expansion_path.production.adapters.base import (AdapterError, EnsureRequest,  # noqa: E402
                                                                      Outcome, FenceRegistry)
from inv34_legacy_cpu_expansion_path.production.adapters.cloud_hypervisor import CloudHypervisorAdapter  # noqa: E402
from inv34_legacy_cpu_expansion_path.production.adapters.emulator import EmulatedHypervisor, FaultPlan  # noqa: E402
from inv34_legacy_cpu_expansion_path.production.audit import AuditChain  # noqa: E402
from inv34_legacy_cpu_expansion_path.production.config import ConfigError, ConfigRepository, validate_config  # noqa: E402
from inv34_legacy_cpu_expansion_path.production.observation import (OBSERVATION_SCHEMA, ObservationRejected,  # noqa: E402
                                                                    ObservationVerifier, classify_stall,
                                                                    parse_cpulist, sign_observation)
from inv34_legacy_cpu_expansion_path.production.policy import (DEFAULT_EVALUATORS, evaluate,  # noqa: E402
                                                               headroom_forecast)
from inv34_legacy_cpu_expansion_path.production.reconciler import DegradedMode, ExpansionService, PolicyDenied  # noqa: E402
from inv34_legacy_cpu_expansion_path.production.resilience import (AdmissionController, CircuitBreaker,  # noqa: E402
                                                                   CircuitOpen, DependencyHealth, Overloaded,
                                                                   RetryBudget, RetryPolicy)
from inv34_legacy_cpu_expansion_path.production.security import (Authenticator, AuthError, CapabilityPolicy,  # noqa: E402
                                                                 EnvSecretSource, Forbidden, Principal,
                                                                 QuotaExceeded, QuotaService, VmBinding, mint_token)
from inv34_legacy_cpu_expansion_path.production.service import Api  # noqa: E402
from inv34_legacy_cpu_expansion_path.production.store import (CasConflict, CorruptDocument, FileStateStore,  # noqa: E402
                                                              LeaseHeld, LeaseLost)
from inv34_legacy_cpu_expansion_path.production.telemetry import (Metrics, StructuredLogger, child_traceparent,  # noqa: E402
                                                                  parse_traceparent, redact)

OBS_KEY = b"k" * 32
AUDIT_KEY = b"a" * 32


def cpu(vm="vm-1", obs=2, des=2, mx=8, host=16, **kw):
    d = dict(vm_id=vm, observed_vcpus=obs, desired_vcpus=des, max_vcpus=mx, host_capacity_vcpus=host,
             acpi_hotplug_supported=True, guest_hotplug_supported=True, expansion_enabled=True, generation=0)
    d.update(kw)
    return d


def healthy() -> DependencyHealth:
    h = DependencyHealth()
    for d in h.MANDATORY:
        h.set(d, "healthy")
    return h


def report(vm, cpus, seq, ts=None, src="agent-1", key=OBS_KEY):
    body = {"schema": OBSERVATION_SCHEMA, "vm_id": vm, "source_id": src, "sequence": seq,
            "observed_at": ts if ts is not None else time.time(), "cpu_online": cpus}
    return {**body, "signature": sign_observation(key, body)}


class Rig:
    def __init__(self, tmp, faults=None, owner="ctl-a", vms=None):
        self.tmp = tmp
        self.store = FileStateStore(os.path.join(tmp, "state"))
        vms = vms or {"vm-1": (2, 8)}
        for vm, (p, m) in vms.items():
            if self.store.load(vm) is None:
                self.store.create(vm, cpu(vm, p, p, m))
        self.hv = EmulatedHypervisor(vms, faults)
        self.verifier = ObservationVerifier({"agent-1": OBS_KEY})
        for vm in vms:
            self.verifier.bind(vm, "agent-1")
        self.audit = AuditChain(os.path.join(tmp, "audit.jsonl"), AUDIT_KEY)
        self.svc = ExpansionService(self.store, self.hv, self.verifier, self.audit, owner=owner,
                                    health=healthy(), logger=StructuredLogger("t", io.StringIO()),
                                    retry=RetryPolicy(base_s=0.0, cap_s=0.0))
        self.svc.policy_ctx["vm-1"] = {"security_state": "ok", "site": "s1", "allowed_sites": ["s1"]}
        for vm in vms:
            self.svc.policy_ctx[vm] = {"security_state": "ok", "site": "s1", "allowed_sites": ["s1"]}


class TmpCase(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = self._td.name

    def tearDown(self):
        self._td.cleanup()


# ---------------------------------------------------------------- MC-005 / MC-007
class FakeCH:
    """Scripted Cloud Hypervisor REST peer (records every call)."""

    def __init__(self, boot=2, mx=8, resize_status=204, fail=None):
        self.boot, self.mx, self.resize_status, self.fail, self.calls = boot, mx, resize_status, fail, []

    def __call__(self, method, path, body, timeout):
        self.calls.append((method, path, json.loads(body) if body else None))
        if self.fail == path:
            raise TimeoutError()
        if path == "/vm.info":
            return 200, json.dumps({"config": {"cpus": {"boot_vcpus": self.boot, "max_vcpus": self.mx}}}).encode()
        if path == "/vm.resize":
            if self.resize_status in (200, 204):
                self.boot = json.loads(body)["desired_vcpus"]
            return self.resize_status, b""
        return 404, b""


def ereq(target, fence=1, vm="vm-1", op="op-1"):
    return EnsureRequest(vm, target, 1, op, fence, time.monotonic() + 10)


class CloudHypervisorAdapterTest(unittest.TestCase):
    """MC-005, MC-007, MC-040 (contract against the donor OpenAPI shape)."""

    def mk(self, **kw):
        t = FakeCH(**kw)
        return CloudHypervisorAdapter("vm-1", t, min_interval_s=0), t

    def test_hot_add_uses_documented_resize(self):
        a, t = self.mk()
        r = a.ensure_vcpus(ereq(4))
        self.assertEqual(r.outcome, Outcome.ACKNOWLEDGED)
        self.assertIn(("PUT", "/vm.resize", {"desired_vcpus": 4}), t.calls)

    def test_never_sends_shrink(self):
        a, t = self.mk(boot=6)
        r = a.ensure_vcpus(ereq(4))
        self.assertEqual(r.error_code, "ADAPTER_SHRINK_REFUSED")
        self.assertFalse([c for c in t.calls if c[1] == "/vm.resize"])

    def test_noop_at_target_and_over_max(self):
        a, t = self.mk(boot=4)
        self.assertEqual(a.ensure_vcpus(ereq(4)).outcome, Outcome.NOOP)
        self.assertEqual(a.ensure_vcpus(ereq(9, fence=2)).error_code, "ADAPTER_OVER_MAX")
        self.assertFalse([c for c in t.calls if c[1] == "/vm.resize"])

    def test_timeout_is_unknown_not_failure(self):
        a, _ = self.mk(fail="/vm.resize")
        r = a.ensure_vcpus(ereq(4))
        self.assertEqual(r.outcome, Outcome.UNKNOWN)
        self.assertTrue(r.retryable)

    def test_stale_fence_refused_before_side_effect(self):
        a, t = self.mk()
        a.ensure_vcpus(ereq(3, fence=5))
        with self.assertRaises(AdapterError):
            a.ensure_vcpus(ereq(4, fence=4))
        self.assertEqual(len([c for c in t.calls if c[1] == "/vm.resize"]), 1)

    def test_malformed_backend_response_and_expired_deadline(self):
        a, t = self.mk()
        t.boot = True  # bool is not a count
        with self.assertRaises(AdapterError):
            a.read_live("vm-1")
        with self.assertRaises(AdapterError):
            a.ensure_vcpus(EnsureRequest("vm-1", 4, 1, "op", 1, time.monotonic() - 1))

    def test_server_error_is_unknown(self):
        a, _ = self.mk(resize_status=500)
        self.assertEqual(a.ensure_vcpus(ereq(4)).outcome, Outcome.UNKNOWN)

    def test_wrong_vm_rejected(self):
        a, _ = self.mk()
        with self.assertRaises(AdapterError):
            a.ensure_vcpus(ereq(4, vm="vm-2"))


# ---------------------------------------------------------------- MC-006 / MC-028
class ObservationTest(unittest.TestCase):
    def v(self, clock=time.time):
        ver = ObservationVerifier({"agent-1": OBS_KEY, "agent-2": b"z" * 32}, clock=clock)
        ver.bind("vm-1", "agent-1")
        return ver

    def test_cpulist_parse(self):
        self.assertEqual(len(parse_cpulist("0-3,6\n")), 5)
        for bad in ("", "0-", "3-1", "a", "0, 1", "0-70000"):
            with self.subTest(bad=bad), self.assertRaises(ObservationRejected):
                parse_cpulist(bad)

    def test_verified_and_rejections(self):
        v = self.v()
        self.assertEqual(v.verify(report("vm-1", "0-3", 1)).online_vcpus, 4)
        cases = {
            "OBS_REPLAY": report("vm-1", "0-3", 1),
            "OBS_BAD_SIGNATURE": {**report("vm-1", "0-3", 2), "cpu_online": "0-7"},
            "OBS_STALE": report("vm-1", "0-3", 3, ts=time.time() - 3600),
            "OBS_FUTURE": report("vm-1", "0-3", 4, ts=time.time() + 3600),
            "OBS_UNKNOWN_SOURCE": report("vm-1", "0-3", 5, src="nobody"),
            "OBS_SOURCE_NOT_BOUND": report("vm-1", "0-3", 6, src="agent-2", key=b"z" * 32),
        }
        for code, rep in cases.items():
            with self.subTest(code=code), self.assertRaises(ObservationRejected) as cm:
                v.verify(rep)
            self.assertEqual(cm.exception.code, code)

    def test_stall_thresholds(self):
        now = 1000.0
        self.assertEqual(classify_stall(4, 4, 0, 0, now, now).state, "CONVERGED")
        self.assertEqual(classify_stall(4, 2, now - 10, now - 10, now, now).state, "PENDING")
        self.assertEqual(classify_stall(4, 2, now - 500, now - 500, now, now).state, "STALLED")
        self.assertEqual(classify_stall(4, 3, now - 500, now - 300, now, now).state, "PARTIAL_STALL")
        self.assertEqual(classify_stall(4, 2, now - 10, now - 10, None, now).state, "OBSERVATION_STALE")


# ---------------------------------------------------------------- MC-019/020/021/026/065
class StoreTest(TmpCase):
    def test_cas_and_corruption_detection(self):
        s = FileStateStore(self.tmp)
        d = s.create("vm-1", cpu())
        s.update("vm-1", d["revision"], lambda x: x["cpu"].update(desired_vcpus=3))
        with self.assertRaises(CasConflict):
            s.update("vm-1", d["revision"], lambda x: x["cpu"].update(desired_vcpus=4))
        p = s._path("vm-1")
        p.write_text(p.read_text().replace('"desired_vcpus": 3', '"desired_vcpus": 7'))
        with self.assertRaises(CorruptDocument):
            s.load("vm-1")

    def test_lease_exclusive_and_fence_monotonic(self):
        clock = [100.0]
        s = FileStateStore(self.tmp, clock=lambda: clock[0])
        s.create("vm-1", cpu())
        f1, _ = s.acquire_lease("vm-1", "a", 10)
        with self.assertRaises(LeaseHeld):
            s.acquire_lease("vm-1", "b", 10)
        clock[0] += 11
        f2, doc = s.acquire_lease("vm-1", "b", 10)
        self.assertGreater(f2, f1)
        with self.assertRaises(LeaseLost):
            s.check_lease(doc, "a", f1)

    def test_backup_restore_marks_needs_reconcile(self):
        s = FileStateStore(os.path.join(self.tmp, "a"))
        s.create("vm-1", cpu())
        m = s.backup(os.path.join(self.tmp, "bk"))
        self.assertEqual(len(m["entries"]), 1)
        r = FileStateStore.restore(os.path.join(self.tmp, "bk"), os.path.join(self.tmp, "b"))
        self.assertTrue(r.load("vm-1")["needs_reconcile"])
        (pathlib.Path(self.tmp, "bk") / m["entries"][0]["file"]).write_text("{}")
        with self.assertRaises(CorruptDocument):
            FileStateStore.restore(os.path.join(self.tmp, "bk"), os.path.join(self.tmp, "c"))

    def test_multiprocess_cas_no_lost_update(self):
        """MC-037 (single host): 4 processes x 10 CAS increments -> exactly 40."""
        s = FileStateStore(self.tmp)
        s.create("vm-1", cpu(mx=64, host=64))
        code = (
            "import sys;sys.path.insert(0,%r)\n"
            "from inv34_legacy_cpu_expansion_path.production.store import FileStateStore,CasConflict\n"
            "s=FileStateStore(%r)\n"
            "n=0\n"
            "while n<10:\n"
            "  d=s.load('vm-1')\n"
            "  try:\n"
            "    s.update('vm-1',d['revision'],lambda x:x.__setitem__('counter',x.get('counter',0)+1));n+=1\n"
            "  except CasConflict: pass\n") % (str(ROOT), self.tmp)
        import subprocess
        procs = [subprocess.Popen([sys.executable, "-B", "-c", code]) for _ in range(4)]
        for p in procs:
            self.assertEqual(p.wait(60), 0)
        self.assertEqual(s.load("vm-1")["counter"], 40)


# ---------------------------------------------------------------- reconciler end-to-end
class ReconcilerTest(TmpCase):
    def test_accept_present_observe_converge(self):
        r = Rig(self.tmp)
        res = r.svc.submit("vm-1", "req-1", 4, 0)
        self.assertEqual(res["status"], "accepted")
        st = r.svc.status("vm-1")
        self.assertFalse(st["converged"])
        self.assertEqual(r.svc.reconcile_once("vm-1")["action"], "presented")
        self.assertFalse(r.svc.status("vm-1")["converged"], "presentation is not convergence")
        r.svc.observe(report("vm-1", "0-3", 1))
        self.assertTrue(r.svc.status("vm-1")["converged"])
        self.assertEqual(r.hv.hotadd_actions, 1)

    def test_durable_idempotency_across_restart(self):
        r = Rig(self.tmp)
        a = r.svc.submit("vm-1", "req-1", 4, 0)
        r2 = Rig(self.tmp)                     # new process view over the same store
        self.assertEqual(r2.svc.submit("vm-1", "req-1", 4, 0), a)
        with self.assertRaises(IdempotencyConflict):
            r2.svc.submit("vm-1", "req-1", 5, 0)

    def test_timeout_after_action_no_double_hotadd(self):
        """MC-038: action performed, ack lost -> UNKNOWN -> live read resolves it."""
        r = Rig(self.tmp, FaultPlan(["timeout_after"]))
        r.svc.submit("vm-1", "req-1", 4, 0)
        self.assertEqual(r.svc.reconcile_once("vm-1")["action"], "ambiguous")
        r.store._clock = lambda: time.time() + 1000
        r.svc.clock = r.store._clock
        self.assertEqual(r.svc.reconcile_once("vm-1")["action"], "presented")
        self.assertEqual(r.hv.hotadd_actions, 1)

    def test_timeout_before_action_reissues_once(self):
        r = Rig(self.tmp, FaultPlan(["timeout_before"]))
        r.svc.submit("vm-1", "req-1", 4, 0)
        r.svc.reconcile_once("vm-1")
        r.svc.clock = r.store._clock = lambda: time.time() + 1000
        self.assertEqual(r.svc.reconcile_once("vm-1")["action"], "presented")
        self.assertEqual(r.hv.hotadd_actions, 1)

    def test_partial_presentation_then_completion(self):
        r = Rig(self.tmp, FaultPlan(["partial:3"]))
        r.svc.submit("vm-1", "req-1", 5, 0)
        self.assertEqual(r.svc.reconcile_once("vm-1")["action"], "in_progress")
        r.svc.clock = r.store._clock = lambda: time.time() + 1000
        self.assertEqual(r.svc.reconcile_once("vm-1")["action"], "presented")
        self.assertEqual(r.hv.present["vm-1"], 5)

    def test_crash_between_accept_and_reconcile_recovers(self):
        """MC-026: accepted request persisted; a fresh process finds and completes it."""
        Rig(self.tmp).svc.submit("vm-1", "req-1", 4, 0)
        r2 = Rig(self.tmp, owner="ctl-b")
        self.assertEqual(r2.svc.recover()["pending"], 1)
        self.assertEqual(r2.svc.reconcile_once("vm-1")["action"], "presented")

    def test_two_replicas_one_lease(self):
        """MC-021/024: a second live replica cannot reconcile the same VM."""
        a, b = Rig(self.tmp, owner="ctl-a"), Rig(self.tmp, owner="ctl-b")
        b.hv = a.hv
        b.svc.adapter = a.hv
        a.svc.submit("vm-1", "req-1", 4, 0)
        a.store.acquire_lease("vm-1", "ctl-a", 60)
        self.assertEqual(b.svc.reconcile_once("vm-1")["action"], "skipped")
        self.assertEqual(a.hv.hotadd_actions, 0)

    def test_policy_quota_degraded_and_limits(self):
        r = Rig(self.tmp)
        r.svc.policy_ctx["vm-1"] = {"site": "s1", "allowed_sites": ["s1"]}   # security unknown
        with self.assertRaises(PolicyDenied):
            r.svc.submit("vm-1", "r1", 4)
        r.svc.policy_ctx["vm-1"]["security_state"] = "ok"
        r.svc.health.set("state_store", "degraded")
        with self.assertRaises(DegradedMode):
            r.svc.submit("vm-1", "r2", 4)
        r.svc.health.set("state_store", "healthy")
        with self.assertRaises(ShrinkNotSupported):
            r.svc.submit("vm-1", "r3", 1)
        with self.assertRaises(GuestLimitExceeded):
            r.svc.submit("vm-1", "r4", 9)
        with self.assertRaises(StaleGeneration):
            r.svc.submit("vm-1", "r5", 4, expected_generation=7)

    def test_freeze_blocks_new_expansion_keeps_cpus(self):
        r = Rig(self.tmp)
        r.svc.set_enabled("vm-1", False, "op")
        with self.assertRaises(Exception) as cm:
            r.svc.submit("vm-1", "r1", 4)
        self.assertEqual(cm.exception.code, "EXPANSION_DISABLED")
        self.assertEqual(r.svc.status("vm-1")["observed_vcpus"], 2)

    def test_regressive_observation_refused(self):
        r = Rig(self.tmp)
        r.svc.submit("vm-1", "r1", 4)
        r.svc.reconcile_once("vm-1")
        r.svc.observe(report("vm-1", "0-3", 1))
        with self.assertRaises(Exception) as cm:
            r.svc.observe(report("vm-1", "0-1", 2))
        self.assertEqual(cm.exception.code, "OBSERVATION_REGRESSION")

    def test_observation_replay_protection_survives_restart(self):
        r = Rig(self.tmp)
        r.svc.submit("vm-1", "r1", 4)
        r.svc.observe(report("vm-1", "0-2", 5))
        r2 = Rig(self.tmp)
        r2.svc.recover()
        with self.assertRaises(ObservationRejected):
            r2.svc.observe(report("vm-1", "0-2", 5))

    def test_retry_exhaustion_fails_closed(self):
        r = Rig(self.tmp, FaultPlan(["backend_error"] * 10))
        r.svc.budget = RetryBudget(1.0, min_tokens=50)
        r.svc.submit("vm-1", "r1", 4)
        last = None
        for _ in range(8):
            last = r.svc.reconcile_once("vm-1")
            if last["action"] in ("failed", "circuit_open"):
                break
        self.assertIn(last["action"], ("failed", "circuit_open"))
        self.assertEqual(r.hv.present["vm-1"], 2)

    def test_degraded_mode_ends_when_breaker_closes(self):
        """Regression for the defect tools/perf.py found: health stayed 'down' after recovery."""
        r = Rig(self.tmp, FaultPlan(["timeout_before"] * 5))
        r.svc.breaker = CircuitBreaker("hypervisor_adapter", 2, 0.0)
        r.svc.submit("vm-1", "r1", 4)
        t = [time.time()]
        r.svc.clock = r.store._clock = lambda: t[0]
        for _ in range(3):
            t[0] += 100
            r.svc.reconcile_once("vm-1")
        r.hv.faults.queue.clear()
        for _ in range(3):
            t[0] += 100
            r.svc.reconcile_once("vm-1")
        self.assertEqual(r.svc.health.status["hypervisor_adapter"], "healthy")
        self.assertEqual(r.hv.present["vm-1"], 4)
        r.svc.submit("vm-1", "r2", 5)          # not refused as degraded

    def test_concurrent_submits_single_commit(self):
        """MC-037: 16 threads, same request id -> one accepted operation."""
        r = Rig(self.tmp)
        out, errs = [], []

        def go():
            try:
                out.append(r.svc.submit("vm-1", "same", 6, None))
            except Exception as e:  # noqa: BLE001
                errs.append(e)
        ts = [threading.Thread(target=go) for _ in range(16)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertFalse(errs)
        self.assertEqual(len({o["operation_id"] for o in out}), 1)
        self.assertEqual(len(r.store.load("vm-1")["journal"]), 1)

    def test_property_random_sequences_invariants(self):
        """MC-036: random submit/reconcile/observe sequences never break invariants."""
        rng = random.Random(1234)
        for trial in range(15):
            with tempfile.TemporaryDirectory() as td:
                faults = FaultPlan([rng.choice(["timeout_after", "timeout_before", "partial:5", "backend_error", ""])
                                    for _ in range(20)])
                r = Rig(td, faults, vms={"vm-1": (2, 16)})
                r.svc.clock = r.store._clock = (lambda base=[time.time()]: base.__setitem__(0, base[0] + 50) or base[0])
                seq, n = 1, 0
                for step in range(40):
                    op = rng.random()
                    try:
                        if op < 0.3:
                            r.svc.submit("vm-1", f"r{rng.randint(0, 6)}", rng.randint(1, 18))
                        elif op < 0.7:
                            r.svc.reconcile_once("vm-1")
                        else:
                            online = r.hv.guest_tick("vm-1")
                            r.svc.observe(report("vm-1", f"0-{online - 1}", seq, ts=time.time()))
                            seq += 1
                    except Exception:  # noqa: BLE001 - rejections are allowed; invariants are what we check
                        pass
                    st = r.svc.status("vm-1")
                    self.assertLessEqual(st["observed_vcpus"], st["desired_vcpus"])
                    self.assertLessEqual(st["desired_vcpus"], st["max_vcpus"])
                    self.assertLessEqual(r.hv.present["vm-1"], max(st["desired_vcpus"], 2))
                    self.assertGreaterEqual(r.hv.present["vm-1"], n)
                    n = r.hv.present["vm-1"]


# ---------------------------------------------------------------- MC-010/011/012/031/035
class SecurityTest(unittest.TestCase):
    def setUp(self):
        self.env = {"INV34_SECRET_CALLER_A": "11" * 32, "INV34_SECRET_CALLER_B": "22" * 32}
        self.dir = {"caller-a": Principal("caller-a", "caller", "t1"), "caller-b": Principal("caller-b", "caller", "t2")}
        self.auth = Authenticator(self.dir, EnvSecretSource(self.env))

    def test_authn_accept_replay_forge_skew(self):
        tok = mint_token("caller-a", bytes.fromhex("11" * 32))
        self.assertEqual(self.auth.authenticate(tok).principal_id, "caller-a")
        with self.assertRaises(AuthError):
            self.auth.authenticate(tok)                          # replay
        forged = mint_token("caller-a", bytes.fromhex("22" * 32))
        with self.assertRaises(AuthError):
            self.auth.authenticate(forged)                       # spoof with other key
        with self.assertRaises(AuthError):
            self.auth.authenticate(mint_token("caller-a", bytes.fromhex("11" * 32), now=time.time() - 9999))
        for bad in (None, "", "a.b", "x" * 600):
            with self.assertRaises(AuthError):
                self.auth.authenticate(bad)

    def test_secret_rotation_and_redacted_repr(self):
        env = {"INV34_SECRET_CALLER_A": "11" * 32, "INV34_SECRET_CALLER_A_NEXT": "33" * 32}
        a = Authenticator(self.dir, EnvSecretSource(env))
        self.assertTrue(a.authenticate(mint_token("caller-a", bytes.fromhex("33" * 32))))
        self.assertEqual(repr(EnvSecretSource(env).get("caller-a")), "<redacted>")

    def test_authz_least_privilege_and_cross_tenant(self):
        pol = CapabilityPolicy()
        pol.grant("caller-a", "cpu.expand", "tenant:t1")
        vm1, vm2 = VmBinding("vm-1", "t1", "w", "s1"), VmBinding("vm-2", "t2", "w", "s1")
        pol.authorize(self.dir["caller-a"], "cpu.expand", vm1)
        for p, act, vm in ((self.dir["caller-a"], "cpu.expand", vm2), (self.dir["caller-a"], "ops.disable", vm1),
                           (self.dir["caller-b"], "cpu.expand", vm1)):
            with self.assertRaises(Forbidden):
                pol.authorize(p, act, vm)

    def test_quota_tenant_site_fleet_fairness(self):
        q = QuotaService({"t1": 10, "t2": 100}, {"s1": 20}, 30)
        q.register(VmBinding("a", "t1", "w", "s1"), 4)
        q.register(VmBinding("b", "t2", "w", "s1"), 4)
        q.reserve("a", 10)
        with self.assertRaises(QuotaExceeded):
            q.reserve("a", 11)                                   # tenant
        with self.assertRaises(QuotaExceeded):
            q.reserve("b", 11)                                   # fair share at s1 = 10
        q2 = QuotaService({}, {"s1": 20}, 30)
        q2.register(VmBinding("a", "tx", "w", "s1"), 1)
        with self.assertRaises(QuotaExceeded):
            q2.reserve("a", 2)                                   # no quota -> fail closed


# ---------------------------------------------------------------- MC-009/013/014/027/050/051/055 via API
class ApiTest(TmpCase):
    def setUp(self):
        super().setUp()
        self.r = Rig(self.tmp)
        self.env = {"INV34_SECRET_CALLER_A": "11" * 32, "INV34_SECRET_OBS": "44" * 32,
                    "INV34_SECRET_OPS": "55" * 32, "INV34_SECRET_CALLER_B": "66" * 32}
        d = {"caller-a": Principal("caller-a", "caller", "t1"), "obs": Principal("obs", "observer"),
             "ops": Principal("ops", "operator"), "caller-b": Principal("caller-b", "caller", "t2")}
        pol = CapabilityPolicy()
        for a in ("cpu.expand", "cpu.status"):
            pol.grant("caller-a", a, "tenant:t1")
        pol.grant("obs", "cpu.observe", "vm-1")
        for a in ("ops.disable", "ops.enable", "ops.explain", "cpu.status"):
            pol.grant("ops", a, "tenant:t1")
        self.api = Api(self.r.svc, Authenticator(d, EnvSecretSource(self.env)), pol,
                       {"vm-1": VmBinding("vm-1", "t1", "w", "s1")}, logger=StructuredLogger("t", io.StringIO()))

    def call(self, method, path, who="caller-a", body=None, **hdr):
        key = {"caller-a": "11", "obs": "44", "ops": "55", "caller-b": "66"}[who] * 32
        h = {"Authorization": "INV34 " + mint_token(who, bytes.fromhex(key)), **hdr}
        return self.api.handle(method, path, h, json.dumps(body).encode() if body is not None else b"")

    def expand(self, target=4, rid="r1", **kw):
        return self.call("POST", "/v1/cpu/expand", body={"schema": "PK_CPU_EXPANSION_REQUEST/1", "request_id": rid,
                                                         "vm_id": "vm-1", "target_vcpus": target}, **kw)

    def test_full_path_and_trace_propagation(self):
        tp = "00-" + "ab" * 16 + "-" + "cd" * 8 + "-01"
        s, h, b = self.expand(traceparent=tp)
        self.assertEqual(s, 202)
        self.assertTrue(h["traceparent"].startswith("00-" + "ab" * 16))
        self.assertEqual(b["trace_id"], "ab" * 16)
        self.r.svc.reconcile_once("vm-1")
        s, _, b = self.call("POST", "/v1/cpu/observe", "obs", body=report("vm-1", "0-3", 1))
        self.assertEqual(s, 200)
        s, _, b = self.call("GET", "/v1/cpu/status?vm_id=vm-1")
        self.assertTrue(b["converged"])

    def test_error_mapping(self):
        self.assertEqual(self.api.handle("POST", "/v1/cpu/expand", {}, b"{}")[0], 401)
        self.assertEqual(self.expand(1)[0], 422)
        self.assertEqual(self.expand(9, rid="r9")[0], 422)
        self.assertEqual(self.call("POST", "/v1/cpu/expand", body={"schema": "X"})[0], 400)
        self.assertEqual(self.call("POST", "/v1/cpu/expand", body={"schema": "PK_CPU_EXPANSION_REQUEST/1",
                                   "request_id": "r", "vm_id": "vm-1", "target_vcpus": 4, "evil": 1})[0], 400)
        self.assertEqual(self.expand(**{"X-INV34-Protocol": "2"})[0], 426)
        self.assertEqual(self.expand(**{"X-INV34-Deadline-Ms": "0"})[0], 504)
        self.assertEqual(self.api.handle("POST", "/v1/cpu/expand", {"Authorization": "INV34 x"},
                                         b"x" * 20000)[0], 413)
        self.assertEqual(self.call("GET", "/v1/cpu/status?vm_id=vm-9")[0], 403)
        self.assertEqual(self.call("POST", "/v1/ops/disable", body={"vm_id": "vm-1"})[0], 403)
        self.assertEqual(self.call("GET", "/v1/cpu/status?vm_id=vm-1", "caller-b")[0], 403)

    def test_quarantine_explain_health_metrics(self):
        self.assertEqual(self.call("POST", "/v1/ops/disable", "ops", body={"vm_id": "vm-1"})[0], 200)
        self.assertEqual(self.expand()[0], 423)
        self.call("POST", "/v1/ops/enable", "ops", body={"vm_id": "vm-1"})
        self.expand(rid="r2")
        s, _, b = self.call("GET", "/v1/explain?vm_id=vm-1", "ops")
        self.assertEqual(b["last_policy_decision"]["allowed"], True)
        self.assertEqual(self.api.handle("GET", "/healthz", {}, b"")[0], 200)
        s, _, b = self.api.handle("GET", "/readyz", {}, b"")
        self.assertEqual(b["mode"], "normal")
        s, _, b = self.api.handle("GET", "/metrics", {}, b"")
        self.assertIn("inv34_requests_total", b["_text"])

    def test_hostile_payloads_fuzz(self):
        """MC-035/036: random bytes and type-confused JSON never 5xx and never mutate state."""
        rng = random.Random(7)
        before = self.r.store.load("vm-1")["cpu"]
        samples = [bytes(rng.randrange(256) for _ in range(rng.randrange(1, 200))) for _ in range(60)]
        samples += [json.dumps(x).encode() for x in ([], None, 3, "s", {"schema": "PK_CPU_EXPANSION_REQUEST/1",
                    "request_id": ["x"], "vm_id": "vm-1", "target_vcpus": "4"},
                    {"schema": "PK_CPU_EXPANSION_REQUEST/1", "request_id": "r", "vm_id": "vm-1",
                     "target_vcpus": True}, {"schema": "PK_CPU_EXPANSION_REQUEST/1", "request_id": "r\n",
                                             "vm_id": "vm-1", "target_vcpus": 4})]
        for body in samples:
            h = {"Authorization": "INV34 " + mint_token("caller-a", bytes.fromhex("11" * 32))}
            s, _, _ = self.api.handle("POST", "/v1/cpu/expand", h, body)
            self.assertLess(s, 500, body[:40])
        self.assertEqual(self.r.store.load("vm-1")["cpu"], before)

    def test_overload_sheds(self):
        self.api.admission = AdmissionController(max_in_flight=0, max_queue=0)
        s, h, b = self.expand()
        self.assertEqual(s, 429)
        self.assertEqual(h.get("retry-after"), "1")


# ---------------------------------------------------------------- MC-015..018
def good_cfg(**kw):
    c = {"schema": "INV34_CONFIG/1", "version": "2026.09.1", "environment": "staging", "site": "s1",
         "expansion_enabled": False, "adapter": "cloud-hypervisor-rest", "max_vcpus_default": 8,
         "host_reserve_vcpus": 2, "stall_after_s": 120, "observation_max_age_s": 30,
         "tenant_quotas": {"t1": 64}, "site_ceiling": 256, "fleet_ceiling": 1024,
         "precedence": ["security", "residency", "capacity", "slo", "cost"]}
    c.update(kw)
    return c


class ConfigTest(TmpCase):
    def test_validation_rejects(self):
        validate_config(good_cfg())
        for bad in (good_cfg(extra=1), good_cfg(adapter="rogue"), good_cfg(environment="production", adapter="emulator"),
                    good_cfg(site_ceiling=5000), good_cfg(precedence=["cost"]), good_cfg(expansion_enabled="yes")):
            with self.assertRaises(ConfigError):
                validate_config(bad)

    def test_activate_provenance_rollback(self):
        repo = ConfigRepository(self.tmp)
        with self.assertRaises(ConfigError):
            repo.active()
        d1 = repo.stage(good_cfg())
        repo.activate(d1, author="alice", approver=None, reason="init")
        d2 = repo.stage(good_cfg(version="2026.09.2", expansion_enabled=True))
        repo.activate(d2, author="alice", approver=None, reason="enable")
        self.assertTrue(repo.active()["expansion_enabled"])
        repo.rollback(author="alice", approver=None, reason="bad")
        self.assertEqual(repo.active_digest(), d1)
        self.assertEqual(len(repo.history()), 3)
        dp = repo.stage(good_cfg(environment="production"))
        with self.assertRaises(ConfigError):
            repo.activate(dp, author="alice", approver="alice", reason="self-approve")


# ---------------------------------------------------------------- MC-022/023/025/030/034/048/052..054
class ResilienceTelemetryAuditTest(TmpCase):
    def test_backoff_bounded_jitter(self):
        p, rng = RetryPolicy(base_s=1, cap_s=8), random.Random(0)
        for a in range(1, 10):
            self.assertLessEqual(p.backoff(a, rng), min(8, 2 ** (a - 1)))

    def test_budget_and_breaker(self):
        b = RetryBudget(0.1, min_tokens=1)
        self.assertTrue(b.try_spend())
        self.assertFalse(b.try_spend())
        t = [0.0]
        cb = CircuitBreaker("x", 2, 10, clock=lambda: t[0])
        cb.before_call(); cb.record(False); cb.before_call(); cb.record(False)
        with self.assertRaises(CircuitOpen):
            cb.before_call()
        t[0] = 11
        cb.before_call()
        with self.assertRaises(CircuitOpen):
            cb.before_call()          # only one half-open probe
        cb.record(True)
        self.assertEqual(cb.state, "closed")

    def test_admission(self):
        a = AdmissionController(1, 0)
        a.acquire(0.1)
        with self.assertRaises(Overloaded):
            a.acquire(0.1)
        a.release()

    def test_precedence(self):
        ctx = {"security_state": "ok", "site": "s1", "allowed_sites": ["s1"], "add_vcpus": 2, "host_free_vcpus": 1,
               "cost_after": 5, "cost_cap": 1}
        d = evaluate(["cost", "security", "residency", "capacity", "slo"], DEFAULT_EVALUATORS, ctx)
        self.assertEqual(d.deciding, "cost")
        d = evaluate(["security", "residency", "capacity", "slo", "cost"], DEFAULT_EVALUATORS, ctx)
        self.assertEqual(d.deciding, "capacity")
        d = evaluate(["security", "residency", "capacity", "slo", "cost"], DEFAULT_EVALUATORS, {"add_vcpus": 1})
        self.assertFalse(d.allowed)

    def test_forecast(self):
        self.assertEqual(headroom_forecast([(0, 1)], 10, 5)["status"], "INSUFFICIENT_DATA")
        f = headroom_forecast([(0, 2), (10, 4), (20, 6)], 10, 30)
        self.assertAlmostEqual(f["time_to_saturation_s"], 20.0)
        self.assertTrue(f["saturating_within_horizon"])

    def test_audit_chain_tamper(self):
        p = os.path.join(self.tmp, "a.jsonl")
        c = AuditChain(p, AUDIT_KEY)
        for i in range(5):
            c.append("request.accepted", vm_id="vm-1", n=i)
        head = c.head()
        self.assertTrue(AuditChain.verify(p, AUDIT_KEY, head)[0])
        lines = pathlib.Path(p).read_text().splitlines()
        pathlib.Path(p).write_text("\n".join(lines[:4]) + "\n")
        self.assertFalse(AuditChain.verify(p, AUDIT_KEY, head)[0])       # truncation vs anchored head
        pathlib.Path(p).write_text("\n".join([lines[0], lines[2]] + lines[3:]) + "\n")
        self.assertFalse(AuditChain.verify(p, AUDIT_KEY)[0])             # deletion
        pathlib.Path(p).write_text("\n".join(lines).replace('"n":1', '"n":9') + "\n")
        self.assertFalse(AuditChain.verify(p, AUDIT_KEY)[0])             # edit
        self.assertFalse(AuditChain.verify(p, b"wrong" * 8)[0])
        with self.assertRaises(ValueError):
            c.append("made.up")

    def test_redaction_and_bounded_labels(self):
        tok = mint_token("caller-a", b"x" * 32)
        r = redact({"authorization": "INV34 " + tok, "note": "token " + tok, "nested": {"secret": "s"}})
        self.assertNotIn(tok, json.dumps(r))
        buf = io.StringIO()
        StructuredLogger("c", buf).log("info", "m", password="p", vm_id="vm-1")
        self.assertNotIn('"p"', buf.getvalue())
        m = Metrics()
        with self.assertRaises(ValueError):
            m.inc("x", code="vm 1 tenant")

    def test_traceparent(self):
        self.assertIsNone(parse_traceparent("00-" + "0" * 32 + "-" + "1" * 16 + "-01"))
        self.assertIsNone(parse_traceparent("garbage"))
        t, s, h = child_traceparent(None)
        self.assertEqual(parse_traceparent(h), (t, s))


if __name__ == "__main__":
    unittest.main()
