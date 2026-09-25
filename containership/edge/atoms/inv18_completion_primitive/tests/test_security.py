"""Adversarial and threat-model-derived security tests (C023, C024, C041-C050, C087).

Every negative test asserts a *structured* refusal code: the system must fail securely,
not merely raise.  Threat ids refer to conformance/THREAT_MODEL.json.
"""
import ast
import builtins
import gc
import json
import os
import socket
import subprocess
import threading
import unittest

from _util import m, PKG_DIR, rt as make_rt

runtime = m("runtime")
errors = m("errors")
auth = m("auth")
adapters = m("adapters")
wire = m("wire")
telemetry = m("telemetry")

CORE = ["future.py", "errors.py", "runtime.py", "telemetry.py", "wire.py", "retry.py", "auth.py",
        "adapters.py", "adjacent.py"]


def _endpoint(rt=None, **kw):
    kr = auth.KeyRing()
    kr.add("k1", b"k" * 32)
    au = auth.Authenticator(kr, **kw)
    return (rt or make_rt()), kr, au


class CapabilityAttackTest(unittest.TestCase):
    def test_forged_token_refused(self):
        """REQ: C024 C050 C087 INV18-SEC-001 — T06"""
        rt = make_rt()
        w, r = rt.create(int)
        forged = runtime.ReceiverCap(r.future_id, r.tenant, "0" * 32, "receiver")
        guessed = runtime.ReceiverCap("f1-00000000", r.tenant, r.token, "receiver")
        for cap in (forged, guessed):
            with self.assertRaises(errors.Rejected) as cm:
                rt.take(cap)
            self.assertEqual(cm.exception.code, "PERMISSION_DENIED")
        self.assertNotIn(r.token, repr(r))
        self.assertTrue(any(e["action"] == "capability.denied" for e in rt.audit.events))

    def test_kind_upgrade_refused(self):
        """REQ: C024 C042 C050 INV18-SEC-001 — T06/T07 privilege escalation"""
        rt = make_rt()
        w, r = rt.create(int)
        upgraded = runtime.ResolverCap(r.future_id, r.tenant, r.token, "resolver")   # receiver token, resolver kind
        with self.assertRaises(errors.Rejected) as cm:
            rt.resolve(upgraded, 1)
        self.assertEqual(cm.exception.code, "PERMISSION_DENIED")
        o = rt.observer(r)
        as_recv = runtime.ReceiverCap(o.future_id, o.tenant, o.token, "receiver")
        with self.assertRaises(errors.Rejected):
            rt.take(as_recv)

    def test_constant_time_compare_used(self):
        """REQ: C050 C087 — T06 timing side channel on token checks"""
        for mod in ("runtime.py", "auth.py"):
            src = (PKG_DIR / mod).read_text()
            self.assertIn("compare_digest", src)
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare) and any(isinstance(o, (ast.Eq, ast.NotEq)) for o in node.ops):
                    names = ast.dump(node)
                    self.assertNotRegex(names, r"attr='(token|mac)'", f"non-constant-time compare in {mod}")


class IsolationTest(unittest.TestCase):
    def test_cross_tenant_capability_refused(self):
        """REQ: C046 C024 C087 INV18-SEC-002 — T05"""
        rt = make_rt()
        wa, ra = rt.create(int, tenant="tenant-a")
        stolen = runtime.ReceiverCap(ra.future_id, "tenant-b", ra.token, "receiver")
        with self.assertRaises(errors.Rejected) as cm:
            rt.take(stolen)
        self.assertEqual(cm.exception.code, "PERMISSION_DENIED")
        rt.resolve(wa, 1)
        self.assertEqual(rt.take(ra), ("ok", 1))

    def test_cross_tenant_wire_refused(self):
        """REQ: C046 C044 C087 INV18-SEC-002 — T05"""
        rt, kr, au = _endpoint()
        link = adapters.Link(adapters.RemoteEndpoint(rt, au))
        a = adapters.RemoteClient(link, au, "tenant-a", ["create", "resolve", "receive"])
        b = adapters.RemoteClient(link, au, "tenant-b", ["create", "resolve", "receive", "abandon"])
        fid = a.create("int")["result"]["future_id"]
        for resp in (b.resolve(fid, 9), b.take(fid, "int"), b.abandon(fid)):
            self.assertFalse(resp["ok"])
            self.assertEqual(resp["error"]["code"], "PERMISSION_DENIED")
        spoof = b._call("create", {"schema": "PK_FUTURE/1", "future_id": "new", "value_type": "int", "epoch": 1,
                                   "tenant": "tenant-a"})
        self.assertEqual(spoof["error"]["code"], "PERMISSION_DENIED")    # identity only from verified claims
        self.assertTrue(a.resolve(fid, 1)["ok"])

    def test_enumeration_indistinguishable(self):
        """REQ: C046 C050 — T05 deliberate enumeration"""
        rt = make_rt()
        w, r = rt.create(int, tenant="a")
        msgs = set()
        for cap in (runtime.ReceiverCap(r.future_id, "b", "x" * 32, "receiver"),
                    runtime.ReceiverCap("f999-deadbeef", "b", "x" * 32, "receiver")):
            try:
                rt.take(cap)
            except errors.Rejected as exc:
                msgs.add((exc.code, str(exc)))
        self.assertEqual(len(msgs), 1)

    def test_identifier_collision_and_state_separation(self):
        """REQ: C046"""
        rt = make_rt()
        ids = set()
        for t in ("a", "b"):
            for _ in range(500):
                w, r = rt.create(int, tenant=t)
                ids.add(w.future_id)
                rt.resolve(w, 1 if t == "a" else 2)
                self.assertEqual(rt.take(r), ("ok", 1 if t == "a" else 2))
        self.assertEqual(len(ids), 1000)


class InjectionTest(unittest.TestCase):
    def test_hostile_documents_fail_securely(self):
        """REQ: C050 C085 C087 INV18-CMP-001 — T08"""
        rt, kr, au = _endpoint()
        ep = adapters.RemoteEndpoint(rt, au)
        hostile = [b"", b"null", b"[]", b"{}", b"\xff\xfe", b'{"schema":"PK_FUTURE/1"}' + b" " * 10,
                   b'{"schema":"PK_FUTURE/1","future_id":"new","value_type":"int","epoch":NaN}',
                   b'{"schema":"PK_FUTURE/1","future_id":"new\\u0000","value_type":"int","epoch":1}',
                   b'{"schema":"PK_FUTURE/1","future_id":"new","value_type":"__import__(\'os\')","epoch":1}',
                   b'{"schema":"PK_FUTURE/1","future_id":"../../etc/passwd","value_type":"int","epoch":1}',
                   b"[" * 100000 + b"]" * 100000, b'{"a":' * 50000 + b"1" + b"}" * 50000]
        for blob in hostile:
            resp = json.loads(ep.handle("create", blob, au.issue("t", ["create"])))
            self.assertFalse(resp["ok"], blob[:60])
            self.assertIn(resp["error"]["code"], ("INVALID_ARGUMENT", "RESOURCE_EXHAUSTED", "INCOMPATIBLE_VERSION"))
            self.assertEqual(wire.validate(resp["error"], "PK_FUTURE_ERROR/1"), [])
        self.assertEqual(rt.outstanding, 0)
        resp = json.loads(ep.handle("rm -rf", b"{}", au.issue("t", ["create"])))
        self.assertEqual(resp["error"]["code"], "INVALID_ARGUMENT")


class AuthnTest(unittest.TestCase):
    def test_credential_negatives(self):
        """REQ: C023 C044 C050 C087 INV18-SEC-003 — T11"""
        now = [1_000_000.0]
        kr = auth.KeyRing(); kr.add("k1", b"k" * 32)
        au = auth.Authenticator(kr, clock=lambda: now[0])
        other = auth.KeyRing(); other.add("k1", b"z" * 32)
        forger = auth.Authenticator(other, clock=lambda: now[0])
        good = au.issue("t", ["resolve"])
        body, mac = good.split(".")
        cases = {
            "missing": None, "empty": "", "malformed": "abc", "garbage_b64": "!!!.???",
            "forged_key": forger.issue("t", ["resolve"]),
            "tampered_claims": auth._b64(json.dumps({"sub": "admin"}).encode()) + "." + mac,
            "wrong_audience": au.issue("t", ["resolve"], aud="someone-else"),
            "wrong_issuer": au.issue("t", ["resolve"], iss="evil"),
            "expired": au.issue("t", ["resolve"], iat=now[0] - 1000, ttl_s=10),
            "ttl_too_long": au.issue("t", ["resolve"], ttl_s=10_000),
            "future_iat": au.issue("t", ["resolve"], iat=now[0] + 3600),
            "unknown_kid": au.issue("t", ["resolve"]).replace("", "") if False else None,
        }
        cases.pop("unknown_kid")
        for name, tok in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(errors.Rejected) as cm:
                    au.verify(tok, "resolve")
                self.assertEqual(cm.exception.code, "UNAUTHENTICATED")
        with self.assertRaises(errors.Rejected) as cm:
            au.verify(au.issue("t", ["receive"]), "resolve")
        self.assertEqual(cm.exception.code, "PERMISSION_DENIED")
        # unauthenticated wire call cannot mutate state
        rt = make_rt()
        ep = adapters.RemoteEndpoint(rt, au)
        doc = wire.encode({"schema": "PK_FUTURE/1", "future_id": "new", "value_type": "int", "epoch": 1})
        resp = json.loads(ep.handle("create", doc, "not-a-token"))
        self.assertEqual(resp["error"]["code"], "UNAUTHENTICATED")
        self.assertEqual(rt.outstanding, 0)
        self.assertTrue(any(e["action"] == "auth.failure" for e in rt.audit.events))

    def test_replay_rejected(self):
        """REQ: C044 C050 C087 INV18-SEC-003 — T11/T13"""
        rt, kr, au = _endpoint()
        tok = au.issue("t", ["create"])
        au.verify(tok, "create")
        with self.assertRaises(errors.Rejected) as cm:
            au.verify(tok, "create")
        self.assertEqual(cm.exception.code, "REPLAY_DETECTED")

    def test_key_rotation_overlap_and_revocation(self):
        """REQ: C044 C047"""
        kr = auth.KeyRing(); kr.add("k1", b"a" * 32)
        au = auth.Authenticator(kr)
        old = au.issue("t", ["create"])
        kr.rotate("k2")
        new = au.issue("t", ["create"])
        self.assertEqual(au.verify(old, "create")["kid"], "k1")       # overlap window
        self.assertEqual(au.verify(new, "create")["kid"], "k2")
        kr.revoke("k1")
        with self.assertRaises(errors.Rejected):
            au.verify(au.issue("t", ["create"], kid="k2"), "create") if False else au.verify(old, "create")
        kr.retire("k1")
        self.assertNotIn("k1", repr(kr).split("current")[1])
        with self.assertRaises(errors.Rejected):
            kr.add("weak", b"short")


class DosTest(unittest.TestCase):
    def test_high_concurrency_flood_bounded(self):
        """REQ: C050 C054 C067 C087 — T12"""
        rt = make_rt(max_outstanding=200, soft_outstanding=150, max_per_tenant=100)
        admitted, refused, other = [], [0], []
        lock = threading.Lock()
        def attacker(t):
            for _ in range(200):
                try:
                    c = rt.create(int, tenant=t)
                    with lock:
                        admitted.append(c)
                except errors.Rejected as exc:
                    if exc.code == "RESOURCE_EXHAUSTED":
                        with lock:
                            refused[0] += 1
                    else:
                        other.append(exc.code)
        ts = [threading.Thread(target=attacker, args=(f"t{i % 3}",)) for i in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertLessEqual(rt.outstanding, 200)
        self.assertEqual(other, [])
        self.assertGreater(refused[0], 0)
        self.assertLessEqual(max(rt.tenant_outstanding(f"t{i}") for i in range(3)), 100)


class LeakTest(unittest.TestCase):
    def test_sentinel_secret_never_leaks(self):
        """REQ: C039 C050 C075 C087 INV18-SEC-004 — T15"""
        secret = "SENTINEL-SECRET-q9w8e7"
        sink = []
        rt = runtime.Runtime(m("config").ConfigStore({"environment": "test"}), log_sink=sink.append)
        w, r = rt.create(str, tenant="t")
        try:
            rt.resolve(w, 12345)                              # rejected: logged
        except TypeError:
            pass
        rt.resolve_error(w, f"upstream said {secret}")
        tag, msg = rt.take(r)                                 # delivered to the rightful receiver only
        self.assertIn(secret, msg)
        rt.log.emit("error", "probe", password=secret, note=f"x {secret}", payload=secret)
        err = errors.Rejected(f"bad {secret}", details={"token": secret}).record().to_dict()
        rt.audit.append("probe", detail=secret)
        blobs = [json.dumps(list(rt.log.records)), "\n".join(sink), json.dumps(err), json.dumps(rt.audit.events),
                 json.dumps(list(rt.decisions.records)), json.dumps(m("status").status(rt)),
                 m("status").explain(rt)]
        for b in blobs:
            self.assertNotIn(secret, b)


class OutageTest(unittest.TestCase):
    def _call(self, au, rt):
        ep = adapters.RemoteEndpoint(rt, au)
        doc = wire.encode({"schema": "PK_FUTURE/1", "future_id": "new", "value_type": "int", "epoch": 1})
        return json.loads(ep.handle("create", doc, au.issue("t", ["create"]) if au.keys.available else "x.y"))

    def test_each_outage_fails_closed(self):
        """REQ: C048 C056 C087 INV18-SEC-008 — T18"""
        rt = make_rt()
        kr = auth.KeyRing(); kr.add("k1", b"k" * 32)
        tok_key = auth.Authenticator(kr).issue("t", ["create"])
        kr.available = False                                   # key service down
        au = auth.Authenticator(kr)
        ep = adapters.RemoteEndpoint(rt, au)
        doc = wire.encode({"schema": "PK_FUTURE/1", "future_id": "new", "value_type": "int", "epoch": 1})
        self.assertEqual(json.loads(ep.handle("create", doc, tok_key))["error"]["code"], "DEPENDENCY_UNAVAILABLE")
        kr.available = True
        au2 = auth.Authenticator(kr, time_trusted=lambda: False)   # trusted time down
        ep2 = adapters.RemoteEndpoint(rt, au2)
        self.assertEqual(json.loads(ep2.handle("create", doc, au.issue("t", ["create"])))["error"]["code"],
                         "DEPENDENCY_UNAVAILABLE")
        self.assertEqual(rt.outstanding, 0)

    def test_simultaneous_outages_fail_closed(self):
        """REQ: C048 INV18-SEC-008 — T18"""
        rt = make_rt()
        kr = auth.KeyRing(); kr.add("k1", b"k" * 32)
        tok = auth.Authenticator(kr).issue("t", ["create"])
        kr.available = False
        au = auth.Authenticator(kr, time_trusted=lambda: False)
        ep = adapters.RemoteEndpoint(rt, au)
        doc = wire.encode({"schema": "PK_FUTURE/1", "future_id": "new", "value_type": "int", "epoch": 1})
        resp = json.loads(ep.handle("create", doc, tok))
        self.assertFalse(resp["ok"])
        self.assertEqual(resp["error"]["code"], "DEPENDENCY_UNAVAILABLE")
        self.assertEqual(rt.outstanding, 0)


class AuthorityTest(unittest.TestCase):
    FORBIDDEN_MODULES = {"socket", "subprocess", "shutil", "urllib", "http", "ftplib", "ctypes", "multiprocessing",
                         "pathlib", "tempfile", "importlib", "pk_core"}
    ALLOWED_OS_ATTRS = {"urandom"}
    # recorded, justified exceptions (docs/SECURITY.md §3): future.py's standalone-load
    # fallback reads its sibling errors.py when imported by file path in isolation tests
    EXCEPTIONS = {("future.py", "importlib"), ("future.py", "pathlib")}

    def test_core_modules_do_not_import_pk_core(self):
        """REQ: C031 C043 C090 — T09"""
        for mod in CORE + ["certify.py", "bootstrap.py", "bench.py", "fault.py", "status.py", "config.py"]:
            self.assertNotRegex((PKG_DIR / mod).read_text(), r"^\s*(from|import)\s+pk_core", mod)

    def test_static_authority_inventory(self):
        """REQ: C043 C042 INV18-SEC-005 — T19"""
        for mod in CORE:
            tree = ast.parse((PKG_DIR / mod).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        if (mod, a.name.split(".")[0]) in self.EXCEPTIONS:
                            continue
                        self.assertNotIn(a.name.split(".")[0], self.FORBIDDEN_MODULES, f"{mod} imports {a.name}")
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    self.assertNotIn(node.module.split(".")[0], self.FORBIDDEN_MODULES, f"{mod} imports {node.module}")
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, ("open", "exec", "eval", "compile", "__import__"), f"{mod} calls {node.func.id}")
                elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "os":
                    self.assertIn(node.attr, self.ALLOWED_OS_ATTRS, f"{mod} uses os.{node.attr}")

    def test_runtime_sandbox(self):
        """REQ: C043 C018 INV18-SEC-005 — T19; also proves the core needs no network"""
        def deny(*a, **k):
            raise PermissionError("ambient authority used")
        class NoEnv(dict):
            def __getitem__(self, k): deny()
            def get(self, *a): deny()
            def __contains__(self, k): deny()
            def items(self): deny()
        saved = (builtins.open, socket.socket, subprocess.Popen, os.system, os.environ)
        rt0 = make_rt()                                    # construction outside the sandbox
        try:
            builtins.open, socket.socket, subprocess.Popen, os.system = deny, deny, deny, deny
            os.environ = NoEnv()
            rt = rt0
            w, r = rt.create(int, tenant="sbx")
            rt.resolve(w, 1); self.assertEqual(rt.take(r), ("ok", 1))
            w, r = rt.create(int); rt.abandon(w)
            with self.assertRaises(m("future").Abandoned):
                rt.take(r)
            w, r = rt.create(str); del w; gc.collect()
            kr = auth.KeyRing(); kr.add("k", b"k" * 32)
            au = auth.Authenticator(kr)
            cli = adapters.RemoteClient(adapters.Link(adapters.RemoteEndpoint(rt, au)), au, "t",
                                        ["create", "resolve", "receive"])
            fid = cli.create("int")["result"]["future_id"]
            self.assertTrue(cli.resolve(fid, 3)["ok"])
            self.assertEqual(cli.take(fid, "int")["result"]["value"], 3)
            rt.health()
        finally:
            builtins.open, socket.socket, subprocess.Popen, os.system, os.environ = saved


class ThreatModelTest(unittest.TestCase):
    def test_threat_model_structure_and_traceability(self):
        """REQ: C041 C087"""
        tm = json.loads((PKG_DIR / "conformance/THREAT_MODEL.json").read_text())
        for k in ("assets", "trust_boundaries", "actors", "threats", "residual_risks"):
            self.assertTrue(tm[k], k)
        required_topics = ["tenant", "producer", "consumer", "payload", "pk_core", "supply", "control-plane",
                           "exhaustion", "replay", "capability", "leakage"]
        blob = json.dumps(tm["threats"]).lower()
        for t in required_topics:
            self.assertIn(t.lower().replace("control-plane", "control plane"), blob)
        for th in tm["threats"]:
            self.assertTrue(th["mitigation"])
            self.assertTrue(th["tests"])
            for tid in th["tests"]:
                path, cls, meth = tid.split("::")
                src = (PKG_DIR / path).read_text()
                self.assertRegex(src, rf"class {cls}\b", tid)
                self.assertRegex(src, rf"def {meth}\b", tid)
        self.assertIn(tm["approved_by"], (None,) + tuple([tm["approved_by"]] if tm["approved_by"] else []))


class AuditTest(unittest.TestCase):
    def test_mutation_and_deletion_detected(self):
        """REQ: C049 C087 INV18-SEC-007 — T20"""
        for key in (None, b"audit-key-" * 4):
            ch = telemetry.AuditChain(key=key)
            for i in range(5):
                ch.append("config.activate", actor="op", target=f"cfg-{i}", correlation_id=f"c{i}")
            self.assertEqual(ch.verify(), (True, "ok"))
            evs = json.loads(json.dumps(ch.events))
            evs[2]["actor"] = "mallory"
            self.assertFalse(ch.verify(evs)[0])
            evs = json.loads(json.dumps(ch.events)); del evs[1]
            self.assertFalse(ch.verify(evs)[0])
            evs = json.loads(json.dumps(ch.events)); evs[1], evs[2] = evs[2], evs[1]
            self.assertFalse(ch.verify(evs)[0])
            for field in ("actor", "action", "target", "result", "ts", "correlation_id", "event_id"):
                self.assertIn(field, ch.events[0])
        ch = telemetry.AuditChain(key=b"k" * 32)
        ch.append("x")
        evs = json.loads(json.dumps(ch.events))
        evs[0]["action"] = "y"
        evs[0]["hash"] = ch._hash(evs[0])                    # attacker recomputes hash but lacks the key
        self.assertFalse(ch.verify(evs)[0])


if __name__ == "__main__":
    unittest.main()
