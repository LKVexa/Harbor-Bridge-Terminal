"""Certification, store, audit, auth, config, site control, governance, telemetry
(MC-08..10, 18..24, 27, 28, 38..44, 48, 49, 60, 63)."""
import copy
import importlib
import json
import os
import sqlite3
import tempfile
import threading
import unittest

from _support import D1, D2, D3, PKG, PKG_DIR, Clock

cert = importlib.import_module(f"{PKG}.cert")
store_mod = importlib.import_module(f"{PKG}.store")
auth = importlib.import_module(f"{PKG}.auth")
config = importlib.import_module(f"{PKG}.config")
gov = importlib.import_module(f"{PKG}.governance")
lifecycle = importlib.import_module(f"{PKG}.lifecycle")
telemetry = importlib.import_module(f"{PKG}.telemetry")
matrix = importlib.import_module(f"{PKG}.matrix")
ops_mod = importlib.import_module(f"{PKG}.ops")
E = importlib.import_module(f"{PKG}.errors").Inv22Error

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

T0 = 1_800_000_000
BASE = {"standards": D2, "fork": D3}


def mk_trust(*signers, **kw):
    ts = cert.TrustStore()
    for s in signers:
        ts.add(cert.TrustedKey(s.key_id, s.issuer, s.public_b64(), **kw))
    return ts


def mk_cert(signer, cid="c1", branch="standards", artifact=D1, issued=T0, until=T0 + 86400):
    return cert.issue(signer, cert_id=cid, component_id="edge", component_version="1.0", artifact_digests=[artifact],
                      branch=branch, baselines=BASE, matrix_digest=D2, evidence_digest=D3, issued_at=issued, not_after=until)


def fresh(now=T0 + 10, **kw):
    return cert.RevocationView(sequence=1, fetched_at=now, **kw)


class Certificates(unittest.TestCase):
    def setUp(self):
        self.s = cert.LocalSigner("k1", "issuer-a")
        self.trust = mk_trust(self.s)
        self.env = mk_cert(self.s)

    def v(self, env=None, **kw):
        args = dict(now=T0 + 10, branch="standards", artifact_digest=D1, revocation=fresh())
        args.update(kw)
        return cert.verify(env or self.env, self.trust, **args)

    def code(self, **kw):
        with self.assertRaises(E) as c:
            self.v(**kw)
        return c.exception.code

    def test_valid(self):
        self.assertEqual(self.v()["cert_id"], "c1")

    def test_signer_repr_hides_key(self):
        self.assertNotIn("PrivateKey", repr(self.s))

    def test_every_payload_field_is_bound(self):
        for key in self.env["payload"]:
            t = copy.deepcopy(self.env)
            val = t["payload"][key]
            t["payload"][key] = (val + 1 if isinstance(val, int) else
                                 "sha256:" + "9" * 64 if isinstance(val, str) and val.startswith("sha256:") else
                                 ["sha256:" + "9" * 64] if key == "artifact_digests" else
                                 {"standards": D3, "fork": D2} if key == "baselines" else
                                 {"id": "x", "version": "2"} if key == "component" else
                                 {"runtimes": ["x"]} if key == "scope" else ["w"] if key == "waivers" else
                                 "fork" if key == "branch" else val + "x")
            with self.subTest(key), self.assertRaises(E):
                self.v(env=t)

    def test_negative_matrix(self):
        self.assertEqual(self.code(now=T0 + 86400 + 200), "INV22.CERT.EXPIRED")
        self.assertEqual(self.code(now=T0 - 500), "INV22.CERT.NOT_YET_VALID")
        self.assertEqual(self.code(branch="fork"), "INV22.CERT.UNCERTIFIED_BRANCH")
        self.assertEqual(self.code(artifact_digest=D2), "INV22.CERT.DIGEST_MISMATCH")
        self.assertEqual(self.code(now=None), "INV22.DEPENDENCY.UNAVAILABLE")
        self.assertEqual(self.code(revocation=None), "INV22.CERT.STALE_REVOCATION")
        self.assertEqual(self.code(revocation=fresh(now=T0 - 7200)), "INV22.CERT.STALE_REVOCATION")
        self.assertEqual(self.code(revocation=fresh(revoked=frozenset({"c1"}))), "INV22.CERT.REVOKED")
        self.assertEqual(self.code(revocation=fresh(superseded=frozenset({"c1"}))), "INV22.CERT.SUPERSEDED")
        self.assertEqual(self.code(revocation=fresh(suspended=frozenset({"c1"}))), "INV22.CERT.SUSPENDED")

    def test_skew_boundaries(self):
        at = lambda t: dict(now=t, revocation=fresh(t))  # noqa: E731
        self.v(**at(T0 - 120))                  # inside skew
        self.assertEqual(self.code(**at(T0 - 121)), "INV22.CERT.NOT_YET_VALID")
        self.v(**at(T0 + 86400 + 119))
        self.assertEqual(self.code(**at(T0 + 86400 + 120)), "INV22.CERT.EXPIRED")

    def test_unknown_issuer_and_impostor_key(self):
        other = cert.LocalSigner("k1", "issuer-a")          # same ids, different key
        with self.assertRaises(E) as c:
            self.v(env=mk_cert(other))
        self.assertEqual(c.exception.code, "INV22.CERT.INVALID_SIGNATURE")
        stranger = cert.LocalSigner("k9", "issuer-z")
        with self.assertRaises(E) as c:
            self.v(env=mk_cert(stranger))
        self.assertEqual(c.exception.code, "INV22.CERT.UNKNOWN_ISSUER")

    def test_rotation_and_compromise(self):
        k2 = cert.LocalSigner("k2", "issuer-a")
        trust = cert.TrustStore()
        trust.add(cert.TrustedKey("k1", "issuer-a", self.s.public_b64(), retired_at=T0 + 100))
        trust.add(cert.TrustedKey("k2", "issuer-a", k2.public_b64(), active_from=T0 + 100))
        ctx = dict(now=T0 + 200, branch="standards", artifact_digest=D1, revocation=fresh(T0 + 200))
        cert.verify(self.env, trust, **ctx)                                   # old sig before retirement still valid
        with self.assertRaises(E):
            cert.verify(mk_cert(self.s, "late", issued=T0 + 150), trust, **ctx)  # retired key signing new certs
        cert.verify(mk_cert(k2, "new", issued=T0 + 150), trust, **ctx)
        trust.keys["k1"].revoked = True                                      # compromise invalidates history
        with self.assertRaises(E):
            cert.verify(self.env, trust, **ctx)

    def test_fixture_corpus(self):
        fx_dir = PKG_DIR / "fixtures/cert"
        t = json.loads((fx_dir / "trust_store.json").read_text())["document"]
        trust = cert.TrustStore()
        for k in t["keys"]:
            trust.add(cert.TrustedKey(k["key_id"], k["issuer"], k["public_key"]))
        n = 0
        for f in sorted(fx_dir.glob("*.json")):
            if f.name == "trust_store.json":
                continue
            fx = json.loads(f.read_text())
            ctx = fx["document"]["context"]
            args = dict(now=ctx["now"], branch=ctx["branch"], artifact_digest=ctx["artifact_digest"],
                        revocation=fresh(ctx["now"]))
            with self.subTest(f.name):
                if fx["expect"] == "ok":
                    cert.verify(fx["document"]["envelope"], trust, **args)
                else:
                    with self.assertRaises(E) as c:
                        cert.verify(fx["document"]["envelope"], trust, **args)
                    self.assertEqual(c.exception.code, fx["expect"])
            n += 1
        self.assertGreaterEqual(n, 8)

    def test_json_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema missing")
        jsonschema.validate(self.env, json.loads((PKG_DIR / "schemas/pk_branch_cert.v1.schema.json").read_text()))


class StoreBase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "s.db")
        self.clock = Clock(T0 + 10)
        self.st = store_mod.Store(self.path, clock=self.clock)
        self.s = cert.LocalSigner("k1", "issuer-a")
        self.trust = mk_trust(self.s)

    def tearDown(self):
        self.st.close()
        self.dir.cleanup()


class Store(StoreBase):
    def test_persistence_across_restart(self):
        env = mk_cert(self.s)
        self.st.issue_cert(env, actor="ci")
        self.st.revoke("c1", actor="op", reason="test")
        self.st.close()
        self.st = store_mod.Store(self.path, clock=self.clock)
        rec = self.st.get_cert("c1")
        self.assertEqual(rec["envelope"], env)
        self.assertEqual(rec["status"], "revoked")
        self.assertIn("c1", self.st.revocation_snapshot().revoked)

    def test_no_resurrection_and_illegal_transitions(self):
        self.st.issue_cert(mk_cert(self.s), actor="ci")
        self.st.revoke("c1", actor="op", reason="r")
        with self.assertRaises(E) as c:
            self.st.reinstate("c1", actor="op", reason="r")
        self.assertEqual(c.exception.code, "INV22.STATE.ILLEGAL_TRANSITION")
        with self.assertRaises(E):
            self.st.issue_cert(mk_cert(self.s), actor="ci")

    def test_supersede_and_expire(self):
        self.st.issue_cert(mk_cert(self.s), actor="ci")
        with self.assertRaises(E):
            self.st.supersede("c1", "c2", actor="ci", reason="no successor yet")
        self.st.issue_cert(mk_cert(self.s, "c2"), actor="ci")
        self.st.supersede("c1", "c2", actor="ci", reason="renewal")
        self.clock.t = T0 + 86400
        self.assertEqual(self.st.expire_due(), ["c2"])

    def test_optimistic_concurrency(self):
        self.st.issue_cert(mk_cert(self.s), actor="ci")
        with self.assertRaises(E) as c:
            self.st.suspend("c1", actor="op", reason="r", expected_rev=7)
        self.assertEqual(c.exception.code, "INV22.STORAGE.CONFLICT")

    def test_concurrent_revocation_race(self):
        self.st.issue_cert(mk_cert(self.s), actor="ci")
        results = []

        def worker(i):
            st = store_mod.Store(self.path, clock=self.clock)
            try:
                st.revoke("c1", actor=f"op{i}", reason="race", expected_rev=1)
                results.append("ok")
            except E as e:
                results.append(e.code)
            finally:
                st.close()
        ths = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        [t.start() for t in ths]
        [t.join() for t in ths]
        self.assertEqual(results.count("ok"), 1)
        self.assertEqual(sum(1 for e in self.st.audit_events() if e["action"] == "cert.revoked"), 1)

    def test_corruption_detected(self):
        self.st.issue_cert(mk_cert(self.s), actor="ci")
        raw = sqlite3.connect(self.path)
        raw.execute("UPDATE certs SET envelope=replace(envelope, 'edge', 'evil')")
        raw.commit()
        raw.close()
        with self.assertRaises(E) as c:
            self.st.get_cert("c1")
        self.assertEqual(c.exception.code, "INV22.INTEGRITY.CORRUPT")
        self.assertFalse(self.st.integrity_check()["ok"])

    def test_audit_append_only_and_tamper_evident(self):
        self.st.issue_cert(mk_cert(self.s), actor="ci")
        self.st.revoke("c1", actor="op", reason="r")
        self.assertTrue(self.st.verify_audit_chain()["ok"])
        with self.assertRaises(sqlite3.DatabaseError):
            self.st.db.execute("UPDATE audit SET actor='x'")
        raw = sqlite3.connect(self.path)
        raw.execute("DROP TRIGGER audit_no_update")
        raw.execute("UPDATE audit SET reason='hidden' WHERE seq=2")
        raw.commit()
        raw.close()
        chain = self.st.verify_audit_chain()
        self.assertFalse(chain["ok"])
        self.assertEqual(chain["broken_at"], 2)

    def test_backup_restore(self):
        self.st.issue_cert(mk_cert(self.s), actor="ci")
        self.st.revoke("c1", actor="op", reason="r")
        dest = os.path.join(self.dir.name, "b.db")
        self.assertTrue(self.st.backup(dest)["ok"])
        r = store_mod.Store(dest, read_only=True)
        self.assertEqual(r.get_cert("c1")["status"], "revoked")      # revoked trust not revived
        self.assertEqual(r.audit_events(), self.st.audit_events())
        with self.assertRaises(E):
            r.revoke("c1", actor="x", reason="read-only")
        r.close()

    def test_migration_refuses_newer_store(self):
        self.st.db.execute("UPDATE kv SET v='99' WHERE k='schema_version'")
        self.st.close()
        with self.assertRaises(E) as c:
            self.st = store_mod.Store(self.path, clock=self.clock)
        self.assertEqual(c.exception.code, "INV22.VERSION.UNSUPPORTED")
        raw = sqlite3.connect(self.path)
        raw.execute("UPDATE kv SET v='1' WHERE k='schema_version'")
        raw.commit()
        raw.close()
        self.st = store_mod.Store(self.path, clock=self.clock)

    def test_drift_history_immutable(self):
        m = matrix.parse(json.loads((PKG_DIR / "data/matrix.json").read_text()))
        self.assertEqual(self.st.record_drift("r1", m, actor="ci")["divergent"], 2)
        with self.assertRaises(E):
            self.st.record_drift("r1", m, actor="ci")
        with self.assertRaises(sqlite3.DatabaseError):
            self.st.db.execute("DELETE FROM drift")
        self.assertEqual(self.st.drift_history()[0]["matrix_digest"], m.digest)


def cfg(**site):
    c = copy.deepcopy(config.DEFAULTS)
    c["site"].update(id="edge-1", **site)
    return c


class Config(StoreBase):
    def test_precedence_and_provenance(self):
        eff, prov = config.load({**cfg()}, overlay={"limits": {"max_concurrency": 4}},
                                env={"INV22__LIMITS__MAX_CONCURRENCY": "6", "UNRELATED": "x"},
                                cli={"limits.max_concurrency": 7})
        self.assertEqual(eff["limits"]["max_concurrency"], 7)
        self.assertEqual(prov["limits.max_concurrency"], "cli")
        self.assertEqual(prov["site.id"], "file")

    def test_rejections(self):
        bad = [
            lambda c: c["listen"].update(host="0.0.0.0"), lambda c: c["features"].update(auto_classify_unknown=True),
            lambda c: c["limits"].update(max_concurrency=0), lambda c: c.update(extra=1),
            lambda c: c["store"].update(credential="plaintext-password"), lambda c: c["store"].update(path="../../etc/x"),
            lambda c: c.update(contract="PK_BRANCH_CONFIG/2"), lambda c: c["limits"].update(max_concurrency="8"),
            lambda c: c["site"].update(branch="beta"),
        ]
        for i, fn in enumerate(bad):
            c = cfg()
            fn(c)
            with self.subTest(i), self.assertRaises(E):
                config.validate(c)
        with self.assertRaises(E):
            config.load(cfg(), overlay={"baselines": {"manifest": "other.json"}})    # immutable via overlay
        with self.assertRaises(E):
            config.load(cfg(), env={"INV22__FEATURES__ANONYMOUS_READ": "true"})

    def test_secret_refs_and_redaction(self):
        c = cfg()
        c["store"]["credential"] = "secret://vault/inv22/db"
        eff, prov = config.load(c)
        view = config.effective_view(eff, prov)
        self.assertNotIn("vault/inv22/db", view)
        marker = {"note": "-----BEGIN PRIVATE KEY----- abc", "nested": [{"password": "p"}], "ok": "fine"}
        red = json.dumps(config.redact(marker))
        self.assertNotIn("abc", red)
        self.assertNotIn('"p"', red)
        self.assertIn("fine", red)

    def test_atomic_activation_fault_injection(self):
        r1 = self.st.activate_config(cfg(), actor="op", expected_active=None, reason="init", validator=config.validate)
        for stage in ("validated", "prepared", "committing"):
            def boom(s, stage=stage):
                if s == stage:
                    raise RuntimeError("injected")
            with self.subTest(stage):
                with self.assertRaises(RuntimeError):
                    self.st.activate_config(cfg(branch="fork"), actor="op", expected_active=r1, reason="x",
                                            validator=config.validate, fault=boom)
                self.assertEqual(self.st.active_config()[0], r1)
                self.assertEqual(self.st.active_config()[1]["site"]["branch"], "standards")

    def test_invalid_never_activates_and_stale_writer_fenced(self):
        r1 = self.st.activate_config(cfg(), actor="op", expected_active=None, reason="init", validator=config.validate)
        bad = cfg()
        bad["listen"]["host"] = "0.0.0.0"
        with self.assertRaises(E):
            self.st.activate_config(bad, actor="op", expected_active=r1, reason="x", validator=config.validate)
        r2 = self.st.activate_config(cfg(branch="fork"), actor="op", expected_active=r1, reason="x", validator=config.validate)
        with self.assertRaises(E) as c:
            self.st.activate_config(cfg(), actor="op2", expected_active=r1, reason="stale", validator=config.validate)
        self.assertEqual(c.exception.code, "INV22.STORAGE.CONFLICT")
        self.assertEqual(self.st.rollback_config(actor="op", reason="bad rollout", validator=config.validate), r1)
        self.assertEqual(self.st.active_config()[0], r1)
        self.assertTrue(r2 > r1)
        acts = [e["action"] for e in self.st.audit_events()]
        self.assertEqual(acts.count("config.activate"), 2)
        self.assertIn("config.rollback", acts)


class SiteAndAdmission(StoreBase):
    def test_fencing_race_single_winner(self):
        self.st.set_site_branch("edge-1", "standards", D2, actor="ctl", fence=0, reason="init")
        outcomes = []

        def ctl(branch):
            st = store_mod.Store(self.path, clock=self.clock)
            try:
                st.set_site_branch("edge-1", branch, D2, actor=f"ctl-{branch}", fence=1, reason="race")
                outcomes.append(branch)
            except E as e:
                outcomes.append(e.code)
            finally:
                st.close()
        ths = [threading.Thread(target=ctl, args=(b,)) for b in ("fork", "standards", "fork", "standards")]
        [t.start() for t in ths]
        [t.join() for t in ths]
        winners = [o for o in outcomes if not o.startswith("INV22")]
        self.assertEqual(len(winners), 1)
        state = self.st.site_state("edge-1")
        self.assertEqual((state["branch"], state["epoch"]), (winners[0], 2))

    def test_admission(self):
        self.st.set_site_branch("edge-1", "fork", D3, actor="ctl", fence=0, reason="init")
        self.st.issue_cert(mk_cert(self.s, "std", branch="standards"), actor="ci")
        self.st.issue_cert(mk_cert(self.s, "frk", branch="fork"), actor="ci")
        with self.assertRaises(E) as c:
            gov.admit(store=self.st, trust=self.trust, site="edge-1", cert_id="std", artifact_digest=D1, now=T0 + 10)
        self.assertEqual(c.exception.code, "INV22.CERT.UNCERTIFIED_BRANCH")
        self.assertTrue(gov.admit(store=self.st, trust=self.trust, site="edge-1", cert_id="frk", artifact_digest=D1, now=T0 + 10)["admitted"])
        self.st.set_frozen("edge-1", True, actor="op", reason="incident")
        with self.assertRaises(E) as c:
            gov.admit(store=self.st, trust=self.trust, site="edge-1", cert_id="frk", artifact_digest=D1, now=T0 + 10)
        self.assertEqual(c.exception.code, "INV22.SITE.FROZEN")
        self.st.set_frozen("edge-1", False, actor="op", reason="resolved")
        self.st.revoke("frk", actor="op", reason="bad build")
        with self.assertRaises(E):
            gov.admit(store=self.st, trust=self.trust, site="edge-1", cert_id="frk", artifact_digest=D1, now=T0 + 10)
        acts = [e["action"] for e in self.st.audit_events()]
        self.assertEqual(acts.count("admission.refused"), 3)
        self.assertTrue(self.st.verify_audit_chain()["ok"])

    def test_branch_change_plan_blocks_uncertified(self):
        self.st.issue_cert(mk_cert(self.s, "std", branch="standards"), actor="ci")
        plan = gov.plan_branch_change(self.st, site="edge-1", target_branch="fork", workloads={D1: "std"}, trust=self.trust, now=T0 + 10)
        self.assertFalse(plan["ok"])

    def test_offline_staleness_bounded(self):
        self.st.issue_cert(mk_cert(self.s, "std"), actor="ci")
        env = self.st.get_cert("std")["envelope"]
        cached = self.st.revocation_snapshot()          # taken at T0+10
        cert.verify(env, self.trust, now=T0 + 3000, branch="standards", artifact_digest=D1, revocation=cached)
        with self.assertRaises(E) as c:
            cert.verify(env, self.trust, now=T0 + 3700, branch="standards", artifact_digest=D1, revocation=cached)
        self.assertEqual(c.exception.code, "INV22.CERT.STALE_REVOCATION")


class AuthN(unittest.TestCase):
    def setUp(self):
        self.k = Ed25519PrivateKey.generate()
        s = cert.LocalSigner("idp1", "idp", self.k)
        self.a = auth.Authenticator(audience="inv22", issuers={"idp1": {"issuer": "idp", "public_key": s.public_b64(),
                                                                         "kinds": ["operator", "ci"]}})
        self.n = 0

    def tok(self, **kw):
        self.n += 1
        args = dict(kid="idp1", iss="idp", sub="alice", aud="inv22", roles=["operator"], kind="operator",
                    nbf=T0, exp=T0 + 600, jti=f"j{self.n}")
        args.update(kw)
        key = args.pop("key", self.k)
        return auth.mint_token(key, **args)

    def test_valid_and_negative_matrix(self):
        self.assertEqual(self.a.authenticate(self.tok(), now=T0 + 1).subject, "alice")
        bad = {"expired": dict(exp=T0 + 10), "not_yet": dict(nbf=T0 + 500, exp=T0 + 900), "aud": dict(aud="other"),
               "iss": dict(iss="evil"), "kid": dict(kid="nope"), "kind": dict(kind="service"),
               "lifetime": dict(exp=T0 + 99999), "forged": dict(key=Ed25519PrivateKey.generate())}
        for name, kw in bad.items():
            with self.subTest(name), self.assertRaises(E) as c:
                self.a.authenticate(self.tok(**kw), now=T0 + 100)
            self.assertEqual(c.exception.code, "INV22.AUTH.UNAUTHENTICATED")
        for junk in (None, "", "a.b", "....", "x" * 5000):
            with self.assertRaises(E):
                self.a.authenticate(junk, now=T0)
        with self.assertRaises(E):
            self.a.authenticate(self.tok(), now=None)

    def test_replay(self):
        t = self.tok()
        self.a.authenticate(t, now=T0 + 1)
        with self.assertRaises(E):
            self.a.authenticate(t, now=T0 + 2)


class AuthZ(unittest.TestCase):
    def setUp(self):
        self.pol = auth.Policy([auth.Grant("operator", "cert.revoke", "cert:*"),
                                auth.Grant("releaser", "cert.issue", "branch:*/component:*"),
                                auth.Grant("operator", "site.freeze", "site:edge-*")])
        self.z = auth.Authorizer(self.pol)
        self.op = auth.Principal("alice", frozenset({"operator"}), "idp", "operator")

    def test_default_deny_and_scopes(self):
        self.assertEqual(self.z.authorize(self.op, "cert.revoke", "cert:c1", now=T0), "grant")
        for action, scope in (("cert.issue", "branch:fork/component:x"), ("site.freeze", "site:core-1"),
                              ("policy.admin", "policy:all"), ("cert.revoke", "cert:*"), ("bogus", "x")):
            with self.subTest(action + scope), self.assertRaises(E):
                self.z.authorize(self.op, action, scope, now=T0)
        with self.assertRaises(E):
            self.z.authorize(None, "cert.revoke", "cert:c1", now=T0)

    def test_policy_rejects_unknown_actions(self):
        with self.assertRaises(E):
            auth.Policy([auth.Grant("x", "root.everything")])

    def test_separation_of_duties(self):
        with self.assertRaises(E) as c:
            self.z.check_separation("alice", "cert.issue", {"matrix.publish": "alice"})
        self.assertEqual(c.exception.code, "INV22.AUTH.SEPARATION_OF_DUTIES")
        self.z.check_separation("alice", "cert.issue", {"matrix.publish": "bob"})

    def test_break_glass_expires_and_is_audited(self):
        events = []

        class A:
            def record_event(self, **kw):
                events.append(kw)
        self.pol.break_glass.append(auth.BreakGlass("alice", "policy.admin", "policy:*", T0 + 60, "INC-1"))
        z = auth.Authorizer(self.pol, audit=A())
        self.assertEqual(z.authorize(self.op, "policy.admin", "policy:main", now=T0), "break-glass")
        self.assertEqual(events[0]["reason"], "INC-1")
        with self.assertRaises(E):
            z.authorize(self.op, "policy.admin", "policy:main", now=T0 + 61)


class OpsFacade(StoreBase):
    def test_end_to_end_authenticated_ops(self):
        k = Ed25519PrivateKey.generate()
        idp = cert.LocalSigner("idp1", "idp", k)
        authn = auth.Authenticator(audience="inv22", issuers={"idp1": {"issuer": "idp", "public_key": idp.public_b64(), "kinds": ["operator", "ci"]}})
        authz = auth.Authorizer(auth.Policy([auth.Grant("releaser", "cert.issue", "*"), auth.Grant("operator", "cert.revoke", "*"),
                                             auth.Grant("operator", "config.activate", "*"), auth.Grant("auditor", "audit.read", "*")]))
        ops = ops_mod.Ops(self.st, authn, authz, clock=self.clock)
        n = iter(range(100))
        tok = lambda sub, roles, kind="operator": auth.mint_token(k, kid="idp1", iss="idp", sub=sub, aud="inv22", roles=roles,  # noqa: E731
                                                                  kind=kind, nbf=T0, exp=T0 + 600, jti=f"j{next(n)}")
        with self.assertRaises(E):
            ops.issue_cert(tok("bob", ["releaser"], "ci"), mk_cert(self.s), matrix_publisher="bob", reason="x")
        ops.issue_cert(tok("ci-bot", ["releaser"], "ci"), mk_cert(self.s), matrix_publisher="bob", reason="release")
        with self.assertRaises(E):
            ops.revoke_cert(tok("mallory", ["auditor"]), "c1", reason="x")
        ops.revoke_cert(tok("alice", ["operator"]), "c1", reason="bad build")
        ops.activate_config(tok("alice", ["operator"]), cfg(), expected_active=None, reason="init")
        events = ops.read_audit(tok("carol", ["auditor"]))
        self.assertEqual([e["actor"] for e in events], ["ci-bot", "alice", "alice"])
        with self.assertRaises(E):
            ops.read_audit(None)


class Governance(unittest.TestCase):
    def w(self, **kw):
        base = dict(waiver_id="W1", gate="drift.review_required", tier="operational", scope="comp:edge", owner="team-a",
                    approver="bob", requested_by="alice", risk="low", compensating_controls=("weekly review",),
                    issued_at=T0, expires_at=T0 + 86400)
        base.update(kw)
        return gov.Waiver(**base)

    def test_precedence_is_fail_closed(self):
        f = [gov.Finding("cost", "cost.ok", True, ""), gov.Finding("semantic", "sem.divergent", False, "divergent"),
             gov.Finding("security", "sec.ok", True, "")]
        d = gov.decide(f, scope="comp:edge", now=T0, waivers=[self.w(gate="sem.divergent", tier="semantic")])
        self.assertFalse(d["allow"])
        self.assertEqual(d["decided_by"], "sem.divergent")
        self.assertEqual([t["tier"] for t in d["trail"]], ["security", "semantic"])
        self.assertFalse(gov.decide([gov.Finding("mystery", "x", True, "")], scope="s", now=T0)["allow"])

    def test_waiver_rules(self):
        f = [gov.Finding("operational", "drift.review_required", False, "delta=1")]
        self.assertTrue(gov.decide(f, scope="comp:edge", now=T0 + 1, waivers=[self.w()])["allow"])
        for bad in (self.w(expires_at=T0 + 1), self.w(approver="alice"), self.w(scope="comp:other"),
                    self.w(compensating_controls=()), self.w(expires_at=T0 + 91 * 86400)):
            with self.subTest(bad), self.assertRaises(E):
                bad.check(gate="drift.review_required", scope="comp:edge", now=T0 + 10)
        self.assertFalse(gov.decide(f, scope="comp:edge", now=T0 + 86400, waivers=[self.w()])["allow"])

    def test_drift_policy(self):
        hist = [{"divergent": 2}, {"divergent": 2}]
        self.assertTrue(gov.decide(gov.drift_findings(hist), scope="s", now=T0)["allow"])
        self.assertFalse(gov.decide(gov.drift_findings(hist + [{"divergent": 3}]), scope="s", now=T0)["allow"])
        blocked = gov.decide(gov.drift_findings(hist + [{"divergent": 6}]), scope="s", now=T0)
        self.assertEqual(blocked["decided_by"], "drift.block")
        self.assertFalse(gov.decide(gov.drift_findings([]), scope="s", now=T0)["allow"])


class Lifecycle(unittest.TestCase):
    def test_exhaustive(self):
        for name, table in lifecycle.MACHINES.items():
            states = list(table)
            for a in states:
                for b in states:
                    with self.subTest(f"{name}:{a}->{b}"):
                        if b in table[a]:
                            lifecycle.check(name, a, b)
                        else:
                            with self.assertRaises(E):
                                lifecycle.check(name, a, b)

    def test_revoked_never_reaches_valid(self):
        seen, frontier = {"revoked"}, ["revoked"]
        while frontier:
            for nxt in lifecycle.MACHINES["cert"][frontier.pop()]:
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
        self.assertNotIn("valid", seen)


class Telemetry(unittest.TestCase):
    def test_bounded_cardinality(self):
        m = telemetry.Metrics()
        for i in range(2000):
            m.inc("shim_refusals", interface=f"i{i}", tenant_secret="x")
        snap = m.snapshot()
        self.assertLessEqual(len(snap["counters"]), telemetry.MAX_SERIES + 1)
        self.assertGreater(snap["dropped_series"], 0)
        self.assertNotIn("tenant_secret", json.dumps(snap))
        self.assertEqual(m.total("shim_refusals"), 2000)

    def test_exporter_redacts(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            telemetry.JsonlExporter(p).emit("x", token="abc", detail="-----BEGIN PRIVATE KEY-----")
            with open(p) as fh:
                text = fh.read()
        self.assertNotIn("abc", text)
        self.assertNotIn("BEGIN PRIVATE", text)

    def test_slos_zero_budget(self):
        ok = telemetry.evaluate_slos({"uncertified_runs": 0, "unclassified_interfaces": 0, "releases_without_drift_record": 0})
        self.assertFalse(any(s["breached"] for s in ok))
        bad = telemetry.evaluate_slos({"uncertified_runs": 1})
        self.assertTrue(all(s["breached"] for s in bad))
        self.assertTrue(all(s["action"] for s in bad))

    def test_health_readiness(self):
        with tempfile.TemporaryDirectory() as d:
            st = store_mod.Store(os.path.join(d, "s.db"))
            h = telemetry.health(version="4.3.0", config_digest=D1, store=st, trust_loaded=True, baselines_pinned=True,
                                 revocation_age=5, max_revocation_age=3600, frozen_sites=[])
            self.assertEqual(h["state"], "ready")
            h = telemetry.health(version="4.3.0", config_digest=D1, store=st, trust_loaded=True, baselines_pinned=False,
                                 revocation_age=99999, max_revocation_age=3600, frozen_sites=["edge-1"])
            self.assertFalse(h["ready"])
            self.assertEqual(len(h["reasons"]), 2)
            st.close()


if __name__ == "__main__":
    unittest.main()
