"""Fuzz/property and adversarial tests derived from docs/THREAT_MODEL.md (C050, C085, C087).

Iterations default to 2,000 per target; CI's deep job sets INV52_FUZZ_ITERATIONS=20000.
"""
import json
import os
import random
import string
import unittest

from _support import authority, env
from inv52_messaging_abstraction import adapters as ad
from inv52_messaging_abstraction import config as cfgm
from inv52_messaging_abstraction import runtime as rt
from inv52_messaging_abstraction import schemas as sc
from inv52_messaging_abstraction import security as sec

N = int(os.environ.get("INV52_FUZZ_ITERATIONS", "2000"))


def rand_value(rng, depth=0):
    kinds = ["int", "float", "str", "none", "bool", "list", "dict", "nan", "big"]
    k = rng.choice(kinds if depth < 4 else kinds[:5])
    if k == "int":
        return rng.randint(-10**6, 10**6)
    if k == "float":
        return rng.uniform(-1e9, 1e9)
    if k == "nan":
        return rng.choice([float("nan"), float("inf"), -float("inf")])
    if k == "big":
        return 10 ** rng.randint(20, 400)
    if k == "str":
        return "".join(rng.choice(string.printable + "\u0000퟿ ::") for _ in range(rng.randint(0, 20)))
    if k == "none":
        return None
    if k == "bool":
        return rng.random() < .5
    if k == "list":
        return [rand_value(rng, depth + 1) for _ in range(rng.randint(0, 4))]
    return {rng.choice(["id", "source", "type", "time", "data", "traceparent", "x", ""]): rand_value(rng, depth + 1)
            for _ in range(rng.randint(0, 6))}


def mutate_bytes(rng, b):
    b = bytearray(b)
    for _ in range(rng.randint(1, 8)):
        op = rng.random()
        if op < .4 and b:
            b[rng.randrange(len(b))] = rng.randrange(256)
        elif op < .7:
            b.insert(rng.randrange(len(b) + 1), rng.randrange(256))
        elif b:
            del b[rng.randrange(len(b))]
    return bytes(b)


SEED_REQ = json.dumps({"contract": "PK_MSG_PUBLISH/1", "app": "a", "topic": "t",
                       "message": {"id": "1", "source": "a", "type": "e", "time": 0, "data": {"k": [1, 2]}}}).encode()


class FuzzTest(unittest.TestCase):
    def test_validate_envelope_only_raises_structured_errors(self):
        rng = random.Random(1)
        for _ in range(N):
            v = rand_value(rng)
            try:
                rt.validate_envelope(v)
            except rt.IncompleteEnvelope:
                pass

    def test_parse_publish_request_bytes(self):
        rng = random.Random(2)
        ok = 0
        for _ in range(N):
            raw = mutate_bytes(rng, SEED_REQ)
            try:
                sc.parse_publish_request(raw)
                ok += 1
            except rt.MessagingError:
                pass
        self.assertGreater(ok, 0)  # the mutator must also produce valid inputs, or it tests nothing

    def test_from_cloudevent(self):
        rng = random.Random(3)
        for _ in range(N):
            v = rand_value(rng)
            if isinstance(v, dict) and rng.random() < .5:
                v["specversion"] = "1.0"
            try:
                ad.from_cloudevent(v)
            except rt.IncompleteEnvelope:
                pass

    def test_config_validate_never_raises(self):
        rng = random.Random(4)
        base = cfgm.layered()
        for _ in range(N):
            c = json.loads(json.dumps(base))
            key = rng.choice(list(c) + ["zzz"])
            c[key] = rand_value(rng)
            self.assertIsInstance(cfgm.validate(c), list)

    def test_publish_random_messages_keeps_invariants(self):
        rng = random.Random(5)
        b = rt.PubSub(max_dead_letters=50, max_decisions=50)
        b.allow("t", "a")
        b.subscribe("t", lambda m: m["data"] == 1, [])
        for _ in range(N):
            msg = rand_value(rng)
            if isinstance(msg, dict) and rng.random() < .6:
                msg.update({"id": "x", "source": "a", "type": "e", "time": 0})
            try:
                b.publish("a", "t", msg)
            except rt.MessagingError:
                pass
        m = b.metrics()
        self.assertLessEqual(m["dead_letter_backlog"], 50)
        self.assertLessEqual(len(b.decisions(1000)), 50)

    def test_token_verify_fuzz(self):
        auth, _ = authority()
        rng = random.Random(6)
        seed = auth.issue("a", "t")
        for _ in range(N // 4):
            tok = mutate_bytes(rng, seed.encode()).decode("latin-1")
            try:
                auth.verify(tok)
            except (sec.Unauthenticated, sec.TrustUnavailable):
                pass


class AdversarialTest(unittest.TestCase):
    def test_json_nesting_bomb_rejected_without_recursion_error(self):
        raw = b'{"contract":"PK_MSG_PUBLISH/1","app":"a","topic":"t","message":' + b"[" * 100_000 + b"]" * 100_000 + b"}"
        with self.assertRaises(rt.IncompleteEnvelope):
            sc.parse_publish_request(raw)

    def test_oversize_request_rejected_before_parse(self):
        with self.assertRaises(rt.IncompleteEnvelope) as ctx:
            sc.parse_publish_request(b" " * (2 * 1024 * 1024))
        self.assertIn("size", str(ctx.exception))

    def test_unknown_fields_and_wrong_contract_rejected(self):
        for body in ({"contract": "PK_MSG_PUBLISH/1", "app": "a", "topic": "t", "message": env(), "sudo": True},
                     {"contract": "PK_MSG_PUBLISH/2", "app": "a", "topic": "t", "message": env()},
                     {"contract": "PK_MSG_CONFIG/1", "app": "a", "topic": "t", "message": env()}):
            with self.assertRaises(rt.MessagingError):
                sc.parse_publish_request(json.dumps(body))

    def test_predicate_cannot_escalate_by_mutating_policy_through_message(self):
        b = rt.PubSub()
        b.allow("t", "a")

        def evil(m):
            m["source"] = "admin"
            return True
        sink = []
        b.subscribe("t", evil, [])
        b.subscribe("t", lambda m: True, sink)
        b.publish("a", "t", env())
        self.assertEqual(sink[0]["source"], "a")
        self.assertEqual(b.publishers["t"], frozenset({"a"}))

    def test_replay_of_captured_token_and_cross_tenant_token(self):
        auth, _ = authority()
        tb = sec.TenantBus(rt.PubSub(), auth)
        tb.grant("acme", "shop", "publish:o")
        t = auth.issue("shop", "acme")
        tb.publish(t, "o", env("shop"))
        with self.assertRaises(sec.Unauthenticated):
            tb.publish(t, "o", env("shop"))
        with self.assertRaises(rt.TopicDenied):
            tb.publish(auth.issue("shop", "other"), "o", env("shop"))

    def test_error_details_do_not_echo_payload(self):
        b = rt.PubSub()
        b.allow("t", "a")

        def leaky(m):
            raise RuntimeError("secret=" + str(m["data"]))
        b.subscribe("t", leaky, [])
        b.publish("a", "t", env(data={"card": "4111111111111111"}))
        errs = json.dumps(b.dead_letter[-1]["errors"]) + json.dumps(b.decisions()[-1])
        self.assertNotIn("4111", errs)

    def test_log_injection_in_topic_names_is_contained(self):
        b = rt.PubSub()
        with self.assertRaises(rt.InvalidArgument):
            b.allow("x" * 600, "a")
        b.allow("t\n{\"forged\":1}", "a")  # stored as data, never interpreted
        self.assertIn("t\n{\"forged\":1}", b.publishers)


if __name__ == "__main__":
    unittest.main()
