"""M09 M10 M11 M16 M20 M21 M22 M23 M67 - results, lifecycle, interfaces, negotiation, limits."""
import json, pathlib, random, shutil, subprocess, unittest
from _harness import World
from inv60_wasm_application_fabric.fabric import errors, lifecycle as lc, negotiation as ng, wire, limits
from inv60_wasm_application_fabric.fabric.errors import FabricError, Result, REGISTRY
from inv60_wasm_application_fabric.fabric.identity import new_keypair

PKG = pathlib.Path(__file__).resolve().parents[1]


class ResultModel(unittest.TestCase):
    def test_every_code_roundtrips_and_validates(self):
        sch = wire.load("RESULT")
        for code in REGISTRY:
            w = Result(code, message="m").to_wire()
            self.assertEqual(wire.validate(w, sch), [], code)
            self.assertEqual(Result.from_wire(json.loads(json.dumps(w))).code, code)

    def test_numbers_unique_and_registry_matches_published(self):
        nums = [v[0] for v in REGISTRY.values()]
        self.assertEqual(len(nums), len(set(nums)))
        pub = json.loads((PKG / "schemas/ERROR_REGISTRY.json").read_text())["codes"]
        self.assertEqual(set(pub), set(REGISTRY))
        for k, v in REGISTRY.items():
            self.assertEqual(pub[k]["number"], v[0])

    def test_unknown_code_maps_to_unknown(self):
        self.assertEqual(Result.from_wire({"code": "FROM_THE_FUTURE"}).code, "UNKNOWN")

    def test_retry_hints(self):
        self.assertEqual(Result("RATE_LIMITED", retry_after_s=2).to_wire()["retry_after_s"], 2.0)
        self.assertNotIn("retry_after_s", Result("PERMISSION_DENIED", retry_after_s=2).to_wire())
        self.assertEqual(Result("DIGEST_MISMATCH").retry, "never")

    def test_size_bound_and_redaction(self):
        r = Result("INTERNAL", message="x" * 10000, detail={f"k{i}": "v" * 300 for i in range(40)},
                   per_target=[Result("OK") for _ in range(200)])
        w = r.to_wire()
        self.assertLessEqual(len(json.dumps(w, sort_keys=True)), errors.MAX_SERIALIZED_ERROR_BYTES)
        d = errors.redact_detail({"api_key": "s3cr3t", "note": "-----BEGIN PRIVATE KEY-----abc-----END PRIVATE KEY-----"})
        self.assertEqual(d["api_key"], "[REDACTED]")
        self.assertNotIn("abc", d["note"])

    def test_exception_mapping(self):
        from inv60_wasm_application_fabric import runtime as rt
        for exc, code in [(rt.DigestMismatch("x"), "DIGEST_MISMATCH"), (rt.NotLinked("x"), "NOT_LINKED"),
                          (rt.AlreadyRunning("x"), "ALREADY_EXISTS"), (rt.UnknownArtifact("x"), "NOT_FOUND"),
                          (TimeoutError(), "DEADLINE_EXCEEDED"), (RuntimeError(), "INTERNAL")]:
            self.assertEqual(errors.map_exception(exc), code)

    def test_public_boundary_never_raises(self):
        w = World()
        r = w.fabric.start("garbage", "api", "sha256:" + "0" * 64, tenant="tenant-a")
        self.assertIsInstance(r, Result)
        self.assertEqual(r.code, "UNAUTHENTICATED")

    def test_partial_fanout_has_per_target(self):
        w = World(hosts=("h1", "h2"), regions={"h1": "eu", "h2": "us"})
        w.deploy("a", regions=("eu",)); w.deploy("b", name="tenant-a/b", data=b"b", app="x")
        w.mono.advance(9); w.fabric.heartbeat("h2")
        res = w.fabric.sweep()
        self.assertTrue(res)
        self.assertTrue(res[0].per_target)


class Lifecycle(unittest.TestCase):
    def test_tables_valid(self):
        self.assertEqual(lc.validate_tables(), [])

    def test_illegal_transition(self):
        m = lc.component_machine("c")
        with self.assertRaises(FabricError) as cm:
            m.fire("ready")
        self.assertEqual(cm.exception.code, "ILLEGAL_TRANSITION")

    def test_idempotent_repeat(self):
        m = lc.link_machine("l"); m.fire("grant"); m.fire("revoke")
        self.assertEqual(m.fire("revoke"), ("revoked", "noop"))

    def test_model_based_random_sequences(self):
        rng = random.Random(60)
        events = sorted({e for (_, e) in lc.COMPONENT_TABLE})
        for _ in range(300):
            m = lc.component_machine("c")
            for _ in range(20):
                ev = rng.choice(events)
                before = m.state
                try:
                    m.fire(ev)
                    self.assertIn(m.state, lc.COMPONENT_STATES)
                except FabricError as e:
                    self.assertEqual(e.code, "ILLEGAL_TRANSITION")
                    self.assertEqual(m.state, before)   # refused transitions do not mutate

    def test_fabric_start_stop_idempotent(self):
        w = World()
        self.assertEqual(w.deploy().code, "OK")
        self.assertEqual(w.fabric.stop(w.tok("deployer-a"), "api", tenant="tenant-a").code, "OK")
        self.assertEqual(w.fabric.stop(w.tok("deployer-a"), "api", tenant="tenant-a").code, "OK")
        ref = w.fabric.push(w.tok("deployer-a"), "tenant-a/api", b"\x00asm-component-v1", w.artifact(), tenant="tenant-a").value
        self.assertEqual(w.fabric.start(w.tok("deployer-a"), "api", ref, tenant="tenant-a").code, "OK")
        self.assertEqual(w.fabric.start(w.tok("deployer-a"), "api", ref, tenant="tenant-a").code, "ALREADY_EXISTS")

    def test_idempotency_key(self):
        w = World()
        ref = w.fabric.push(w.tok("deployer-a"), "tenant-a/api", b"\x00asm-component-v1", w.artifact(), tenant="tenant-a").value
        r1 = w.fabric.start(w.tok("deployer-a"), "api", ref, tenant="tenant-a", idempotency_key="key-0001")
        r2 = w.fabric.start(w.tok("deployer-a"), "api", ref, tenant="tenant-a", idempotency_key="key-0001")
        self.assertEqual(r1.operation_id, r2.operation_id)
        with self.assertRaises(FabricError):
            w.fabric.start(w.tok("deployer-a"), "api2", ref, tenant="tenant-a", idempotency_key="key-0001")

    def test_markdown_table_generated(self):
        self.assertIn("| component | absent | stage | staged |", lc.transition_table_markdown())


class Interfaces(unittest.TestCase):
    def test_fixtures_python(self):
        idx = json.loads((PKG / "fixtures/INDEX.json").read_text())
        n = 0
        for name in idx["files"]:
            if not name.endswith(".json"):
                continue
            fx = json.loads((PKG / "fixtures" / name).read_text())
            ok = wire.validate(fx["instance"], wire.load(fx["schema"])) == []
            self.assertEqual(ok, fx["expect_valid"], name)
            n += 1
        self.assertGreaterEqual(n, 40)

    def test_fixtures_regenerate_deterministically(self):
        before = (PKG / "fixtures/INDEX.json").read_bytes()
        subprocess.run(["python3", "-B", str(PKG / "tools/gen_fixtures.py")], check=True, capture_output=True)
        self.assertEqual(before, (PKG / "fixtures/INDEX.json").read_bytes())

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_fixtures_cross_language_node(self):
        p = subprocess.run(["node", str(PKG / "fixtures/validate.mjs")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn('"failures":0', p.stdout)

    def test_no_pickles(self):
        self.assertFalse(list((PKG / "fixtures").glob("*.pkl")) + list((PKG / "fixtures").glob("*.pickle")))

    def test_wit_declares_three_protocols(self):
        wit = (PKG / "wit/lattice.wit").read_text()
        self.assertIn("package inv60:lattice@1.0.0;", wit)
        for p in ("PK_LATTICE_START/1", "PK_LATTICE_LINK/1", "PK_LATTICE_CALL/1"):
            self.assertIn(p, wit)

    def test_decode_bounds_before_parse(self):
        with self.assertRaises(FabricError) as cm:
            wire.decode(b"{" * (wire.MAX_WIRE_BYTES + 1), "PK_LATTICE_CALL")
        self.assertEqual(cm.exception.code, "PAYLOAD_TOO_LARGE")
        with self.assertRaises(FabricError) as cm:
            wire.decode(b"{not json", "PK_LATTICE_CALL")
        self.assertEqual(cm.exception.code, "INVALID_ARGUMENT")


class Negotiation(unittest.TestCase):
    def setUp(self):
        self.seed, self.pub = new_keypair()

    def test_select_highest_common(self):
        r = ng.negotiate(ng.offer(self.seed, lo="1.0", hi="1.1", features=("batching", "x-unknown")), self.pub)
        self.assertEqual(r["version"], "1.1")
        self.assertEqual(r["features"], ["batching"])

    def test_pairwise_matrix(self):
        for lo, hi in [("1.0", "1.0"), ("1.0", "1.1"), ("1.1", "1.1"), ("0.9", "1.0")]:
            r = ng.negotiate(ng.offer(self.seed, lo=lo, hi=hi), self.pub)
            self.assertIn(r["version"], ("1.0", "1.1"))

    def test_no_overlap(self):
        with self.assertRaises(FabricError) as cm:
            ng.negotiate(ng.offer(self.seed, lo="2.0", hi="2.5"), self.pub)
        self.assertEqual(cm.exception.code, "UNSUPPORTED_VERSION")

    def test_minimum_enforced_downgrade(self):
        with self.assertRaises(FabricError):
            ng.negotiate(ng.offer(self.seed, lo="0.1", hi="1.0"), self.pub, minimum=(1, 1))

    def test_unauthenticated_offer(self):
        o = ng.offer(self.seed); o["body"]["versions"] = ["0.1", "0.2"]
        with self.assertRaises(FabricError) as cm:
            ng.negotiate(o, self.pub)
        self.assertEqual(cm.exception.code, "UNAUTHENTICATED")

    def test_malformed(self):
        for bad in (["1", "2"], ["1.1", "1.0"], ["1.0"]):
            o = ng.offer(self.seed); o["body"]["versions"] = bad
            o["sig"] = ng.ed25519.sign(self.seed, ng.canonical(o["body"])).hex()
            with self.assertRaises(FabricError):
                ng.negotiate(o, self.pub)

    def test_cache_bounded_and_reconnect(self):
        from _harness import Clock
        c = Clock(); cache = ng.NegotiationCache(clock=c)
        cache.put("p", {"version": "1.1", "expires_at": c() + 10})
        self.assertIsNotNone(cache.get("p"))
        cache.on_reconnect("p")
        self.assertIsNone(cache.get("p"))
        cache.put("p", {"version": "1.1", "expires_at": c() + 10}); c.advance(11)
        self.assertIsNone(cache.get("p"))


class ResourceLimits(unittest.TestCase):
    def test_bounds_reject_unsafe(self):
        for k, v in [("max_payload_bytes", 0), ("max_payload_bytes", 10**12), ("rate_per_tenant", True), ("nope", 1)]:
            with self.assertRaises(FabricError):
                limits.validate_limits({k: v})

    def test_payload_limit_boundaries(self):
        L = limits.Limiter({"max_payload_bytes": 100})
        L.check_payload(99); L.check_payload(100)
        with self.assertRaises(FabricError):
            L.check_payload(101)

    def test_token_bucket_burst_and_refill(self):
        from _harness import Clock
        c = Clock(0.0)
        L = limits.Limiter({"rate_per_tenant": 10.0, "burst_per_tenant": 5}, clock=c)
        for _ in range(5):
            L.rate("t")
        with self.assertRaises(FabricError) as cm:
            L.rate("t")
        self.assertEqual(cm.exception.code, "RATE_LIMITED")
        self.assertGreater(cm.exception.retry_after_s, 0)
        L.rate("other")                     # fairness: another tenant unaffected
        c.advance(0.1); L.rate("t")

    def test_inflight_per_tenant_and_global(self):
        L = limits.Limiter({"max_inflight_per_tenant": 2, "max_inflight_global": 3})
        L.acquire("a"); L.acquire("a")
        with self.assertRaises(FabricError) as cm:
            L.acquire("a")
        self.assertEqual(cm.exception.code, "QUOTA_EXCEEDED")
        L.acquire("b")
        with self.assertRaises(FabricError) as cm:
            L.acquire("c")
        self.assertEqual(cm.exception.code, "OVERLOADED")
        L.release("a"); L.acquire("c")

    def test_fabric_component_quota(self):
        w = World(limits={"max_components_per_tenant": 1})
        self.assertEqual(w.deploy("a1", name="tenant-a/a1", data=b"1").code, "OK")
        self.assertEqual(w.deploy("a2", name="tenant-a/a2", data=b"2").code, "QUOTA_EXCEEDED")

    def test_link_quota(self):
        w = World(limits={"max_links_per_component": 1})
        w.deploy()
        f = w.fabric
        self.assertEqual(f.link(w.tok("deployer-a"), "api", "l1", print, tenant="tenant-a", grantee=w.p["api"].id).code, "OK")
        self.assertEqual(f.link(w.tok("deployer-a"), "api", "l2", print, tenant="tenant-a", grantee=w.p["api"].id).code, "QUOTA_EXCEEDED")


if __name__ == "__main__":
    unittest.main()
