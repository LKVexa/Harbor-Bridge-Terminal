"""Seeded fuzzing of keys, revisions, frames, authz and resource exhaustion (MC-045)."""
from __future__ import annotations

import json
import random
import resource
import string
import unittest

from _util import NS_A, NS_B, ctx, make_service, principal, txn_body
from inv05_current_control_state_system.errors import StateError
from inv05_current_control_state_system.limits import Limits
from inv05_current_control_state_system.schema import check_message, loads, parse_compare, parse_op
from inv05_current_control_state_system.security import ACTIONS, CLUSTER, DEFAULT_POLICY, Authorizer, Namespace, Principal
from inv05_current_control_state_system.store import ControlStore, Range

SEED = 20260922
WEIRD = ["", "\x00", "\n", "/", "//", "..", "../../", "‮", "é", "\ud800", "￿", "\U0010ffff", "*", "%00",
         "a" * 2000, "é", "🔑", " ", "\\", "\"", "'", "${x}", "<script>"]


def rand_key(rng):
    if rng.random() < 0.3:
        return rng.choice(WEIRD)
    return "".join(rng.choice(string.printable + "é🔑\x00‮") for _ in range(rng.randrange(0, 40)))


def rand_json(rng, depth=0):
    r = rng.random()
    if depth > 3 or r < 0.3:
        return rng.choice([None, True, False, 0, -1, 2**63, 2**64, 1.5, "x", "", [], {}, rng.randrange(-5, 5)])
    if r < 0.6:
        return [rand_json(rng, depth + 1) for _ in range(rng.randrange(0, 4))]
    return {rng.choice(["schema", "key", "compare", "success", "failure", "put", "delete", "range", "revision",
                        "limit", "target", "op", "operand", "value", "prefix", "x"]): rand_json(rng, depth + 1)
            for _ in range(rng.randrange(0, 5))}


class FuzzTest(unittest.TestCase):
    def test_keys_never_crash_or_escape(self):
        rng = random.Random(SEED)
        s = ControlStore()
        for _ in range(3000):
            k = rand_key(rng)
            try:
                s.put(k, 1)
                self.assertIsNotNone(s.get(k))
            except StateError as e:
                self.assertIn(e.code, ("CSTATE_INVALID_ARGUMENT", "CSTATE_LIMIT"))
        self.assertEqual(s.check_invariants(), [])

    def test_revisions(self):
        rng = random.Random(SEED + 1)
        s = ControlStore()
        for i in range(20):
            s.put("k", i)
        s.compact(5)
        for _ in range(2000):
            rev = rng.choice([-1, 0, 1, 5, 6, 20, 21, 2**63, 2**63 - 1, 2**64, True, 1.0, "3", None, rng.randrange(-100, 100)])
            try:
                s.get("k", revision=rev)
                self.assertTrue(isinstance(rev, int) and not isinstance(rev, bool) and (rev == 0 or 5 <= rev <= 20))
            except StateError as e:
                self.assertIn(e.code, ("CSTATE_INVALID_ARGUMENT", "CSTATE_COMPACTED", "CSTATE_FUTURE_REVISION"))

    def test_frames_and_unknown_fields(self):
        rng = random.Random(SEED + 2)
        for _ in range(4000):
            msg = rand_json(rng)
            kind = rng.choice(["txn", "range", "watch", "compact", "lease_grant", "hello"])
            if isinstance(msg, dict) and rng.random() < 0.5:
                msg["schema"] = f"cstate.{kind}/1.{rng.randrange(0, 3)}"
            try:
                m = check_message(kind, msg)
                if kind == "txn":
                    [parse_compare(c) for c in m.get("compare", [])]
                    [parse_op(o) for o in m.get("success", []) + m.get("failure", [])]
            except StateError:
                pass  # typed rejection is the only acceptable failure
        for _ in range(2000):
            raw = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 60)))
            try:
                loads(raw, 10_000)
            except StateError:
                pass

    def test_service_txn_fuzz_never_leaks_or_crashes(self):
        rng = random.Random(SEED + 3)
        svc = make_service(Limits(rate_per_identity_rps=1e9, burst_per_identity=10**9))
        a, b = principal(NS_A, "writer"), principal(NS_B, "writer")
        svc.txn(ctx(b), txn_body(success=[{"put": {"key": "secret", "value": "B"}}]))
        for _ in range(1500):
            body = rand_json(rng)
            if isinstance(body, dict):
                body["schema"] = "cstate.txn/1.1"
            try:
                out = svc.txn(ctx(a), body)
                self.assertNotIn('"B"', json.dumps(out))
            except StateError:
                pass
        # tenant B's key untouched
        r = svc.range(ctx(b), {"schema": "cstate.range/1.1", "key": "secret"})
        self.assertEqual(r["kvs"][0]["value"], "B")

    def test_authz_privilege_boundaries(self):
        rng = random.Random(SEED + 4)
        az = Authorizer(DEFAULT_POLICY)
        roles = ["reader", "writer", "operator", "security-admin", "replicator", "", "admin", "root", "*"]
        nss = [NS_A, NS_B, CLUSTER, Namespace("x", "y", "z", "w")]
        admin_roles = {"operator", "security-admin", "replicator"}
        for _ in range(5000):
            p = Principal("s", rng.choice(nss), frozenset(rng.sample(roles, rng.randrange(0, 3))))
            act = rng.choice(sorted(ACTIONS) + ["fly", "*", ""])
            target = rng.choice(nss + [None])
            d = az.decide(p, act, target)
            if d.allowed:
                self.assertIn(act, ACTIONS)
                if (target or p.namespace) != p.namespace:
                    self.assertTrue(p.roles & admin_roles, (p, act, target))
                if act.startswith("admin.") or act in ("compact", "replicate"):
                    self.assertTrue(p.roles & admin_roles)
                if not p.roles & {"writer", "operator", "security-admin", "replicator"}:
                    self.assertIn(act, ("read", "watch"))

    def test_resource_exhaustion_under_limits(self):
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        try:
            resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, hard))
        except (ValueError, OSError):
            pass
        try:
            s = ControlStore(Limits(max_history_events=5000, max_value_bytes=1024, max_page_size=100))
            errors = 0
            for i in range(6000):
                try:
                    s.put(f"k{i % 50}", "x" * 1000)
                except StateError as e:
                    self.assertEqual(e.code, "CSTATE_OVERLOADED")
                    errors += 1
            self.assertEqual(s.history_size, 5000)
            self.assertEqual(errors, 1000)
            with self.assertRaises(StateError):
                s.range(Range("", prefix=True, limit=101))
            with self.assertRaises(StateError):
                s.put("big", "x" * 2000)
            with self.assertRaises(StateError):
                loads(b"[" * 100000, 10**6)  # deep nesting rejected, no crash
        finally:
            resource.setrlimit(resource.RLIMIT_AS, (soft, hard))


if __name__ == "__main__":
    unittest.main()
