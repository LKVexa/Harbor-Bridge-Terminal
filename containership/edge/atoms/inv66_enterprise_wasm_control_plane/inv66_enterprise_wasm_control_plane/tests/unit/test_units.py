"""Unit tests for every production module (MC-011..MC-054 building blocks)."""
from __future__ import annotations

import io
import json
import os
import random
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.support import EcpError, Estate, FakeClock
from inv66_enterprise_wasm_control_plane.production import errors, schema
from inv66_enterprise_wasm_control_plane.production.config import ConfigManager, build_policy, load_layers
from inv66_enterprise_wasm_control_plane.production.identity import Authenticator, StaticJwks, mint_token, ReplayCache
from inv66_enterprise_wasm_control_plane.production.journal import Journal, verify_export
from inv66_enterprise_wasm_control_plane.production.keys import Keyring, LocalSecretProvider, Signer
from inv66_enterprise_wasm_control_plane.production.lifecycle import Lifecycle, TRANSITIONS, TERMINAL
from inv66_enterprise_wasm_control_plane.production.policy_engine import evaluate_local
from inv66_enterprise_wasm_control_plane.production.provenance import verify_component, sign_component
from inv66_enterprise_wasm_control_plane.production.quarantine import QuarantineController
from inv66_enterprise_wasm_control_plane.production.quota import Quotas
from inv66_enterprise_wasm_control_plane.production.rbac import Binding, Rbac
from inv66_enterprise_wasm_control_plane.production.identity import Principal
from inv66_enterprise_wasm_control_plane.production.resilience import (CircuitBreaker, Deadline, IdempotencyStore,
                                                                       LoadShedder, RetryPolicy, DependencyHealth)
from inv66_enterprise_wasm_control_plane.production.telemetry import Logger, Metrics, Tracer


def tmp() -> Path:
    d = Path(tempfile.mkdtemp(prefix="inv66-u-"))
    return d


class ErrorRegistryTest(unittest.TestCase):
    def test_codes_and_wires_unique_and_envelope_safe(self):
        specs = list(errors.REGISTRY.values())
        self.assertEqual(len({s.wire for s in specs}), len(specs))
        e = errors.EcpError("ECP_FORBIDDEN", "nope", scope="a/b", token="SECRET", password="x")
        env = e.envelope("r1")
        self.assertNotIn("token", env["details"])
        self.assertNotIn("SECRET", json.dumps(env))
        schema.validate(env, "PK_ECP_ERROR_1")

    def test_unknown_code_becomes_internal(self):
        self.assertEqual(errors.EcpError("NOPE", "x").code, "ECP_INTERNAL")

    def test_registry_digest_pinned(self):
        pin = (Path(schema.SCHEMA_DIR) / "ERROR_REGISTRY.pin").read_text().split()[0]
        self.assertEqual(pin, errors.registry_digest(), "error registry changed: bump REGISTRY_VERSION and re-pin")


class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.idp = Signer("k1")
        self.jwks = StaticJwks({"https://idp": {"k1": self.idp.public_b64()}})
        self.auth = Authenticator(self.jwks, audience="aud", clock=self.clock, single_use=True, trust_domain="acme.example")

    def tok(self, **over):
        t = self.clock()
        c = {"iss": "https://idp", "aud": "aud", "sub": "ops", "org": "acme", "iat": t, "nbf": t, "exp": t + 60,
             "jti": os.urandom(8).hex()}
        c.update(over)
        return mint_token(self.idp, c)

    def test_valid(self):
        p = self.auth.authenticate_token(self.tok())
        self.assertEqual((p.subject, p.org, p.kind), ("ops", "acme", "user"))

    def test_rejections(self):
        bad = [self.tok(aud="other"), self.tok(iss="https://evil"), self.tok(exp=self.clock() - 100),
               self.tok(nbf=self.clock() + 100), self.tok(exp=self.clock() + 99999), self.tok(jti=""),
               self.tok(kind="root"), "a.b", "x" * 9000, None, 42]
        forged = mint_token(Signer("k1"), {"iss": "https://idp", "aud": "aud", "sub": "ops", "org": "acme",
                                           "iat": self.clock(), "nbf": self.clock(), "exp": self.clock() + 60, "jti": "z"})
        bad.append(forged)
        h, c, s = self.tok().split(".")
        import base64
        none_hdr = base64.urlsafe_b64encode(b'{"alg":"none","kid":"k1"}').rstrip(b"=").decode()
        bad.append(f"{none_hdr}.{c}.{s}")
        bad.append(f"{h}.{c[:-2]}xx.{s}")
        for t in bad:
            with self.assertRaises(EcpError) as cm:
                self.auth.authenticate_token(t)
            self.assertEqual(cm.exception.code, "ECP_UNAUTHENTICATED")

    def test_replay_single_use(self):
        t = self.tok()
        self.auth.authenticate_token(t)
        with self.assertRaises(EcpError) as cm:
            self.auth.authenticate_token(t)
        self.assertEqual(cm.exception.code, "ECP_REPLAY_DETECTED")

    def test_replay_cache_bounded_fail_closed(self):
        rc = ReplayCache(capacity=2)
        self.assertTrue(rc.check_and_add("a", 100, 0))
        self.assertTrue(rc.check_and_add("b", 100, 0))
        self.assertFalse(rc.check_and_add("c", 100, 0))  # full of live entries -> refuse
        self.assertTrue(rc.check_and_add("c", 200, 150))  # expired entries evicted

    def test_spiffe_peer(self):
        p = self.auth.authenticate_peer("spiffe://acme.example/ns/payments/sa/deployer")
        self.assertEqual((p.subject, p.tenant, p.kind), ("payments/deployer", "payments", "workload"))
        for bad in ("spiffe://evil.example/ns/payments/sa/x", "https://x", "spiffe://acme.example/ns/../sa/x", None):
            with self.assertRaises(EcpError):
                self.auth.authenticate_peer(bad)


class RbacTest(unittest.TestCase):
    def setUp(self):
        self.rb = Rbac({}, [Binding.from_doc(b) for b in [
            {"subject": "c", "role": "deployer", "scope": "acme/pay", "effect": "allow"},
            {"subject": "c", "role": "deployer", "scope": "acme/pay/prod", "effect": "deny"},
            {"group": "g", "role": "viewer", "scope": "acme", "effect": "allow"},
            {"subject": "ta", "role": "tenant-admin", "scope": "acme/pay", "effect": "allow"}]])

    def p(self, sub, groups=(), org="acme", kind="user", tenant=None):
        return Principal(subject=sub, kind=kind, issuer="i", org=org, groups=tuple(groups), tenant=tenant)

    def test_hierarchy_and_deny_overrides(self):
        self.rb.check(self.p("c"), "admit", ("acme", "pay", "staging"))
        with self.assertRaises(EcpError):
            self.rb.check(self.p("c"), "admit", ("acme", "pay", "prod"))
        self.rb.check(self.p("x", ["g"]), "inventory.read", ("acme", "any", "l"))
        with self.assertRaises(EcpError):
            self.rb.check(self.p("x", ["g"]), "admit", ("acme", "any", "l"))

    def test_cross_org_and_workload_confinement(self):
        with self.assertRaises(EcpError):
            self.rb.check(self.p("c", org="other"), "admit", ("acme", "pay", "staging"))
        rb = Rbac({}, [Binding.from_doc({"subject": "w", "role": "deployer", "scope": "acme", "effect": "allow"})])
        rb.check(self.p("w", kind="workload", tenant="pay"), "admit", ("acme", "pay", "x"))
        with self.assertRaises(EcpError):
            rb.check(self.p("w", kind="workload", tenant="pay"), "admit", ("acme", "other", "x"))

    def test_delegation_cannot_escalate_or_escape_scope(self):
        ta = self.p("ta")
        self.rb.check_delegation(ta, Binding.from_doc({"subject": "n", "role": "deployer", "scope": "acme/pay/dev", "effect": "allow"}))
        for b in ({"subject": "n", "role": "org-admin", "scope": "acme/pay", "effect": "allow"},
                  {"subject": "n", "role": "deployer", "scope": "acme/other", "effect": "allow"},
                  {"subject": "n", "role": "auditor", "scope": "acme/pay", "effect": "allow"}):
            with self.assertRaises(EcpError):
                self.rb.check_delegation(ta, Binding.from_doc(b))

    def test_explain(self):
        ex = self.rb.explain(self.p("c"), "admit", ("acme", "pay", "prod"))
        self.assertFalse(ex["allowed"])
        self.assertEqual(len(ex["matched_bindings"]), 2)

    def test_binding_needs_one_principal(self):
        with self.assertRaises(EcpError):
            Binding.from_doc({"role": "viewer", "scope": "acme", "effect": "allow"})


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.e = Estate(approvals=2)
        self.cm = self.e.service.config

    def test_dual_authorization_and_author_exclusion(self):
        doc = self.e.config(site="eu-west-2")
        gen = self.cm.stage(doc, author="alice", source_repo="git", source_rev="b" * 40)
        with self.assertRaises(EcpError):
            self.cm.approve(gen, "alice")
        self.cm.approve(gen, "bob")
        cur = self.cm.active.generation
        with self.assertRaises(EcpError) as cm:
            self.cm.activate(gen, activated_by="bob", expected_active=cur)
        self.assertEqual(cm.exception.code, "ECP_DUAL_AUTH_REQUIRED")
        self.cm.approve(gen, "carol")
        self.cm.activate(gen, activated_by="bob", expected_active=cur)
        self.assertEqual(self.cm.active.generation, gen)
        h = self.cm.history()[-1]
        self.assertEqual((h["author"], h["approvers"], h["previous"]), ("alice", ["bob", "carol"], cur))

    def test_cas_conflict_and_rollback(self):
        first = self.cm.active.generation
        gen = self.cm.stage(self.e.config(site="x"), author="a", source_repo="g", source_rev="c")
        self.cm.approve(gen, "b"); self.cm.approve(gen, "c")
        with self.assertRaises(EcpError) as cm:
            self.cm.activate(gen, activated_by="b", expected_active="0" * 64)
        self.assertEqual(cm.exception.code, "ECP_CONFIG_CONFLICT")
        self.cm.activate(gen, activated_by="b", expected_active=first)
        self.cm.rollback(first, activated_by="b", reason="bad site")
        self.assertEqual(self.cm.active.generation, first)
        # the restarted service ends on the same generation (replay)
        self.assertEqual(self.e.open().config.active.generation, first)

    def test_invalid_config_never_staged(self):
        head = self.e.service.journal.head
        for bad in (self.e.config(org="other"), self.e.config(registries=[]),
                    self.e.config(signers=[{"id": "s", "public_key": "A" * 44, "scope": "acme"}]),
                    {**self.e.config(), "extra": 1},
                    self.e.config(provenance={"require_digest": True, "require_signature": False})):
            with self.assertRaises(EcpError):
                self.cm.stage(bad, author="a", source_repo="g", source_rev="r")
        self.assertEqual(self.e.service.journal.head, head)

    def test_layered_overrides(self):
        d = tmp()
        (d / "base.json").write_text(json.dumps(self.e.config()))
        (d / "prod.json").write_text(json.dumps({"limits": {"max_components": 10}}))
        (d / "site.json").write_text(json.dumps({"site": "us-east-1"}))
        doc = load_layers(d / "base.json", d / "prod.json", d / "site.json")
        p = build_policy(doc)
        self.assertEqual((p.limits["max_components"], p.doc["site"], p.limits["max_manifest_bytes"]),
                         (10, "us-east-1", 1_000_000))

    def test_diff(self):
        a = self.cm.active.generation
        b = self.cm.stage(self.e.config(site="y"), author="a", source_repo="g", source_rev="r")
        self.assertEqual(list(self.cm.diff(a, b)), ["site"])


class KeysTest(unittest.TestCase):
    def test_seal_open_rotate_retire(self):
        kr = Keyring()
        k1 = kr.rotate()
        env = kr.seal(b"secret", b"ctx")
        self.assertEqual(kr.open(env, b"ctx"), b"secret")
        with self.assertRaises(EcpError):
            kr.open(env, b"other")
        k2 = kr.rotate()
        self.assertEqual(kr.open(env, b"ctx"), b"secret")  # old key still decrypts
        self.assertEqual(kr.seal(b"x", b"c")["kid"], k2)
        kr.retire(k1)
        with self.assertRaises(EcpError):
            kr.open(env, b"ctx")
        with self.assertRaises(EcpError):
            kr.retire(k2)

    def test_secret_provider(self):
        sp = LocalSecretProvider(environ={"A": "Zq9-secret"})
        self.assertEqual(sp.resolve("env:A"), b"Zq9-secret")
        for bad in ("env:B", "nope", "ftp:x"):
            with self.assertRaises(EcpError) as cm:
                sp.resolve(bad)
            self.assertNotIn("Zq9", json.dumps(cm.exception.envelope()))
        d = tmp()
        (d / "s").write_text("zz")
        self.assertEqual(LocalSecretProvider(allowed_dirs=(str(d),)).resolve(f"file:{d}/s"), b"zz")
        with self.assertRaises(EcpError):
            LocalSecretProvider(allowed_dirs=(str(d),)).resolve("file:/etc/hostname")


class JournalTest(unittest.TestCase):
    def setUp(self):
        self.root = tmp()
        self.j = Journal(self.root, segment_records=5, fsync=False)
        for i in range(12):
            self.j.append("t.e", {"i": i, "tenant": "a" if i % 2 else "b"})
        self.signer = Signer("anchor-1")

    def test_verify_and_anchor(self):
        a = self.j.anchor(self.signer)
        r = self.j.verify({"anchor-1": self.signer.public_b64()})
        self.assertEqual((r["records"], r["anchors_verified"], a["seq"]), (12, 1, 12))

    def test_recomputed_chain_detected_by_anchor(self):
        self.j.anchor(self.signer)
        # attacker rewrites record 3 and recomputes every later hash (no signing key)
        recs = list(self.j.records())
        from inv66_enterprise_wasm_control_plane.production.journal import _hash
        prev = recs[1]["hash"]
        for r in recs[2:]:
            r.pop("hash")
            r["prev"] = prev
            if r["seq"] == 3:
                r["body"] = {"i": 999}
            r["hash"] = prev = _hash(r)
        for seg in self.j._segments():
            seg.unlink()
        j2root = self.root / "segments"
        by_seg: dict[int, list] = {}
        for r in recs:
            by_seg.setdefault((r["seq"] - 1) // 5, []).append(r)
        for k, rs in by_seg.items():
            (j2root / f"{k * 5 + 1:012d}.jsonl").write_text("".join(json.dumps(x, sort_keys=True, separators=(",", ":")) + "\n" for x in rs))
        j2 = Journal(self.root, segment_records=5, fsync=False)  # chain itself is internally consistent
        with self.assertRaises(EcpError) as cm:
            j2.verify({"anchor-1": self.signer.public_b64()})
        self.assertEqual(cm.exception.code, "ECP_AUDIT_TAMPERED")

    def test_truncation_detected_by_anchor(self):
        self.j.anchor(self.signer)
        last = self.j._segments()[-1]
        last.unlink()
        j2 = Journal(self.root, segment_records=5, fsync=False)
        with self.assertRaises(EcpError):
            j2.verify({"anchor-1": self.signer.public_b64()})

    def test_untrusted_anchor_key(self):
        self.j.anchor(Signer("anchor-1"))  # different key, same id
        with self.assertRaises(EcpError):
            self.j.verify({"anchor-1": self.signer.public_b64()})

    def test_torn_tail_recovered_interior_corruption_fails(self):
        last = self.j._segments()[-1]
        with last.open("ab") as fh:
            fh.write(b'{"seq": 13, "partial')
        j2 = Journal(self.root, segment_records=5, fsync=False)
        self.assertGreater(j2.recovery["truncated_tail_bytes"], 0)
        self.assertEqual(j2.head[0], 12)
        j2.append("t.e", {"i": 12})
        self.assertEqual(j2.verify()["records"], 13)
        first = self.j._segments()[0]
        data = first.read_bytes().replace(b'"i":1', b'"i":7', 1)
        first.write_bytes(data)
        with self.assertRaises(EcpError) as cm:
            Journal(self.root, segment_records=5, fsync=False)
        self.assertEqual(cm.exception.code, "ECP_STORE_CORRUPT")

    def test_compaction_holds_and_summary_chain(self):
        self.j.set_hold("legal-1", 7, 8, "litigation")
        archived = []
        res = self.j.compact(10, archive=lambda p: archived.append(p.name))
        self.assertEqual(res["dropped_segments"], 1)  # seg 1-5 dropped; 6-10 held
        self.assertEqual(self.j.verify()["compacted_segments"], 1)
        self.j.release_hold("legal-1")
        self.assertEqual(self.j.compact(10)["dropped_segments"], 1)
        j2 = Journal(self.root, segment_records=5, fsync=False)
        self.assertEqual(j2.head[0], 12)
        j2.append("t.e", {})
        self.assertEqual(j2.verify()["records"], 3)
        self.assertEqual(len(archived), 1)

    def test_archive_failure_deletes_nothing(self):
        def boom(p):
            raise OSError("worm down")
        with self.assertRaises(OSError):
            self.j.compact(10, archive=boom)
        self.assertEqual(len(self.j._segments()), 3)

    def test_query_export(self):
        self.j.anchor(self.signer)
        self.assertEqual(len(self.j.query(tenant="a")), 6)
        ex = self.j.export(1)
        self.assertEqual(verify_export(ex, {"anchor-1": self.signer.public_b64()})["records"], 12)
        ex["records"][4]["body"]["i"] = 99
        with self.assertRaises(EcpError):
            verify_export(ex, {"anchor-1": self.signer.public_b64()})

    def test_encrypted_bodies(self):
        kr = Keyring(); kr.rotate()
        j = Journal(tmp(), keyring=kr, fsync=False)
        j.append("x", {"secret": "manifest"})
        raw = b"".join(p.read_bytes() for p in j._segments())
        self.assertNotIn(b"manifest", raw)
        self.assertEqual(list(j.replay())[0][1], {"secret": "manifest"})
        self.assertEqual(j.verify()["records"], 1)

    def test_io_failure_raises_audit_unavailable(self):
        def fault():
            raise OSError(28, "No space left on device")
        j = Journal(tmp(), fsync=False, writer_fault=fault)
        with self.assertRaises(EcpError) as cm:
            j.append("x", {})
        self.assertEqual(cm.exception.code, "ECP_AUDIT_UNAVAILABLE")
        self.assertEqual(j.head[0], 0)


class PolicyEngineTest(unittest.TestCase):
    RULES = [
        {"id": "SEC", "effect": "deny", "priority": 1, "class": "security", "when": {"component_name": "dbg"}, "message": "no"},
        {"id": "RES", "effect": "require", "priority": 1, "class": "residency", "when": {"tenant": "t"},
         "require_image_prefix": "eu/", "message": "eu"},
        {"id": "AV", "effect": "deny", "priority": 5, "class": "availability", "when": {"lattice": "frozen"}, "message": "x"},
        {"id": "EX-COST", "effect": "exempt", "priority": 1, "class": "cost", "when": {}, "targets": ["RES", "SEC"], "message": "m"},
        {"id": "EX-AV", "effect": "exempt", "priority": 1, "class": "availability", "when": {"tenant": "t"}, "targets": ["AV"], "message": "m"},
    ]

    def test_precedence_and_exemptions(self):
        r = evaluate_local(self.RULES, {"tenant": "t", "lattice": "frozen"}, [{"name": "dbg", "image": "us/x"}])
        self.assertEqual([f["rule"] for f in r["fired"]], ["SEC", "RES"])  # security first, AV exempted
        self.assertEqual(r["suppressed"], {"AV": "EX-AV"})
        self.assertEqual({x["target"] for x in r["exemption_refused"]}, {"RES", "SEC"})
        self.assertEqual(r["order"][:2], ["SEC", "RES"])

    def test_deterministic(self):
        rules = self.RULES[:]
        outs = set()
        for _ in range(20):
            random.shuffle(rules)
            outs.add(json.dumps(evaluate_local(rules, {"tenant": "t", "lattice": "frozen"}, [{"name": "a", "image": "eu/a"}]), sort_keys=True))
        self.assertEqual(len(outs), 1)


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.e = Estate()
        self.p = self.e.service.config.active
        self.t = ("acme", "payments", "prod")

    def codes(self, c, **kw):
        r, _ = verify_component(self.p, c, self.t, 0, c.get("name", "?"), **kw)
        return sorted(x["code"] for x in r)

    def test_valid_and_failures(self):
        c = self.e.component("api")
        self.assertEqual(self.codes(c), [])
        self.assertEqual(self.codes({**c, "signature": self.e.component("web")["signature"]}), ["ECP_SIGNATURE_INVALID"])
        self.assertEqual(self.codes({**c, "name": "web"}), ["ECP_SIGNATURE_INVALID"])  # name-swap replay
        self.assertEqual(self.codes({**c, "image": c["image"].split("@")[0] + ":1"}),
                         ["ECP_DIGEST_REQUIRED", "ECP_SIGNATURE_INVALID"])
        self.assertEqual(self.codes(self.e.component("api", signer=self.e.other_signer)), ["ECP_SIGNER_NOT_APPROVED"])
        rogue = Signer("release-signer")  # same id, different key
        self.assertEqual(self.codes(self.e.component("api", signer=rogue)), ["ECP_SIGNATURE_INVALID"])

    def test_revoked_and_expired(self):
        doc = self.e.config()
        doc["signers"][0]["revoked"] = True
        p = build_policy(doc)
        r, _ = verify_component(p, self.e.component("api"), self.t, 0, "api")
        self.assertIn("ECP_SIGNER_NOT_APPROVED", [x["code"] for x in r])
        doc = self.e.config()
        doc["signers"][0]["not_after"] = 10.0
        r, _ = verify_component(build_policy(doc), self.e.component("api"), self.t, 11.0, "api")
        self.assertIn("ECP_SIGNER_NOT_APPROVED", [x["code"] for x in r])

    def test_attestation(self):
        doc = self.e.config(provenance={"require_digest": True, "require_signature": True, "require_attestation": True,
                                        "trusted_builders": ["https://ci.acme.example/builder@v3"]})
        p = build_policy(doc)
        ok = self.e.component("api", attest=True)
        r, ev = verify_component(p, ok, self.t, 0, "api")
        self.assertEqual(r, [])
        self.assertEqual(ev["attestation"]["builder"], "https://ci.acme.example/builder@v3")
        bad = json.loads(json.dumps(ok)); bad["attestation"]["builder"] = "evil"
        self.assertTrue(verify_component(p, bad, self.t, 0, "api")[0])
        other = self.e.component("web", attest=True)
        mism = {**ok, "attestation": other["attestation"]}
        self.assertTrue(verify_component(p, mism, self.t, 0, "api")[0])
        self.assertTrue(verify_component(p, self.e.component("api"), self.t, 0, "api")[0])

    def test_registry_resolver(self):
        from inv66_enterprise_wasm_control_plane.production.provenance import IndexResolver, image_digest
        c = self.e.component("api")
        res = IndexResolver({("eu.registry.estate.local", "api", image_digest(c["image"]))})
        self.assertEqual(self.codes(c, resolver=res), [])
        self.assertEqual(self.codes(self.e.component("web"), resolver=res), ["ECP_PROVENANCE_INVALID"])


class SmallPartsTest(unittest.TestCase):
    def test_quota(self):
        clk = FakeClock()
        q = Quotas(clock=clk, max_tenants=2)
        spec = {"default": {"rate_per_s": 2.0, "burst": 2, "max_inflight": 1}}
        q.take(spec, "a"); q.take(spec, "a")
        with self.assertRaises(EcpError) as cm:
            q.take(spec, "a")
        self.assertGreater(cm.exception.details["retry_after_ms"], 0)
        q.take(spec, "b")  # other tenant unaffected (fairness)
        clk.advance(1.0)
        q.take(spec, "a")
        clk.advance(10)
        q.take(spec, "c")
        self.assertLessEqual(len(q), 2)

    def test_lifecycle(self):
        lc = Lifecycle()
        lc.check("d", "admitted"); lc.apply("d", "admitted")
        for bad in ("delivered", "quarantined", "proposed"):
            with self.assertRaises(EcpError):
                lc.check("d", bad)
        for s in TERMINAL:
            self.assertEqual(TRANSITIONS[s], frozenset())

    def test_quarantine(self):
        q = QuarantineController()
        q.apply_record("quarantine.freeze", {"scope": "acme/pay", "by": "s"})
        with self.assertRaises(EcpError):
            q.check(("acme", "pay", "prod"))
        q.check(("acme", "other", "prod"))

    def test_retry_classification(self):
        calls = []
        rp = RetryPolicy(max_attempts=4, sleep=lambda s: None)

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise EcpError("ECP_DELIVERY_FAILED", "x")
            return "ok"
        self.assertEqual(rp.run(flaky), "ok")
        calls.clear()
        with self.assertRaises(EcpError):
            rp.run(lambda: (_ for _ in ()).throw(EcpError("ECP_FORBIDDEN", "x")))
        self.assertEqual(len(calls), 0)

    def test_retry_respects_deadline(self):
        clk = FakeClock()
        d = Deadline(10, clock=clk)
        rp = RetryPolicy(max_attempts=10, base_s=1.0, sleep=lambda s: None, rng=random.Random(1))
        with self.assertRaises(EcpError) as cm:
            rp.run(lambda: (_ for _ in ()).throw(EcpError("ECP_DELIVERY_FAILED", "x")), d)
        self.assertEqual(cm.exception.code, "ECP_DEADLINE_EXCEEDED")

    def test_breaker(self):
        clk = FakeClock()
        b = CircuitBreaker("d", failure_threshold=2, reset_after_s=5, clock=clk)
        boom = lambda: (_ for _ in ()).throw(EcpError("ECP_DELIVERY_FAILED", "x"))  # noqa: E731
        for _ in range(2):
            with self.assertRaises(EcpError):
                b.call(boom)
        with self.assertRaises(EcpError) as cm:
            b.call(lambda: "ok")
        self.assertEqual(cm.exception.code, "ECP_CIRCUIT_OPEN")
        clk.advance(6)
        self.assertEqual(b.call(lambda: "ok"), "ok")
        self.assertEqual(b.state, "closed")

    def test_shedder_fairness(self):
        s = LoadShedder(3, 2)
        s.acquire("a"); s.acquire("a")
        with self.assertRaises(EcpError):
            s.acquire("a")
        s.acquire("b")
        with self.assertRaises(EcpError):
            s.acquire("c")
        s.release("a")
        s.acquire("c")

    def test_deadline_cancel(self):
        d = Deadline(10_000)
        d.cancel()
        with self.assertRaises(EcpError) as cm:
            d.check()
        self.assertEqual(cm.exception.code, "ECP_CANCELLED")

    def test_idempotency_conflict(self):
        s = IdempotencyStore()
        s.put("k", "d1", {"x": 1})
        self.assertEqual(s.get("k", "d1"), {"x": 1})
        with self.assertRaises(EcpError):
            s.get("k", "d2")

    def test_dependency_health_modes(self):
        h = DependencyHealth()
        h.register("journal", True); h.register("deployment", False)
        h.report("deployment", False, "down")
        self.assertEqual(h.mode(), "normal")
        h.report("journal", False, "disk")
        self.assertEqual(h.mode(), "degraded")


class TelemetryTest(unittest.TestCase):
    def test_prometheus_and_bounded_series(self):
        m = Metrics(max_series=3)
        for i in range(10):
            m.inc("x_total", tenant=f"t{i}")
        m.observe("lat_ms", 3.0)
        out = m.render()
        self.assertIn('x_total{overflow="true"} 7', out)
        self.assertIn('lat_ms_bucket{le="5"} 1', out)
        self.assertIn("lat_ms_count 1", out)
        self.assertLessEqual(len([l for l in out.splitlines() if l.startswith("x_total")]), 4)

    def test_log_allowlist_and_redaction(self):
        buf = io.StringIO()
        lg = Logger(buf, redact_subjects=True)
        lg.log("info", "e", subject="alice", token="SECRET", tenant="t")
        rec = json.loads(buf.getvalue())
        self.assertNotIn("token", rec)
        self.assertTrue(rec["subject"].startswith("sha256:"))
        self.assertEqual(rec["schema"], "PK_ECP_LOG/1")

    def test_trace_propagation(self):
        tr = Tracer()
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        with tr.span("outer", tp) as o:
            with tr.span("inner") as i:
                self.assertEqual(tr.headers()["traceparent"].split("-")[1], "a" * 32)
        self.assertEqual((o.trace_id, o.parent_id, i.parent_id), ("a" * 32, "b" * 16, o.span_id))
        self.assertIsNone(Tracer.parse("00-" + "0" * 32 + "-" + "b" * 16 + "-01"))


if __name__ == "__main__":
    unittest.main()
