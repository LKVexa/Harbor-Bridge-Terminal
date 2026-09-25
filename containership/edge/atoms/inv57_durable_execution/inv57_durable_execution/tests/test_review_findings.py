"""Regression tests for defects found by the independent adversarial review of v4.3.0.

R1  effect_mark/effect_prepare were not scoped to the lease's workflow (cross-workflow overwrite).
R2  HistoryEvent.payload was a mutable dict reachable via store.events (in-place history rewrite).
R3  gate: symlinked evidence resolved; any HMAC key counted as a signature; test report unhashed.
R4  decoder: list-typed kind (TypeError), deep nesting (RecursionError), bytes input escaped.
R5  crash test: no kill points at effect-ledger commits; child lease TTL (0.5 s) could flake.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from . import _path  # noqa: F401

from inv57_durable_execution import effects
from inv57_durable_execution.acceptance import evaluate
from inv57_durable_execution.durable import (ActivityInDoubt, HistoryCorruption, InMemoryHistoryStore,
                                             Worker)
from inv57_durable_execution.errors import Unauthorized
from inv57_durable_execution.identity import WorkflowIdentity
from inv57_durable_execution.sqlite_store import CRASH_ENV, SQLiteBackend, SQLiteHistoryStore

PKG = str(_path.ROOT / "inv57_durable_execution")


def ident(wf):
    return WorkflowIdentity("t", "test", "s", "n", wf, "run-1")


class R1EffectScoping(unittest.TestCase):
    def test_foreign_lease_cannot_mark_or_alias_effect(self):
        b = SQLiteBackend(os.path.join(tempfile.mkdtemp(), "x.db"))
        la, lb = b.acquire(ident("A"), "wa", 60), b.acquire(ident("B"), "wb", 60)
        b.effect_prepare(la, "effA", "act", "idempotent", "{}")
        with self.assertRaises(Unauthorized):
            b.effect_mark(lb, "effA", "done", "forged")
        with self.assertRaises(Unauthorized):
            b.effect_prepare(lb, "effA", "act", "idempotent", "{}")
        with self.assertRaises(Unauthorized):
            b.effect_prepare(la, "effA", "act", "idempotent", '{"other":1}')
        self.assertEqual(b.effect_get("effA")["status"], "prepared")
        b.effect_prepare(la, "effA", "act", "idempotent", "{}")          # idempotent re-prepare ok


class R2FrozenPayload(unittest.TestCase):
    def test_payload_cannot_be_mutated_through_events(self):
        w = Worker()
        w.run(lambda w: w.activity("a", lambda: {"x": [1, 2]}))
        ev = w.history_store.events[1]
        with self.assertRaises(TypeError):
            ev.payload["v"] = "999"
        with self.assertRaises((TypeError, AttributeError)):
            ev.payload["v"][0][1]["v"].append(1)
        self.assertEqual(w.history_store.completed_history(), [("a", {"x": [1, 2]})])
        text = w.history_store.to_json()
        self.assertEqual(InMemoryHistoryStore.from_json(text).to_json(), text)


class R3GateHardening(unittest.TestCase):
    def _copy(self):
        root = os.path.join(tempfile.mkdtemp(), "pkg")
        shutil.copytree(PKG, root, ignore=shutil.ignore_patterns("__pycache__"))
        return root

    def test_symlinked_evidence_rejected(self):
        root = self._copy()
        os.symlink("/etc/hostname", os.path.join(root, "evil.txt"))
        reg_p = os.path.join(root, "STATUS_REGISTER.json")
        with open(reg_p) as fh:
            reg = json.load(fh)
        reg["components"][0]["evidence"] = ["evil.txt"]
        with open(reg_p, "w") as fh:
            json.dump(reg, fh)
        m = evaluate(root)
        self.assertIn("evidence does not resolve: evil.txt", [p["problem"] for p in m["problems"]])

    def test_forged_everything_with_untrusted_key_is_still_no_go(self):
        root = self._copy()
        for name, key in (("TRACEABILITY.json", "items"), ("STATUS_REGISTER.json", "components")):
            p = os.path.join(root, name)
            with open(p) as fh:
                d = json.load(fh)
            for it in d[key]:
                it["status"] = "present" if key == "items" else "CLOSED"
                it["evidence"], it["tests"] = [], []
            with open(p, "w") as fh:
                json.dump(d, fh)
        with open(os.path.join(root, "OWNERS.yaml"), "w") as fh:
            fh.write("schema: x\n")
        with open(os.path.join(root, "test-report.json"), "w") as fh:
            json.dump({"tests": {"fake.t": "passed"}}, fh)
        m = evaluate(root, signing_key=b"x", key_id="attacker")
        self.assertEqual(m["verdict"], "NO_GO")
        self.assertIn("signing key is not an active key in TRUST_POLICY.json", m["blockers"])
        self.assertIn("no asymmetric provenance attestation (RG-06)", m["blockers"])
        self.assertIsNotNone(m["test_report"]["sha256"])
        self.assertFalse(m["test_report"]["attested"])


class R4DecoderEscapes(unittest.TestCase):
    def _valid(self):
        w = Worker()
        w.run(lambda w: w.activity("a", lambda: 1))
        return json.loads(w.history_store.to_json())

    def test_wrong_typed_fields(self):
        for field, bad in (("kind", []), ("kind", {}), ("schema", []), ("seq", True), ("seq", "0"),
                           ("prev_digest", [])):
            with self.subTest(field=field, bad=bad):
                h = self._valid()
                h[0][field] = bad
                with self.assertRaises(HistoryCorruption):
                    InMemoryHistoryStore.from_json(json.dumps(h))

    def test_deep_nesting_and_bytes(self):
        with self.assertRaises(HistoryCorruption):
            InMemoryHistoryStore.from_json("[" * 100000)
        h = self._valid()
        marker = '"__DEEP__"'
        h[1]["payload"] = "__DEEP__"
        deep = '{"t":"list","v":[' * 5000 + '{"t":"none"}' + "]}" * 5000   # built as text: json.dumps would recurse
        with self.assertRaises(HistoryCorruption):
            InMemoryHistoryStore.from_json(json.dumps(h).replace(marker, deep))
        with self.assertRaises(HistoryCorruption):
            InMemoryHistoryStore.from_json(b"\xff")


class FileProvider:
    """Provider with durable conditional-create keyed by effect_id (file-backed, survives kill)."""

    def __init__(self, path):
        self.path = path

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        with open(self.path) as fh:
            return json.load(fh)

    def submit(self, eid, req):
        d = self._load()
        if eid not in d:
            d[eid] = {"receipt": "r-" + eid[-6:], "submits": 0}
        d[eid]["submits"] += 1
        with open(self.path, "w") as fh:
            json.dump(d, fh)
            fh.flush()
            os.fsync(fh.fileno())
        return {"receipt": d[eid]["receipt"]}

    def lookup(self, eid):
        d = self._load()
        return {"receipt": d[eid]["receipt"]} if eid in d else None


EFFECT_CHILD = textwrap.dedent("""
    import sys
    sys.path.insert(0, {root!r})
    from inv57_durable_execution.durable import Worker
    from inv57_durable_execution.identity import WorkflowIdentity
    from inv57_durable_execution.sqlite_store import SQLiteBackend, SQLiteHistoryStore
    from inv57_durable_execution import effects
    from inv57_durable_execution.tests.test_review_findings import FileProvider
    ident = WorkflowIdentity("t", "test", "s", "ns", "wf", "run-1")
    b = SQLiteBackend(sys.argv[1])
    store = SQLiteHistoryStore(b, ident, b.acquire(ident, "child", 30))
    Worker(store).run(lambda w: effects.run_effect(w, "pay", FileProvider(sys.argv[2]), {{"amt": 5}},
                                                    effect_class="idempotent"))
""")


class R5EffectCrashBoundaries(unittest.TestCase):
    def test_kill_at_every_effect_ledger_commit(self):
        from .test_crash_boundaries import _ident
        for point in ("effect_prepare_before_commit", "effect_prepare_after_commit",
                      "effect_mark_before_commit", "effect_mark_after_commit"):
            with self.subTest(point=point):
                d = tempfile.mkdtemp()
                db, prov = os.path.join(d, "h.db"), os.path.join(d, "provider.json")
                env = dict(os.environ, **{CRASH_ENV: f"{point}:0"})
                r = subprocess.run([sys.executable, "-c", EFFECT_CHILD.format(root=str(_path.ROOT)), db, prov],
                                   env=env, capture_output=True, text=True, timeout=60)
                self.assertEqual(r.returncode, 137, r.stderr)
                b = SQLiteBackend(db, clock=lambda: 1e12)
                store = SQLiteHistoryStore(b, _ident(), b.acquire(_ident(), "recovery", 60))
                w = Worker(store)
                provider = FileProvider(prov)
                wf = lambda w: effects.run_effect(w, "pay", provider, {"amt": 5}, effect_class="idempotent")
                with self.assertRaises(ActivityInDoubt):
                    w.run(wf)
                if point == "effect_prepare_before_commit":
                    # prepare never committed → dispatch never happened → operator decision, no apply
                    from inv57_durable_execution.errors import EffectUnresolved
                    with self.assertRaises(EffectUnresolved):
                        effects.reconcile_in_doubt(w, provider)
                    self.assertFalse(os.path.exists(prov))
                else:
                    effects.reconcile_in_doubt(w, provider)
                    with open(prov) as fh:
                        applied = json.load(fh)
                    self.assertEqual(len(applied), 1)
                    # Provider dedupes on effect_id: however many submits, one real effect.
                    self.assertEqual(Worker(SQLiteHistoryStore(b, _ident(), b.acquire(_ident(), "recovery", 60)))
                                     .run(wf)["receipt"], next(iter(applied.values()))["receipt"])
                b.close()


if __name__ == "__main__":
    unittest.main()
