import json
import pathlib
import random
import unittest

import _util  # noqa: F401
from gap05_state_replication_consistency_model.production import errors as E
from gap05_state_replication_consistency_model.production.limits import Limits
from gap05_state_replication_consistency_model.production.schemas import (
    SUPPORTED, json_schemas, make_merge_result, make_write_doc, negotiate, strict_loads, validate_conflict_set,
    validate_write_doc)
from gap05_state_replication_consistency_model.production.transport import (
    decode_frame, decode_write_bin, encode_frame, encode_write_bin)

CORPUS = pathlib.Path(__file__).resolve().parents[2] / "schemas" / "corpus"


def base():
    return make_write_doc(tenant="t", environment="prod", key="k", value="v", site="a",
                          vector={"a": 2, "b": 1}, epoch=3)


class SchemaTests(unittest.TestCase):
    def test_machine_readable_schemas_shipped(self):
        """items: MC07-001 MC07-008
        JSON-Schema documents for all three wire schemas; tenant/env/epoch/op_id explicit fields."""
        s = json_schemas()
        self.assertEqual(set(s), {"PK_REPLICATED_WRITE/1", "PK_MERGE_RESULT/1", "PK_CONFLICT_SET/1"})
        req = set(s["PK_REPLICATED_WRITE/1"]["required"])
        self.assertTrue({"tenant", "environment", "epoch", "op_id"} <= req)
        shipped = pathlib.Path(__file__).resolve().parents[2] / "schemas"
        for name in s:
            f = shipped / (name.replace("/", "_v") + ".schema.json")
            self.assertTrue(f.exists(), f)
            self.assertEqual(json.loads(f.read_text()), s[name])

    def test_canonical_and_opid(self):
        """items: MC07-002 MC09-001 MC09-002
        op_id is content-addressed over the canonical form: stable, and any semantic change alters it."""
        d = base()
        self.assertEqual(validate_write_doc(d)["op_id"], d["op_id"])
        d2 = dict(d, value="w")
        with self.assertRaises(E.SchemaError) as cm:
            validate_write_doc(d2)
        self.assertEqual(cm.exception.code, "CORR_SCHEMA_OPID")

    def test_unknown_and_missing_fields(self):
        """items: MC07-005 MC07-006 MC08-004
        Strict ingress: unknown fields and missing mandatory fields are rejected."""
        d = dict(base(), surprise=1)
        with self.assertRaises(E.SchemaError) as cm:
            validate_write_doc(d)
        self.assertEqual(cm.exception.code, "CORR_SCHEMA_UNKNOWN")
        d = base()
        d.pop("epoch")
        with self.assertRaises(E.SchemaError):
            validate_write_doc(d)

    def test_numeric_and_vector_edges(self):
        """items: MC07-003 MC03-008 MC30-007 MC30-011
        Counter range 1..2^63-1, bools are not ints, vectors canonical-sorted, no duplicates."""
        for vec in ([["a", 0]], [["a", True]], [["a", 2 ** 63]], [["a", 1], ["a", 2]], [["b", 1], ["a", 1]],
                    [["a", 1.0]], [["a"]], []):
            d = dict(base(), vector=vec)
            with self.assertRaises(E.SchemaError, msg=vec):
                validate_write_doc(d)
        d = make_write_doc(tenant="t", environment="e", key="k", value="", site="a", vector={"a": 2 ** 63 - 1},
                           epoch=1)
        validate_write_doc(d)

    def test_merge_and_conflict_union(self):
        """items: MC07-004
        Merge outcomes are a closed union; conflict sets are internally consistent."""
        with self.assertRaises(E.SchemaError):
            make_merge_result(tenant="t", environment="e", key="k", op_id="x", outcome="winner")
        cs = {"schema": "PK_CONFLICT_SET/1", "key": "k", "siblings": [], "quarantined": [], "open": True,
              "total_unresolved": 0}
        with self.assertRaises(E.SchemaError):
            validate_conflict_set(cs)

    def test_published_corpus(self):
        """items: MC07-009 MC07-010 MC07-012 MC33-002 MC33-009
        Normative valid/invalid corpus: validator agrees with every fixture's expected verdict."""
        fixtures = sorted(CORPUS.glob("*.json"))
        self.assertGreaterEqual(len(fixtures), 10)
        for f in fixtures:
            case = json.loads(f.read_text())
            try:
                validate_write_doc(strict_loads(case["document"]))
                verdict = "valid"
            except E.Gap05Error as exc:
                verdict = "invalid:" + exc.code
            self.assertTrue(verdict.startswith(case["expect"]), f"{f.name}: {verdict} vs {case['expect']}")

    def test_negotiation(self):
        """items: MC08-001 MC08-002 MC08-003 MC08-009 MC08-011
        Highest common version wins; no common version or missing family is a stable-coded refusal."""
        self.assertEqual(negotiate(SUPPORTED, {k: [1, 2] for k in SUPPORTED})["PK_REPLICATED_WRITE"], 1)
        with self.assertRaises(E.IncompatibleVersion) as cm:
            negotiate(SUPPORTED, {k: [2] for k in SUPPORTED})
        self.assertEqual(cm.exception.code, "CORR_NEGOTIATION_NONE")
        with self.assertRaises(E.IncompatibleVersion) as cm:
            negotiate(SUPPORTED, {"PK_REPLICATED_WRITE": [1]})
        self.assertEqual(cm.exception.code, "CORR_NEGOTIATION_MISSING")
        d = dict(base(), schema="PK_REPLICATED_WRITE/2")
        with self.assertRaises(E.IncompatibleVersion):
            validate_write_doc(d)

    def test_limits_boundaries(self):
        """items: MC30-001 MC30-002 MC30-006 MC30-011
        N-1/N/N+1 on key and vector limits; contradictory configurations refused at startup."""
        lim = Limits(max_key_bytes=4, max_vector_entries=2, max_siblings=2, max_unresolved_per_key=2)
        for n, ok in ((3, True), (4, True), (5, False)):
            d = make_write_doc(tenant="t", environment="e", key="k" * n, value="", site="a", vector={"a": 1}, epoch=1)
            if ok:
                validate_write_doc(d, lim)
            else:
                with self.assertRaises(E.SchemaError):
                    validate_write_doc(d, lim)
        d = make_write_doc(tenant="t", environment="e", key="k", value="", site="a",
                           vector={"a": 1, "b": 1, "c": 1}, epoch=1)
        with self.assertRaises(E.SchemaError):
            validate_write_doc(d, lim)
        with self.assertRaises(E.ConfigError):
            Limits(max_siblings=10, max_unresolved_per_key=5)
        with self.assertRaises(E.ConfigError):
            Limits(max_key_bytes=0)
        with self.assertRaises(E.ConfigError):
            Limits(max_value_bytes=10, max_frame_bytes=5)


class FuzzTests(unittest.TestCase):
    """Deterministic mutation fuzzing (stdlib; seeds recorded).  Budget: 4 x 3,000 cases."""

    SEEDS = (1, 7, 42, 2026)

    def _mutate(self, rng, data: bytes) -> bytes:
        b = bytearray(data)
        for _ in range(rng.randint(1, 6)):
            op = rng.randrange(6)
            if op == 0 and b:
                b[rng.randrange(len(b))] = rng.randrange(256)
            elif op == 1 and b:
                del b[rng.randrange(len(b)):rng.randrange(len(b)) + 1]
            elif op == 2:
                b[rng.randrange(len(b) + 1):rng.randrange(len(b) + 1)] = bytes(rng.randrange(256) for _ in range(rng.randint(1, 8)))
            elif op == 3:
                b += b'{"a":' * rng.randint(1, 50)
            elif op == 4 and b:
                i = rng.randrange(len(b))
                b[i:i] = b[i:i + rng.randint(1, 20)]
            else:
                b = b[: rng.randrange(len(b) + 1)]
        return bytes(b)

    def test_json_decoder_fuzz(self):
        """items: MC33-001 MC33-003 MC33-007 MC33-008 MC07-011 MC38-007
        Mutated wire documents only ever produce a valid doc or a stable Gap05Error: no crash, no hang."""
        seed_doc = json.dumps(base()).encode()
        outcomes = {"valid": 0, "rejected": 0}
        for seed in self.SEEDS:
            rng = random.Random(seed)
            for _ in range(3000):
                data = self._mutate(rng, seed_doc)
                try:
                    validate_write_doc(strict_loads(data))
                    outcomes["valid"] += 1
                except E.Gap05Error:
                    outcomes["rejected"] += 1
        self.assertEqual(sum(outcomes.values()), 12000)

    def test_binary_and_frame_fuzz(self):
        """items: MC33-001 MC43-005 MC18-011 MC38-007
        Mutated binary writes/frames never raise anything but Gap05Error and never over-read."""
        seed = encode_frame(4, encode_write_bin(base()))
        for s in self.SEEDS:
            rng = random.Random(s)
            for _ in range(3000):
                data = self._mutate(rng, seed)
                try:
                    kind, payload, _end = decode_frame(data)
                    decode_write_bin(payload)
                except E.Gap05Error:
                    pass

    def test_duplicate_keys_unicode_extremes(self):
        """items: MC33-003 MC07-011 MC06-005
        Duplicate JSON keys, lone surrogates, NaN/Infinity, deep nesting and control chars are rejected."""
        cases = [
            b'{"schema":"PK_REPLICATED_WRITE/1","schema":"x"}',
            json.dumps(dict(base(), key="\ud800")).encode("utf-8", "surrogatepass"),
            b'{"x": NaN}', b'[' * 5000 + b']' * 5000,
            json.dumps(dict(base(), tenant="t\x00")).encode(),
            b"\xff\xfe",
        ]
        for c in cases:
            with self.assertRaises(E.Gap05Error, msg=c[:40]):
                validate_write_doc(strict_loads(c))

    def test_downgrade_fuzz(self):
        """items: MC33-004 MC08-011
        Random schema identifiers are rejected unless exactly supported."""
        rng = random.Random(5)
        for _ in range(500):
            ident = rng.choice(["PK_REPLICATED_WRITE/", "PK_REPLICATED_WRITE/0", "PK/1", "PK_REPLICATED_WRITE/1/1",
                                "pk_replicated_write/1", "PK_REPLICATED_WRITE/01", ""]) + str(rng.randint(0, 3))
            if ident == "PK_REPLICATED_WRITE/1":
                continue  # the one supported identifier
            d = dict(base(), schema=ident)
            with self.assertRaises(E.Gap05Error):
                validate_write_doc(d)


class BinaryCodecTests(unittest.TestCase):
    def test_roundtrip_equivalence(self):
        """items: MC43-002 MC43-003 MC43-006 MC43-012
        Binary encoding is lossless: decode(encode(doc)) == doc and re-validates op_id."""
        from gap05_state_replication_consistency_model.production.testkit import Cluster, T, E as ENV
        c = Cluster(("a",))
        try:
            r = c.nodes["a"].write(T, ENV, "k", "é" * 1000, principal="operator", value_type="crdt.g_set/1")
            doc = c.nodes["a"].docs[r["op_id"]]
            self.assertEqual(decode_write_bin(encode_write_bin(doc)), doc)
            d2 = dict(doc, deleted=True)
            d2.pop("provenance")
            from gap05_state_replication_consistency_model.production.schemas import op_id_for
            d2["op_id"] = op_id_for(d2)
            self.assertEqual(decode_write_bin(encode_write_bin(d2)), d2)
        finally:
            c.close()

    def test_lazy_value_view(self):
        """items: MC43-004 MC43-008
        lazy_value returns a read-only memoryview slice of the input (no copy until materialised)."""
        data = encode_write_bin(dict(base(), value="x" * 4096))
        _doc, view = decode_write_bin(data, lazy_value=True)
        self.assertIsInstance(view, memoryview)
        self.assertTrue(view.readonly)
        self.assertEqual(bytes(view), b"x" * 4096)

    def test_trailing_and_truncation(self):
        """items: MC43-005
        Trailing bytes and truncation are rejected."""
        data = encode_write_bin(base())
        for bad in (data + b"\0", data[:-1], b"XXXX" + data[4:]):
            with self.assertRaises(E.SchemaError):
                decode_write_bin(bad)


if __name__ == "__main__":
    unittest.main()
