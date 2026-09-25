"""M23 adjacent-layer integration -- against CONTRACT STUBS of INV-60/55/64/61.

The real adjacent repositories are not in this archive.  These tests pin the
integration seams INV-65 exposes to each; they must be re-run against the real
layers before M23 can close (see traceability/INV65_RTM.json).
"""
import json, unittest
from inv65_capability_providers.tests.helpers import World
from inv65_capability_providers.errors.mapping import ProviderFault, from_envelope, to_envelope


class Inv60FabricStub:
    """INV-60 links components to providers: it presents workload tokens and decisions."""
    def __init__(self, w):
        self.w = w
    def link_component(self, component, link_name, cfg):
        return self.w.link(link_name, cfg, component=component)


class Inv64AppModelStub:
    """INV-64 declares links in an application manifest."""
    manifest = {"app": "shop", "links": [{"component": "orders", "name": "primary", "config": {"bucket": "o", "user": "u"}},
                                         {"component": "reports", "name": "default", "config": {"bucket": "r", "user": "ro"}}]}


class Inv61RpcStub:
    """INV-61 carries calls: JSON over the wire both ways, errors as PK_PROVIDER_ERROR/1."""
    def __init__(self, w):
        self.w = w
    def invoke(self, wire: bytes) -> bytes:
        m = json.loads(wire)
        try:
            out = self.w.call(m["link"], m["op"], m.get("payload"), component=m["component"])
            return json.dumps({"ok": out}).encode()
        except ProviderFault as e:
            return json.dumps({"err": to_envelope(e)}).encode()


class AdjacentLayers(unittest.TestCase):
    def setUp(self):
        self.w = World(); self.w.svc.start()

    def test_inv64_manifest_applied_via_inv60(self):
        fab = Inv60FabricStub(self.w)
        for l in Inv64AppModelStub.manifest["links"]:
            fab.link_component(l["component"], l["name"], l["config"])
        self.assertEqual(self.w.call("default", component="reports")["result"]["as"], "ro")

    def test_inv61_wire_roundtrip_and_error_envelope(self):
        Inv60FabricStub(self.w).link_component("orders", "primary", {"bucket": "o", "user": "u"})
        rpc = Inv61RpcStub(self.w)
        ok = json.loads(rpc.invoke(json.dumps({"link": "primary", "op": "get", "component": "orders"}).encode()))
        self.assertEqual(ok["ok"]["result"]["bucket"], "o")
        err = json.loads(rpc.invoke(json.dumps({"link": "primary", "op": "get", "component": "marketing"}).encode()))
        self.assertEqual(from_envelope(err["err"]).code, "PK_PROVIDER_NO_LINK")

    def test_inv55_secret_seam(self):
        self.w.inv55.put("secret://kv/o", ("acme", "prod", "sfo1", "shop", "orders"), b"v")
        self.w.link("primary", {"bucket": "o", "user": "u"}, secret_ref="secret://kv/o")
        self.w.call("primary")
        self.assertEqual(self.w.inv55.fetches, 1)
