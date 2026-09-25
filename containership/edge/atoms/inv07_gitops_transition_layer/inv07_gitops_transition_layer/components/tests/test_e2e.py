"""Components 41 (local end-to-end integration against real git + a durable
file-backed target), 44 (fuzz), 45 (fault injection) and the CLI."""
from __future__ import annotations

import io
import json
import os
import random
import subprocess
import sys
import threading
import unittest
from contextlib import redirect_stdout

import fixtures as F
from inv07_gitops_transition_layer.components import cli, errors as E, manifests as M, signing
from inv07_gitops_transition_layer.components.gitrepo import parse_commit
from inv07_gitops_transition_layer.components.redact import scrub
from inv07_gitops_transition_layer.components.target import DirectoryTarget


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.e = F.Env(prune=True)

    def tearDown(self):
        self.e.cleanup()

    def test_full_lifecycle(self):
        e = self.e
        o1 = e.commit({"deploy/web.yaml": F.deployment(), "deploy/cm.json": F.configmap()})
        c = e.controller()
        r = c.reconcile("refs/heads/main")
        self.assertEqual((r["outcome"], r["mode"], len(r["actions"])), ("applied", "initial", 2))
        self.assertEqual(c.reconcile("refs/heads/main")["outcome"], "no_change")
        # out-of-band hotfix -> reverted and reported by name
        web = ("apps", "Deployment", "team-a", "web")
        c.target.tamper(web, lambda o: o["spec"].__setitem__("replicas", 9))
        r = c.reconcile("refs/heads/main")
        self.assertEqual((r["outcome"], r["drift"]), ("applied", ["apps/Deployment/team-a/web"]))
        self.assertEqual(c.target.get(web)[0]["spec"]["replicas"], 2)
        drift_doc = c.state.s["drift"][-1]
        self.assertEqual((drift_doc["detected_against"], drift_doc["action"]), (o1, "reverted"))
        # new signed commit (fast-forward) incl. prune of the ConfigMap
        o2 = e.commit({"deploy/web.yaml": F.deployment(replicas=3), "deploy/cm.json": None})
        r = c.reconcile("refs/heads/main")
        self.assertEqual((r["outcome"], r["mode"], r["oid"]), ("applied", "fast_forward", o2))
        self.assertEqual({a["op"] for a in r["actions"]}, {"update", "delete"})
        # rollback by signed revert -> its own history entry
        o3 = e.revert(o1)
        r = c.reconcile("refs/heads/main")
        self.assertEqual((r["outcome"], r["mode"], r["oid"]), ("applied", "signed_revert", o3))
        self.assertEqual(c.target.get(web)[0]["spec"]["replicas"], 2)
        self.assertEqual([a["oid"] for a in c.state.applied()], [o1, o1, o2, o3])   # drift fix re-applies o1
        # audit + provenance of every decision survives restart
        c2 = e.controller()
        self.assertEqual(c2.state.s["cursors"]["refs/heads/main"], o3)
        info = c2.audit.verify()
        self.assertGreater(info["entries"], 8)
        self.assertEqual(c2.reconcile("refs/heads/main")["outcome"], "no_change")

    def test_two_controllers_one_leader_and_stale_leader_fenced(self):
        e = self.e
        e.commit({"a.json": F.configmap()})
        a = e.controller(node="a")
        b = e.controller(node="b")
        b.target = a.target
        self.assertEqual(a.reconcile("refs/heads/main")["outcome"], "applied")
        rb = b.reconcile("refs/heads/main")
        self.assertEqual((rb["outcome"], rb["error"]["code"]), ("failed", "PKG-OPS-002"))
        # a's lease expires while "paused"; b takes over with a higher epoch
        with open(a.lease.path) as fh:
            doc = json.load(fh)
        doc["expires"] = 0
        with open(a.lease.path, "w") as fh:
            json.dump(doc, fh)
        e.commit({"a.json": F.configmap(mode="v2")})
        self.assertEqual(b.reconcile("refs/heads/main")["outcome"], "applied")
        # a wakes up: renew fails (fenced), it re-acquires only if free -> NotLeader
        ra = a.reconcile("refs/heads/main")
        self.assertEqual(ra["outcome"], "failed")
        self.assertIn(ra["error"]["code"], ("PKG-OPS-002", "PKG-OPS-003"))
        with self.assertRaises(E.FencedOff):
            a.target.fence.check(1)

    def test_partial_apply_auto_quarantines_target(self):
        e = self.e
        e.commit({"a.json": F.configmap("a"), "b.json": F.configmap("b")})
        n = {"i": 0}

        def fail(op, rid):
            n["i"] += 1
            if n["i"] >= 4:
                raise E.TargetUnavailable("control plane lost")
        tgt = DirectoryTarget(os.path.join(e.tmp, "tgt"), fail=fail, allow_delete=True)
        e.target = tgt
        c = e.controller()
        r = c.reconcile("refs/heads/main")
        self.assertEqual((r["outcome"], r["error"]["code"]), ("failed", "PKG-APPLY-002"))
        self.assertEqual(c.freezes.active()[0]["scope"], "target")
        tgt._fail = None
        self.assertEqual(c.reconcile("refs/heads/main")["outcome"], "frozen")


class TestFaultInjection(unittest.TestCase):
    def test_git_outage_then_recovery(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            c = e.controller()
            c.retry.sleep = lambda s: None
            c.breaker.threshold = 2
            os.rename(e.work, e.work + ".x")
            for _ in range(2):
                self.assertEqual(c.reconcile("refs/heads/main")["error"]["code"], "PKG-REPO-002")
            self.assertEqual(c.breaker.state, "open")
            self.assertEqual(c.reconcile("refs/heads/main")["error"]["code"], "PKG-OPS-005")
            os.rename(e.work + ".x", e.work)
            c.breaker.opened_at -= 1000
            self.assertEqual(c.reconcile("refs/heads/main")["outcome"], "applied")
        finally:
            e.cleanup()

    def test_crash_between_intent_and_commit_then_restart(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap(), "b.json": F.configmap("b")})
            calls = {"n": 0}

            def crash(op, rid):
                calls["n"] += 1
                if calls["n"] == 4:          # after preflight(2) + 1 real apply
                    raise SystemExit("simulated process crash")
            e.target = DirectoryTarget(os.path.join(e.tmp, "tgt"), fail=crash)
            c = e.controller()
            with self.assertRaises(SystemExit):
                c.reconcile("refs/heads/main")
            self.assertEqual(len(c.state.pending_intents()), 1)
            e.target._fail = None
            c2 = e.controller()              # restart: ambiguous intent read back + aborted
            self.assertEqual(c2.state.pending_intents(), {})
            self.assertEqual(c2.reconcile("refs/heads/main")["outcome"], "applied")
            self.assertEqual(len(c2.target.list()), 2)
        finally:
            e.cleanup()

    def test_disk_full_journal(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            c = e.controller()
            c.state.max_bytes = c.state._size + 10
            r = c.reconcile("refs/heads/main")
            self.assertEqual((r["outcome"], r["error"]["code"]), ("failed", "PKG-INPUT-002"))
            self.assertEqual(c.target.list(), {})     # nothing applied without a journalled intent
        finally:
            e.cleanup()

    def test_concurrent_reconciles_serialised_by_lease_and_journal(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            c = e.controller()
            out = []
            ts = [threading.Thread(target=lambda: out.append(c.reconcile("refs/heads/main")["outcome"]))
                  for _ in range(4)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(len(c.target.list()), 1)
            self.assertIn("applied", out)
            c.audit.verify()
        finally:
            e.cleanup()


class TestFuzz(unittest.TestCase):
    """Structure-aware property fuzzing (deterministic seeds; failures become
    regression cases in fuzz_corpus/).  Property: parsers either return a value
    or raise a *typed* GitOps error -- never another exception."""

    CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuzz_corpus")

    def _mutate(self, rng, data: bytes) -> bytes:
        b = bytearray(data)
        for _ in range(rng.randint(1, 8)):
            op = rng.randint(0, 3)
            pos = rng.randint(0, max(0, len(b) - 1)) if b else 0
            if op == 0 and b:
                b[pos] = rng.randint(0, 255)
            elif op == 1:
                b[pos:pos] = rng.choice([b"&", b"*", b"!", b"<<", b"{", b"[", b"\t", b":", b"-", b"\n  ", b"\"", b"'"])
            elif op == 2 and b:
                del b[pos:pos + rng.randint(1, 4)]
            else:
                b += b[: rng.randint(0, 16)]
        return bytes(b)

    def _prop(self, fn, data):
        try:
            fn(data)
        except E.GitOpsError:
            pass

    def test_yaml_json_manifest_fuzz(self):
        rng = random.Random(7)
        seeds = [F.deployment().encode(), F.configmap().encode()]
        for f in sorted(os.listdir(self.CORPUS)):
            with open(os.path.join(self.CORPUS, f), "rb") as fh:
                seeds.append(fh.read())
        for i in range(3000):
            d = self._mutate(rng, rng.choice(seeds))
            self._prop(M.parse_yaml, d)
            self._prop(M.parse_json, d)
            self._prop(lambda x: M.load_tree([("f.yaml", x), ("g.json", x)]), d)

    def test_commit_signature_fuzz(self):
        rng = random.Random(11)
        e = F.Env()
        try:
            oid = e.commit({"a.json": F.configmap()}, provenance=False)
            raw = subprocess.run(["git", "-C", e.work, "cat-file", "commit", oid], capture_output=True).stdout
            roots = signing.TrustRoots.from_doc(F.trust_doc())
            ok = 0
            for _ in range(400):
                d = self._mutate(rng, raw)
                try:
                    c = parse_commit(oid, d)
                    signing.verify_commit(c, roots, ref="refs/heads/main", now=F.NOW)
                    ok += 1
                except E.GitOpsError:
                    pass
            self.assertLessEqual(ok, 5)      # only mutations outside the signed payload may still verify
        finally:
            e.cleanup()

    def test_redaction_fuzz(self):
        rng = random.Random(3)
        for _ in range(500):
            secret = "".join(rng.choice("abcdef0123456789") for _ in range(24))
            blob = json.dumps(scrub({"x": f"token {secret}", "password": secret, "u": f"https://a:{secret}@h/"}))
            self.assertNotIn(secret, blob)


class TestCLI(unittest.TestCase):
    def test_config_validate_sync_status_backup(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            cfg = os.path.join(e.tmp, "config.json")
            doc = dict(e.doc)
            doc["repository"] = dict(doc["repository"], url="https://git.example/acme/deploy")
            with open(cfg, "w") as fh:
                json.dump(doc, fh)
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(cli.main(["config-validate", cfg]), 0)
            self.assertTrue(json.loads(buf.getvalue())["valid"])
            bad = os.path.join(e.tmp, "bad.json")
            with open(bad, "w") as fh:
                json.dump({"schema": "PK_GITOPS_CONFIG/1", "trust": {"require_signed": False}}, fh)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["config-validate", bad]), 64)
            c = e.controller()
            c.reconcile("refs/heads/main")
            sd = os.path.join(e.tmp, "acme", "edge-1", "state")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["backup", cfg, os.path.join(e.tmp, "bk"), "--base-dir", e.tmp]), 0)
                self.assertEqual(cli.main(["restore", os.path.join(e.tmp, "bk"), os.path.join(e.tmp, "rs")]), 0)
            self.assertTrue(os.path.exists(os.path.join(e.tmp, "rs", "audit.jsonl")))
            self.assertTrue(os.path.isdir(sd))
            p = subprocess.run([sys.executable, "-B", "-m", "inv07_gitops_transition_layer.components.cli",
                                "config-validate", cfg], capture_output=True, text=True,
                               cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                                   os.path.abspath(__file__))))))
            self.assertEqual(p.returncode, 0, p.stderr)
        finally:
            e.cleanup()


if __name__ == "__main__":
    unittest.main()
