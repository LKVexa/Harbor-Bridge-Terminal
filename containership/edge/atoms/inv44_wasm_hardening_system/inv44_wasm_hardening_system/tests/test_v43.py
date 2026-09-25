"""INV-44 v4.3.0 tests: verifier, capability, tenant gateway, audit log, config,
observability, provenance, schemas, lifecycle, faults and the release gate.

stdlib unittest only. Each security property has a positive case AND a
negative case; a refusal-only test is not accepted as proof of a gate.
"""
from __future__ import annotations

import base64
import copy
import importlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG_DIR.parent))
sys.path.insert(0, str(PKG_DIR / "tests"))
pkg = importlib.import_module(PKG_DIR.name)
sub = lambda m: importlib.import_module(f"{PKG_DIR.name}.{m}")
runtime, errors, wv, cap, gw, al, obs, cfg, schema, prov, lc, rg = (
    sub(m) for m in ("runtime", "errors", "wasm_verify", "capability", "gateway", "audit_log",
                     "observability", "config", "schema", "provenance", "lifecycle", "release_gate"))
import wasm_fixtures as fx  # noqa: E402

KEY = b"k" * 32
TC = wv.Toolchain("swivel-clang", "0.0-test", "a" * 64)
FULL = runtime.REQUIRED_HARDENING


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def receipt(data, *, hardening=FULL, kid="k1", tc=TC, at=1_000_000):
    return wv.issue_receipt(data, toolchain=tc, hardening=hardening,
                            keyring=wv.Keyring({kid: KEY}), key_id=kid, issued_at=at)


class VerifierTest(unittest.TestCase):
    def test_valid_module_parses_and_lists_imports(self):
        s = wv.parse_module(fx.module(imports=(("env", "log"),)))
        self.assertEqual(s.imports, (("env", "log", "func"),))
        self.assertEqual((s.memory_min_pages, s.memory_max_pages), (1, 4))
        self.assertIn("code", s.sections)

    def test_malformed_modules_are_refused(self):
        good = fx.module()
        cases = {
            "magic": b"\x00ASM" + good[4:],
            "version": good[:4] + b"\x02\x00\x00\x00" + good[8:],
            "truncated": good[:-1],
            "trailing_garbage": good + b"\x01",
            "unknown_section": good + fx.section(99, b""),
            "out_of_order": good + fx.section(1, b"\x00"),
            "duplicate": good[:8] + fx.section(1, b"\x00") + fx.section(1, b"\x00"),
            "leb_overflow": good[:8] + b"\x01\xff\xff\xff\xff\x7f",
            "two_memories": good[:8] + fx.section(5, b"\x02\x00\x01\x00\x01"),
            "memory64": good[:8] + fx.section(5, b"\x01\x04\x01"),
            "not_bytes": "text",
        }
        for label, data in cases.items():
            with self.subTest(label), self.assertRaises(wv.MalformedModule):
                wv.parse_module(data)

    def test_receipt_round_trip(self):
        data = fx.module()
        s = wv.verify_receipt(data, receipt(data), keyring=wv.Keyring({"k1": KEY}),
                              approved_toolchains=[TC.ident()], max_age_s=60, now=1_000_010)
        self.assertEqual(s.sha256, wv.parse_module(data).sha256)

    def test_receipt_refusals(self):
        data = fx.module()
        ring = wv.Keyring({"k1": KEY})
        ok = [TC.ident()]
        r = receipt(data)
        swapped = fx.module(imports=(("env", "x"),))
        forged = copy.deepcopy(r); forged["body"]["hardening"] = sorted(FULL)[:-1]
        partial = receipt(data, hardening=FULL - {"cfi"})
        cases = [
            ("other bytes", swapped, r, ok, wv.ReceiptInvalid),
            ("forged body", data, forged, ok, wv.ReceiptInvalid),
            ("bad mac", data, {**r, "mac": "0" * 64}, ok, wv.ReceiptInvalid),
            ("unknown key", data, receipt(data, kid="k9"), ok, wv.ReceiptInvalid),
            ("unapproved toolchain", data, r, [], wv.ToolchainUnapproved),
            ("partial hardening", data, partial, ok, wv.ReceiptInvalid),
            ("extra field", data, {**r, "x": 1}, ok, wv.ReceiptInvalid),
        ]
        for label, d, rc, tcs, exc in cases:
            with self.subTest(label), self.assertRaises(exc):
                wv.verify_receipt(d, rc, keyring=ring, approved_toolchains=tcs)
        with self.assertRaises(wv.ReceiptInvalid):
            wv.verify_receipt(data, r, keyring=ring, approved_toolchains=ok, max_age_s=60, now=1_000_100)
        with self.assertRaises(wv.ReceiptInvalid):  # issued in the future
            wv.verify_receipt(data, r, keyring=ring, approved_toolchains=ok, max_age_s=60, now=999_000)

    def test_keyring_hides_secrets_and_rejects_short_keys(self):
        self.assertNotIn("kkkk", repr(wv.Keyring({"k1": KEY})))
        with self.assertRaises(ValueError):
            wv.Keyring({"k1": b"short"})


class ParserFuzzTest(unittest.TestCase):
    """Seeded mutation fuzzing (C085): parse_module either returns a summary or
    raises MalformedModule — never any other exception, never a hang."""

    def test_mutations_never_escape_the_error_contract(self):
        import random
        rng = random.Random(44)
        seeds = [fx.module(), fx.module(imports=(("env", "a"), ("wasi", "b"))), fx.module(mem=None)]
        outcomes = {"ok": 0, "refused": 0}
        for i in range(6000):
            data = bytearray(rng.choice(seeds))
            for _ in range(rng.randint(1, 6)):
                op = rng.random()
                pos = rng.randrange(len(data))
                if op < 0.5:
                    data[pos] = rng.randrange(256)
                elif op < 0.75:
                    del data[pos:pos + rng.randint(1, 4)]
                else:
                    data[pos:pos] = bytes(rng.randrange(256) for _ in range(rng.randint(1, 4)))
                if not data:
                    data = bytearray(b"\x00")
            try:
                wv.parse_module(bytes(data))
                outcomes["ok"] += 1
            except wv.MalformedModule:
                outcomes["refused"] += 1
        self.assertEqual(sum(outcomes.values()), 6000)
        self.assertGreater(outcomes["refused"], 0)


@unittest.skipIf(shutil.which("node") is None, "lane NODE_WASM not available: node not on PATH")
class IndependentValidatorLane(unittest.TestCase):
    """Cross-check: V8's WebAssembly.validate agrees with parse_module on fixtures."""

    def test_v8_agrees_on_valid_fixtures(self):
        mods = [fx.module(), fx.module(imports=(("env", "a"), ("env", "b"))), fx.module(mem=None)]
        js = ("const l=require('fs').readFileSync(0,'utf8').trim().split('\\n');"
              "console.log(JSON.stringify(l.map(x=>WebAssembly.validate(Buffer.from(x,'base64')))))")
        out = subprocess.run(["node", "-e", js], input="\n".join(base64.b64encode(m).decode() for m in mods),
                             capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(out.stdout), [True, True, True])
        for m in mods:
            wv.parse_module(m)


def make_world(tmp, *, tenant="t1", clock=None, ceiling=8, revoked=None, max_inflight=4, max_instances=4):
    clock = clock or Clock()
    authn = cap.Authenticator(b"a" * 32)
    authz = cap.Authorizer(b"z" * 32, clock=clock, revoked=revoked)
    audit = al.AuditLog(pathlib.Path(tmp) / "audit.jsonl", mac_key=b"m" * 32, clock=clock)
    metrics = obs.Metrics()
    engine = runtime.Engine("swivel-ref", FULL, memory_page_ceiling=ceiling)
    gate = gw.TenantGateway(tenant=tenant, engine=engine, authorizer=authz, keyring=wv.Keyring({"k1": KEY}),
                            approved_toolchains=[TC.ident()], audit=audit, metrics=metrics,
                            admission=gw.Admission(max_instances, max_inflight), clock=clock)
    return authn, authz, audit, metrics, gate, clock


def login(authn, subject="alice", tenant="t1"):
    return authn.authenticate(subject, tenant, service=False,
                              credential=authn.credential(subject, tenant, service=False))


class CapabilityAndGatewayTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.authn, self.authz, self.audit, self.metrics, self.gate, self.clock = make_world(self.tmp)
        self.p = login(self.authn)
        self.tok = self.authz.grant(self.p, token_id="tok1", operations={"instantiate"}, imports={"env.log"})
        self.data = fx.module(imports=(("env", "log"),))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_positive_path_admits_and_audits(self):
        inst = self.gate.instantiate(self.p, self.tok, "m1", self.data, receipt(self.data), fuel=5)
        self.assertEqual(inst.step(5), 0)
        self.assertEqual(self.metrics.value("instances", tenant="t1"), 1)
        self.assertEqual(self.audit.verify(expected_head=self.audit.head()), 1)
        rec = json.loads((pathlib.Path(self.tmp) / "audit.jsonl").read_text().splitlines()[0])
        self.assertEqual(rec["outcome"], "success")
        self.assertTrue(all(c["passed"] for c in rec["detail"]["explanation"]["checks"]))

    def test_bare_principal_and_bad_credentials_are_refused(self):
        with self.assertRaises(cap.AuthenticationFailed):
            cap.Principal("alice", "t1", False)
        with self.assertRaises(cap.AuthenticationFailed):
            self.authn.authenticate("alice", "t1", service=False, credential="0" * 64)

    def test_refusals_are_structured_audited_and_counted(self):
        other = login(self.authn, "bob", "t2")
        other_tok = self.authz.grant(other, token_id="tok2", operations={"instantiate"}, imports={"env.log"})
        no_import = self.authz.grant(self.p, token_id="tok3", operations={"instantiate"})
        wrong_op = self.authz.grant(self.p, token_id="tok4", operations={"read_metrics"})
        cases = [
            ("cross tenant", other, other_tok, self.data, receipt(self.data), "WH-TENANT-MISMATCH"),
            ("ambient import", self.p, no_import, self.data, receipt(self.data), "WH-AMBIENT-IMPORT"),
            ("operation not granted", self.p, wrong_op, self.data, receipt(self.data), "WH-AUTHZ-DENIED"),
            ("stolen token", other, self.tok, self.data, receipt(self.data), "WH-AUTHZ-DENIED"),
            ("receipt for other bytes", self.p, self.tok, self.data, receipt(fx.module()), "WH-RECEIPT-INVALID"),
            ("unbounded memory", self.p, self.tok, fx.module(imports=(("env", "log"),), mem=(1, None)),
             receipt(fx.module(imports=(("env", "log"),), mem=(1, None))), "WH-MEMORY-CEILING"),
        ]
        for label, pr, tk, data, rc, code in cases:
            with self.subTest(label):
                with self.assertRaises(Exception) as ctx:
                    self.gate.instantiate(pr, tk, f"m-{label}", data, rc, fuel=5)
                self.assertEqual(errors.classify(ctx.exception)["code"], code)
        self.assertEqual(self.audit.verify(), len(cases))
        self.assertEqual(self.metrics.value("instances", tenant="t1"), 0)
        self.assertGreaterEqual(self.metrics.value("tenant_violations", tenant="t1", code="WH-TENANT-MISMATCH"), 1)

    def test_expiry_revocation_and_dependency_loss_fail_closed(self):
        self.clock.t += 10_000
        with self.assertRaises(cap.CapabilityExpired):
            self.authz.authorize(self.p, self.tok, "instantiate")
        authz = cap.Authorizer(b"z" * 32, clock=Clock(), revoked=lambda: {"tok1"})
        tok = authz.grant(self.p, token_id="tok1", operations={"instantiate"})
        with self.assertRaises(cap.CapabilityExpired):
            authz.authorize(self.p, tok, "instantiate")

        def broken():
            raise OSError("revocation service down")
        authz = cap.Authorizer(b"z" * 32, clock=Clock(), revoked=broken)
        tok = authz.grant(self.p, token_id="tok5", operations={"instantiate"})
        with self.assertRaises(cap.DependencyUnavailable):
            authz.authorize(self.p, tok, "instantiate")

    def test_token_tampering_is_detected(self):
        forged = cap.CapabilityToken(**{**cap._as_kwargs(self.tok), "operations": frozenset({"instantiate", "configure"})})
        with self.assertRaises(cap.AuthorizationDenied):
            self.authz.authorize(self.p, forged, "configure")

    def test_duplicate_execution_and_quota(self):
        self.gate.instantiate(self.p, self.tok, "dup", self.data, receipt(self.data), fuel=5)
        with self.assertRaises(errors.HardeningError):
            self.gate.instantiate(self.p, self.tok, "dup", self.data, receipt(self.data), fuel=5)
        for i in range(3):
            self.gate.instantiate(self.p, self.tok, f"q{i}", self.data, receipt(self.data), fuel=5)
        with self.assertRaises(gw.Overloaded):
            self.gate.instantiate(self.p, self.tok, "q9", self.data, receipt(self.data), fuel=5)
        self.gate.release("q0")
        self.gate.instantiate(self.p, self.tok, "q9", self.data, receipt(self.data), fuel=5)


class AuditLogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.path = self.tmp / "a.jsonl"
        self.log = al.AuditLog(self.path, mac_key=b"m" * 32, clock=Clock())
        for i in range(5):
            self.log.append("e", actor="alice", outcome="success", n=i, token="SECRETVALUE")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_chain_verifies_and_secrets_are_redacted(self):
        self.assertEqual(self.log.verify(expected_head=self.log.head()), 5)
        self.assertNotIn("SECRETVALUE", self.path.read_text())

    def test_reopen_continues_chain(self):
        again = al.AuditLog(self.path, mac_key=b"m" * 32, clock=Clock())
        again.append("e", actor="alice", outcome="success")
        self.assertEqual(again.verify(), 6)

    def test_tampering_is_detected(self):
        lines = self.path.read_text().splitlines()
        mutations = {
            "edit": lines[:2] + [lines[2].replace('"n": 2', '"n": 7')] + lines[3:],
            "delete_middle": lines[:2] + lines[3:],
            "reorder": [lines[1], lines[0]] + lines[2:],
            "garbage": lines + ["{not json"],
        }
        for label, content in mutations.items():
            with self.subTest(label):
                self.path.write_text("\n".join(content) + "\n")
                with self.assertRaises(al.AuditChainBroken):
                    probe = object.__new__(al.AuditLog)
                    probe.path, probe._mac_key = self.path, b"m" * 32
                    probe.verify()

    def test_tail_truncation_needs_and_uses_external_anchor(self):
        head = self.log.head()
        lines = self.path.read_text().splitlines()
        self.path.write_text("\n".join(lines[:3]) + "\n")
        probe = object.__new__(al.AuditLog)
        probe.path, probe._mac_key = self.path, b"m" * 32
        self.assertEqual(probe.verify(), 3)  # the chain alone cannot see it — documented limit
        with self.assertRaises(al.AuditChainBroken):
            probe.verify(expected_head=head)

    def test_rehashed_forgery_without_mac_key_is_detected(self):
        lines = [json.loads(l) for l in self.path.read_text().splitlines()]
        lines[0]["detail"]["n"] = 99
        body = {k: v for k, v in lines[0].items() if k != "hash"}
        lines[0]["hash"] = __import__("hashlib").sha256(al._canon(body)).hexdigest()
        self.path.write_text("\n".join(json.dumps(l, sort_keys=True) for l in lines) + "\n")
        probe = object.__new__(al.AuditLog)
        probe.path, probe._mac_key = self.path, b"m" * 32
        with self.assertRaises(al.AuditChainBroken):
            probe.verify()


def config_doc(version=1, parent=None, **over):
    doc = {
        "interface": "PK_WASM_HARDENING/1", "engine": "swivel-ref", "tenant": "t1", "environment": "test",
        "required_features": sorted(FULL), "active_features": sorted(FULL), "memory_page_ceiling": 16,
        "default_fuel": 1000, "approved_toolchains": [TC.ident()],
        "provenance": {"author": "alice", "version": version, "created_at": 1, "reason": "initial",
                       "parent_digest": parent},
    }
    doc.update(over)
    return doc


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = cfg.ConfigStore(self.tmp, clock=Clock())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_propose_activate_rollback(self):
        d1 = config_doc()
        self.store.propose(d1)
        self.store.activate(1, expected_active=None, activated_by="alice")
        d2 = config_doc(2, cfg.digest(d1), memory_page_ceiling=4)
        self.store.propose(d2)
        self.store.activate(2, expected_active=1, activated_by="alice")
        self.assertEqual(self.store.engine()[0].memory_page_ceiling, 4)
        self.store.rollback(1, activated_by="alice")
        self.assertEqual(self.store.engine()[0].memory_page_ceiling, 16)
        self.assertEqual(self.store.versions(), [1, 2])  # history never rewritten

    def test_invalid_and_partial_configs_are_refused(self):
        bad = [config_doc(active_features=sorted(FULL - {"cfi"})), config_doc(extra=1),
               config_doc(memory_page_ceiling=-1), config_doc(environment="moon"),
               config_doc(required_features=sorted(FULL)[:5])]
        for d in bad:
            with self.subTest(d=str(d)[:60]), self.assertRaises(cfg.ConfigInvalid):
                self.store.propose(d)

    def test_cas_conflict_parent_chain_and_tamper(self):
        d1 = config_doc(); self.store.propose(d1)
        self.store.activate(1, expected_active=None, activated_by="a")
        with self.assertRaises(cfg.ConfigConflict):
            self.store.activate(1, expected_active=None, activated_by="a")
        with self.assertRaises(cfg.ConfigConflict):
            self.store.propose(config_doc(2, "0" * 64))
        with self.assertRaises(cfg.ConfigConflict):
            self.store.propose(config_doc(5, cfg.digest(d1)))
        p = pathlib.Path(self.tmp) / "versions" / "000001.json"
        p.write_text(p.read_text().replace('"memory_page_ceiling":16', '"memory_page_ceiling":17'))
        with self.assertRaises(cfg.ConfigInvalid):
            self.store.engine()

    def test_crash_mid_activation_leaves_old_pointer(self):
        self.store.propose(config_doc())
        self.store.activate(1, expected_active=None, activated_by="a")
        (pathlib.Path(self.tmp) / "ACTIVE.tmp").write_text("{partial")  # simulated crash before replace
        self.assertEqual(self.store.active()["version"], 1)
        self.store.engine()


class SchemaTest(unittest.TestCase):
    def test_schemas_are_self_consistent_and_enforced(self):
        h = schema.load("pk_wasm_hardening.v1.schema.json")
        i = schema.load("pk_wasm_instance.v1.schema.json")
        self.assertEqual(schema.validate(config_doc(), h), [])
        self.assertTrue(schema.validate({**config_doc(), "interface": "PK_WASM_HARDENING/2"}, h))
        req = {"interface": "PK_WASM_INSTANCE/1", "kind": "request", "tenant": "t1", "module": "m",
               "module_sha256": "a" * 64, "fuel": 10, "pages": 1, "deadline_ms": 50, "idempotency_key": "k"}
        self.assertEqual(schema.validate(req, i), [])
        for bad in ({**req, "fuel": 0}, {**req, "fuel": True}, {**req, "state": "zombie"},
                    {**req, "surprise": 1}, {**req, "module_sha256": "XYZ"}):
            with self.subTest(bad=bad):
                self.assertTrue(schema.validate(bad, i))

    def test_unsupported_keyword_is_an_error_not_a_pass(self):
        self.assertTrue(schema.validate(1, {"type": "integer", "multipleOf": 2}))

    def test_every_error_code_documented_in_schema_pattern(self):
        import re
        for code in errors.CODES:
            self.assertRegex(code, r"WH-[A-Z-]+")
        self.assertTrue(all(c.outcome in errors.OUTCOMES for c in errors.CODES.values()))


class LifecycleTest(unittest.TestCase):
    def test_transitions(self):
        lc.check_transition("requested", "admitted")
        for src, dst in (("terminated", "running"), ("refused", "admitted"), ("running", "requested")):
            with self.subTest(f"{src}->{dst}"), self.assertRaises(errors.HardeningError):
                lc.check_transition(src, dst)

    def test_retry_only_retryable(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise errors.HardeningError("busy", code="WH-OVERLOADED")
            return "ok"
        self.assertEqual(lc.retry(flaky, sleep=lambda s: None), "ok")
        calls.clear()

        def terminal():
            calls.append(1)
            raise errors.HardeningError("no", code="WH-AUTHZ-DENIED")
        with self.assertRaises(errors.HardeningError):
            lc.retry(terminal, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)


class ObservabilityTest(unittest.TestCase):
    def test_exposition_and_logger(self):
        m = obs.Metrics()
        m.inc("hardening_refusals", feature="cfi")
        m.observe("instantiate_seconds", 0.002, tenant="t1")
        text = m.exposition()
        self.assertIn('inv44_hardening_refusals{feature="cfi"} 1', text)
        self.assertIn('inv44_instantiate_seconds_bucket{tenant="t1",le="+Inf"} 1', text)
        with self.assertRaises(KeyError):
            m.inc("made_up")
        buf = io.StringIO()
        obs.StructuredLogger(buf, clock=Clock()).log("warn", "refuse", tenant="t1\nforged", secret="x")
        rec = json.loads(buf.getvalue())
        self.assertEqual(rec["detail"]["secret"], "[REDACTED]")
        self.assertEqual(len(buf.getvalue().strip().splitlines()), 1)  # newline in label cannot split the record

    def test_every_contract_signal_is_declared(self):
        declared = set(obs.CONTRACT_SIGNALS)
        self.assertEqual(declared, {"instances", "hardening_refusals", "verification_failures",
                                    "fuel_exhaustions", "memory_growth_refusals"})


class ProvenanceTest(unittest.TestCase):
    def test_sign_verify_and_detect_drift(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            (tmp / "a.py").write_text("x = 1\n")
            st = prov.statement(tmp, version="4.3.0", builder_id="local", invocation={}, dependencies=[])
            env = prov.sign(st, key=KEY, key_id="k1")
            self.assertEqual(prov.verify(env, keys={"k1": KEY}, root=tmp)["subject"][0]["name"], "a.py")
            with self.assertRaises(ValueError):
                prov.verify(env, keys={"k1": b"q" * 32})
            (tmp / "a.py").write_text("x = 2\n")
            with self.assertRaises(ValueError):
                prov.verify(env, keys={"k1": KEY}, root=tmp)
        finally:
            shutil.rmtree(tmp)


class FaultInjectionTest(unittest.TestCase):
    """Component 17, process-local scope: faults inside one process only."""

    def test_audit_write_failure_refuses_instantiation(self):
        tmp = tempfile.mkdtemp()
        try:
            authn, authz, audit, metrics, gate, clock = make_world(tmp)
            p = login(authn)
            tok = authz.grant(p, token_id="t", operations={"instantiate"})
            data = fx.module()
            audit.path = pathlib.Path(tmp) / "no-such-dir" / "\0bad"  # unwritable
            with self.assertRaises(Exception):
                gate.instantiate(p, tok, "m", data, receipt(data), fuel=5)
            self.assertEqual(metrics.value("instances", tenant="t1"), 0)
        finally:
            shutil.rmtree(tmp)

    def test_clock_failure_fails_closed(self):
        def dead():
            raise OSError("clock")
        authz = cap.Authorizer(b"z" * 32, clock=dead)
        authn = cap.Authenticator(b"a" * 32)
        p = login(authn)
        tok = cap.Authorizer(b"z" * 32, clock=Clock()).grant(p, token_id="t", operations={"instantiate"})
        with self.assertRaises(cap.DependencyUnavailable):
            authz.authorize(p, tok, "instantiate")

    def test_admission_sheds_under_concurrent_burst(self):
        tmp = tempfile.mkdtemp()
        try:
            authn, authz, audit, metrics, gate, clock = make_world(tmp, max_inflight=2, max_instances=100)
            p = login(authn)
            tok = authz.grant(p, token_id="t", operations={"instantiate"})
            data = fx.module(); rc = receipt(data)
            results = []
            barrier = threading.Barrier(16)

            def worker(i):
                barrier.wait()
                try:
                    gate.instantiate(p, tok, f"b{i}", data, rc, fuel=5)
                    results.append("ok")
                except gw.Overloaded:
                    results.append("shed")
            ts = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
            [t.start() for t in ts]; [t.join() for t in ts]
            self.assertEqual(len(results), 16)
            self.assertEqual(audit.verify(), 16)  # every admit and every shed audited, chain intact
            self.assertEqual(metrics.value("instances", tenant="t1"), results.count("ok"))
        finally:
            shutil.rmtree(tmp)


class DuplicateRaceTest(unittest.TestCase):
    def test_concurrent_same_name_admits_exactly_once(self):
        tmp = tempfile.mkdtemp()
        try:
            authn, authz, audit, metrics, gate, clock = make_world(tmp, max_inflight=32, max_instances=32)
            p = login(authn)
            tok = authz.grant(p, token_id="t", operations={"instantiate"})
            data = fx.module(); rc = receipt(data)
            ok = []
            barrier = threading.Barrier(12)

            def worker():
                barrier.wait()
                try:
                    gate.instantiate(p, tok, "same", data, rc, fuel=5); ok.append(1)
                except errors.HardeningError:
                    pass
            ts = [threading.Thread(target=worker) for _ in range(12)]
            [t.start() for t in ts]; [t.join() for t in ts]
            self.assertEqual(len(ok), 1)
        finally:
            shutil.rmtree(tmp)


class ReleaseGateTest(unittest.TestCase):
    def setUp(self):
        self.components = json.loads((PKG_DIR / "COMPONENTS_STATUS.json").read_text())
        self.matrix = json.loads((PKG_DIR / "POST_AUDIT_MATRIX.json").read_text())

    def test_delivered_state_is_no_go(self):
        r = rg.evaluate(self.components, self.matrix, tests_passed=True, pk_gate=None, approval=None)
        self.assertEqual(r["verdict"], "NO_GO")
        self.assertTrue(any("pk_core" in b for b in r["blockers"]))

    def test_falsifier_gate_is_a_gate_not_a_wall(self):
        """With every input synthetically satisfied the gate must say GO."""
        comps = copy.deepcopy(self.components)
        for c in comps["components"]:
            c["status"] = "COMPLETE"
        matrix = copy.deepcopy(self.matrix)
        for r in matrix["requirements"]:
            r["status"] = "verified"
        full = dict(tests_passed=True, pk_gate={"verdict": "PASS"},
                    approval={"decision": "APPROVE", "approver": "NOT_A_REAL_PERSON"})
        self.assertEqual(rg.evaluate(comps, matrix, **full)["verdict"], "GO")
        # each single omission is NO_GO
        for key, bad in (("tests_passed", False), ("pk_gate", None), ("approval", None),
                         ("approval", {"decision": "APPROVE", "approver": "release-bot"}),
                         ("approval", {"decision": "APPROVE", "approver": "Claude"})):
            with self.subTest(key=key, bad=bad):
                self.assertEqual(rg.evaluate(comps, matrix, **{**full, key: bad})["verdict"], "NO_GO")
        self.assertEqual(rg.evaluate(comps, matrix, **{**full, "approval": {"decision": "APPROVE",
                         "approver": "Priscilla Ng"}})["verdict"], "GO")  # 'ci' substring is not a token
        comps["components"][0]["status"] = "BLOCKED"
        self.assertEqual(rg.evaluate(comps, matrix, **full)["verdict"], "NO_GO")


if __name__ == "__main__":
    unittest.main()
