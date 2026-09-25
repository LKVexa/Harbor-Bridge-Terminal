"""INV-35-C030/C083: integration against the adjacent-layer contracts named in contract.py.

The adjacent layers are *contract doubles* that speak the documented interfaces
(docs/architecture/BOUNDARY_INVENTORY.md).  They prove this component's side of
each boundary; they do not substitute for integration with the real INV-24/
INV-25/PLN-06 implementations, which stays tracked under WVR-002 until those
builds are available to CI.
"""
from __future__ import annotations

import unittest

from _support import BULK, CTL, Inv35Error, MemoryRegion, State, one, pkg, rt


class MicroVMRuntimeDouble:
    """INV-24 (upstream): owns the guest and its registered memory regions."""

    def __init__(self, tenant, regions):
        self.tenant, self.regions = tenant, tuple(MemoryRegion(b, l) for b, l in regions)


class MicroVMDevicesDouble:
    """INV-25 (upstream): decides which devices (and therefore queues) exist."""

    def __init__(self, devices):
        self.devices = devices  # {"virtio-net0": ["rx", "tx"], "virtio-blk0": ["req"]}

    def queues(self):
        return [f"{d}.{q}" for d, qs in self.devices.items() for q in qs]


class DataPlaneDouble:
    """PLN-06 (downstream): consumes completions for bulk transfers."""

    def __init__(self):
        self.completed_bytes = 0
        self.wakeups = 0

    def on_complete(self, submit_res, complete_res):
        self.completed_bytes += submit_res["bytes"]
        self.wakeups += complete_res["notified"]


class AdjacentLayerTest(unittest.TestCase):
    def setUp(self):
        self.guest = MicroVMRuntimeDouble("tenant-a", [(0x10000, 0x10000), (0x40000, 0x1000)])
        self.devs = MicroVMDevicesDouble({"virtio-net0": ["rx", "tx"], "virtio-blk0": ["req"]})
        self.r = rt.Runtime()
        self.cp, self.dp = rt.ControlPlane(self.r), rt.Datapath(self.r)
        names = set(self.devs.queues())
        self.ctl = self.r.authority.mint("vmm-controller", "tenant-a", names, CTL)
        self.bulk = self.r.authority.mint("vhost-worker", "tenant-a", names, BULK)
        for q in sorted(names):
            self.cp.register_queue(self.ctl, tenant=self.guest.tenant, queue=q, regions=self.guest.regions)
        self.plane = DataPlaneDouble()

    def test_version_negotiation_with_vmm(self):
        agreed = self.cp.negotiate({"PK_VIRTQUEUE_SUBMIT": [1, 2], "PK_VIRTQUEUE_COMPLETE": [1], "FUTURE_X": [9]})
        self.assertEqual(agreed, {"PK_VIRTQUEUE_SUBMIT": 1, "PK_VIRTQUEUE_COMPLETE": 1})
        with self.assertRaises(Inv35Error) as cm:
            self.cp.negotiate({"PK_VIRTQUEUE_SUBMIT": [2], "PK_VIRTQUEUE_COMPLETE": [1]})
        self.assertEqual(cm.exception.code, "INV35-E503")

    def test_every_device_queue_moves_bulk_data_to_data_plane(self):
        for q in self.devs.queues():
            res = self.dp.submit(self.bulk, tenant="tenant-a", queue=q, chain=one(addr=0x40000, length=512), head=0)
            done = self.dp.complete(self.bulk, tenant="tenant-a", queue=q, guest_wants_notification=True)
            self.plane.on_complete(res, done)
        self.assertEqual(self.plane.completed_bytes, 512 * 3)
        self.assertEqual(self.plane.wakeups, 3)

    def test_gap_between_guest_regions_is_not_memory(self):
        with self.assertRaises(Inv35Error) as cm:
            self.dp.submit(self.bulk, tenant="tenant-a", queue="virtio-blk0.req", chain=one(addr=0x20000, length=16), head=0)
        self.assertEqual(cm.exception.code, "INV35-E105")

    def test_device_removal_drains_then_stops(self):
        q = "virtio-net0.tx"
        self.dp.submit(self.bulk, tenant="tenant-a", queue=q, chain=one(), head=0)
        self.cp.transition(self.ctl, tenant="tenant-a", queue=q, target=State.DRAINING, reason="hot-unplug",
                           actor="INV-25", epoch=1)
        with self.assertRaises(Inv35Error):
            self.dp.submit(self.bulk, tenant="tenant-a", queue=q, chain=one(), head=0)
        self.dp.complete(self.bulk, tenant="tenant-a", queue=q, guest_wants_notification=True)
        self.cp.transition(self.ctl, tenant="tenant-a", queue=q, target=State.STOPPED, reason="drained",
                           actor="INV-25", epoch=1)
        self.assertEqual(self.r.status()["queues"][q]["state"], "stopped")

    def test_trace_context_crosses_the_boundary(self):
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        res = self.dp.submit(self.bulk, tenant="tenant-a", queue="virtio-blk0.req", chain=one(), head=0, traceparent=tp)
        self.assertEqual(res["trace_id"], "4bf92f3577b34da6a3ce929d0e0e4736")

    def test_transient_execution_peer_optional(self):
        # INV-43 is an optional peer: its absence must not change safety outcomes.
        res = self.dp.submit(self.bulk, tenant="tenant-a", queue="virtio-blk0.req", chain=one(), head=0)
        self.assertTrue(res["validated"])


if __name__ == "__main__":
    unittest.main()
