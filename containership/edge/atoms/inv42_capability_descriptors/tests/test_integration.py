"""MC-005 integration tests across adjacent-layer adapters, processes and schemas."""
from __future__ import annotations

import json
import multiprocessing as mp
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

import adapters  # noqa: E402
import delegation  # noqa: E402
import descriptors as d  # noqa: E402


class Cap:
    capability_type = "stream"


def _child(wire, q):
    import descriptors as cd
    t = cd.DescriptorTable("child")
    try:
        t.from_wire(wire)
        q.put("accepted")
    except cd.DescriptorError as e:
        q.put(e.code)


def _check(schema, obj, tc):
    tc.assertTrue(set(schema["required"]) <= set(obj), obj)
    if schema.get("additionalProperties") is False:
        tc.assertTrue(set(obj) <= set(schema["properties"]), set(obj) - set(schema["properties"]))
    for k, spec in schema["properties"].items():
        if k in obj and "const" in spec:
            tc.assertEqual(obj[k], spec["const"])
        if k in obj and "enum" in spec:
            tc.assertIn(obj[k], spec["enum"])


class AdjacentLayerTest(unittest.TestCase):
    def test_inv41_to_inv13_round_trip(self):
        t = d.DescriptorTable("svc")
        wire = adapters.InProcessCapabilitySource(t).export(Cap())
        abi = adapters.SystemInterfaceBoundary(t)
        payload = json.dumps(wire).encode()
        self.assertEqual(abi.call("resolve", payload, expect="stream")["ok"], True)
        self.assertEqual(abi.call("resolve", payload, expect="socket")["code"], "type_mismatch")
        self.assertTrue(abi.call("close", payload)["closed"])
        r = abi.call("resolve", payload)
        self.assertEqual((r["code"], r["class"]), ("descriptor_closed", "terminal"))
        for junk in (b"\xff", b"x" * 5000, "str", b"[]", b"{}"):
            r = abi.call("resolve", junk)
            self.assertFalse(r["ok"])
            self.assertNotIn(wire["auth"], json.dumps(r))
        with self.assertRaises(TypeError):
            adapters.InProcessCapabilitySource(t).export(object())

    def test_process_transfer_confers_no_authority(self):
        t = d.DescriptorTable("parent")
        wire = t.open("stream", 1).to_wire()
        ctx = mp.get_context("spawn")
        q = ctx.Queue()
        p = ctx.Process(target=_child, args=(wire, q))
        p.start()
        p.join(30)
        self.assertEqual(q.get(timeout=5), "foreign_descriptor")

    def test_degraded_control_plane(self):
        def kms_down():
            raise ConnectionError
        with self.assertRaises(d.KeyUnavailable):
            d.DescriptorTable("w", key_provider=kms_down)
        d.emergency_disable()
        try:
            t = d.DescriptorTable("w")
            r = adapters.SystemInterfaceBoundary(t).call("resolve", b"{}")
            self.assertEqual(r["code"], "invalid_descriptor")
        finally:
            d.emergency_enable()

    def test_outputs_conform_to_schemas(self):
        sch = {p.stem: json.loads(p.read_text()) for p in (PKG_DIR / "schemas").glob("*.json")}
        events = []
        t = d.DescriptorTable("w", observer=events.append)
        fd = t.open("stream", 1)
        _check(sch["PK_DESCRIPTOR_v2.schema"], fd.to_wire(), self)
        _check(sch["PK_DESCRIPTOR_TABLE_STATUS_v1.schema"], t.status(), self)
        u = d.DescriptorTable("u")
        new, rec = delegation.Delegator(lambda *a: True).delegate(t, u, fd, txn_id="txn-int-01", mode="share")
        _check(sch["PK_DESCRIPTOR_DELEGATION_v1.schema"], rec, self)
        _check(sch["PK_DESCRIPTOR_CLOSE_v2.schema"], t.close(fd), self)
        for e in events:
            _check(sch["PK_DESCRIPTOR_EVENT_v1.schema"], e, self)


if __name__ == "__main__":
    unittest.main()
