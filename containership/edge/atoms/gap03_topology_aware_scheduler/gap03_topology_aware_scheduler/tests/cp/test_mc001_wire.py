import json
import unittest

from gap03_topology_aware_scheduler import Topology
from gap03_topology_aware_scheduler.controlplane import bindings, canonical, gen_bindings, wire
from gap03_topology_aware_scheduler.controlplane.errors import SchedulerError
from gap03_topology_aware_scheduler.tests.cp._util import covers

T = {"schema": "PK_TOPOLOGY/1.1", "environment": "prod", "generation": 3,
     "nodes": [{"node": "a", "region": "eu", "site": "dub", "rack": "r1"}], "provenance": ""}


def topo():
    t = Topology()
    t.place("a", "eu", "dub", "r1")
    t.place("b", "eu", "dub", "r2")
    return t


class Wire(unittest.TestCase):
    @covers("MC-001", 6, 7, 25)
    def test_mc001_schemas_declare_ids_types_units_bounds(self):
        for name, s in wire.SCHEMAS.items():
            self.assertTrue(s["media_type"].startswith("application/vnd.pk."))
            for f, spec in s["fields"].items():
                self.assertIn(spec["type"], ("string", "integer", "boolean", "array", "object"))
                if spec["type"] == "integer":
                    self.assertIn("minimum", spec)
                    self.assertIn("maximum", spec)
                    self.assertIn("unit", spec)
                if spec["type"] == "string":
                    self.assertTrue("max_len" in spec or "enum" in spec, f"{name}.{f} unbounded")

    @covers("MC-001", 9, 18, 25, 27)
    def test_mc001_parser_rejects_malformed_and_adversarial(self):
        good = canonical.dumps(T)
        self.assertEqual(wire.parse("PK_TOPOLOGY/1.1", good)["generation"], 3)
        bad = [b'{"schema":"PK_TOPOLOGY/1.1","schema":"x"}', b"[" * 40 + b"]" * 40, b'{"a":NaN}', b'{"a":Infinity}',
               b'{"a":' + b"9" * 30 + b"}", b"\xff\xfe", b"", b"{", b'"x"', b"x" * (canonical.MAX_BYTES + 1)]
        for b in bad:
            with self.assertRaises(SchedulerError, msg=b[:30]):
                wire.parse("PK_TOPOLOGY/1.1", b)
        confused = dict(T, schema="PK_TOPOLOGY/1.0")
        with self.assertRaises(SchedulerError):
            wire.validate("PK_TOPOLOGY/1.1", confused)  # schema confusion
        dup = dict(T, nodes=T["nodes"] * 2)
        with self.assertRaises(SchedulerError):
            wire.validate("PK_TOPOLOGY/1.1", dup)
        with self.assertRaises(SchedulerError):
            wire.validate("PK_TOPOLOGY/1.1", dict(T, extra=1))
        with self.assertRaises(SchedulerError):
            wire.validate("PK_TOPOLOGY/1.1", dict(T, generation=-1))

    @covers("MC-001", 10, 25)
    def test_mc001_generated_bindings_in_sync_and_pinned(self):
        text = open(gen_bindings.__file__.replace("gen_bindings.py", "bindings.py"), encoding="utf-8").read()
        self.assertEqual(text, gen_bindings.render(), "bindings.py drifted from schema - rerun gen_bindings")
        self.assertIn(gen_bindings.GENERATOR_VERSION, text)
        obj = bindings.PkTopologyV11.from_wire(dict(T))
        self.assertEqual(obj.to_wire(), T)

    @covers("MC-001", 11, 26)
    def test_mc001_registry_digests_and_negotiation(self):
        reg = wire.registry()
        self.assertEqual(reg["PK_TOPOLOGY/1.1"]["sha256"], wire.fingerprint("PK_TOPOLOGY/1.1"))
        self.assertEqual(bindings.SCHEMA_DIGESTS, {k: v["sha256"] for k, v in reg.items()})
        self.assertEqual(wire.negotiate("pk.topology", ["1.0", "1.1", "2.0"]), "1.1")
        self.assertEqual(wire.negotiate("pk.topology", ["1.0"]), "1.0")
        with self.assertRaises(SchedulerError) as cm:
            wire.negotiate("pk.topology", ["2.0"])
        self.assertEqual(cm.exception.code, "UNSUPPORTED_VERSION")

    @covers("MC-001", 12, 26)
    def test_mc001_fixture_classes_for_all_three_interfaces(self):
        snap = topo().snapshot()
        cases = {"PK_TOPOLOGY/1.1": wire.topology_to_wire(snap, "prod"),
                 "PK_LOCALITY_COST/1.0": wire.cost_to_wire(snap, "a", "b")}
        from gap03_topology_aware_scheduler import FairShare
        fs = FairShare(reserved={"t": 1}, capacity=2)
        cases["PK_FAIR_SHARE/1.0"] = wire.verdict_to_wire(fs.verdict("t"), 0, fs.starved())
        for name, obj in cases.items():
            self.assertEqual(wire.parse(name, canonical.dumps(obj)), obj)  # positive / round trip
        self.assertEqual(cases["PK_LOCALITY_COST/1.0"]["level"], "same_site")
        # boundary
        wire.validate("PK_LOCALITY_COST/1.0", dict(cases["PK_LOCALITY_COST/1.0"], cost=101, level="cross_region"))
        with self.assertRaises(SchedulerError):
            wire.validate("PK_LOCALITY_COST/1.0", dict(cases["PK_LOCALITY_COST/1.0"], cost=102))
        # backward compat: a 1.0 payload is accepted and migrates forward
        old = {k: v for k, v in cases["PK_TOPOLOGY/1.1"].items() if k != "provenance"}
        old["schema"] = "PK_TOPOLOGY/1.0"
        self.assertEqual(wire.migrate(wire.validate("PK_TOPOLOGY/1.0", old), "PK_TOPOLOGY/1.1")["provenance"], "")
        # forward compat: an unknown future field is rejected (strict v1 policy)
        with self.assertRaises(SchedulerError):
            wire.validate("PK_FAIR_SHARE/1.0", dict(cases["PK_FAIR_SHARE/1.0"], future_field=1))
        with self.assertRaises(SchedulerError):
            wire.validate("PK_FAIR_SHARE/1.0", dict(cases["PK_FAIR_SHARE/1.0"], reason="new_enum_value"))

    @covers("MC-001", 13, 25)
    def test_mc001_canonical_serialization_is_deterministic(self):
        a = {"b": 1, "a": [3, {"z": 1, "y": "é"}]}
        b = json.loads(json.dumps(a))
        self.assertEqual(canonical.dumps(a), canonical.dumps(b))
        self.assertEqual(canonical.dumps(a), b'{"a":[3,{"y":"\xc3\xa9","z":1}],"b":1}')
        self.assertTrue(canonical.is_canonical(canonical.dumps(a)))
        self.assertFalse(canonical.is_canonical(b'{"b":1, "a":2}'))
        self.assertEqual(canonical.digest(a), canonical.digest(b))

    @covers("MC-001", 14, 25)
    def test_mc001_migration_round_trip_and_lossy_downgrade_refused(self):
        v10 = {k: v for k, v in T.items() if k != "provenance"}
        v10["schema"] = "PK_TOPOLOGY/1.0"
        up = wire.migrate(v10, "PK_TOPOLOGY/1.1")
        self.assertEqual(wire.migrate(up, "PK_TOPOLOGY/1.0"), v10)
        with self.assertRaises(SchedulerError):
            wire.migrate(dict(up, provenance="sig:abc"), "PK_TOPOLOGY/1.0")

    @covers("MC-001", 8, 15, 29)
    def test_mc001_compatibility_gate_and_api_reference(self):
        self.assertEqual(wire.compatible("PK_TOPOLOGY/1.0", "PK_TOPOLOGY/1.1"), [])
        broken = json.loads(json.dumps(wire.SCHEMAS["PK_TOPOLOGY/1.1"]))
        broken["fields"]["generation"]["type"] = "string"
        broken["fields"]["new_required"] = {"type": "string", "required": True}
        wire.SCHEMAS["PK_TOPOLOGY/9.9"] = broken
        try:
            probs = wire.compatible("PK_TOPOLOGY/1.0", "PK_TOPOLOGY/9.9")
        finally:
            del wire.SCHEMAS["PK_TOPOLOGY/9.9"]
        self.assertTrue(any("type change" in p for p in probs))
        self.assertTrue(any("new required" in p for p in probs))
        ref = wire.api_reference()
        for k in ("idl", "registry", "supported", "deprecations", "compatibility_matrix"):
            self.assertIn(k, ref)
        json.dumps(ref)  # machine readable

    @covers("MC-001", 28)
    def test_mc001_parse_benchmark_bound(self):
        import time
        nodes = [{"node": f"n{i}", "region": f"r{i % 4}", "site": f"s{i % 16}", "rack": f"k{i % 64}"} for i in range(5000)]
        data = canonical.dumps({"schema": "PK_TOPOLOGY/1.1", "environment": "prod", "generation": 1, "nodes": nodes, "provenance": ""})
        t = time.perf_counter()
        wire.parse("PK_TOPOLOGY/1.1", data)
        self.assertLess(time.perf_counter() - t, 2.0, "5k-node topology parse exceeded local bound")
