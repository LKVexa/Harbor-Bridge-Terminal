"""Unit tests for the v4.3.0 hardening layer (stdlib only, no pk_core)."""
from __future__ import annotations

import json
import os
import random
import socket
import tempfile
import threading
import unittest

from _support import KEY, keys, tok
from fvt import audit, compat, config, errors, fencing, identity, integrity, journal, provider, resilience, schema, telemetry


class ErrorsTest(unittest.TestCase):
    def test_every_code_classified_and_schema_valid(self):
        s = schema.load("PK_FULL_VM_ERROR.v1")
        for code in errors.CATALOG:
            schema.validate(errors.OpError(code, "x").as_dict(), s)

    def test_unregistered_code_refused(self):
        with self.assertRaises(KeyError):
            errors.OpError("PK_FULL_VM_MADE_UP", "x")

    def test_runtime_errors_map_to_catalog(self):
        from fvt._rt import runtime
        d = errors.classify(runtime.PrimitiveRequired("no"))
        self.assertEqual((d["code"], d["class"], d["retryable"]), ("PK_FULL_VM_PRIMITIVE_REQUIRED", "terminal", False))
        self.assertEqual(errors.classify(ValueError("x"))["code"], "PK_FULL_VM_INVALID_REQUEST")


class SchemaTest(unittest.TestCase):
    def test_create_request_negative_cases(self):
        from _support import req
        good = req()
        schema.parse_and_validate(json.dumps(good), "PK_FULL_VM_CREATE_REQUEST.v1")
        bads = [dict(good, memory_mib=True), dict(good, memory_mib=10), dict(good, image_digest="md5:x"),
                dict(good, schema="PK_FULL_VM/2"), dict(good, evil=1), {k: v for k, v in good.items() if k != "tenant"},
                dict(good, name="../etc"), dict(good, extra_devices=["a"] * 17)]
        for b in bads:
            with self.subTest(b=b), self.assertRaises(schema.SchemaError):
                schema.parse_and_validate(json.dumps(b), "PK_FULL_VM_CREATE_REQUEST.v1")

    def test_size_and_depth_bounds(self):
        with self.assertRaises(schema.SchemaError):
            schema.parse_and_validate(b"[" * 100000, "PK_FULL_VM_CREATE_REQUEST.v1")
        with self.assertRaises(schema.SchemaError):
            schema.validate({"a": 1}, {"type": "object", "properties": {"a": {"type": "string"}}})


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = config.ConfigStore(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_secure_defaults_valid(self):
        d = config.validate(config.layer())
        self.assertTrue(d["require_hardware_primitive"])
        self.assertFalse(d["allow_software_emulation"])

    def test_security_critical_fail_closed(self):
        for bad in ({"allow_software_emulation": True}, {"require_hardware_primitive": False},
                    {"environment": "prod"}, {"footprint_ceiling_mib": "big"}, {"unknown_key": 1}):
            with self.subTest(bad=bad), self.assertRaises(errors.OpError):
                config.validate(config.layer(bad))

    def test_secret_material_refused(self):
        for bad in ({"site": "-----BEGIN RSA PRIVATE KEY-----"}, {"api_key": "x"}):
            with self.subTest(bad=bad), self.assertRaises(errors.OpError) as cm:
                config.validate(config.layer(bad))
            self.assertIn("secret", str(cm.exception))

    def test_layering_without_rebuild(self):
        d = config.layer({"site": "dc1"}, {"environment": "staging", "max_queue": 8})
        self.assertEqual((d["site"], d["environment"], d["max_queue"]), ("dc1", "staging", 8))

    def test_activate_provenance_and_rollback(self):
        p1 = self.store.activate(config.layer(), author="alice", reason="init")
        p2 = self.store.activate(config.layer({"max_queue": 5}), author="bob", reason="tune")
        self.assertEqual((p2["generation"], p2["previous_digest"], p2["author"]), (2, p1["digest"], "bob"))
        self.assertIn("activated_at", p2)
        rb = self.store.rollback(author="ops", reason="bad tune")
        self.assertEqual(rb["digest"], p1["digest"])
        self.assertEqual(self.store.active()["config"]["max_queue"], 64)

    def test_invalid_never_partially_applied(self):
        self.store.activate(config.layer(), author="a", reason="r")
        before = self.store.active_path.read_bytes()
        with self.assertRaises(errors.OpError):
            self.store.activate(config.layer({"allow_software_emulation": True}), author="a", reason="r")
        self.assertEqual(before, self.store.active_path.read_bytes())

    def test_auto_rollback_on_failed_health(self):
        p1 = self.store.activate(config.layer(), author="a", reason="r")
        with self.assertRaises(errors.OpError):
            self.store.activate(config.layer({"max_queue": 1}), author="a", reason="r", health_check=lambda d: False)
        self.assertEqual(self.store.active()["provenance"]["digest"], p1["digest"])

    def test_tamper_detected(self):
        self.store.activate(config.layer(), author="a", reason="r")
        rec = json.loads(self.store.active_path.read_text())
        rec["config"]["allow_gpu_passthrough"] = True
        self.store.active_path.write_text(json.dumps(rec))
        with self.assertRaises(errors.OpError):
            self.store.active()


class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.kp = keys()
        self.now = [1_800_000_000.0]
        self.auth = identity.Authenticator(self.kp, clock=lambda: self.now[0])

    def t(self, **kw):
        return tok(self.kp, now=self.now[0], **kw)

    def test_valid_and_scoped(self):
        p = self.auth.authenticate(self.t())
        identity.authorize(p, "boot", "t1")
        with self.assertRaises(errors.OpError):
            identity.authorize(p, "boot", "t2")
        with self.assertRaises(errors.OpError):
            identity.authorize(p, "admin", "t1")

    def test_replay_refused(self):
        t = self.t()
        self.auth.authenticate(t)
        with self.assertRaises(errors.OpError) as cm:
            self.auth.authenticate(t)
        self.assertIn("replayed", str(cm.exception))

    def test_expiry_signature_audience_revocation(self):
        t = self.t(ttl_s=60)
        self.now[0] += 1000
        with self.assertRaises(errors.OpError):
            self.auth.authenticate(t)
        body, mac = self.t().split(".")
        with self.assertRaises(errors.OpError):
            self.auth.authenticate(body + "." + mac[:-2] + ("AA" if mac[-2:] != "AA" else "BB"))
        with self.assertRaises(errors.OpError):
            self.auth.authenticate(self.t(aud="someone-else"))
        t = self.t()
        self.kp.revoke("k1")
        with self.assertRaises(errors.OpError) as cm:
            self.auth.authenticate(t)
        self.assertEqual(cm.exception.code, "PK_FULL_VM_UNAUTHENTICATED")

    def test_trust_services_unavailable_fail_closed(self):
        t = self.t()
        self.kp.available = False
        with self.assertRaises(errors.OpError) as cm:
            self.auth.authenticate(t)
        self.assertEqual(cm.exception.code, "PK_FULL_VM_TRUST_UNAVAILABLE")
        self.kp.available = True

        def broken():
            raise OSError("ntp gone")
        a = identity.Authenticator(self.kp, clock=broken)
        with self.assertRaises(errors.OpError) as cm:
            a.authenticate(self.t())
        self.assertEqual(cm.exception.code, "PK_FULL_VM_TRUST_UNAVAILABLE")

    def test_garbage_credentials(self):
        for g in (None, 5, "", "a.b.c", "x" * 9000, "!!!.???"):
            with self.subTest(g=g), self.assertRaises(errors.OpError):
                self.auth.authenticate(g)

    def test_short_key_refused(self):
        kp = identity.KeyProvider({"k": b"short"})
        with self.assertRaises(LookupError):
            identity.issue(kp, "k", sub="s", kind="service", tenants=["t"], ops=["read"], nonce="n")


class AuditTest(unittest.TestCase):
    def test_chain_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            log = audit.AuditLog(os.path.join(d, "a.jsonl"))
            for i in range(5):
                log.append(actor="svc", action="boot", outcome="ok", token="SECRET", n=i)
            recs = log.records()
            self.assertEqual(audit.AuditLog.verify(recs), (True, None))
            self.assertEqual(recs[0]["fields"]["token"], "[REDACTED]")
            reloaded = audit.AuditLog(os.path.join(d, "a.jsonl"))
            self.assertEqual(reloaded.head(), log.head())
            recs[2]["outcome"] = "deny"
            self.assertEqual(audit.AuditLog.verify(recs), (False, 2))
            recs2 = log.records()
            del recs2[1]
            self.assertFalse(audit.AuditLog.verify(recs2)[0])


class IntegrityTest(unittest.TestCase):
    def test_verify_paths(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"image-bytes")
        try:
            d = integrity.file_digest(f.name)
            sig = integrity.sign_digest(KEY, d)
            self.assertEqual(integrity.verify_artifact(f.name, expected=d, approved=[d], signature=sig, key=KEY), d)
            cases = [dict(expected="sha256:" + "0" * 64, approved=[d], signature=sig),
                     dict(expected=d, approved=[], signature=sig),
                     dict(expected=d, approved=[d], signature=None),
                     dict(expected=d, approved=[d], signature="00" * 32)]
            for c in cases:
                with self.subTest(c=c), self.assertRaises(errors.OpError):
                    integrity.verify_artifact(f.name, key=KEY, **c)
        finally:
            os.unlink(f.name)


class ProviderTest(unittest.TestCase):
    def test_host_probe(self):
        with tempfile.TemporaryDirectory() as d:
            ci = os.path.join(d, "cpuinfo")
            open(ci, "w").write("flags\t: fpu vme\n")
            r = provider.HostProbe(dev=os.path.join(d, "kvm"), cpuinfo=ci).probe()
            self.assertFalse(r.usable)
            self.assertEqual(len(r.reasons), 2)
            open(ci, "w").write("flags\t: fpu vmx\n")
            dev = os.path.join(d, "kvm")
            open(dev, "w").close()
            r = provider.HostProbe(dev=dev, cpuinfo=ci).probe()
            self.assertTrue(r.usable)
            self.assertEqual(r.cpu_flag, "vmx")

    def test_this_host_probe_is_honest(self):
        r = provider.HostProbe().probe()
        self.assertEqual(r.usable, os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK) and r.cpu_flag is not None)

    def test_qemu_argv_is_kvm_only_and_full_model(self):
        p = provider.QemuKvmProvider(binary="/nonexistent/qemu")
        a = " ".join(p.argv({"name": "g", "instance_id": "i", "memory_mib": 512}, "/tmp/q"))
        self.assertIn("-accel kvm", a)
        self.assertNotIn("tcg", a)
        for dev in ("virtio-net-pci", "virtio-balloon-pci", "virtio-rng-pci", "virtio-serial-pci", "qemu-xhci", "ahci"):
            self.assertIn(dev, a)
        self.assertIn("-sandbox on", a)

    def test_qemu_refuses_without_primitive(self):
        class NoKvm(provider.HostProbe):
            def probe(self):
                return provider.ProbeResult(False, ["no kvm"])
        p = provider.QemuKvmProvider(binary="/nonexistent/qemu", probe=NoKvm())
        with self.assertRaises(errors.OpError) as cm:
            p.launch({"name": "g", "instance_id": "i", "memory_mib": 512})
        self.assertEqual(cm.exception.code, "PK_FULL_VM_PRIMITIVE_REQUIRED")

    def test_qmp_client_protocol(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "q.sock")
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(path)
        srv.listen(1)
        seen = []

        def serve():
            c, _ = srv.accept()
            c.sendall(b'{"QMP": {"version": {}, "capabilities": []}}\n')
            f = c.makefile("rb")
            for line in f:
                m = json.loads(line)
                seen.append(m["execute"])
                if m["execute"] == "query-status":
                    c.sendall(b'{"event": "RESUME"}\n{"return": {"running": true, "status": "running"}}\n')
                elif m["execute"] == "bad":
                    c.sendall(b'{"error": {"class": "GenericError", "desc": "nope"}}\n')
                else:
                    c.sendall(b'{"return": {}}\n')
            c.close()
        th = threading.Thread(target=serve, daemon=True)
        th.start()
        q = provider.QmpClient(path)
        self.assertTrue(q.execute("query-status")["running"])
        with self.assertRaises(errors.OpError):
            q.execute("bad")
        q.close()
        th.join(2)
        self.assertEqual(seen[:2], ["qmp_capabilities", "query-status"])


class JournalTest(unittest.TestCase):
    def test_torn_tail_corrupt_middle_compact_backup(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "j.wal")
            j = journal.Journal(p)
            j.append({"op": "create", "instance_id": "a", "state": "created", "tenant": "t"})
            j.append({"op": "boot", "instance_id": "a", "state": "running"})
            with open(p, "ab") as fh:
                fh.write(b'deadbeef\t{"op":"bo')   # crash mid-append
            self.assertEqual(j.state()["a"]["state"], "running")
            self.assertTrue(j.torn_tail)
            lines = open(p, "rb").read().split(b"\n")
            lines[0] = lines[0].replace(b"created", b"CREATED")
            open(p, "wb").write(b"\n".join(lines))
            with self.assertRaises(journal.JournalCorrupt):
                j.replay()
            j2 = journal.Journal(os.path.join(d, "k.wal"))
            for i in range(50):
                j2.append({"op": "boot", "instance_id": f"g{i % 3}", "state": "running", "tenant": "t"})
            j2.append({"op": "destroy", "instance_id": "g0", "state": "destroyed"})
            before = j2.state()
            j2.compact()
            self.assertEqual(j2.state(), before)
            self.assertEqual(len(open(j2.path, "rb").read().splitlines()), 1)
            j2.export(os.path.join(d, "backup.wal"))
            j3 = journal.Journal.restore(os.path.join(d, "backup.wal"), os.path.join(d, "restored.wal"))
            self.assertEqual(j3.state(), before)


class ResilienceTest(unittest.TestCase):
    def test_retry_semantics(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise errors.OpError("PK_FULL_VM_PROVIDER_UNAVAILABLE", "x")
            return "ok"
        sleeps = []
        self.assertEqual(resilience.retry(flaky, attempts=3, idempotent=True, rng=random.Random(1), sleep=sleeps.append), "ok")
        self.assertEqual(len(sleeps), 2)
        self.assertTrue(all(0 <= s <= 0.1 for s in sleeps))
        calls.clear()
        with self.assertRaises(errors.OpError):
            resilience.retry(flaky, attempts=3, idempotent=False, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)
        n = []

        def terminal():
            n.append(1)
            raise errors.OpError("PK_FULL_VM_PROVIDER_FAILED", "x")
        with self.assertRaises(errors.OpError):
            resilience.retry(terminal, attempts=5, idempotent=True, sleep=lambda s: None)
        self.assertEqual(len(n), 1)

    def test_deadline_and_cancel(self):
        t = [0.0]
        dl = resilience.Deadline(100, clock=lambda: t[0])
        dl.check()
        t[0] = 0.2
        with self.assertRaises(errors.OpError) as cm:
            dl.check()
        self.assertEqual(cm.exception.code, "PK_FULL_VM_TIMEOUT")
        dl2 = resilience.Deadline(1000)
        dl2.cancel()
        with self.assertRaises(errors.OpError) as cm:
            dl2.check()
        self.assertEqual(cm.exception.code, "PK_FULL_VM_CANCELLED")

    def test_breaker(self):
        t = [0.0]
        b = resilience.CircuitBreaker(2, 1000, clock=lambda: t[0])
        b.failure()
        b.before()
        b.failure()
        with self.assertRaises(errors.OpError):
            b.before()
        t[0] = 1.5
        b.before()
        self.assertEqual(b.state, "half_open")
        b.failure()
        self.assertEqual(b.state, "open")
        t[0] = 3.0
        b.before()
        b.success()
        self.assertEqual(b.state, "closed")

    def test_admission_shed_and_quota(self):
        a = resilience.Admission(1, 0, guest_quota=2, memory_quota_mib=1000)
        a.acquire(0.1)
        with self.assertRaises(errors.OpError) as cm:
            a.acquire(0.1)
        self.assertEqual(cm.exception.code, "PK_FULL_VM_OVERLOADED")
        a.release()
        a.reserve("t", 400)
        a.reserve("t", 400)
        with self.assertRaises(errors.OpError):
            a.reserve("t", 100)
        a.reserve("u", 900)   # other tenant unaffected (fairness)
        with self.assertRaises(errors.OpError):
            a.reserve("u", 200)


class FencingTest(unittest.TestCase):
    def test_stale_controller_rejected(self):
        t = [0.0]
        lt = fencing.LeaseTable(ttl_s=10, clock=lambda: t[0])
        e1 = lt.acquire("c1")
        lt.check("c1", e1)
        with self.assertRaises(errors.OpError):
            lt.acquire("c2")
        t[0] = 11
        e2 = lt.acquire("c2")
        self.assertGreater(e2, e1)
        with self.assertRaises(errors.OpError):
            lt.check("c1", e1)   # partitioned old controller wakes up
        lt.check("c2", e2)


class TelemetryTest(unittest.TestCase):
    def test_redaction_cardinality_trace(self):
        lg = telemetry.Logger("n1")
        r = lg.log("info", "boot", "m", tenant="acme", token="abc", nested={"password": "p"})
        self.assertEqual(r["token"], "[REDACTED]")
        self.assertEqual(r["nested"]["password"], "[REDACTED]")
        self.assertNotIn("acme", json.dumps(r))
        m = telemetry.Metrics()
        for i in range(telemetry.MAX_SERIES + 50):
            m.inc("x", {"i": str(i)})
        self.assertEqual(m.snapshot()["dropped_series"], 50)
        tid, sid = telemetry.parse_traceparent("00-" + "1" * 32 + "-" + "2" * 16 + "-01")
        self.assertEqual((tid, sid), ("1" * 32, "2" * 16))
        self.assertEqual(len(telemetry.parse_traceparent("garbage")[0]), 32)

    def test_sink_failure_is_noncritical(self):
        def bad(_):
            raise OSError("collector down")
        lg = telemetry.Logger("n1", sink=bad)
        lg.log("info", "op", "m")
        self.assertEqual(lg.sink_failures, 1)

    def test_explain(self):
        d = telemetry.Decisions()
        did = d.record("admit", "shed", "queue full", inputs={"q": 64}, policy="max_queue")
        self.assertIn("queue full", d.explain(did))


class CompatTest(unittest.TestCase):
    def test_declared_api_covers_imports(self):
        imported = compat.imported_pk_core_symbols()
        for mod, names in imported.items():
            self.assertTrue(names <= compat.PK_CORE_API.get(mod, set()), f"{mod}: {names}")

    def test_pk_core_status_is_stable_diagnostic(self):
        r = compat.check_pk_core()
        self.assertIn(r["status"], {"ABSENT", "INCOMPATIBLE", "BLOCKED", "OK"})
        self.assertNotEqual(r["status"], "OK")   # no range is pinned in this build

    def test_negotiate(self):
        self.assertEqual(compat.negotiate({"PK_FULL_VM": [1, 2]}), {"PK_FULL_VM": 1})
        with self.assertRaises(errors.OpError) as cm:
            compat.negotiate({"PK_FULL_VM": [2]})
        self.assertEqual(cm.exception.code, "PK_FULL_VM_VERSION_UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()


class JournalRegressionTest(unittest.TestCase):
    def test_d02_non_object_record_is_corrupt_not_crash(self):
        import zlib
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.wal")
            for body in (b"[1,2]", b"7", b'{"op":"snapshot","state":[]}', b'{"op":"boot"}'):
                open(p, "wb").write(f"{zlib.crc32(body):08x}\t".encode() + body + b"\n" + body[:0])
                j = journal.Journal(p)
                with self.subTest(body=body):
                    try:
                        j.state()
                    except journal.JournalCorrupt:
                        pass
