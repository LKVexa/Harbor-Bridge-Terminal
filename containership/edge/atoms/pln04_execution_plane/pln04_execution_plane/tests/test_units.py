"""Unit/contract tests for errors (M43), validation (M35), config (M17), store (M11/M31),
resilience (M15/M45), observability (M19-M21/M36/M44), transport (M34) and the
provider contract suite incl. the real POSIX process provider (M03/M10/M24/M40)."""
from __future__ import annotations

import io
import json
import os
import random
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from helpers import AUD, FakeClock, dev_plane, keyring, pkg, request
from pln04_execution_plane import errors, observability, policy, providers, resilience, security, store, transport, validation
from pln04_execution_plane.errors import PlaneError

Z = "sha256:" + "0" * 64


class ErrorTaxonomyTest(unittest.TestCase):
    def test_codes_are_unique_categorised_and_documented(self):
        self.assertEqual(len(errors.ERROR_CODES), len(errors._SPECS))
        doc = open(os.path.join(os.path.dirname(pkg.__file__), "docs", "ERRORS.md"), encoding="utf-8").read()
        for code, spec in errors.ERROR_CODES.items():
            self.assertRegex(code, r"^PLN04-[A-Z]+-\d{3}$")
            self.assertIn(code, doc)
            if spec.retry_after_allowed:
                self.assertTrue(spec.retryable or spec.category == "policy")

    def test_legacy_mapping_and_sanitised_public_body(self):
        self.assertEqual(errors.from_exception(pkg.NoSufficientTier("x")).code, "PLN04-POL-001")
        self.assertEqual(errors.from_exception(pkg.CapacityExceeded("x")).code, "PLN04-CAP-001")
        self.assertEqual(errors.from_exception(KeyError("secret")).code, "PLN04-INT-001")
        err = PlaneError("PLN04-VAL-001", details={"field": "x", "password": "hunter2"})
        self.assertNotIn("password", json.dumps(err.public()))
        with self.assertRaises(ValueError):
            PlaneError("PLN04-VAL-001", retry_after_s=1)
        with self.assertRaises(ValueError):
            PlaneError("NOPE")


class ValidationTest(unittest.TestCase):
    def test_every_shipped_schema_loads_under_the_strict_keyword_set(self):
        for name in validation.SCHEMA_FILES:
            validation.load_schema(name)

    def test_bounds_and_hostile_documents(self):
        good = json.dumps(request())
        validation.parse(good, "PK_ADMISSION/1")
        for bad in ("[]", "{", '{"a":1,"a":2}', "NaN", "x" * (validation.MAX_DOCUMENT_BYTES + 1),
                    "[" * 100 + "]" * 100, json.dumps({**request(), "extra": 1}),
                    json.dumps({**request(), "trust_class": "root"}), json.dumps({**request(), "workload": ""}),
                    json.dumps({**request(), "retryable": 1})):
            with self.assertRaises(PlaneError):
                validation.parse(bad, "PK_ADMISSION/1")

    def test_unknown_schema_and_canonical_dump(self):
        with self.assertRaises(PlaneError):
            validation.load_schema("PK_NOPE/1")
        out = validation.dumps(request(), "PK_ADMISSION/1")
        self.assertEqual(out, json.dumps(json.loads(out), sort_keys=True, separators=(",", ":")))


class ConfigTest(unittest.TestCase):
    def test_defaults_generation_and_rejections(self):
        a, b = policy.PlaneConfig.load(), policy.PlaneConfig.load()
        self.assertEqual(a.generation, b.generation)
        self.assertNotEqual(a.generation, policy.PlaneConfig.load({"site": "x"}).generation)
        for bad in ({"profile": "prod"}, {"limits": {"max_instances": 1, "per_tenant_limit": 2}},
                    {"residency": {"t": []}}, {"coresidency": {"hostile": "yolo"}}, {"unknown": 1},
                    {"limits": {"headroom": 0.95}}):
            with self.assertRaises(PlaneError):
                policy.PlaneConfig.load(bad)

    def test_example_configs_validate(self):
        root = os.path.join(os.path.dirname(pkg.__file__), "config")
        for name in sorted(os.listdir(root)):
            policy.PlaneConfig.from_file(os.path.join(root, name))


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_cas_persistence_torn_tail_and_corruption(self):
        path = os.path.join(self.d, "s")
        s = store.FileStateStore(path, fsync=False)
        self.assertEqual(s.cas("a", 0, {"v": 1}), 1)
        with self.assertRaises(PlaneError) as ctx:
            s.cas("a", 0, {"v": 2})
        self.assertEqual(ctx.exception.code, "PLN04-STATE-001")
        s.cas("a", 1, {"v": 2})
        s.cas("b", 0, [1])
        s.delete("b", 1)
        with self.assertRaises(PlaneError):
            store.FileStateStore(path, fsync=False)            # single writer (flock)
        s.close()
        with open(os.path.join(path, "state.wal.jsonl"), "a") as fh:
            fh.write('{"key":"a","ver":3,"val')                # torn final record
        s2 = store.FileStateStore(path, fsync=False)
        self.assertTrue(s2.recovered_torn_record)
        self.assertEqual(s2.get("a"), (2, {"v": 2}))
        self.assertIsNone(s2.get("b"))
        s2.close()
        lines = open(os.path.join(path, "state.wal.jsonl")).read().splitlines()
        lines[0] = lines[0].replace('"v":1', '"v":9')
        open(os.path.join(path, "state.wal.jsonl"), "w").write("\n".join(lines) + "\n")
        with self.assertRaises(PlaneError) as ctx:
            store.FileStateStore(path, fsync=False)
        self.assertEqual(ctx.exception.code, "PLN04-STATE-003")

    def test_compaction_backup_restore_and_migration(self):
        s = store.FileStateStore(os.path.join(self.d, "s"), fsync=False)
        for i in range(50):
            s.cas(f"k{i}", 0, {"i": i})
        s.compact()
        manifest = s.backup(os.path.join(self.d, "backup.json"))
        self.assertEqual(manifest["records"], 50)
        s.cas("k0", 1, {"i": "changed"})
        self.assertEqual(s.restore(os.path.join(self.d, "backup.json")), 50)
        self.assertEqual(s.get("k0"), (1, {"i": 0}))
        s.close()
        s = store.FileStateStore(os.path.join(self.d, "s"), fsync=False)
        self.assertEqual(len(list(s.items("k"))), 50)
        s.close()
        doc = json.load(open(os.path.join(self.d, "backup.json")))
        doc["data"]["k1"][1]["i"] = 999
        json.dump(doc, open(os.path.join(self.d, "backup.json"), "w"))
        s = store.FileStateStore(os.path.join(self.d, "s2"), fsync=False)
        with self.assertRaises(PlaneError):
            s.restore(os.path.join(self.d, "backup.json"))
        s.close()
        migrated = store.migrate({"x": {"a": 1}})
        self.assertEqual(migrated["data"]["x"], [1, {"a": 1}])
        with self.assertRaises(PlaneError):
            store.migrate({"format": "PK_PLN04_STATE/99"})


class ResilienceTest(unittest.TestCase):
    def test_retry_only_retryable_codes_with_budget(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise PlaneError("PLN04-PROV-001")
            return "ok"

        sleeps = []
        self.assertEqual(resilience.retry(flaky, resilience.RetryPolicy(max_attempts=5), sleep=sleeps.append, rng=random.Random(1)), "ok")
        self.assertEqual(len(sleeps), 2)
        self.assertTrue(all(0 <= s <= 2.0 for s in sleeps))
        calls.clear()
        with self.assertRaises(PlaneError):
            resilience.retry(lambda: (_ for _ in ()).throw(PlaneError("PLN04-POL-001")), resilience.RetryPolicy(), sleep=sleeps.append)
        with self.assertRaises(ValueError):
            resilience.RetryPolicy(max_attempts=0)

    def test_circuit_breaker_open_half_open_close(self):
        clock = FakeClock(0)
        cb = resilience.CircuitBreaker("p", threshold=2, reset_s=10, clock=clock)
        fail = lambda: (_ for _ in ()).throw(PlaneError("PLN04-PROV-001"))
        for _ in range(2):
            with self.assertRaises(PlaneError):
                cb.call(fail)
        self.assertEqual(cb.state, "open")
        with self.assertRaises(PlaneError) as ctx:
            cb.call(lambda: 1)
        self.assertEqual(ctx.exception.code, "PLN04-DEP-001")
        clock.advance(10)
        self.assertEqual(cb.state, "half_open")
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.state, "closed")

    def test_admission_gate_backpressure_fairness_and_deadline(self):
        gate = resilience.AdmissionGate(max_inflight=1, max_queue=2, per_tenant_queue=1)
        gate.acquire("a", time.monotonic() + 1)
        order = []

        def waiter(t):
            try:
                gate.acquire(t, time.monotonic() + 2)
                order.append(t)
                gate.release()
            except PlaneError as exc:
                order.append(exc.code)

        ths = [threading.Thread(target=waiter, args=(t,)) for t in ("b", "c")]
        [t.start() for t in ths]
        time.sleep(0.05)
        with self.assertRaises(PlaneError) as ctx:
            gate.acquire("b", time.monotonic() + 1)        # b's queue slot is full
        self.assertEqual(ctx.exception.code, "PLN04-CAP-002")
        gate.release()
        [t.join() for t in ths]
        self.assertEqual(sorted(order), ["b", "c"])
        gate.acquire("a", time.monotonic() + 1)
        with self.assertRaises(PlaneError) as ctx:
            gate.acquire("z", time.monotonic() + 0.05)
        self.assertEqual(ctx.exception.code, "PLN04-TIME-001")
        gate.release()
        self.assertEqual(gate.depth(), 0)


class ObservabilityTest(unittest.TestCase):
    def test_audit_sink_resume_anchor_and_redaction(self):
        d = tempfile.mkdtemp()
        try:
            anchor = observability.FileAnchor(os.path.join(d, "anchor"))
            sink = observability.DurableAuditSink(os.path.join(d, "a.jsonl"), anchor=anchor, anchor_every=3, fsync=False)
            for i in range(7):
                sink.append("e", {"i": i, "token": "secret-value", "note": "sk-live-ABCDEFGHIJKL"})
            sink.close()
            sink2 = observability.DurableAuditSink(os.path.join(d, "a.jsonl"), fsync=False)
            self.assertEqual(sink2.sequence, 7)
            sink2.close()
            text = open(os.path.join(d, "a.jsonl")).read()
            self.assertNotIn("secret-value", text)
            self.assertNotIn("sk-live-ABCDEFGHIJKL", text)
            ok, seq, _, _ = observability.verify_audit_file(os.path.join(d, "a.jsonl"), anchor.anchors())
            self.assertTrue(ok)
            self.assertEqual([a["sequence"] for a in anchor.anchors()], [3, 6])
        finally:
            shutil.rmtree(d)

    def test_exporter_at_least_once_and_bounded(self):
        class Flaky:
            def __init__(self):
                self.fail, self.got = True, []

            def publish(self, batch):
                if self.fail:
                    self.fail = False
                    raise OSError("down")
                self.got.extend(batch)

        sink = Flaky()
        ex = observability.EventExporter(sink, max_outbox=3)
        for i in range(3):
            ex.enqueue({"event_hash": f"h{i}"})
        with self.assertRaises(PlaneError):
            ex.enqueue({"event_hash": "h3"})
        self.assertEqual(ex.flush(), 0)
        self.assertEqual(ex.flush(), 3)
        self.assertEqual([e["event_id"] for e in sink.got], ["h0", "h1", "h2"])

    def test_metrics_logs_traces_slo_and_privacy(self):
        buf = io.StringIO()
        tel = observability.Telemetry(observability.TelemetryPolicy(), log_stream=buf)
        tel.inc("x", tier="vm")
        for v in range(200):
            tel.observe("lat", v / 100)
        tel.log("info", "admitted", tenant="acme", authorization="Bearer abc")
        rec = json.loads(buf.getvalue())
        self.assertNotEqual(rec["tenant"], "acme")
        self.assertEqual(rec["authorization"], "[REDACTED]")
        prom = tel.prometheus()
        self.assertIn('x_total{tier="vm"} 1.0', prom)
        self.assertIn('lat_bucket{le="+Inf"} 200', prom)
        tid, sampled = tel.new_trace("00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual((tid, sampled), ("a" * 32, True))
        slo = observability.LatencySlo(p50_ms=1.0, p99_ms=2.5, min_samples=100)
        self.assertEqual(slo.evaluate(tel.histogram("lat"))["status"], "MET")
        self.assertEqual(observability.LatencySlo(p50_ms=0.1).evaluate(tel.histogram("lat"))["status"], "BREACHED")
        with self.assertRaises(ValueError):
            observability.TelemetryPolicy(retention_days_audit=1, retention_days_logs=30)


class ProviderContractSuite:
    """Every provider must pass this (M03 contract tests)."""

    def make(self) -> providers.ExecutionProvider: ...

    def req(self, prov, workload="cw", epoch=1, key=None):
        cmd = self.command() if hasattr(self, "command") else ()
        return providers.ProviderRequest(workload, "t", prov.tier, Z, Z, key or f"key-{workload}-{epoch:04d}",
                                         time.monotonic_ns() + 10**10, epoch, providers.Resources(1000, 128), cmd)

    def test_contract(self):
        prov = self.make()
        self.assertTrue(prov.probe().available)
        inst = prov.start(self.req(prov))
        self.assertEqual(prov.start(self.req(prov)).provider_instance_id, inst.provider_instance_id)  # idempotent
        self.assertEqual(prov.observe("cw"), "running")
        with self.assertRaises(PlaneError):
            prov.start(self.req(prov, key="other-key-0001"))      # at most one live instance
        self.assertTrue(prov.stop("cw", 1))
        receipt = prov.zeroize("cw", 1)
        self.assertTrue(receipt.verified, receipt)
        self.assertEqual(prov.observe("cw"), "absent")
        self.assertFalse(prov.stop("cw", 1))                        # idempotent destroy
        self.assertTrue(prov.zeroize("cw", 1).verified)
        with self.assertRaises(PlaneError):
            prov.stop("cw", 0)                                      # invalid epoch
        with self.assertRaises(PlaneError):
            prov.start(providers.ProviderRequest("cw", "t", prov.tier, Z, Z, "late-key-01", 0, 2))  # deadline


class ReferenceProviderContract(ProviderContractSuite, unittest.TestCase):
    def make(self):
        return providers.ReferenceProvider("microvm")


@unittest.skipUnless(os.name == "posix" and os.path.exists("/bin/sleep"), "POSIX process provider lane")
class ProcessProviderContract(ProviderContractSuite, unittest.TestCase):
    def make(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        return providers.ProcessProvider(scratch_root=self.root)

    def command(self):
        return ("/bin/sleep", "30")

    def test_limits_are_enforced_on_the_child(self):
        prov = self.make()
        script = ("import resource,os,json;"
                  "open('limits.json','w').write(json.dumps([resource.getrlimit(resource.RLIMIT_NOFILE)[0],"
                  "resource.getrlimit(resource.RLIMIT_CORE)[0], sorted(os.environ), os.getsid(0)==os.getpid()]))")
        req = providers.ProviderRequest("lim", "t", "process", Z, Z, "key-limits-1", time.monotonic_ns() + 10**10, 1,
                                        providers.Resources(1000, 512), (sys.executable, "-c", script))
        prov.start(req)
        proc, scratch = prov._procs["lim"]
        proc.wait(timeout=20)
        nofile, core, env, own_session = json.load(open(os.path.join(scratch, "limits.json")))
        self.assertEqual((nofile, core, own_session), (64, 0, True))
        self.assertEqual(env, ["HOME", "LC_CTYPE", "PATH"] if "LC_CTYPE" in env else ["HOME", "PATH"])
        receipt = prov.zeroize("lim", 1)
        self.assertTrue(receipt.verified)
        self.assertFalse(os.path.exists(scratch))


class WasmProviderLane(unittest.TestCase):
    def test_binding_is_explicit_and_fails_closed_without_runtime(self):
        prov = providers.WasmProvider(wasmtime="")
        prov._bin = None
        cap = prov.probe()
        self.assertFalse(cap.available)
        pl, _ = dev_plane(tiers=("process",), attest=False)
        reg = providers.ProviderRegistry(allow_reference=False)
        reg.register(prov)
        from pln04_execution_plane import plane as plane_mod
        p2 = plane_mod.ExecutionPlane(policy.PlaneConfig.load(), reg)
        with self.assertRaises(PlaneError) as ctx:
            p2.attest_tier("wasm")
        self.assertEqual(ctx.exception.code, "PLN04-ATT-002")

    @unittest.skipUnless(shutil.which("wasmtime"), "declared lane: wasmtime runtime not installed")
    def test_real_wasmtime(self):  # pragma: no cover - environment dependent
        self.assertTrue(providers.WasmProvider().probe().available)


class CommandProviderTest(unittest.TestCase):
    def test_json_stdio_driver(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        driver = os.path.join(d, "driver.py")
        open(driver, "w").write(
            "import sys,json,os\nop=sys.argv[1];p=json.load(sys.stdin);st=os.path.join(%r,'state')\n"
            "alive=os.path.exists(st)\n"
            "r={'probe':{'ok':True,'available':True,'isolation':['kvm']},"
            "'start':{'ok':True,'instance_id':'vm-1'},'stop':{'ok':True},"
            "'zeroize':{'ok':True,'zeroized':True,'method':'balloon+scrub'},'observe':{'ok':True,'alive':alive}}[op]\n"
            "if op=='start': open(st,'w').close()\n"
            "if op=='stop' and alive: os.remove(st)\n"
            "print(json.dumps(r))\n" % d)
        prov = providers.CommandProvider("microvm", (sys.executable, driver), name="fc-wrapper", version="1")
        self.assertTrue(prov.probe().available)
        inst = prov.start(providers.ProviderRequest("m", "t", "microvm", Z, Z, "key-m-0001", time.monotonic_ns() + 10**10, 1))
        self.assertEqual(inst.provider_instance_id, "vm-1")
        self.assertEqual(prov.observe("m"), "running")
        prov.stop("m", 1)
        self.assertEqual(prov.zeroize("m", 1).method, "balloon+scrub")
        bad = providers.CommandProvider("vm", (sys.executable, "-c", "import sys;sys.exit(3)"), name="x", version="1")
        self.assertFalse(bad.probe().available)
        with self.assertRaises(PlaneError) as ctx:
            bad.start(providers.ProviderRequest("m", "t", "vm", Z, Z, "key-m-0002", time.monotonic_ns() + 10**10, 1))
        self.assertEqual(ctx.exception.code, "PLN04-PROV-001")


class TransportTest(unittest.TestCase):
    def setUp(self):
        ring = keyring()
        self.signer = ring.signer("k1")
        clock = security.TrustedClock()
        self.pl, _ = dev_plane(authenticator=security.Authenticator({"HS256": ring}, clock, audience=AUD))
        self.server, _ = transport.serve(self.pl)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, method, path, body=None, token=None, ctype="application/json"):
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", ctype)
        if token:
            req.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
                return resp.status, dict(resp.headers), raw
        except urllib.error.HTTPError as err:
            return err.code, dict(err.headers), err.read()

    def tok(self, caps, tenant="t1"):
        return security.issue_actor_token(self.signer, subject="svc", tenant=tenant, caps=caps, audience=AUD)

    def test_end_to_end(self):
        t = self.tok(["admission:create", "admission:teardown", "catalogue:read", "plane:read"])
        status, _, body = self.call("POST", "/v1/admissions", request("w1", trust_class="first-party"), t)
        self.assertEqual((status, json.loads(body)["tier"]), (200, "wasm"))
        status, _, body = self.call("GET", "/v1/catalogue", token=t)
        validation.validate(json.loads(body), "PK_TIER_CATALOGUE/1")
        status, _, body = self.call("GET", "/metrics", token=t)
        self.assertIn(b"pln04_admissions_total", body)
        self.assertEqual(self.call("GET", "/readyz")[0], 200)
        status, _, body = self.call("GET", "/v1/explain/w1", token=t)
        self.assertEqual(json.loads(body)["record"]["tier"], "wasm")
        status, _, body = self.call("DELETE", "/v1/admissions/w1?tenant=t1", token=t)
        self.assertEqual(json.loads(body)["removed"], True)

    def test_error_mapping(self):
        t = self.tok(["admission:create"])
        cases = [
            (("POST", "/v1/admissions", request("w1")), None, 401, "PLN04-AUTHN-001"),
            (("POST", "/v1/admissions", b"{bad"), t, 400, "PLN04-VAL-001"),
            (("POST", "/v1/admissions", request("w1", trust_class="nope")), t, 400, "PLN04-VAL-001"),
            (("GET", "/v1/catalogue", None), t, 403, "PLN04-AUTHZ-001"),
            (("POST", "/v1/admissions", request("w1", tenant="t2")), t, 403, "PLN04-AUTHZ-001"),
        ]
        for (method, path, body), tok, status, code in cases:
            got, _, raw = self.call(method, path, body, tok)
            self.assertEqual((got, json.loads(raw)["error_code"]), (status, code))
        got, _, raw = self.call("POST", "/v1/admissions", b"{}", t, ctype="text/plain")
        self.assertEqual(got, 415)
        self.pl.emergency_disable("test")
        got, headers, raw = self.call("POST", "/v1/admissions", request("w9"), t)
        self.assertEqual((got, json.loads(raw)["error_code"]), (503, "PLN04-POL-006"))
        self.assertEqual(headers.get("Retry-After"), "30")


class CapabilityDiscoveryTest(unittest.TestCase):
    def test_discovery_and_tier_gating(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        open(os.path.join(d, "cpuinfo"), "w").write("flags : fpu vmx sse\n")
        rep = security.discover_local_capabilities("n", os.path.join(d, "cpuinfo"))
        self.assertIn("virtualization", rep.features)
        self.assertTrue(rep.supports("unikernel"))
        self.assertFalse(security.CapabilityReport("n", "x86_64", frozenset({"virtualization"}), None).supports("vm"))
        pl, _ = dev_plane(tiers=("process", "vm"), attest=False,
                          capability_report=security.CapabilityReport("n", "x86_64", frozenset(), None))
        pl.attest_tier("process")
        with self.assertRaises(PlaneError):
            pl.attest_tier("vm")


if __name__ == "__main__":
    unittest.main()
