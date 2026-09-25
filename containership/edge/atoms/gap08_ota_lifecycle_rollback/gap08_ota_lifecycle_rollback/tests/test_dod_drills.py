"""Definition-of-Done drills named in the GAP-08 professional checklist (sections 3, 5, 6, 11, 15)."""
from __future__ import annotations

import threading
import unittest

import _path  # noqa: F401
from gap08_ota_lifecycle_rollback.audit_sink import reconstruct
from gap08_ota_lifecycle_rollback.authz import Principal
from gap08_ota_lifecycle_rollback.dependencies import POLICY, Mode, OpClass
from gap08_ota_lifecycle_rollback.errors import (Conflict, DependencyUnavailable, Gap08Error, IntegrityFailure,
                                                 Unauthorized)
from gap08_ota_lifecycle_rollback.harness import COMPAT, OPERATOR, SRE, build_world, spread_waves


def create(w, c, env="prod", lineage="edge"):
    return c.create(OPERATOR, bundle="v2", waves=spread_waves(w, (1, 2, 3, 6)), environment=env,
                    verification=w.verification(), compat_profile=COMPAT, lineage=lineage)["rollout_id"]


class Section03OverlapSameInstant(unittest.TestCase):
    def test_simultaneous_overlapping_rollouts_one_blocked_before_execution(self):
        w = build_world()
        ctls = [w.controller(f"c{i}") for i in range(6)]
        res = []

        def go(c):
            try:
                res.append(create(w, c))
            except Conflict:
                res.append("blocked")
        ts = [threading.Thread(target=go, args=(c,)) for c in ctls]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sum(r != "blocked" for r in res), 1, res)
        self.assertTrue(all(s.executions == 0 for s in w.nodes.values()))  # nothing executed on any node


class Section05TamperDrill(unittest.TestCase):
    def test_post_seal_tamper_detected_and_chain_reconstructed(self):
        w = build_world()
        c = w.controller()
        rid = create(w, c)
        c.step(OPERATOR, rid)
        w.pass_gate(c, rid, healthy=False)
        state = w.store.load(rid).state
        local = [dict(e) for e in state["core"]["audit_log"]]
        w.sink.verify_against(local)
        forged = [dict(e) for e in local]
        forged[-1] = {**forged[-1], "payload": {**forged[-1]["payload"], "reason": "nothing happened"}}
        with self.assertRaises(IntegrityFailure):
            w.sink.verify_against(forged)          # edit without re-hashing
        from gap08_ota_lifecycle_rollback.common import canonical_json, sha256_hex
        body = {k: v for k, v in forged[-1].items() if k != "event_hash"}
        forged[-1]["event_hash"] = sha256_hex(canonical_json(body))
        with self.assertRaises(IntegrityFailure):
            w.sink.verify_against(forged)          # edit with re-hashing (privileged rewriter)
        chain = reconstruct(w.sink, w.ring, rid)
        self.assertEqual([e["event_hash"] for e in chain], [e["event_hash"] for e in local])


class Section06OneByteMutation(unittest.TestCase):
    def test_mutated_byte_blocks_install_before_activation(self):
        w = build_world(installers=True)
        c = w.controller()
        rid = create(w, c)
        n = spread_waves(w, (1,))[0][0]
        bad = bytearray(w.payload)
        bad[100] ^= 0x01
        w.nodes[n].payloads[w.digest] = bytes(bad)      # corrupted in transit/cache after verification
        try:
            c.step(OPERATOR, rid)
        except Gap08Error:
            pass
        ins = w.nodes[n].installer
        self.assertIsNone(ins.ctl()["pending"])         # never activated
        self.assertEqual(ins.ctl()["active"], "A")
        self.assertEqual(w.nodes[n].version, "v1")


class Section11ScopedAuthorization(unittest.TestCase):
    def test_every_lifecycle_action_denied_outside_scope(self):
        w = build_world()
        c = w.controller()
        rid = create(w, c)
        c.step(OPERATOR, rid)
        staging_op = Principal("sam", frozenset({"release-operator", "sre-oncall"}), environments=frozenset({"stg"}))
        actions = {
            "create": lambda: create(w, c, env="prod", lineage="other"),
            "step": lambda: c.step(staging_op, rid),
            "gate": lambda: c.gate(staging_op, rid, {}),
            "retry": lambda: c.retry_deferred(staging_op, rid, force=True),
            "rollback": lambda: c.rollback(staging_op, rid, reason="x"),
            "pause": lambda: c.pause(staging_op, rid, "x"),
            "resume": lambda: c.resume(staging_op, rid, "x"),
            "cancel": lambda: c.cancel(staging_op, rid, reason="x"),
            "reconcile": lambda: c.reconcile(staging_op, rid),
            "reverify": lambda: c.reverify(staging_op, rid, w.verification()),
            "release": lambda: c.release_quarantine(staging_op, rid, "n001", approval_id="x", evidence_note="x"),
        }
        actions["create"] = lambda: c.create(staging_op, bundle="v2", waves=[["n001"]], environment="prod",
                                             verification=w.verification(), compat_profile=COMPAT)
        for name, fn in actions.items():
            with self.subTest(name):
                with self.assertRaises(Unauthorized):
                    fn()


class Section15DependencyMatrix(unittest.TestCase):
    """Remove each dependency at each lifecycle phase; the action must match the documented policy."""

    PHASES = {
        "step": (OpClass.FORWARD, lambda w, c, rid: c.step(OPERATOR, rid)),
        "gate": (OpClass.FORWARD, lambda w, c, rid: w.pass_gate(c, rid)),
        "rollback": (OpClass.ROLLBACK, lambda w, c, rid: c.rollback(SRE, rid, reason="matrix")),
        "pause": (OpClass.ROLLBACK, lambda w, c, rid: c.pause(SRE, rid, "matrix")),
    }

    def test_matrix(self):
        for dep, modes in POLICY.items():
            for phase, (op, fn) in self.PHASES.items():
                with self.subTest(dep=dep, phase=phase):
                    w = build_world()
                    c = w.controller()
                    rid = create(w, c)
                    if phase == "gate":
                        c.step(OPERATOR, rid)
                    w.deps.report(dep, False)
                    mode = modes[op]
                    if mode is Mode.REQUIRED:
                        with self.assertRaises(DependencyUnavailable):
                            fn(w, c, rid)
                        self.assertTrue(all(s.executions == 0 for s in w.nodes.values()) or phase == "gate")
                    else:
                        fn(w, c, rid)   # BUFFERED / NOT_USED: the recovery action proceeds


if __name__ == "__main__":
    unittest.main()
