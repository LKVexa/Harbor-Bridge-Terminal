"""MC-35..MC-41: integration, property/fuzz, scale/soak, fault-injection,
concurrency and conformance-vector suites. Seeds are fixed; set
INV10_FUZZ_CASES / INV10_SOAK_SECONDS to scale up in CI nightly."""
from __future__ import annotations

import io
import json
import os
import pathlib
import random
import tempfile
import threading
import time
import tracemalloc
import unittest

from _common import PKG_DIR, U, compose, stack
from inv10_component_composition_system import (adapters, controlplane, errors, features, governance, manifest,
                                                observability, schemas, security, wit)
from inv10_component_composition_system.composition import CompositionError, CompositionLimits

EXT = frozenset({"wasi:http/outgoing@0.2.0"})
FUZZ = int(os.environ.get("INV10_FUZZ_CASES", "400"))
SOAK = float(os.environ.get("INV10_SOAK_SECONDS", "1.5"))


def rand_dag(rng, n):
    units = []
    for i in range(n):
        deps = rng.sample(range(i), min(i, rng.randint(0, 3))) if i else []
        units.append(U(f"c{i}", [f"i{d}" for d in deps], [f"i{i}"]))
    rng.shuffle(units)
    return units


class TestIntegrationPipeline(unittest.TestCase):  # MC-35
    """WIT -> INV-09 gate -> INV-11 resolve -> link -> INV-12 -> policy -> env -> store -> activate -> PLN-02."""

    WIT = """package acme:shop@1.0.0;
    interface store { get: func(k: string) -> option<string>; }
    interface handler { handle: func(); }
    world kv { export store; }
    world app { import acme:shop/store@1.0.0; import wasi:http/outgoing@0.2.0; export handler; }"""

    def test_end_to_end(self):
        pkg = wit.parse(self.WIT)
        self.assertEqual(pkg.to_unit("kv").exports, frozenset({"acme:shop/store@1.0.0"}))
        app = pkg.to_unit("app", component_name="app")  # imports acme:shop/store@1.0.0
        # provider was upgraded to a newer minor; INV-11 resolver must rewrite the binding explicitly
        kv = U("kv", (), ["acme:shop/store@1.1.0"])
        units, aliases = adapters.resolve_interfaces([kv, app], adapters.SemverInterfaceResolver())
        self.assertEqual(aliases, {"app": {"acme:shop/store@1.0.0": "acme:shop/store@1.1.0"}})
        v = adapters.ReferenceModuleValidator()
        att = {u.name: v.validate(u.name, b"\x00asm\x0d\x00\x01\x00" + u.name.encode()) for u in units}
        adapters.require_validated(units, att)
        res = compose(units, external=EXT)
        langs = {"kv": adapters.LanguageBinding("kv", "rust"), "app": adapters.LanguageBinding("app", "js")}
        adapters.check_language_interop(res["bindings"], langs)
        ctx = governance.CompositionContext("t1", "shop", "prod")
        governance.LinkPolicy([governance.LinkRule("*", "*")]).enforce(ctx, res["bindings"])
        governance.EnvironmentResolver({"prod": [governance.EnvironmentOffer("wasi:http/outgoing@0.2.1")]},
                                       adapters.SemverInterfaceResolver()).resolve(ctx, res["external_imports"])
        with tempfile.TemporaryDirectory() as d:
            store = controlplane.CompositionStore(d)
            cid = store.put(res)
            controlplane.ActivationController(store, "shop").activate(cid)
            plan = adapters.realization_plan(store.get(cid))
        self.assertEqual([s["instantiate"] for s in plan.steps], ["kv", "app"])
        self.assertEqual(plan.externals, ["wasi:http/outgoing@0.2.0"])

    def test_manifest_cli_roundtrip(self):
        from inv10_component_composition_system import cli
        doc = {"schema": "PK_COMPOSITION_MANIFEST/1", "external": sorted(EXT),
               "components": [schemas.component_document(u) for u in stack()]}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.json")
            pathlib.Path(p).write_text(json.dumps(doc))
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(cli.main(["compose", p]), 0)
            self.assertEqual(json.loads(buf.getvalue())["composition"], compose(stack(), external=EXT)["composition"])
            doc["components"].pop(0)
            pathlib.Path(p).write_text(json.dumps(doc))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["explain", p]), 1)


class TestPropertyFuzz(unittest.TestCase):  # MC-36
    def test_dag_properties(self):
        rng = random.Random(20260922)
        for _ in range(FUZZ):
            units = rand_dag(rng, rng.randint(0, 30))
            a = compose(units)
            b = compose(list(reversed(units)))
            self.assertEqual(a["composition"], b["composition"])
            pos = {n: i for i, n in enumerate(a["order"])}
            for bd in a["bindings"]:
                self.assertLess(pos[bd["provider"]], pos[bd["consumer"]])
            schemas.validate_composition(a)

    def test_graph_mutation_changes_identity(self):
        rng = random.Random(5)
        for _ in range(FUZZ // 4):
            units = rand_dag(rng, rng.randint(2, 15))
            base = compose(units)["composition"]
            i = rng.randrange(len(units))
            u = units[i]
            mutated = units[:i] + [U(u.name, u.imports, set(u.exports) | {f"extra{rng.random()}"})] + units[i + 1:]
            self.assertNotEqual(compose(mutated)["composition"], base)

    def test_malformed_inputs_never_crash(self):
        rng = random.Random(99)
        alphabet = ["a", "b", " ", "\u0000", "​", "é", "é", ":", "/", "@", "\n", "x" * 600]
        for _ in range(FUZZ):
            ident = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 4)))
            try:
                compose([U(ident, [ident] if rng.random() < .3 else [], ["q"])], external=[ident] if rng.random() < .5 else [])
            except CompositionError:
                pass  # every rejection must be a typed CompositionError

    def test_manifest_and_wit_fuzz(self):
        rng = random.Random(3)
        seed_manifest = json.dumps({"schema": "PK_COMPOSITION_MANIFEST/1", "components": [
            schemas.component_document(u) for u in stack()]})
        seed_wit = TestIntegrationPipeline.WIT
        for _ in range(FUZZ):
            for seed, fn in ((seed_manifest, manifest.loads), (seed_wit, wit.parse)):
                s = list(seed)
                for _ in range(rng.randint(1, 5)):
                    s[rng.randrange(len(s))] = rng.choice('{}[]":;,@/ \x00é')
                try:
                    fn("".join(s))
                except CompositionError:
                    pass

    def test_deep_nesting_bounded(self):
        with self.assertRaises(errors.SchemaViolation):
            manifest.loads('{"schema":"PK_COMPOSITION_MANIFEST/1","components":[],"provenance":' + "[" * 40 + "]" * 40 + "}")


class TestScaleSoak(unittest.TestCase):  # MC-38
    def test_large_composition(self):
        units = rand_dag(random.Random(1), 4000)
        t = time.perf_counter()
        r = compose(units)
        self.assertEqual(len(r["order"]), 4000)
        self.assertLess(time.perf_counter() - t, 10.0)

    def test_limits_enforced_at_scale(self):
        with self.assertRaises(errors.CompositionError):
            compose(rand_dag(random.Random(1), 50), limits=CompositionLimits(max_components=49))

    def test_soak_memory_stable(self):
        units = rand_dag(random.Random(2), 200)
        tracemalloc.start()
        compose(units)
        base = tracemalloc.get_traced_memory()[0]
        end = time.monotonic() + SOAK
        n = 0
        while time.monotonic() < end:
            compose(units)
            n += 1
        growth = tracemalloc.get_traced_memory()[0] - base
        tracemalloc.stop()
        self.assertGreater(n, 10)
        self.assertLess(growth, 2 * 1024 * 1024, f"memory grew {growth} bytes over {n} links")

    def test_burst_overload_sheds(self):
        adm = controlplane.AdmissionController(max_concurrent=2, max_per_tenant=2, max_queue=2, queue_timeout=0.2)
        results = []
        gate = threading.Event()

        def work():
            try:
                with adm.admit("t"):
                    gate.wait(0.5)
                    results.append("ok")
            except errors.Overloaded:
                results.append("shed")
        ts = [threading.Thread(target=work) for _ in range(12)]
        [t.start() for t in ts]
        time.sleep(0.05)
        gate.set()
        [t.join() for t in ts]
        self.assertIn("shed", results)
        self.assertIn("ok", results)
        self.assertEqual(adm.running, 0)  # recovered after burst


class TestFaultInjection(unittest.TestCase):  # MC-39
    ctx = governance.CompositionContext("t1", "shop", "prod")

    def test_degraded_dependencies_fail_closed(self):
        kp = security.KeyProvider()
        kid = kp.generate()
        kp.available = False
        with self.assertRaises(errors.DependencyUnavailable):
            governance.ProvenanceVerifier(kp, {"a": {"1"}}).verify(
                governance.ArtifactRecord("a", "1", "0" * 64, "00", kid))
        with self.assertRaises(errors.ExternalUnavailable):
            governance.EnvironmentResolver({}).resolve(self.ctx, ["x"])
        with self.assertRaises(errors.PolicyRejected):
            governance.LinkPolicy().enforce(self.ctx, compose(stack(), external=EXT)["bindings"])

    def test_store_write_failure_is_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            store = controlplane.CompositionStore(d)
            r = compose(stack(), external=EXT)
            real = os.replace
            try:
                controlplane.os.replace = lambda *a: (_ for _ in ()).throw(OSError("disk full"))
                with self.assertRaises(OSError):
                    store.put(r)
            finally:
                controlplane.os.replace = real
            self.assertEqual(store.ids(), [])
            self.assertEqual([p.name for p in (store.root / "objects").rglob(".tmp-*")], [])
            store.put(r)
            self.assertEqual(store.ids(), [r["composition"]])

    def test_truncated_store_object_detected(self):
        with tempfile.TemporaryDirectory() as d:
            store = controlplane.CompositionStore(d)
            cid = store.put(compose(stack(), external=EXT))
            p = store._path(cid)
            p.write_bytes(p.read_bytes()[:40])
            with self.assertRaises(errors.IntegrityError):
                store.get(cid)
            act = controlplane.ActivationController(store, "w")
            with self.assertRaises(errors.IntegrityError):
                act.activate(cid)

    def test_service_refuses_when_keys_down(self):
        from test_extensions import make_service
        with tempfile.TemporaryDirectory() as d:
            svc, auth = make_service(d)
            tok = auth.issue("ci", "operator")
            auth.keys.available = False
            with self.assertRaises(errors.DependencyUnavailable):
                svc.publish(tok, stack(), context=self.ctx, external=EXT)
            self.assertEqual(svc.health()["dependencies"]["keys"], "degraded")

    def test_clock_skew_expires_tokens(self):
        kp = security.KeyProvider()
        kp.generate()
        t = security.Authenticator(kp, clock=lambda: 0.0).issue("a", "admin", ttl=5)
        with self.assertRaises(errors.Unauthenticated):
            security.Authenticator(kp, clock=lambda: 10.0).authenticate(t)


class TestConcurrency(unittest.TestCase):  # MC-40
    def test_concurrent_publication_single_object(self):
        with tempfile.TemporaryDirectory() as d:
            store = controlplane.CompositionStore(d)
            r = compose(stack(), external=EXT)
            errs = []
            def go():
                try:
                    store.put(r)
                except Exception as e:  # pragma: no cover
                    errs.append(e)
            ts = [threading.Thread(target=go) for _ in range(16)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(errs, [])
            self.assertEqual(store.ids(), [r["composition"]])

    def test_stale_controller_cas(self):
        with tempfile.TemporaryDirectory() as d:
            store = controlplane.CompositionStore(d)
            ids = [store.put(compose(stack()[:k], external=EXT)) for k in (1, 2, 3)]
            a1 = controlplane.ActivationController(store, "w")
            a2 = controlplane.ActivationController(store, "w")  # second controller, same pointer
            g = a1.activate(ids[0])["generation"]
            wins, losses = [], []
            barrier = threading.Barrier(2)
            def attempt(ctrl, cid):
                barrier.wait()
                try:
                    wins.append(ctrl.activate(cid, expected_generation=g))
                except errors.Conflict:
                    losses.append(cid)
            # serialize via a shared lock to emulate a file lock across processes
            lock = threading.Lock()
            a1._lock = a2._lock = lock
            ts = [threading.Thread(target=attempt, args=(a1, ids[1])),
                  threading.Thread(target=attempt, args=(a2, ids[2]))]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual((len(wins), len(losses)), (1, 1))

    def test_idempotent_concurrent_service(self):
        from test_extensions import make_service
        with tempfile.TemporaryDirectory() as d:
            svc, auth = make_service(d)
            tok = auth.issue("ci", "publisher")
            ctx = governance.CompositionContext("t1", "w", "prod")
            out = []
            def go():
                out.append(svc.publish(tok, stack(), context=ctx, external=EXT, idempotency_key="same")["composition"])
            ts = [threading.Thread(target=go) for _ in range(8)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(len(set(out)), 1)
            self.assertEqual(svc.d.audit.verify(), len(svc.d.audit.records))

    def test_incremental_linker_threadsafe_cache(self):
        inc = features.IncrementalLinker(capacity=4)
        rng = random.Random(0)
        graphs = [rand_dag(rng, 20) for _ in range(6)]
        def go(i):
            for k in range(30):
                inc.link(graphs[(i + k) % 6])
        ts = [threading.Thread(target=go, args=(i,)) for i in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertLessEqual(len(inc._cache), 4)


class TestConformanceVectors(unittest.TestCase):  # MC-41
    def test_vectors_reproduce(self):
        doc = json.loads((PKG_DIR.parent / "conformance" / "vectors.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["profile"], "PK_COMPOSITION_ID/2")
        self.assertGreaterEqual(len(doc["vectors"]), 10)
        for v in doc["vectors"]:
            units = [U(u["name"], u["imports"], u["exports"]) for u in v["input"]["units"]]
            if "expected_error" in v:
                with self.assertRaises(CompositionError) as cm:
                    compose(units, external=v["input"]["external"])
                self.assertEqual(cm.exception.code, v["expected_error"], v["name"])
            else:
                got = compose(units, external=v["input"]["external"])
                self.assertEqual(got, v["expected"], v["name"])
                # forward-compat: a consumer ignores additive fields
                schemas.validate_composition({**got, "added_in_future": {"x": 1}})

    def test_independent_reimplementation_of_spec(self):
        """Recompute ids straight from docs/IDENTITY_PROFILE.md, without the linker's digest helper."""
        import hashlib
        doc = json.loads((PKG_DIR.parent / "conformance" / "vectors.json").read_text(encoding="utf-8"))
        for v in doc["vectors"]:
            if "expected" not in v:
                continue
            e = v["expected"]
            units = sorted(({"name": u["name"], "imports": sorted(u["imports"]), "exports": sorted(u["exports"])}
                            for u in v["input"]["units"]), key=lambda u: u["name"])
            material = {"schema": "PK_COMPOSITION/1", "identity_profile": "PK_COMPOSITION_ID/2", "units": units,
                        "bindings": e["bindings"], "external_imports": sorted(e["external_imports"])}
            canon = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            self.assertEqual(hashlib.sha256(canon).hexdigest(), e["composition"], v["name"])


if __name__ == "__main__":
    unittest.main()
