"""Unit tests for MC-01..MC-34 and MC-46..MC-50 (stdlib unittest only)."""
from __future__ import annotations

import io
import json
import tempfile
import unittest

from _common import PKG_DIR, U, compose, stack
from inv10_component_composition_system import (adapters, controlplane, errors, features, governance, manifest,
                                                observability, pkcore_compat, schemas, security, wit)

EXT = frozenset({"wasi:http/outgoing@0.2.0"})


class TestDependencyAndSchemas(unittest.TestCase):
    def test_pkcore_missing_is_stable_error(self):  # MC-01
        with self.assertRaises(errors.DependencyUnavailable) as cm:
            pkcore_compat.check()
        self.assertEqual(cm.exception.as_dict()["code"], "DEPENDENCY_UNAVAILABLE")

    def test_version_parse(self):
        self.assertEqual(pkcore_compat._parse("1.4.2rc1"), (1, 4, 2))

    def test_component_schema_roundtrip(self):  # MC-03
        u = stack()[1]
        self.assertEqual(schemas.validate_component(schemas.component_document(u)), u)
        with self.assertRaises(errors.SchemaViolation):
            schemas.validate_component({**schemas.component_document(u), "evil": 1})
        with self.assertRaises(errors.SchemaViolation):
            schemas.validate_component({"schema": "PK_COMPONENT/1", "name": "x", "imports": ["a", "a"]})

    def test_composition_schema(self):  # MC-04
        r = compose(stack(), external=EXT)
        schemas.validate_composition(r)
        schemas.validate_composition({**r, "future_field": 1})  # additive tolerated
        bad = dict(r, order=list(reversed(r["order"])))
        with self.assertRaises(errors.SchemaViolation):
            schemas.validate_composition(bad)
        for f in ("PK_COMPONENT-1.schema.json", "PK_COMPOSITION-1.schema.json",
                  "PK_COMPOSITION_MANIFEST-1.schema.json"):
            self.assertIn("$id", schemas.load_schema(f))


class TestWitAndAdapters(unittest.TestCase):
    SRC = """package acme:kv@1.2.0;
    // storage
    interface store { resource bucket { get: func(k: string) -> option<string>; }
                      record entry { k: string, v: list<u8> }
                      get: func(key: string) -> option<list<u8>>; }
    world provider { export store; }
    world consumer { import store; import wasi:http/outgoing@0.2.0; export acme:app/handler@1.0.0; }"""

    def test_wit_worlds_link(self):  # MC-06
        p = wit.parse(self.SRC)
        self.assertEqual(p.interfaces["store"].resources, ["bucket"])
        r = compose([p.to_unit("provider", component_name="store"), p.to_unit("consumer", component_name="api")],
                    external=EXT)
        self.assertEqual(r["order"], ["store", "api"])

    def test_wit_rejects(self):
        for bad in ["interface x {}", "package a:b;\nworld w { import nope; }", "package a:b;\ninterface x {",
                    "package a:b;\nworld w { frob x; }"]:
            with self.assertRaises(errors.WitParseError):
                wit.parse(bad)

    def test_inv09_gate(self):  # MC-07
        v = adapters.ReferenceModuleValidator()
        att = {"a": v.validate("a", b"\x00asm\x0d\x00\x01\x00")}
        adapters.require_validated([U("a")], att)
        with self.assertRaises(errors.ValidationRequired):
            adapters.require_validated([U("a"), U("b")], att)
        with self.assertRaises(errors.ValidationRequired):
            v.validate("x", b"ELF.....")

    def test_inv11_semver(self):  # MC-08
        r = adapters.SemverInterfaceResolver()
        self.assertTrue(r.compatible("a:b/c@1.2.0", "a:b/c@1.4.1"))
        self.assertFalse(r.compatible("a:b/c@1.5.0", "a:b/c@1.4.1"))
        self.assertFalse(r.compatible("a:b/c@1.0.0", "a:b/c@2.0.0"))
        self.assertFalse(r.compatible("a:b/c@0.2.0", "a:b/c@0.3.0"))
        self.assertFalse(r.compatible("a:b/c@1.0.0-rc1", "a:b/c@1.0.0"))
        units, aliases = adapters.resolve_interfaces(
            [U("p", (), ["a:b/c@1.4.1"]), U("q", ["a:b/c@1.2.0"])], r)
        self.assertEqual(aliases, {"q": {"a:b/c@1.2.0": "a:b/c@1.4.1"}})
        compose(units)
        with self.assertRaises(errors.InterfaceIncompatible):
            adapters.resolve_interfaces([U("p", (), ["a:b/c@1.4.1"]), U("p2", (), ["a:b/c@1.5.0"]),
                                         U("q", ["a:b/c@1.2.0"])], r)

    def test_inv12_interop(self):  # MC-09
        r = compose(stack(), external=EXT)
        langs = {n: adapters.LanguageBinding(n, l) for n, l in [("store", "rust"), ("api", "python"), ("gw", "go")]}
        self.assertEqual(len(adapters.check_language_interop(r["bindings"], langs)), 2)
        langs["store"] = adapters.LanguageBinding("store", "rust", abi="native-c")
        with self.assertRaises(errors.InterfaceIncompatible):
            adapters.check_language_interop(r["bindings"], langs)

    def test_pln02_plan(self):  # MC-10
        r = compose(stack(), external=EXT)
        plan = adapters.realization_plan(r)
        self.assertEqual([s["instantiate"] for s in plan.steps], r["order"])
        wired = {b["consumer"]: {} for b in r["bindings"]}
        for b in r["bindings"]:
            wired[b["consumer"]][b["interface"]] = b.get("provider", "<external>")
        adapters.verify_realization(r, r["order"], wired)
        with self.assertRaises(errors.SchemaViolation):
            adapters.verify_realization(r, list(reversed(r["order"])), wired)


class TestGovernance(unittest.TestCase):
    ctx = governance.CompositionContext("t1", "shop", "prod", "eu-1")

    def test_context_and_tenant(self):  # MC-11
        with self.assertRaises(errors.BoundaryViolation):
            governance.CompositionContext("T 1", "w", "e")
        governance.enforce_tenant_boundary(self.ctx, {"a": "t1", "b": "shared"})
        with self.assertRaises(errors.BoundaryViolation):
            governance.enforce_tenant_boundary(self.ctx, {"a": "t2"})

    def test_policy(self):  # MC-12
        r = compose(stack(), external=EXT)
        pol = governance.LinkPolicy([governance.LinkRule("*", "acme:*"),
                                     governance.LinkRule("api", "wasi:*", "<external>")], version="7")
        self.assertEqual(len(pol.enforce(self.ctx, r["bindings"])), 3)
        pol.rules.append(governance.LinkRule("gw", "acme:app/*", effect="deny"))
        with self.assertRaises(errors.PolicyRejected) as cm:
            pol.enforce(self.ctx, r["bindings"])
        self.assertEqual(cm.exception.details["denied"][0]["reason"], "explicit-deny")
        self.assertFalse(governance.LinkPolicy().decide(self.ctx, r["bindings"][0])["allowed"])

    def test_provenance(self):  # MC-13
        keys = security.KeyProvider()
        kid = keys.generate()
        art = b"\x00asm\x01\x00\x00\x00"
        import hashlib
        d = hashlib.sha256(art).hexdigest()
        _, sig = keys.sign(governance.ProvenanceVerifier.message("store", "1.0.0", d))
        rec = governance.ArtifactRecord("store", "1.0.0", d, sig, kid)
        v = governance.ProvenanceVerifier(keys, {"store": {"1.0.0"}})
        v.verify(rec, art)
        with self.assertRaises(errors.ProvenanceRejected):
            v.verify(rec, art + b"x")
        with self.assertRaises(errors.ProvenanceRejected):
            governance.ProvenanceVerifier(keys, {"store": {"2.0.0"}}).verify(rec)
        with self.assertRaises(errors.ProvenanceRejected):
            v.verify(governance.ArtifactRecord("store", "1.0.0", d, "00" * 32, kid))

    def test_environment_resolver(self):  # MC-14
        env = governance.EnvironmentResolver(
            {"prod": [governance.EnvironmentOffer("wasi:http/outgoing@0.2.3")]},
            adapters.SemverInterfaceResolver())
        self.assertEqual(env.resolve(self.ctx, ["wasi:http/outgoing@0.2.0"]),
                         {"wasi:http/outgoing@0.2.0": "wasi:http/outgoing@0.2.3"})
        with self.assertRaises(errors.ExternalUnavailable):
            env.resolve(self.ctx, ["wasi:kv/store@1.0.0"])
        with self.assertRaises(errors.ExternalUnavailable):
            env.resolve(governance.CompositionContext("t1", "w", "dev"), [])
        low = governance.EnvironmentResolver({"prod": [governance.EnvironmentOffer("x:y/z", trust="tenant")]})
        with self.assertRaises(errors.ExternalUnavailable):
            low.resolve(self.ctx, ["x:y/z"])


class TestManifest(unittest.TestCase):  # MC-15
    DOC = {"schema": "PK_COMPOSITION_MANIFEST/1",
           "context": {"tenant": "t1", "workload": "shop", "environment": "prod"},
           "external": ["wasi:http/outgoing@0.2.0"],
           "components": [schemas.component_document(u) for u in stack()]}

    def test_load(self):
        m = manifest.loads(json.dumps(self.DOC))
        self.assertEqual(compose(m.units, external=m.external)["order"], ["store", "api", "gw"])
        self.assertEqual(m.context.tenant, "t1")

    def test_rejects(self):
        for text in ['{"schema":"PK_COMPOSITION_MANIFEST/1","schema":"x","components":[]}',
                     json.dumps({**self.DOC, "extra": 1}), "not json", '{"schema":"PK_COMPOSITION_MANIFEST/1",'
                     '"components":[{"schema":"PK_COMPONENT/1","name":"a","x":1}]}',
                     '{"schema":"PK_COMPOSITION_MANIFEST/1","components":[],"external":[NaN]}']:
            with self.assertRaises(errors.SchemaViolation):
                manifest.loads(text)
        with self.assertRaises(errors.SchemaViolation) as cm:
            manifest.loads(json.dumps({**self.DOC, "components": [{"schema": "bad", "name": "a"}]}))
        self.assertEqual(cm.exception.details["path"], "$.components[0]")


class TestControlPlane(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_registry(self):  # MC-16
        reg = controlplane.Registry()
        reg.claim("acme:kv/*", "team-kv")
        with self.assertRaises(errors.Conflict):
            reg.claim("acme:*", "team-other")
        reg.register(stack()[0], "1.0.0", "team-kv")
        reg.register(stack()[0], "1.0.0", "team-kv")  # idempotent
        with self.assertRaises(errors.Conflict):
            reg.register(U("store", ["x"], ["acme:kv/store@1.2.0"]), "1.0.0", "team-kv")
        with self.assertRaises(errors.PolicyRejected):
            reg.register(U("rogue", (), ["acme:kv/store@9.0.0"]), "1", "mallory")
        self.assertEqual(reg.resolve("store", "1.0.0"), stack()[0])
        reg.set_state("store", "1.0.0", "withdrawn")
        with self.assertRaises(errors.PolicyRejected):
            reg.resolve("store", "1.0.0")

    def test_store_and_activation(self):  # MC-17, MC-18
        store = controlplane.CompositionStore(self.root)
        a = compose(stack(), external=EXT)
        b = compose(stack()[:2], external=EXT)
        ca, cb = store.put(a), store.put(b)
        self.assertEqual(store.put(a), ca)
        self.assertEqual(store.get(ca)["composition"], ca)
        act = controlplane.ActivationController(store, "shop")
        s1 = act.activate(ca)
        with self.assertRaises(errors.Conflict):
            act.activate(cb, expected_generation=0)
        s2 = act.activate(cb, expected_generation=s1["generation"])
        self.assertEqual(s2["previous"], [ca])
        self.assertEqual(act.rollback()["active"], ca)
        # corruption detection
        p = store._path(cb)
        doc = json.loads(p.read_text())
        doc["bindings"][0]["provider"] = "api"
        p.write_text(json.dumps(doc))
        with self.assertRaises(errors.CompositionError):
            store.get(cb)
        self.assertEqual(store.fsck()["corrupt"], [cb])
        self.assertEqual(store.gc([ca]), [cb])

    def test_config_ledger(self):  # MC-28
        from inv10_component_composition_system.composition import CompositionLimits
        led = controlplane.ConfigLedger(f"{self.root}/cfg.jsonl")
        v1 = led.propose(CompositionLimits(max_components=10), author="ops", source="git:abc")
        v2 = led.propose(CompositionLimits(max_components=20), author="ops", source="git:def")
        led.activate(v1["id"], actor="ops")
        led.activate(v2["id"], actor="ops")
        self.assertEqual(led.active_limits().max_components, 20)
        led.rollback(actor="ops")
        self.assertEqual(controlplane.ConfigLedger(f"{self.root}/cfg.jsonl").active_limits().max_components, 10)

    def test_admission(self):  # MC-29
        adm = controlplane.AdmissionController(max_concurrent=1, max_per_tenant=1, max_queue=0)
        with adm.admit("t1"):
            with self.assertRaises(errors.Overloaded):
                with adm.admit("t2"):
                    pass
        adm2 = controlplane.AdmissionController(max_concurrent=4, max_per_tenant=1, queue_timeout=0.05)
        with adm2.admit("t1"):
            with self.assertRaises(errors.Overloaded):
                with adm2.admit("t1"):
                    pass
            with adm2.admit("t2"):
                pass


def make_service(root, **kw):
    keys = security.KeyProvider()
    keys.generate()
    auth = security.Authenticator(keys)
    deps = controlplane.ServiceDeps(
        store=controlplane.CompositionStore(root), auth=auth,
        audit=security.AuditTrail(f"{root}/audit.jsonl"), metrics=observability.Metrics(),
        logger=observability.StructuredLogger(io.StringIO()), **kw)
    return controlplane.CompositionService(deps), auth


class TestSecurityAndService(unittest.TestCase):
    ctx = governance.CompositionContext("t1", "shop", "prod")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_keys_rotation_and_degraded(self):  # MC-23
        kp = security.KeyProvider()
        k1 = kp.generate()
        kid, sig = kp.sign(b"m")
        k2 = kp.rotate()
        self.assertNotEqual(k1, k2)
        self.assertIn(k1, kp.status()["retired"])
        kp.verification_key(k1)  # old key still verifies
        kp.available = False
        with self.assertRaises(errors.DependencyUnavailable):
            kp.sign(b"m")

    def test_auth(self):  # MC-22
        kp = security.KeyProvider()
        kp.generate()
        clock = [1000.0]
        a = security.Authenticator(kp, clock=lambda: clock[0])
        t = a.issue("alice", "submitter", ttl=10)
        p = a.authenticate(t)
        with self.assertRaises(errors.Unauthenticated):
            a.authorize(p, "publish")
        with self.assertRaises(errors.Unauthenticated):
            a.authenticate(t[:-2] + "00")
        clock[0] += 11
        with self.assertRaises(errors.Unauthenticated):
            a.authenticate(t)

    def test_audit_chain(self):  # MC-21
        path = f"{self.root}/a.jsonl"
        tr = security.AuditTrail(path)
        tr.append("publish", "alice", token="secret-value", composition="abc")
        tr.append("activate", "bob")
        self.assertEqual(security.AuditTrail(path).verify(), 2)
        self.assertNotIn("secret-value", open(path).read())
        lines = open(path).read().splitlines()
        rec = json.loads(lines[0])
        rec["actor"] = "mallory"
        open(path, "w").write(json.dumps(rec) + "\n" + lines[1] + "\n")
        with self.assertRaises(errors.IntegrityError):
            security.AuditTrail(path)

    def test_service_publish_idempotency_replay_quarantine(self):  # MC-30, MC-31
        pol = governance.LinkPolicy([governance.LinkRule("*", "*")])
        svc, auth = make_service(self.root, policy=pol)
        tok = auth.issue("ci", "operator")
        r1 = svc.publish(tok, stack(), context=self.ctx, external=EXT, idempotency_key="k1", nonce="n1")
        with self.assertRaises(errors.Conflict):
            svc.publish(tok, stack(), context=self.ctx, external=EXT, nonce="n1")
        # restart: new service instance recovers idempotency journal from disk
        svc2, _ = make_service(self.root, policy=pol)
        svc2.d.auth = auth
        r2 = svc2.publish(tok, stack(), context=self.ctx, external=EXT, idempotency_key="k1")
        self.assertTrue(r2["idempotent_replay"])
        self.assertEqual(r2["composition"], r1["composition"])
        with self.assertRaises(errors.Conflict):
            svc2.publish(tok, stack()[:2], context=self.ctx, external=EXT, idempotency_key="k1")
        svc.quarantine_component(tok, "store", "CVE-test")
        with self.assertRaises(errors.Quarantined):
            svc.publish(tok, stack(), context=self.ctx, external=EXT)
        svc.set_frozen(tok, True, "incident")
        with self.assertRaises(errors.Frozen):
            svc.publish(tok, stack()[1:], context=self.ctx, external=EXT)
        self.assertEqual(svc.health()["status"], "not-ready")
        events = [r["event"] for r in svc.d.audit.records]
        self.assertIn("quarantine", events)
        self.assertIn("freeze", events)
        with self.assertRaises(errors.Unauthenticated):
            svc.set_frozen(auth.issue("eve", "submitter"), False, "x")


class TestObservability(unittest.TestCase):
    def test_metrics(self):  # MC-24
        m = observability.Metrics()
        m.record_outcome("published", result=compose(stack(), external=EXT), latency_ms=3)
        m.record_outcome("refused", error={"code": "UNSATISFIED_IMPORT", "details": {"interface": 'x"y'}})
        m.record_outcome("refused", error={"code": "COMPOSITION_CYCLE", "details": {}})
        text = m.render_prometheus()
        self.assertIn('inv10_compositions_total{outcome="refused"} 2.0', text)
        self.assertIn('interface="x\\"y"', text)
        self.assertIn("inv10_cycles_detected_total 1.0", text)
        self.assertIn('inv10_link_latency_ms_bucket{le="5"} 1', text)

    def test_logs_and_trace(self):  # MC-25
        buf = io.StringIO()
        lg = observability.StructuredLogger(buf)
        parent = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        child = observability.child_traceparent(parent)
        self.assertTrue(child.startswith("00-" + "a" * 32))
        lg.log("info", "x", operation_id="op1", traceparent=child, token="t0p", tenant="t1")
        rec = json.loads(buf.getvalue())
        self.assertEqual(rec["token"], "[REDACTED]")
        self.assertEqual(rec["tenant"], "t1")
        import random
        quiet = observability.StructuredLogger(io.StringIO(), sample_rate=0.0, rng=random.Random(1))
        self.assertIsNone(quiet.log("info", "x", operation_id="o"))
        self.assertIsNotNone(quiet.log("error", "x", operation_id="o"))

    def test_health_and_explain(self):  # MC-26, MC-27
        from inv10_component_composition_system.composition import DEFAULT_LIMITS
        h = observability.health_report(version="4.3.0", limits=DEFAULT_LIMITS,
                                        dependencies={"ok": lambda: True, "bad": lambda: 1 / 0})
        self.assertEqual(h["status"], "not-ready")
        self.assertEqual(h["dependencies"]["bad"], "down:ZeroDivisionError")
        units = stack() + [U("dup", (), ["acme:kv/store@1.2.0"])]
        rep = observability.explain(units, external=EXT)
        row = next(r for r in rep["imports"] if r["consumer"] == "api" and r["interface"].startswith("acme"))
        self.assertEqual(row["status"], "ambiguous")
        self.assertIn("REFUSED", observability.render_explain_text(
            {**rep, "error": {"code": "AMBIGUOUS_EXPORT", "message": "m"}}))
        ok = observability.explain(stack(), external=EXT, result=compose(stack(), external=EXT))
        self.assertEqual(ok["depth"]["gw"], 2)
        self.assertEqual(ok["unused_exports"], ["wasi:http/incoming-handler@0.2.0"])


class TestFeatures(unittest.TestCase):
    def test_alias(self):  # MC-47
        units = [U("p", (), ["kv@2"]), U("c", ["storage"])]
        r = features.compose_extended(units, aliases={"c": {"storage": "kv@2"}})
        self.assertEqual(r["bindings"][0]["provider"], "p")
        self.assertEqual(r["aliases"], {"c": {"storage": "kv@2"}})
        with self.assertRaises(errors.CompositionError):
            features.apply_aliases(units, {"c": {"nope": "kv@2"}})
        with self.assertRaises(errors.CompositionError):
            features.apply_aliases(units, {"ghost": {}})

    def test_dead_exports(self):  # MC-48
        r = features.compose_extended(stack(), external=EXT, eliminate_dead=True)
        self.assertEqual(r["eliminated_exports"], [{"component": "gw", "interface": "wasi:http/incoming-handler@0.2.0"}])
        base = compose(stack(), external=EXT)
        self.assertNotEqual(r["composition"], base["composition"])
        kept = features.compose_extended(stack(), external=EXT, eliminate_dead=True,
                                         keep_exports=["wasi:http/incoming-handler@0.2.0"])
        self.assertEqual(kept["composition"], base["composition"])

    def test_incremental(self):  # MC-46
        inc = features.IncrementalLinker()
        inc.apply(upsert=stack(), external=EXT)
        r = inc.apply(upsert=[U("store", (), ["acme:kv/store@1.2.0", "acme:kv/admin@1.0.0"])])
        self.assertEqual(r["changed"], ["store"])
        self.assertEqual(r["affected"], ["api", "gw", "store"])
        inc.link(stack(), EXT)
        inc.link(stack(), EXT)
        self.assertGreaterEqual(inc.hits, 1)
        before = dict(inc.units)
        with self.assertRaises(errors.CompositionError):
            inc.apply(remove=["store"])
        self.assertEqual(inc.units, before)  # failed relink leaves state intact

    def test_nested(self):  # MC-49
        inner = compose(stack()[:2], external=EXT)
        outer = features.compose_nested([U("gw", ["acme:app/handler@1.0.0"])], {"backend": (inner, None)},
                                        external=EXT)
        self.assertEqual(outer["order"], ["backend", "gw"])
        self.assertEqual(outer["external_imports"], ["wasi:http/outgoing@0.2.0"])
        self.assertEqual(outer["nested"], {"backend": inner["composition"]})
        with self.assertRaises(errors.CompositionError):
            features.as_unit(inner, "x", exports=["nope"])

    def test_diff(self):  # MC-50
        a = compose(stack(), external=EXT)
        b = compose([U("store2", (), ["acme:kv/store@1.2.0"])] + stack()[1:], external=EXT)
        d = features.diff(a, b)
        self.assertTrue(d["identity_changed"])
        self.assertEqual(d["providers_changed"], [{"interface": "acme:kv/store@1.2.0", "from": "store", "to": "store2"}])
        self.assertEqual(d["impacted_consumers"], ["api"])
        self.assertFalse(features.diff(a, a)["identity_changed"])

    def test_migration(self):  # MC-33
        a = compose(stack(), external=EXT)
        recs = [{"legacy_id": features.legacy_id_41(a), "units": [schemas.component_document(u) for u in stack()],
                 "external": sorted(EXT)},
                {"legacy_id": "deadbeef" * 3},
                {"legacy_id": "cafe" * 6, "units": [{"name": "s", "imports": ["x"], "exports": ["x"]}]}]
        out = features.migrate_legacy(recs)
        self.assertEqual(out["summary"], {"remapped": 1, "unrecoverable": 1, "failed": 1})
        self.assertEqual(out["remap"][0]["composition"], a["composition"])
        self.assertTrue(out["remap"][0]["legacy_reconstruction_matches"])
        self.assertEqual(out["failed"][0]["error"]["code"], "COMPOSITION_CYCLE")


class TestArtifactsPresent(unittest.TestCase):  # MC-19/20/32/34/42/43/44/45 artifact presence
    def test_files(self):
        root = PKG_DIR.parent
        for rel in ["pyproject.toml", "docs/ADR-0001-inv10-composition.md", "docs/OWNERSHIP.md",
                    "docs/COMPATIBILITY.json", "SECURITY.md", "docs/IDENTITY_PROFILE.md", "sbom.cdx.json",
                    ".github/workflows/inv10.yml", "conformance/vectors.json", "tools/sign_release.py"]:
            self.assertTrue((root / rel).exists(), rel)
        json.loads((root / "docs/COMPATIBILITY.json").read_text())


if __name__ == "__main__":
    unittest.main()
