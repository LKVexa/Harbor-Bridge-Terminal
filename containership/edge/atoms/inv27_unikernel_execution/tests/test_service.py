"""MC-007 boot adapter, MC-016 lifecycle, MC-024/025 authz, MC-048 audit, MC-053 load shedding,
MC-056 journal/restart, MC-057 idempotency+fencing, MC-058 quarantine/disable, MC-069 health,
MC-074/075 decisions+explain, and the zero-side-effect property of rejected artifacts."""
import datetime as dt
import importlib
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest

from harness import (HERE, NOW, PKGNAME, UkError, admit, envelope, image, manifest, policy, ref)

svc_mod = importlib.import_module(f"{PKGNAME}.service")
vmm = importlib.import_module(f"{PKGNAME}.vmm")
authz = importlib.import_module(f"{PKGNAME}.authz")
audit_mod = importlib.import_module(f"{PKGNAME}.audit")
lifecycle = importlib.import_module(f"{PKGNAME}.lifecycle")
resilience = importlib.import_module(f"{PKGNAME}.resilience")
telemetry = importlib.import_module(f"{PKGNAME}.telemetry")

FAKE = [sys.executable, str(HERE / "fake_vmm.py")]
KEY = b"k" * 32
_n = [0]


def token(caps=("image.admit", "instance.run", "instance.stop"), tenants=("t1",), sub="alice", ttl=300):
    _n[0] += 1
    now = time.time()
    return authz.mint({"sub": sub, "tenants": list(tenants), "caps": list(caps), "iat": now, "exp": now + ttl,
                       "nonce": f"nonce-{_n[0]:08d}-{os.getpid()}"}, KEY, "kid1")


def service(mode=None, **kw):
    prefix = FAKE + ([f"--mode={mode}"] if mode else [])
    sup = vmm.Supervisor(vmm.ScriptBackend(prefix), grace_s=0.5)
    kw.setdefault("boot_deadline_s", 5.0)
    return svc_mod.UnikernelService(policy(), sup, authz.Authenticator(lambda k: KEY if k == "kid1" else None), **kw)


def run(s, name="uk_good.elf", toolchain="unikraft", key="idem-0001", tok=..., **kw):
    data = image(name)
    return s.run(token() if tok is ... else tok, tenant=kw.pop("tenant", "t1"), image_bytes=data, bound_digest=ref(data),
                 manifest=kw.pop("man", manifest(data, toolchain)), envelope=kw.pop("env", envelope(data, toolchain)),
                 idempotency_key=key, now=NOW, **kw)


class Boot(unittest.TestCase):
    def test_end_to_end_verify_launch_observe_stop_cleanup(self):
        s = service()
        inst = run(s)
        self.assertEqual(inst.state, "running")
        serial = "".join(inst.running.serial)
        self.assertIn("DIGEST " + ref(image("uk_good.elf"))[7:], serial)   # the VMM got the admitted bytes
        path = inst.running.image_path
        self.assertTrue(os.path.exists(path))
        s.stop(token(), inst.instance_id)
        self.assertEqual(inst.state, "stopped")
        self.assertFalse(os.path.exists(path))
        self.assertIsNotNone(inst.running.proc.returncode)
        self.assertEqual([h["to"] for h in inst.history], ["verified", "starting", "running", "stopping", "stopped"])
        s.stop(token(), inst.instance_id)      # idempotent

    def test_qemu_plan_is_hardened_and_attaches_only_the_plan(self):
        a = admit()
        spec = vmm.LaunchSpec("abcdef123", a.blob, "x86_64", 32, 1, "console=ttyS0", "INV27-READY", a.plan)
        argv = vmm.QemuBackend("qemu-system-x86_64", accel="kvm").plan(spec, "/tmp/img")["argv"]
        for flag in ("-nodefaults", "-no-user-config", "-nographic", "-no-reboot"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("-sandbox") + 1], vmm.QEMU_SANDBOX)
        self.assertEqual(argv[argv.index("-nic") + 1], "none")
        self.assertFalse(any("vfio" in x or "pci-assign" in x for x in argv))
        fc = vmm.FirecrackerBackend("firecracker").plan(spec, "/tmp/img")
        self.assertEqual(fc["config"]["network-interfaces"], [])
        self.assertTrue(all(d["is_read_only"] for d in fc["config"]["drives"]))

    def test_unavailable_or_unapproved_vmm_fails_closed(self):
        with self.assertRaises(UkError) as c:
            vmm.QemuBackend("definitely-not-a-qemu-binary").probe()
        self.assertEqual(c.exception.code, "UK_VMM_UNSUPPORTED")
        with self.assertRaises(UkError) as c:
            vmm.QemuBackend(sys.executable).probe()   # exists, but its --version is not an approved QEMU
        self.assertEqual(c.exception.code, "UK_VMM_UNSUPPORTED")

    def test_boot_timeout_crash_and_serial_flood_clean_up(self):
        for mode, code in (("hang", "UK_VMM_TIMEOUT"), ("crash", "UK_VMM_LAUNCH_FAILED"), ("flood", "UK_LIMIT_EXCEEDED")):
            s = service(mode, boot_deadline_s=1.0)
            before = set(os.listdir(tempfile.gettempdir()))
            with self.subTest(mode=mode), self.assertRaises(UkError) as c:
                run(s)
            self.assertEqual(c.exception.code, code)
            inst = next(iter(s.instances.values()))
            self.assertEqual(inst.state, "stopped")
            leaked = [f for f in set(os.listdir(tempfile.gettempdir())) - before if f.startswith("inv27-")]
            self.assertEqual(leaked, [])

    def test_stop_escalates_to_sigkill(self):
        s = service("ignore_term")
        inst = run(s)
        t = time.monotonic()
        s.stop(token(), inst.instance_id)
        self.assertLess(time.monotonic() - t, 5)
        self.assertEqual(inst.running.proc.returncode, -9)


class ZeroSideEffects(unittest.TestCase):
    def test_rejected_artifacts_never_reach_the_vmm(self):
        s = service()
        for name in ("uk_fork.elf", "uk_dlopen.elf", "dyn_fork_dlopen.elf", "uk_stripped.elf", "uk_wx.elf"):
            with self.subTest(name=name), self.assertRaises(UkError):
                run(s, name, key=f"k-{name}")
        with self.assertRaises(UkError):
            run(s, env=None, key="k-nosig")
        self.assertEqual(s.supervisor.launches, 0)
        self.assertEqual(s.instances, {})
        self.assertGreaterEqual(s.metrics.counters[("uk_seal_failures_total", (("reason", "UK_SEAL_MULTIPROCESS"),))], 1)


class Auth(unittest.TestCase):
    def test_authn_failures(self):
        s = service()
        good = token()
        bad = [None, "x.y", good[:-2] + "00", token(ttl=5000)]
        for t in bad:
            with self.subTest(t=str(t)[:20]), self.assertRaises(UkError) as c:
                run(s, tok=t)
            self.assertEqual(c.exception.code, "UK_UNAUTHENTICATED")
        run(s, tok=good)
        with self.assertRaises(UkError) as c:
            run(s, tok=good, key="another-key")
        self.assertEqual(c.exception.code, "UK_REPLAY")

    def test_capability_and_tenant_scope(self):
        s = service()
        for t in (token(caps=("image.admit",)), token(tenants=("t2",))):
            with self.assertRaises(UkError) as c:
                run(s, tok=t)
            self.assertEqual(c.exception.code, "UK_FORBIDDEN")
        inst = run(s)
        with self.assertRaises(UkError) as c:
            s.stop(token(tenants=("t2",)), inst.instance_id)
        self.assertEqual(c.exception.code, "UK_FORBIDDEN")
        s.stop(token(), inst.instance_id)


class Controls(unittest.TestCase):
    def test_idempotent_run(self):
        s = service()
        a = run(s, key="same-key-1")
        b = run(s, key="same-key-1")
        self.assertIs(a, b)
        self.assertEqual(s.supervisor.launches, 1)
        with self.assertRaises(UkError) as c:
            run(s, "solo5_good.elf", "solo5", key="same-key-1")
        self.assertEqual(c.exception.code, "UK_INSTANCE_DUPLICATE")
        s.stop(token(), a.instance_id)

    def test_fencing(self):
        s = service()
        s.set_fence(5)
        with self.assertRaises(UkError) as c:
            s.set_fence(4)
        self.assertEqual(c.exception.code, "UK_STALE_FENCE")
        with self.assertRaises(UkError) as c:
            run(s, fence=4)
        self.assertEqual(c.exception.code, "UK_STALE_FENCE")
        s.stop(token(), run(s, fence=5).instance_id, fence=5)

    def test_quota(self):
        s = service(max_instances_per_tenant=1)
        a = run(s, key="quota-key-1")
        with self.assertRaises(UkError) as c:
            run(s, key="quota-key-2")
        self.assertEqual(c.exception.code, "UK_QUOTA_EXCEEDED")
        s.stop(token(), a.instance_id)

    def test_quarantine_stops_and_blocks(self):
        s = service()
        a = run(s, key="qkey-0001")
        op = token(caps=("instance.quarantine",), tenants=(), sub="op-bob")
        stopped = s.quarantine(op, image_ref=a.image_ref, reason="CVE drill")
        self.assertEqual(stopped, [a.instance_id])
        self.assertEqual(a.state, "stopped")
        self.assertIn("quarantined", [h["to"] for h in a.history])
        with self.assertRaises(UkError) as c:
            run(s, key="qkey-0002")
        self.assertEqual(c.exception.code, "UK_QUARANTINED")

    def test_emergency_disable(self):
        s = service()
        op = token(caps=("component.disable",), tenants=(), sub="op-bob")
        s.disable(op, "drill")
        with self.assertRaises(UkError) as c:
            run(s)
        self.assertEqual(c.exception.code, "UK_DISABLED")
        self.assertFalse(s.health()["ready"])
        s.enable(token(caps=("component.disable",), tenants=(), sub="op-bob"), "drill over")
        s.stop(token(), run(s).instance_id)

    def test_load_shedding(self):
        s = service(admission=resilience.Admission(rate_per_s=0.0001, burst=1, max_inflight=4))
        s.stop(token(), run(s, key="shed-key-1").instance_id)
        with self.assertRaises(UkError) as c:
            run(s, key="shed-key-2")
        self.assertEqual(c.exception.code, "UK_OVERLOADED")

    def test_illegal_transitions(self):
        for cur, tgt in (("stopped", "running"), ("rejected", "verified"), ("pending", "running")):
            with self.assertRaises(UkError):
                lifecycle.check(cur, tgt)


class Durability(unittest.TestCase):
    def test_journal_restart_reconciles_and_detects_tamper(self):
        d = tempfile.mkdtemp()
        jp = os.path.join(d, "journal.jsonl")
        s = service(journal_path=jp)
        a = run(s, key="dur-key-1")
        # controller crash: VMM process group dies with it
        s.supervisor.stop(a.running)
        s2 = service(journal_path=jp)
        self.assertEqual(s2.instances[a.instance_id].state, "stopped")
        self.assertEqual(s2.by_key[("t1", "dur-key-1")], a.instance_id)
        with open(jp, "a") as fh:
            fh.write('{"torn": ')                 # torn final write is tolerated
        service(journal_path=jp)
        lines = open(jp).read().splitlines()
        lines[0] = lines[0].replace('"t1"', '"tX"')
        with open(jp, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        with self.assertRaises(UkError) as c:
            service(journal_path=jp)
        self.assertEqual(c.exception.code, "UK_STATE_CORRUPT")

    def test_keyed_journal_rejects_a_full_rechain(self):
        d = tempfile.mkdtemp()
        jp = os.path.join(d, "j.jsonl")
        J = svc_mod.Journal
        j = J(jp, key=b"s" * 32)
        j.append({"instance": "i1", "tenant": "t1", "image": "x", "state": "running", "reason": "UK_OK", "key": None})
        forger = J(os.path.join(d, "f.jsonl"))            # attacker without the key re-chains the file
        forger.append({"instance": "i1", "tenant": "t1", "image": "x", "state": "stopped", "reason": "UK_OK", "key": None})
        os.replace(forger.path, jp)
        with self.assertRaises(UkError) as c:
            J(jp, key=b"s" * 32)
        self.assertEqual(c.exception.code, "UK_STATE_CORRUPT")

    def test_audit_chain_detects_edit_and_truncation(self):
        s = service()
        s.stop(token(), run(s).instance_id)
        ev = s.audit.export()
        head = (ev[-1]["seq"], ev[-1]["hash"])
        self.assertEqual(audit_mod.AuditLog.verify(ev, expect_head=head), [])
        forged = json.loads(json.dumps(ev))
        forged[1]["outcome"] = "refused"
        self.assertTrue(audit_mod.AuditLog.verify(forged))
        self.assertTrue(audit_mod.AuditLog.verify(ev[:-1], expect_head=head))


class Observability(unittest.TestCase):
    def test_health_decision_explain_metrics_logs(self):
        buf = io.StringIO()
        s = service(logger=telemetry.Logger(stream=buf))
        h = s.health()
        self.assertEqual(h["schema"], "PK_UNIKERNEL_STATUS/1")
        self.assertIn("INV27-FAKE-VMM", h["vmm"])
        with self.assertRaises(UkError) as c:
            run(s, "uk_fork.elf", man=manifest(image("uk_fork.elf"), syscalls=["read", "write", "clock_gettime", "fork"]),
                traceparent="00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        text = s.explain(c.exception.details["decision_id"])
        self.assertIn("[FAIL] A8", text)
        self.assertIn("UK_SEAL_MULTIPROCESS", text)
        rec = json.loads(buf.getvalue().splitlines()[-1])
        self.assertEqual(rec["trace_id"], "a" * 32)
        self.assertTrue(rec["tenant"].startswith("t-"))      # pseudonymised
        self.assertIn("uk_seal_failures_total", s.metrics.render())


class Concurrency(unittest.TestCase):
    def test_parallel_runs_respect_quota_and_idempotency(self):
        s = service(max_instances_per_tenant=3, admission=resilience.Admission(rate_per_s=1000, burst=100, max_inflight=64))
        results, errs = [], []
        toks = [token() for _ in range(8)]

        def go(i):
            try:
                results.append(run(s, key=f"par-key-{i % 4}", tok=toks[i]))
            except UkError as e:
                errs.append(e.code)
        ts = [threading.Thread(target=go, args=(i,)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        live = [i for i in s.instances.values() if i.state == "running"]
        self.assertLessEqual(len(live), 3)
        self.assertTrue(set(errs) <= {"UK_QUOTA_EXCEEDED", "UK_INSTANCE_DUPLICATE"}, errs)
        self.assertEqual(len({(i.tenant, i.idempotency_key) for i in s.instances.values()}), len(s.instances))
        for i in live:
            s.stop(token(), i.instance_id)


if __name__ == "__main__":
    unittest.main()
