"""INV-42 v4.3.0 hardening suites (stdlib only, no network).

Covers MC-010 outcomes, MC-015 transport, MC-016/018 key provider, MC-017 audit,
MC-019 fault injection, MC-020..024 telemetry, MC-027 fuzzing, MC-028 races,
MC-029 adversarial, MC-036 emergency disable, MC-042 delegation.
"""
from __future__ import annotations

import io
import json
import logging
import os
import pathlib
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

import audit  # noqa: E402
import delegation  # noqa: E402
import descriptors as d  # noqa: E402
import outcomes  # noqa: E402
import telemetry  # noqa: E402
import transport  # noqa: E402

FUZZ_ITERATIONS = int(os.environ.get("INV42_FUZZ_ITERATIONS", "20000"))
FUZZ_SEED = int(os.environ.get("INV42_FUZZ_SEED", "4242"))


class Collect(list):
    def __call__(self, e):
        self.append(e)


class OutcomeTaxonomyTest(unittest.TestCase):
    def test_every_error_class_is_classified(self):
        classes = [c for c in vars(d).values() if isinstance(c, type) and issubclass(c, d.DescriptorError)
                   and c is not d.DescriptorError]
        classes.append(delegation.DelegationDenied)
        for cls in classes:
            if cls.code == "delegation_denied":
                continue
            self.assertIn(cls.code, outcomes.TAXONOMY, cls)
        self.assertEqual(outcomes.classify(None).klass, "success")
        self.assertTrue(outcomes.classify(d.TableFull("x")).retryable)
        self.assertEqual(outcomes.classify(d.ComponentDisabled("x")).klass, "degraded")
        self.assertEqual(outcomes.classify(ValueError("x")).code, "invalid_argument")
        self.assertEqual(outcomes.classify(RuntimeError("x")).klass, "terminal")


class EmergencyDisableTest(unittest.TestCase):
    def tearDown(self):
        d.emergency_enable()

    def test_disable_fails_closed_and_keeps_revocation(self):
        t = d.DescriptorTable("w")
        fd = t.open("stream", 1)
        d.emergency_disable()
        for call in (lambda: t.open("stream", 2), lambda: t.resolve(fd), lambda: t.close(fd),
                     lambda: t.from_wire(fd.to_wire())):
            with self.assertRaises(d.ComponentDisabled):
                call()
        self.assertEqual(t.status()["live"], 1)
        t.destroy()
        d.emergency_enable()
        with self.assertRaises(d.TableDestroyed):
            t.resolve(fd)

    def test_env_switch(self):
        t = d.DescriptorTable("w")
        with mock.patch.dict(os.environ, {d.DISABLE_ENV: "1"}):
            with self.assertRaises(d.ComponentDisabled):
                t.open("stream", 1)
            self.assertEqual(telemetry.health([t])["status"], "not_ready")
        t.open("stream", 1)


class KeyProviderTest(unittest.TestCase):
    def test_provider_outage_is_fail_closed(self):
        def down():
            raise TimeoutError("kms unreachable")
        with self.assertRaises(d.KeyUnavailable):
            d.DescriptorTable("w", key_provider=down)
        for bad in (lambda: b"short", lambda: "not-bytes", lambda: None):
            with self.assertRaises(d.KeyUnavailable):
                d.DescriptorTable("w", key_provider=bad)

    def test_provider_key_is_used(self):
        k = os.urandom(32)
        t = d.DescriptorTable("w", key_provider=lambda: k)
        self.assertEqual(bytes(t._key), k)
        t.resolve(t.open("s", 1))


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "audit.jsonl")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def _populate(self, key=None):
        log = audit.AuditLog(self.path, mac_key=key)
        t = d.DescriptorTable("w", observer=log)
        fd = t.open("stream", 1)
        t.resolve(fd)
        t.close(fd)
        with self.assertRaises(d.DescriptorClosed):
            t.resolve(fd)
        return log, fd

    def test_chain_verifies_and_contains_no_bearer_material(self):
        log, fd = self._populate()
        res = audit.verify(self.path, expected_head=log.head)
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["count"], 4)
        text = pathlib.Path(self.path).read_text()
        self.assertNotIn(fd.auth_tag, text)
        self.assertNotIn(fd.table_id, text)
        self.assertIn("descriptor_closed", text)

    def test_tamper_delete_reorder_truncate_detected(self):
        log, _ = self._populate()
        lines = pathlib.Path(self.path).read_text().splitlines()
        variants = {
            "modify": [lines[0].replace('"open"', '"opex"')] + lines[1:],
            "delete": [lines[0]] + lines[2:],
            "reorder": [lines[1], lines[0]] + lines[2:],
        }
        for name, v in variants.items():
            pathlib.Path(self.path).write_text("\n".join(v) + "\n")
            self.assertFalse(audit.verify(self.path)["ok"], name)
        pathlib.Path(self.path).write_text("\n".join(lines[:2]) + "\n")
        self.assertFalse(audit.verify(self.path, expected_head=log.head)["ok"])

    def test_mac_prevents_chain_reforge(self):
        self._populate(key=b"k" * 32)
        recs = [json.loads(line) for line in pathlib.Path(self.path).read_text().splitlines()]
        recs[0]["event"]["outcome"] = "forged"
        prev = audit.GENESIS
        import hashlib
        for r in recs:  # attacker recomputes hashes but lacks MAC key
            r["prev"] = prev
            r["hash"] = hashlib.sha256(prev.encode() + audit._canon({"seq": r["seq"], "event": r["event"]})).hexdigest()
            prev = r["hash"]
        pathlib.Path(self.path).write_text("".join(json.dumps(r) + "\n" for r in recs))
        self.assertTrue(audit.verify(self.path)["ok"])  # hash-only is re-forgeable
        self.assertFalse(audit.verify(self.path, mac_key=b"k" * 32)["ok"])

    def test_forbidden_fields_rejected_and_broken_chain_refused(self):
        with self.assertRaises(ValueError):
            audit.sanitize({"op": "x", "auth": "a" * 64})
        pathlib.Path(self.path).write_text("garbage\n")
        with self.assertRaises(ValueError):
            audit.AuditLog(self.path)


class TelemetryTest(unittest.TestCase):
    def test_metrics_health_logging_tracing_explain(self):
        m = telemetry.Metrics()
        stream = io.StringIO()
        logger = logging.getLogger("inv42.test")
        logger.handlers[:] = [logging.StreamHandler(stream)]
        logger.setLevel(logging.INFO)
        logger.propagate = False
        got = Collect()
        t = d.DescriptorTable("w", observer=telemetry.with_trace(
            telemetry.fanout(m, telemetry.StructuredLogger(logger), got)))
        parent = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        with telemetry.span(parent) as sp:
            fd = t.open("stream", 1)
            with self.assertRaises(d.TypeMismatch):
                t.resolve(fd, expect="socket")
        self.assertEqual(got[0]["trace_id"], "a" * 32)
        self.assertEqual(sp.traceparent[:36], "00-" + "a" * 32 + "-")
        prom = m.prometheus([t])
        self.assertIn('inv42_operations_total{op="resolve",outcome="type_mismatch",class="terminal"} 1', prom)
        self.assertIn('le="+Inf"', prom)
        self.assertIn("inv42_table_saturation_ratio", prom)
        logs = stream.getvalue()
        self.assertNotIn(fd.auth_tag, logs)
        self.assertNotIn(fd.table_id, logs)
        self.assertEqual(telemetry.health([t], m)["status"], "ready")
        ex = telemetry.explain(d.TypeMismatch("x"), table=t, release={"version": "4.3.0"})
        self.assertEqual(ex["class"], "terminal")
        self.assertEqual(ex["release"]["version"], "4.3.0")

    def test_invalid_traceparent_starts_new_trace(self):
        for bad in (None, "", "00-" + "0" * 32 + "-" + "b" * 16 + "-01", "zz" * 30, "00-" + "A" * 32 + "-" + "b" * 16 + "-01"):
            self.assertIsNone(telemetry.parse_traceparent(bad))

    def test_health_saturation_and_stall(self):
        t = d.DescriptorTable("w")
        for _ in range(int(d.TABLE_LIMIT * 0.95)):
            t.open("s", 0)
        m = telemetry.Metrics()
        m.last_event_ts = 1.0
        h = telemetry.health([t], m, now=1.0 + telemetry.STALL_SECONDS + 1, expect_traffic=True)
        self.assertEqual(h["status"], "degraded")
        self.assertTrue(any("saturation" in r for r in h["reasons"]))
        self.assertIn("stalled", h["reasons"])

    def test_redaction_neutralises_injection(self):
        s = telemetry.redact("x\n{\"fake\":1}\r" + "a" * 64)
        self.assertNotIn("\n", s)
        self.assertIn("[REDACTED-TAG]", s)

    def test_observer_failure_never_changes_decision(self):
        def boom(_):
            raise RuntimeError("sink down")
        t = d.DescriptorTable("w", observer=boom)
        fd = t.open("s", 1)
        self.assertEqual(t.resolve(fd), 1)


class FaultInjectionTest(unittest.TestCase):
    def test_mint_failure_commits_nothing(self):
        t = d.DescriptorTable("w")
        with mock.patch.object(d.DescriptorTable, "_mint_tag", side_effect=MemoryError):
            with self.assertRaises(MemoryError):
                t.open("s", 1)
        st = t.status()
        self.assertEqual((st["live"], st["issued"]), (0, 0))
        self.assertEqual(t.open("s", 1).number, d.FIRST_DESCRIPTOR)

    def test_close_failure_leaves_descriptor_live(self):
        t = d.DescriptorTable("w")
        fd = t.open("s", 1)
        with mock.patch.object(d.DescriptorTable, "_authenticate_locked", side_effect=OSError("fault")):
            with self.assertRaises(OSError):
                t.close(fd)
        self.assertEqual(t.resolve(fd), 1)

    def test_restart_does_not_restore_authority(self):
        t = d.DescriptorTable("w")
        wire = t.open("s", 1).to_wire()
        t2 = d.DescriptorTable("w")  # simulated restart
        with self.assertRaises(d.ForeignDescriptor):
            t2.from_wire(wire)

    def test_child_process_crash_isolated(self):
        code = "import sys; sys.path.insert(0, %r); import descriptors as d, os; t=d.DescriptorTable('w'); t.open('s',1); os._exit(9)" % str(PKG_DIR)
        r = subprocess.run([sys.executable, "-c", code])
        self.assertEqual(r.returncode, 9)
        t = d.DescriptorTable("w")
        self.assertEqual(t.status()["live"], 0)


class FuzzTest(unittest.TestCase):
    """Seeded mutational fuzzing of from_wire (MC-027).  Oracle: any mutated
    payload either raises a DescriptorError subclass or equals the original."""

    SEEDS = None

    def _mutants(self, rng, wire):
        junk = [None, True, False, 0, -1, 2**64, 3.5, "", " ", "\x00", "x" * 5000, [], {}, b"b", "PK_DESCRIPTOR/1",
                "0" * 64, "g" * 64, "A" * 64, "0" * 32, "‮", float("nan")]
        m = dict(wire)
        op = rng.randrange(7)
        k = rng.choice(list(wire))
        if op == 0:
            m[k] = rng.choice(junk)
        elif op == 1:
            del m[k]
        elif op == 2:
            m[rng.choice(["x", "Schema", "auth ", k + "_"])] = rng.choice(junk)
        elif op == 3 and isinstance(m[k], str) and m[k]:
            i = rng.randrange(len(m[k]))
            m[k] = m[k][:i] + chr(rng.randrange(0x20, 0x7f)) + m[k][i + 1:]
        elif op == 4 and isinstance(m[k], int):
            m[k] = m[k] + rng.choice([-1, 1, 1 << 31])
        elif op == 5:
            return rng.choice([[], "str", None, 7, (1, 2), type("D", (dict,), {})(wire)])
        else:
            m = {kk: m[kk] for kk in rng.sample(list(m), len(m))}
        return m

    def test_from_wire_fuzz(self):
        rng = random.Random(FUZZ_SEED)
        t = d.DescriptorTable("w")
        live = [t.open(rng.choice(["stream", "socket", "ψ"]), i) for i in range(8)]
        closed = t.open("stream", "c")
        t.close(closed)
        corpus = [fd.to_wire() for fd in live] + [closed.to_wire()]
        accepted = 0
        for _ in range(FUZZ_ITERATIONS):
            base = rng.choice(corpus)
            m = self._mutants(rng, base)
            try:
                fd = t.from_wire(m)
            except d.DescriptorError:
                continue
            accepted += 1
            self.assertEqual(fd.to_wire(), base, f"mutant accepted: {m!r}")
        self.assertGreaterEqual(t.status()["invalid_descriptors"], 1)

    def test_corpus_regressions(self):
        t = d.DescriptorTable("w")
        corpus = json.loads((PKG_DIR / "tests" / "fixtures" / "fuzz_corpus.json").read_text())
        for case in corpus:
            with self.assertRaises(d.DescriptorError, msg=case["why"]):
                t.from_wire(case["payload"])


class AdversarialTest(unittest.TestCase):
    def test_hostile_subclasses_rejected(self):
        t = d.DescriptorTable("w")
        wire = t.open("stream", 1).to_wire()

        class EvilStr(str):
            def __eq__(self, o):
                return True
            __hash__ = str.__hash__

        class EvilInt(int):
            pass

        for k, v in (("type", EvilStr("stream")), ("number", EvilInt(wire["number"])), ("auth", EvilStr(wire["auth"]))):
            with self.assertRaises(d.InvalidDescriptor):
                t.from_wire({**wire, k: v})

        class EvilDict(dict):
            def keys(self):
                return {"schema", "number", "type", "table", "auth"}
        with self.assertRaises(d.InvalidDescriptor):
            t.from_wire(EvilDict(wire))

    def test_error_messages_are_log_safe(self):
        t = d.DescriptorTable("w")
        wire = t.open("s", 1).to_wire()
        with self.assertRaises(d.InvalidDescriptor) as ctx:
            t.from_wire({**wire, "schema": "X" * 10_000 + "\n"})
        self.assertLess(len(str(ctx.exception)), 200)

    def test_constant_time_comparisons_used(self):
        src = (PKG_DIR / "descriptors.py").read_text()
        self.assertIn("hmac.compare_digest(descriptor.auth_tag", src)
        self.assertIn("hmac.compare_digest(descriptor.table_id", src)

    def test_key_compromise_contained_by_destroy(self):
        t = d.DescriptorTable("w")
        real = t.open("stream", "secret")
        stolen = bytes(t._key)
        import hashlib
        import hmac as _h
        msg = json.dumps([d.WIRE_SCHEMA, t.table_id, real.number, "stream"], separators=(",", ":")).encode()
        forged = d.Descriptor(real.number, "stream", t.table_id, _h.new(stolen, msg, hashlib.sha256).hexdigest())
        self.assertEqual(t.resolve(forged), "secret")  # documented residual risk
        t.destroy()
        with self.assertRaises(d.TableDestroyed):
            t.resolve(forged)
        other = d.DescriptorTable("w2")
        with self.assertRaises(d.ForeignDescriptor):
            other.resolve(forged)  # compromise does not cross tables

    def test_sustained_exhaustion_bounded(self):
        t = d.DescriptorTable("w")
        with mock.patch.object(d, "SESSION_ALLOCATION_LIMIT", 5000):
            for _ in range(5000):
                t.close(t.open("s", 0))
            with self.assertRaises(d.SessionExhausted):
                t.open("s", 0)
        self.assertEqual(t.status()["live"], 0)
        self.assertLess(len(t._entries), 1)


class ConcurrencyTest(unittest.TestCase):
    def test_mixed_operations_race(self):
        t = d.DescriptorTable("w")
        closed_twice = []
        errors = []
        pool_fds = [t.open("s", i) for i in range(200)]

        def worker(seed):
            rng = random.Random(seed)
            for _ in range(300):
                op = rng.randrange(4)
                try:
                    if op == 0:
                        pool_fds.append(t.open("s", seed))
                    elif op == 1:
                        t.resolve(rng.choice(pool_fds))
                    elif op == 2:
                        fd = rng.choice(pool_fds)
                        t.close(fd)
                        closed_twice.append(fd)
                    else:
                        st = t.status()
                        if st["live"] > d.TABLE_LIMIT:
                            raise AssertionError("live exceeds limit")
                except (d.DescriptorClosed, d.TableFull):
                    pass
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

        with ThreadPoolExecutor(max_workers=16) as ex:
            list(ex.map(worker, range(32)))
        self.assertEqual(errors, [])
        self.assertEqual(len(closed_twice), len(set(closed_twice)), "a descriptor was closed twice")
        st = t.status()
        self.assertEqual(st["issued"] - st["closed"], st["live"])

    def test_destroy_races_are_fail_closed(self):
        for _ in range(20):
            t = d.DescriptorTable("w")
            fds = [t.open("s", i) for i in range(50)]
            bad = []

            def use(fd):
                try:
                    t.resolve(fd)
                except (d.TableDestroyed, d.DescriptorClosed):
                    pass
                except Exception as exc:  # noqa: BLE001
                    bad.append(exc)
            threads = [threading.Thread(target=use, args=(fd,)) for fd in fds]
            threads.append(threading.Thread(target=t.destroy))
            for th in threads:
                th.start()
            for th in threads:
                th.join()
            self.assertEqual(bad, [])
            for fd in fds:
                with self.assertRaises(d.TableDestroyed):
                    t.resolve(fd)


class EdgeCaseTest(unittest.TestCase):
    def test_edges(self):
        with self.assertRaises(ValueError):
            d.Descriptor("3", "s", "0" * 32, "0" * 64)
        t = d.DescriptorTable("w")
        with self.assertRaises(d.InvalidDescriptor):
            t.resolve("not a descriptor")
        with self.assertRaises(ValueError):
            t.open("bad\ntype", 1)
        fd = t.open("s", 1)
        t._entries[fd.number] = ("other", 1)  # simulated state damage
        with self.assertRaises(d.TypeMismatch):
            t.resolve(fd)
        with d.DescriptorTable("ctx") as c:
            c.open("s", 1)
        self.assertTrue(c.status()["destroyed"])
        c.destroy()  # idempotent


class DelegationTest(unittest.TestCase):
    def setUp(self):
        self.a, self.b = d.DescriptorTable("a"), d.DescriptorTable("b")
        self.events = Collect()

    def test_default_deny(self):
        fd = self.a.open("s", 1)
        with self.assertRaises(delegation.DelegationDenied):
            delegation.Delegator().delegate(self.a, self.b, fd, txn_id="txn-00001")
        self.assertEqual(self.a.resolve(fd), 1)

    def test_move_is_atomic_idempotent_and_audited(self):
        dg = delegation.Delegator(lambda *a: True, audit=self.events)
        fd = self.a.open("s", "R")
        new, rec = dg.delegate(self.a, self.b, fd, txn_id="txn-00002", mode="move")
        self.assertEqual(self.b.resolve(new, expect="s"), "R")
        with self.assertRaises(d.DescriptorClosed):
            self.a.resolve(fd)
        again, _ = dg.delegate(self.a, self.b, fd, txn_id="txn-00002", mode="move")
        self.assertEqual(again, new)
        self.assertEqual(self.b.status()["live"], 1)
        self.assertNotIn(fd.auth_tag, json.dumps(rec))
        self.assertEqual(self.events[-1]["outcome"], "ok")
        with self.assertRaises(delegation.DelegationDenied):
            dg.delegate(self.a, self.b, self.a.open("s", 2), txn_id="txn-00002")

    def test_destination_failure_rolls_back(self):
        dg = delegation.Delegator(lambda *a: True)
        fd = self.a.open("s", 1)
        self.b.destroy()
        with self.assertRaises(d.TableDestroyed):
            dg.delegate(self.a, self.b, fd, txn_id="txn-00003")
        self.assertEqual(self.a.resolve(fd), 1)

    def test_share_policy_error_and_stale(self):
        dg = delegation.Delegator(lambda *a: True)
        fd = self.a.open("s", 1)
        new, _ = dg.delegate(self.a, self.b, fd, txn_id="txn-00004", mode="share")
        self.assertEqual(self.a.resolve(fd), self.b.resolve(new))
        self.a.close(fd)
        with self.assertRaises(d.DescriptorClosed):
            dg.delegate(self.a, self.b, fd, txn_id="txn-00005")

        def broken(*a):
            raise RuntimeError
        with self.assertRaises(delegation.DelegationDenied):
            delegation.Delegator(broken).delegate(self.a, self.b, self.a.open("s", 2), txn_id="txn-00006")
        with self.assertRaises(ValueError):
            dg.delegate(self.a, self.b, fd, txn_id="bad id!")


@unittest.skipUnless(shutil.which("openssl"), "openssl CLI required to mint test PKI")
class TransportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        p = lambda n: os.path.join(cls.dir, n)  # noqa: E731
        run = lambda *a: subprocess.run(a, check=True, capture_output=True)  # noqa: E731
        run("openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
            "-keyout", p("ca.key"), "-out", p("ca.pem"), "-subj", "/CN=inv42-test-ca", "-days", "1")
        for name in ("server", "client", "rogue"):
            ca = "ca" if name != "rogue" else "rogueca"
            if name == "rogue":
                run("openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
                    "-keyout", p("rogueca.key"), "-out", p("rogueca.pem"), "-subj", "/CN=rogue", "-days", "1")
            run("openssl", "req", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
                "-keyout", p(f"{name}.key"), "-out", p(f"{name}.csr"), "-subj", f"/CN={name}.inv42.test")
            ext = p(f"{name}.ext")
            pathlib.Path(ext).write_text(f"subjectAltName=DNS:{name}.inv42.test\n")
            run("openssl", "x509", "-req", "-in", p(f"{name}.csr"), "-CA", p(f"{ca}.pem"), "-CAkey", p(f"{ca}.key"),
                "-CAcreateserial", "-out", p(f"{name}.pem"), "-days", "1", "-extfile", ext)
        cls.p = staticmethod(p)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir)

    def _serve(self, table, result, client_cert="client"):
        p = self.p
        sctx = transport.server_context(ca_file=p("ca.pem"), cert_file=p("server.pem"), key_file=p("server.key"))
        lsock = socket.socket()
        lsock.bind(("127.0.0.1", 0))
        lsock.listen(1)
        port = lsock.getsockname()[1]

        def srv():
            try:
                conn, _ = lsock.accept()
                with sctx.wrap_socket(conn, server_side=True) as s:
                    result["fd"] = transport.recv_descriptor(s, table, peer_identity="client.inv42.test")
            except Exception as exc:  # noqa: BLE001
                result["err"] = exc
            finally:
                lsock.close()
        th = threading.Thread(target=srv)
        th.start()
        return port, th

    def test_mutual_tls13_round_trip(self):
        p = self.p
        t = d.DescriptorTable("w")
        fd = t.open("stream", 1)
        result = {}
        port, th = self._serve(t, result)
        cctx = transport.client_context(ca_file=p("ca.pem"), cert_file=p("client.pem"), key_file=p("client.key"))
        with cctx.wrap_socket(socket.create_connection(("127.0.0.1", port)), server_hostname="server.inv42.test") as c:
            self.assertEqual(c.version(), "TLSv1.3")
            transport.send_descriptor(c, fd, peer_identity="server.inv42.test")
        th.join(5)
        self.assertEqual(result.get("fd"), fd, result.get("err"))

    def test_rogue_client_and_plain_socket_refused(self):
        p = self.p
        t = d.DescriptorTable("w")
        fd = t.open("stream", 1)
        result = {}
        port, th = self._serve(t, result)
        cctx = transport.client_context(ca_file=p("ca.pem"), cert_file=p("rogue.pem"), key_file=p("rogue.key"))
        try:
            with cctx.wrap_socket(socket.create_connection(("127.0.0.1", port)), server_hostname="server.inv42.test") as c:
                transport.send_descriptor(c, fd)
                c.recv(1)
        except (OSError, transport.InsecureChannel):
            pass
        th.join(5)
        self.assertNotIn("fd", result)
        a, b = socket.socketpair()
        with self.assertRaises(transport.InsecureChannel):
            transport.send_descriptor(a, fd)
        a.close()
        b.close()


if __name__ == "__main__":
    unittest.main()
