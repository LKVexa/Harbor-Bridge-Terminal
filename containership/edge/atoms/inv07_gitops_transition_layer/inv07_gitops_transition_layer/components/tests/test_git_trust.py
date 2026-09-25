"""Components 01 (git transport), 02 (ref policy), 03 (signatures), 04
(provenance), 27 (freshness/replay)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest

import fixtures as F
from inv07_gitops_transition_layer.components import ed25519, errors as E, provenance, repotools, signing
from inv07_gitops_transition_layer.components.gitrepo import GitRepository, check_url, parse_commit
from inv07_gitops_transition_layer.components.refpolicy import FreshnessGuard, RefPolicy
from inv07_gitops_transition_layer.components.signing import TrustRoots, verify_commit, verify_openpgp_status

VEC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vectors", "rfc8032_ed25519.json")


def _mirror(env, **kw):
    return GitRepository(env.url, os.path.join(env.tmp, "m-" + os.urandom(3).hex() + ".git"), allow_file=True, **kw)


class TestGitTransport(unittest.TestCase):
    def setUp(self):
        self.e = F.Env()
        self.o1 = self.e.commit({"deploy/a.json": F.configmap()})

    def tearDown(self):
        self.e.cleanup()

    def test_fetch_resolve_read_tree_and_blob(self):
        r = _mirror(self.e)
        info = r.fetch()
        self.assertGreaterEqual(info["refs"], 1)
        self.assertEqual(r.resolve("refs/heads/main"), self.o1)
        items = r.ls_tree(self.o1, "deploy")
        self.assertEqual([p for _, _, p in items], ["deploy/a.json"])
        self.assertIn(b"ConfigMap", r.read_blob(items[0][1]))
        self.assertIsNotNone(r.note(self.o1))

    def test_incremental_fetch_and_prune(self):
        r = _mirror(self.e)
        r.fetch()
        o2 = self.e.commit({"deploy/b.json": F.configmap("two")})
        r.fetch()
        self.assertEqual(r.resolve("refs/heads/main"), o2)
        self.assertTrue(r.is_ancestor(self.o1, o2))
        self.assertFalse(r.is_ancestor(o2, self.o1))

    def test_remote_pinning_detects_changed_url(self):
        r = _mirror(self.e)
        r.fetch()
        subprocess.run(["git", "--git-dir", r.dir, "config", "remote.origin.url", "file:///elsewhere"], check=True)
        with self.assertRaises(E.RepositoryIdentity):
            r.fetch()

    def test_root_commit_identity_pin(self):
        r = _mirror(self.e, root_commit=self.o1)
        r.fetch()
        r.resolve("refs/heads/main")
        other = F.Env()
        try:
            oo = other.commit({"x.json": F.configmap()})
            r2 = GitRepository(other.url, os.path.join(other.tmp, "m.git"), allow_file=True, root_commit=self.o1)
            r2.fetch()
            with self.assertRaises(E.RepositoryIdentity):
                r2.resolve("refs/heads/main")
            self.assertTrue(oo)
        finally:
            other.cleanup()

    def test_shallow_with_identity_refused(self):
        with self.assertRaises(E.RepositoryIdentity):
            _mirror(self.e, root_commit=self.o1, depth=1)

    def test_shallow_fetch_policy(self):
        self.e.commit({"deploy/b.json": F.configmap("b")})
        r = _mirror(self.e, depth=1)
        r.fetch()
        self.assertTrue(os.path.exists(os.path.join(r.dir, "shallow")))

    def test_unavailable_repository_is_retryable_error(self):
        r = GitRepository("file:///nonexistent/repo-" + os.urandom(4).hex(), os.path.join(self.e.tmp, "x.git"),
                          allow_file=True, timeout=20)
        with self.assertRaises(E.RepositoryUnavailable) as cm:
            r.fetch()
        self.assertEqual(cm.exception.retry, E.RETRYABLE)
        self.assertEqual(r.last_error, "PKG-REPO-002")

    def test_url_policy_rejections(self):
        for bad in ("http://git.example/r", "-uevil", "https://user:tok@git.example/r", "ftp://x/y",
                    "https://git.example/r\nx"):
            with self.subTest(bad=bad), self.assertRaises(E.NetworkPolicy):
                check_url(bad)
        with self.assertRaises(E.NetworkPolicy):
            check_url("https://evil.example/r", allowed_hosts=["git.example"])
        with self.assertRaises(E.NetworkPolicy):
            check_url("file:///tmp/r")
        self.assertEqual(check_url("git@git.example:org/r.git", allowed_hosts=["git.example"]), "ssh")

    def test_credential_never_in_argv_and_redacted(self):
        r = GitRepository("file:///nonexistent/" + os.urandom(4).hex(), os.path.join(self.e.tmp, "c.git"),
                          allow_file=True, credential=lambda: "Bearer supersecrettoken123")
        env = r._env()
        self.assertIn("Authorization: Bearer supersecrettoken123", env.values())
        with self.assertRaises(E.RepositoryUnavailable) as cm:
            r.fetch()
        self.assertNotIn("supersecrettoken123", json.dumps(cm.exception.envelope()))

    def test_ref_and_oid_injection_rejected(self):
        r = _mirror(self.e)
        r.fetch()
        for bad in ("--upload-pack=x", "refs/heads/../x", "HEAD", "main"):
            with self.subTest(bad=bad), self.assertRaises(E.Malformed):
                r.resolve(bad)
        with self.assertRaises(E.Malformed):
            r.read_commit("--all")

    def test_blob_size_limit(self):
        self.e.commit({"big.json": "x" * 5000})
        r = _mirror(self.e, max_blob_bytes=1000)
        r.fetch()
        oid = r.resolve("refs/heads/main")
        big = [b for _, b, p in r.ls_tree(oid) if p == "big.json"][0]
        with self.assertRaises(E.LimitExceeded):
            r.read_blob(big)


class TestRefPolicy(unittest.TestCase):
    def test_exact_refs_pins_and_ancestry(self):
        p = RefPolicy("u", ("refs/heads/main",), pins={"refs/heads/main": "a" * 40})
        anc = lambda a, b: a == "b" * 40  # noqa: E731
        with self.assertRaises(E.RefNotApproved):
            p.admit(repo_url="other", ref="refs/heads/main", oid="a" * 40, previous=None, is_ancestor=anc)
        with self.assertRaises(E.RefNotApproved):
            p.admit(repo_url="u", ref="refs/heads/dev", oid="a" * 40, previous=None, is_ancestor=anc)
        with self.assertRaises(E.RefNotApproved):
            p.admit(repo_url="u", ref="refs/heads/main", oid="c" * 40, previous=None, is_ancestor=anc)
        self.assertEqual(p.admit(repo_url="u", ref="refs/heads/main", oid="a" * 40, previous="b" * 40,
                                 is_ancestor=anc)["mode"], "fast_forward")
        q = RefPolicy("u", ("refs/heads/main",))
        with self.assertRaises(E.NonFastForward):
            q.admit(repo_url="u", ref="refs/heads/main", oid="d" * 40, previous="e" * 40, is_ancestor=lambda a, b: False)
        self.assertEqual(q.admit(repo_url="u", ref="refs/heads/main", oid="d" * 40, previous="e" * 40,
                                 is_ancestor=lambda a, b: False,
                                 exception={"ref": "refs/heads/main", "to": "d" * 40, "approved_by": "sec"})["mode"],
                         "rollback_exception")

    def test_globs_only_for_tags_when_enabled(self):
        with self.assertRaises(E.Malformed):
            RefPolicy("u", ("refs/heads/*",))
        with self.assertRaises(E.Malformed):
            RefPolicy("u", ("main",))
        p = RefPolicy("u", ("refs/tags/v*",), allow_tag_globs=True)
        self.assertTrue(p.is_approved("refs/tags/v1.2"))
        self.assertFalse(p.is_approved("refs/heads/v1"))

    def test_non_fast_forward_force_push_refused_end_to_end(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            c = e.controller()
            self.assertEqual(c.reconcile("refs/heads/main")["outcome"], "applied")
            # rewrite history: new root commit on main (force push)
            subprocess.run(["git", "-C", e.work, "update-ref", "-d", "refs/heads/main"], check=True)
            e.commit({"a.json": F.configmap(mode="evil")})
            r = c.reconcile("refs/heads/main")
            self.assertEqual(r["outcome"], "refused")
            self.assertIn(r["error"]["code"], ("PKG-REF-002", "PKG-REF-003"))
        finally:
            e.cleanup()


class TestSignatures(unittest.TestCase):
    def setUp(self):
        self.roots = TrustRoots.from_doc(F.trust_doc())
        self.e = F.Env()

    def tearDown(self):
        self.e.cleanup()

    def _commit(self, **kw):
        oid = self.e.commit({"a.json": F.configmap(v=os.urandom(2).hex())}, provenance=False, **kw)
        raw = subprocess.run(["git", "-C", self.e.work, "cat-file", "commit", oid], capture_output=True).stdout
        return parse_commit(oid, raw)

    def test_rfc8032_vectors(self):
        for v in json.load(open(VEC)):
            sk, pk, msg, sig = (bytes.fromhex(v[k]) for k in ("secret", "public", "message", "signature"))
            self.assertEqual(ed25519.public_key(sk), pk)
            self.assertEqual(ed25519.sign(sk, msg), sig)
            self.assertTrue(ed25519.verify(pk, msg, sig))
            self.assertFalse(ed25519.verify(pk, msg + b"x", sig))

    def test_valid_signed_commit_verifies_and_git_accepts_object(self):
        c = self._commit()
        v = verify_commit(c, self.roots, ref="refs/heads/main", now=F.NOW)
        self.assertEqual((v.key_id, v.algorithm, v.identity), ("dev", "ed25519", F.DEV_EMAIL))
        fsck = subprocess.run(["git", "-C", self.e.work, "fsck", "--strict"], capture_output=True)
        self.assertEqual(fsck.returncode, 0, fsck.stderr)

    def test_unsigned_untrusted_wrong_identity_scope_revoked_expired(self):
        with self.assertRaises(E.Unsigned):
            verify_commit(self._commit(key=None), self.roots, ref="refs/heads/main", now=F.NOW)
        with self.assertRaises(E.Untrusted):
            verify_commit(self._commit(key="rogue"), self.roots, ref="refs/heads/main", now=F.NOW)
        with self.assertRaises(E.Untrusted):  # dev key used with another committer identity
            verify_commit(self._commit(key="dev", email=F.DEV2_EMAIL), self.roots, ref="refs/heads/main", now=F.NOW)
        with self.assertRaises(E.Untrusted):  # dev2 scoped to main only
            verify_commit(self._commit(key="dev2", email=F.DEV2_EMAIL), self.roots, ref="refs/tags/v1", now=F.NOW)
        c = self._commit()
        roots = TrustRoots.from_doc(F.trust_doc())
        roots.revoke("dev", F.NOW - 10)
        with self.assertRaises(E.Revoked):
            verify_commit(c, roots, ref="refs/heads/main", now=F.NOW)
        d = F.trust_doc()
        d["keys"][0]["not_after"] = F.NOW - 100
        with self.assertRaises(E.Expired):
            verify_commit(c, TrustRoots.from_doc(d), ref="refs/heads/main", now=F.NOW)

    def test_signature_confusion_and_tamper(self):
        c = self._commit()
        # signature from dev key claiming key id dev2 (key-id confusion)
        kid, sig = signing.dearmor(c.signature)
        forged = signing.armor("dev2", sig)
        c2 = parse_commit(c.oid, signing.insert_signature(c.signed_payload, forged))
        with self.assertRaises((E.Unsigned, E.Untrusted)):
            verify_commit(c2, self.roots, ref="refs/heads/main", now=F.NOW)
        # payload tamper
        c3 = parse_commit(c.oid, signing.insert_signature(c.signed_payload.replace(b"change", b"chXnge"), c.signature))
        with self.assertRaises(E.Unsigned):
            verify_commit(c3, self.roots, ref="refs/heads/main", now=F.NOW)
        # algorithm policy: key known but algorithm not allowed
        d = F.trust_doc(allowed_algorithms=["openpgp"])
        with self.assertRaises(E.Untrusted):
            verify_commit(c, TrustRoots.from_doc(d), ref="refs/heads/main", now=F.NOW)
        # duplicate signature headers
        dup = signing.insert_signature(signing.insert_signature(c.signed_payload, c.signature), c.signature)
        with self.assertRaises(E.Malformed):
            parse_commit(c.oid, dup)

    def test_trust_roots_file_digest_pin(self):
        p = os.path.join(self.e.tmp, "trust_roots.json")
        import hashlib
        good = hashlib.sha256(open(p, "rb").read()).hexdigest()
        TrustRoots.load(p, expected_sha256=good)
        with self.assertRaises(E.Untrusted):
            TrustRoots.load(p, expected_sha256="0" * 64)

    @unittest.skipUnless(shutil.which("gpg"), "OpenPGP lane: gpg not installed")
    def test_openpgp_lane_with_real_gpg(self):
        home = tempfile.mkdtemp(prefix="gnupg-")
        os.chmod(home, 0o700)
        try:
            env = {**os.environ, "GNUPGHOME": home}
            subprocess.run(["gpg", "--batch", "--pinentry-mode", "loopback", "--passphrase", "", "--quick-gen-key",
                            "PGP Dev <pgp@example.invalid>", "ed25519", "sign", "1d"], env=env, check=True,
                           capture_output=True)
            fpr = [ln.split(":")[9] for ln in subprocess.run(["gpg", "--with-colons", "--list-keys"], env=env,
                   capture_output=True, text=True).stdout.splitlines() if ln.startswith("fpr")][0]
            w = self.e.work
            for k, v in (("user.signingkey", fpr), ("gpg.program", shutil.which("gpg")),
                         ("user.email", "pgp@example.invalid"), ("gpg.format", "openpgp")):
                subprocess.run(["git", "-C", w, "config", k, v], check=True)
            repotools.write_files(w, {"p.json": F.configmap(p="1")})
            subprocess.run(["git", "-C", w, "add", "-A"], check=True)
            subprocess.run(["git", "-C", w, "commit", "-q", "-S", "-m", "pgp"], env=env, check=True)
            r = _mirror(self.e)
            r.fetch()
            oid = r.resolve("refs/heads/main")
            c = r.read_commit(oid)
            status = r.verify_commit_openpgp(oid, home)
            d = F.trust_doc()
            d["keys"].append({"key_id": "pgp", "algorithm": "openpgp", "identity": "pgp@example.invalid",
                              "fingerprint": fpr})
            v = verify_openpgp_status(c, status, TrustRoots.from_doc(d), ref="refs/heads/main", now=F.NOW)
            self.assertEqual(v.key_id, "pgp")
            with self.assertRaises(E.Untrusted):
                verify_openpgp_status(c, status, self.roots, ref="refs/heads/main", now=F.NOW)
            with self.assertRaises(E.Unsigned):
                verify_openpgp_status(c, ["[GNUPG:] REVKEYSIG X"], TrustRoots.from_doc(d), ref="refs/heads/main",
                                      now=F.NOW)
        finally:
            shutil.rmtree(home, ignore_errors=True)


class TestProvenance(unittest.TestCase):
    def setUp(self):
        self.roots = TrustRoots.from_doc(F.trust_doc())
        self.st = provenance.make_statement(commit="a" * 40, tree="b" * 40, repo_url="u", builder_id=F.BUILDER,
                                            ref="refs/heads/main")

    def _v(self, raw, **kw):
        args = dict(commit="a" * 40, tree="b" * 40, repo_url="u", roots=self.roots, now=F.NOW,
                    allowed_builders=(F.BUILDER,))
        args.update(kw)
        return provenance.verify(raw, **args)

    def test_valid_envelope(self):
        raw = provenance.sign_envelope(self.st, [("builder", F.KEYS["builder"][0])])
        self.assertEqual(self._v(raw)["signers"], ["builder"])

    def test_failures_fail_closed(self):
        good = provenance.sign_envelope(self.st, [("builder", F.KEYS["builder"][0])])
        cases = {
            "missing": None,
            "wrong commit binding": good,
            "dev key is not a builder": provenance.sign_envelope(self.st, [("dev", F.KEYS["dev"][0])]),
            "rogue": provenance.sign_envelope(self.st, [("builder", F.KEYS["rogue"][0])]),
            "garbage": b"{not json",
        }
        for name, raw in cases.items():
            with self.subTest(name), self.assertRaises(E.ProvenanceFailed):
                self._v(raw, commit="c" * 40) if name == "wrong commit binding" else self._v(raw)
        with self.assertRaises(E.ProvenanceFailed):
            self._v(good, allowed_builders=("other",))
        with self.assertRaises(E.ProvenanceFailed):
            self._v(good, repo_url="https://elsewhere")
        with self.assertRaises(E.ProvenanceFailed):
            self._v(good, threshold=2)
        with self.assertRaises(E.ProvenanceFailed):
            self._v(good, require_external=True)
        with self.assertRaises(E.ProvenanceFailed):
            self._v(good, external_verifier=lambda raw: False)
        self.assertTrue(self._v(good, external_verifier=lambda raw: True))

    def test_note_copied_to_other_commit_fails(self):
        e = F.Env()
        try:
            o1 = e.commit({"a.json": F.configmap()})
            o2 = e.commit({"a.json": F.configmap(mode="x")}, provenance=False)
            note = subprocess.run(["git", "-C", e.work, "notes", "--ref", "refs/notes/provenance", "show", o1],
                                  capture_output=True).stdout
            subprocess.run(["git", "-C", e.work, "notes", "--ref", "refs/notes/provenance", "add", "-f", "-F", "-", o2],
                           input=note, check=True)
            c = e.controller()
            r = c.reconcile("refs/heads/main")
            self.assertEqual(r["outcome"], "refused")
            self.assertEqual(r["error"]["code"], "PKG-TRUST-005")
        finally:
            e.cleanup()


class TestFreshness(unittest.TestCase):
    def test_age_future_and_generation(self):
        d = tempfile.mkdtemp()
        try:
            g = FreshnessGuard(os.path.join(d, "f.json"), max_commit_age=1000)
            with self.assertRaises(E.StaleRef):
                g.check("r", "a" * 40, 0, 5000, descends=True)
            with self.assertRaises(E.StaleRef):
                g.check("r", "a" * 40, 10_000, 5000, descends=True)
            g.check("r", "a" * 40, 4900, 5000, descends=True)
            self.assertEqual(g.accept("r", "a" * 40, 4900, trust_digest="t", policy_digest="p", mode="initial")
                             ["generation"], 1)
            self.assertEqual(g.accept("r", "b" * 40, 4950, trust_digest="t", policy_digest="p", mode="ff")
                             ["generation"], 2)
            with self.assertRaises(E.StaleRef):
                g.check("r", "a" * 40, 4900, 5000, descends=False)
            g2 = FreshnessGuard(os.path.join(d, "f.json"), max_commit_age=1000)  # durable
            self.assertEqual(g2.last("r")["generation"], 2)
            self.assertTrue(g2.still_valid("r", trust_digest="t", policy_digest="p"))
            self.assertFalse(g2.still_valid("r", trust_digest="t2", policy_digest="p"))
        finally:
            shutil.rmtree(d)

    def test_replay_of_old_signed_commit_refused(self):
        e = F.Env()
        try:
            o1 = e.commit({"a.json": F.configmap()})
            c = e.controller()
            c.reconcile("refs/heads/main")
            e.commit({"a.json": F.configmap(mode="v2")})
            c.reconcile("refs/heads/main")
            subprocess.run(["git", "-C", e.work, "update-ref", "refs/heads/main", o1], check=True)
            r = c.reconcile("refs/heads/main")
            self.assertEqual(r["outcome"], "refused")
            self.assertIn(r["error"]["code"], ("PKG-REF-002", "PKG-REF-003"))
        finally:
            e.cleanup()


if __name__ == "__main__":
    unittest.main()
