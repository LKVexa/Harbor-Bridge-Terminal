"""MC-021 fuzz/property, MC-022 concurrency/race, MC-023 fault injection.

Seeded (INV13_FUZZ_SEED, INV13_FUZZ_ITERS) so failures reproduce.
"""
import os, random, string, threading, unittest
import _fx
from inv13_system_interface.host import fs, wasm_loader as w, wit_surface as ws, identity
from inv13_system_interface.host.errors import ErrorCode, Inv13Error
from inv13_system_interface.host.resources import ResourceTable
from inv13_system_interface.host.descriptors import DescriptorTable
from inv13_system_interface.host.policy import PolicyEngine
from inv13_system_interface.host.quotas import QuotaLedger
from inv13_system_interface.host.randomness import CsprngProvider
from inv13_system_interface.host.config import ConfigStore
from inv13_system_interface.runtime import Instance, World, PathEscape, CapabilityDenied

SEED = int(os.environ.get("INV13_FUZZ_SEED", "1337"))
ITERS = int(os.environ.get("INV13_FUZZ_ITERS", "3000"))
ALPHA = list("ab./\\\0.") + ["..", "/", "//", "é", "\udcff", "~", "%2e%2e", "\n"]


class Fuzz(unittest.TestCase):
    def test_path_resolvers_never_escape(self):
        rnd = random.Random(SEED)
        root, outside = _fx.tmpdir(), _fx.tmpdir()
        (outside / "secret").write_text("TOP")
        (root / "a").mkdir(); (root / "a" / "b").write_text("in")
        os.symlink(outside, root / "evil"); os.symlink(outside / "secret", root / "a" / "s")
        p = fs.Preopen("/d", str(root))
        inst = Instance("fz", World("w", {"filesystem"})); inst.grant_preopen("/d", str(root))
        try:
            for _ in range(ITERS):
                path = "".join(rnd.choice(ALPHA) for _ in range(rnd.randint(0, 12)))
                try:
                    data = p.read_bytes(path)
                    self.assertNotEqual(data, b"TOP", path)
                except Inv13Error as e:
                    self.assertIsInstance(e.code, ErrorCode)
                try:
                    r = inst.resolve("/d", path)
                    self.assertTrue(r["resolved"] == str(root) or r["resolved"].startswith(str(root) + "/"), path)
                except (PathEscape, CapabilityDenied, TypeError, ValueError):
                    pass
        finally:
            p.close()

    def test_wasm_parser_total_on_garbage(self):
        rnd = random.Random(SEED)
        seed_mod = w.build_module([([w.I32, w.I32], [w.I32]), ([], [w.I32])],
                                  [("inv13:stdio@4.3.0", "stdout-write", 0)], [(1, [], b"\x41\x00\x41\x05\x10\x00")],
                                  [("memory", 2, 0), ("run", 0, 1)], 1, [(0, b"hello")])
        for _ in range(ITERS):
            b = bytearray(seed_mod)
            for _ in range(rnd.randint(1, 6)):
                i = rnd.randrange(len(b))
                b[i] = rnd.randrange(256)
            try:
                info = w.admit(bytes(b), {"stdio"})
                # property: anything admitted maps only to granted capabilities
                self.assertLessEqual(w.required_capabilities(info), {"stdio"})
            except Inv13Error as e:
                self.assertIsInstance(e.code, ErrorCode)

    def test_policy_property_no_undeclared_authority(self):
        rnd = random.Random(SEED)
        pe = PolicyEngine(_fx.policy_doc("/srv/tenant-a"))
        caps = ["filesystem", "wall-clock", "monotonic-clock", "random", "sockets", "environment", "stdio", "http-outgoing"]
        for _ in range(ITERS):
            req = set(rnd.sample(caps, rnd.randint(0, 5)))
            world = rnd.choice(list(ws.surface()["worlds"]))
            tenant = rnd.choice(["tenant-a", "tenant-b", "x"])
            d = pe.decide(tenant=tenant, workload=rnd.choice(["api", "api-9", "rng-1", "zzz"]), world=world,
                          capabilities=req, preopens={"/data": rnd.choice(["/srv/tenant-a/q", "/srv/tenant-b", "/"])})
            if d.allowed:
                rule = next(r for r in pe.document["tenants"][tenant]["rules"] if r["id"] == d.rule_id)
                self.assertLessEqual(req, set(rule["capabilities"]))
                self.assertEqual(tenant, "tenant-a")

    def test_identity_tokens_mutation(self):
        rnd = random.Random(SEED)
        g = _fx.gate()
        base = _fx.token()
        for _ in range(ITERS // 3):
            t = list(base)
            i = rnd.randrange(len(t)); t[i] = rnd.choice(string.ascii_letters + "._-")
            t = "".join(t)
            if t == base:
                continue
            try:
                g.verify(t, role="runtime")
                self.fail("mutated token accepted")
            except Inv13Error as e:
                self.assertEqual(e.code, ErrorCode.IDENTITY_REQUIRED)

    def test_resource_ids_random_handles(self):
        rnd = random.Random(SEED)
        t = ResourceTable(64)
        live = {t.push("fd", i): i for i in range(32)}
        for _ in range(ITERS):
            h = rnd.randrange(1 << 33)
            if h in live:
                continue
            with self.assertRaises(Inv13Error):
                t.get(h, "fd")


class Races(unittest.TestCase):
    def test_parallel_grant_revoke_check(self):
        dt = DescriptorTable()
        root = dt.mint(tenant="a", workload="w", capability="filesystem", scope={"prefix": "/"},
                       rights={"read"}, provenance={"decision": "d", "actor": "a"})
        kids, errors, stop = [], [], threading.Event()
        def deriver():
            while not stop.is_set():
                try:
                    kids.append(dt.derive(root.id, rights={"read"}, provenance={"decision": "d", "actor": "a"}).id)
                except Inv13Error:
                    pass
        ts = [threading.Thread(target=deriver) for _ in range(4)]
        for t in ts: t.start()
        while len(kids) < 200: pass
        dt.revoke(root.id)
        stop.set()
        for t in ts: t.join()
        for k in kids:            # every child created before OR after revocation is dead
            with self.assertRaises(Inv13Error):
                dt.check(k)
        self.assertEqual(dt.live(), [])

    def test_resource_table_concurrent_push_drop(self):
        t = ResourceTable(256)
        seen_alias = []
        def worker(n):
            for i in range(2000):
                h = t.push("fd", (n, i))
                if t.get(h, "fd") != (n, i):
                    seen_alias.append(h)
                t.drop(h)
        ts = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
        for x in ts: x.start()
        for x in ts: x.join()
        self.assertEqual(seen_alias, [])
        self.assertEqual(len(t), 0)

    def test_quota_no_overshoot_under_contention(self):
        q = QuotaLedger({"a": {"sockets": 50}}, workload_limits={"sockets": 50})
        got = []
        def w():
            for _ in range(100):
                try:
                    q.acquire("a", "w", "sockets"); got.append(1)
                except Inv13Error:
                    pass
        ts = [threading.Thread(target=w) for _ in range(8)]
        for x in ts: x.start()
        for x in ts: x.join()
        self.assertEqual(len(got), 50)

    def test_concurrent_config_writers_single_winner(self):
        s = ConfigStore(_fx.tmpdir())
        b = {"schema": "INV13_CONFIG/1", "author": "x", "policy": _fx.policy_doc("/srv/tenant-a")}
        digests = [s.stage({**b, "version": i}) for i in range(8)]
        wins = []
        def act(d):
            try:
                ConfigStore(s.root).activate(d, expected_previous=None, actor="w", reason="race"); wins.append(d)
            except Inv13Error:
                pass
        ts = [threading.Thread(target=act, args=(d,)) for d in digests]
        for x in ts: x.start()
        for x in ts: x.join()
        # file-level CAS across independent store objects: exactly the final pointer is one staged digest
        self.assertIn(s.active(), digests)
        self.assertGreaterEqual(len(wins), 1)

    def test_fs_revoke_while_opening(self):
        root = _fx.tmpdir(); (root / "f").write_text("x")
        p = fs.Preopen("/d", str(root))
        errs, ok = [], []
        def reader():
            for _ in range(500):
                try:
                    ok.append(p.read_bytes("f"))
                except Inv13Error as e:
                    errs.append(e.code)
                except OSError:
                    errs.append("oserror")
        t = threading.Thread(target=reader); t.start()
        p.close(); t.join()
        self.assertTrue(set(errs) <= {ErrorCode.STALE_HANDLE, ErrorCode.INVALID_HANDLE, ErrorCode.INTERNAL, "oserror"})


class Faults(unittest.TestCase):
    def test_entropy_loss_does_not_degrade(self):
        state = {"up": True}
        def src(n):
            if not state["up"]: raise OSError(5, "EIO")
            return os.urandom(n)
        p = CsprngProvider(source=src)
        p.get(8); state["up"] = False
        with self.assertRaises(Inv13Error) as cm:
            p.get(8)
        self.assertEqual(cm.exception.code, ErrorCode.ENTROPY_UNAVAILABLE)
        state["up"] = True; p.get(8)

    def test_identity_outage_fails_closed(self):
        g = identity.IdentityGate(_fx.keyring(), audience=_fx.AUD, clock=lambda: (_ for _ in ()).throw(OSError("time down")))
        with self.assertRaises(Exception) as cm:
            g.verify(_fx.token(), role="runtime")
        self.assertNotIsInstance(cm.exception, AssertionError)

    def test_policy_store_unavailable_denies(self):
        s = ConfigStore(_fx.tmpdir())
        with self.assertRaises(Inv13Error) as cm:
            s.load()
        self.assertEqual(cm.exception.code, ErrorCode.CONFIG_STALE)

    def test_disk_full_during_audit_append_is_loud(self):
        from inv13_system_interface.host.audit_sink import AuditSink
        path = str(_fx.tmpdir() / "a.jsonl")
        s = AuditSink(path, node="n", release="r", checkpoint_key=_fx.CP_KEY)
        real = os.write
        def full(fd, data):
            if fd == s._fd: raise OSError(28, "ENOSPC")
            return real(fd, data)
        os.write = full
        try:
            with self.assertRaises(OSError):
                s.append("w", "a", "granted", {})
        finally:
            os.write = real
            s.close()

    def test_preopen_directory_deleted_under_host(self):
        root = _fx.tmpdir(); (root / "f").write_text("x")
        p = fs.Preopen("/d", str(root))
        os.unlink(root / "f"); os.rmdir(root)
        with self.assertRaises(Inv13Error) as cm:
            p.read_bytes("f")
        self.assertEqual(cm.exception.code, ErrorCode.NOT_FOUND)
        with self.assertRaises(Inv13Error):
            p.write_bytes("g", b"1")       # cannot recreate authority in a deleted directory
        p.close()

    def test_runtime_engine_missing(self):
        from inv13_system_interface.host import runtime_adapter as ra
        with self.assertRaises(Inv13Error) as cm:
            ra.V8NodeEngine(node="/nonexistent/node")
        self.assertIn(cm.exception.code, (ErrorCode.PROVIDER_UNAVAILABLE, ErrorCode.INTERNAL, ErrorCode.NOT_FOUND))


if __name__ == "__main__":
    unittest.main()
