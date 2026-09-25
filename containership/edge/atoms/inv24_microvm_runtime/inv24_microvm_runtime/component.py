"""INV-24 - MicroVM runtime.

The microVM runtime is the Firecracker-shaped tier: a stripped VMM with a minimal device model that boots in milliseconds. Its whole value is that the attack surface is small and the boot is fast, so this element refuses a configuration that widens the one or destroys the other.

The component answers all 100 requirements of the INV-24 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)



from .runtime import (
    BOOT_BUDGET_MS,
    MINIMAL_DEVICE_MODEL,
    BootBudgetExceeded,
    DeviceOutsideModel,
    MicroVM,
)


class MicrovmRuntimeComponent(Component):
    """Master-applied component for INV-24."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        vm = MicroVM("i-1", "t1", vcpus=2, memory_mib=256,
                     devices=frozenset({"virtio-net", "virtio-block"}))
        result = vm.boot(elapsed_ms=40)
        _verify(result["boot_ms"] == 40 and vm.state == "running", "check failed: result['boot_ms'] == 40 and vm.state == 'running'")
        _verify(vm.pause() == "paused" and vm.resume() == "running", "check failed: vm.pause() == 'paused' and vm.resume() == 'running'")
        _verify(vm.stop()["destroyed"], "check failed: vm.stop()['destroyed']")
        findings[5] = self.satisfied(
            items[5],
            f"Lifecycle is a strict state machine (created -> running -> paused -> running -> stopped) and "
            f"the instance booted in {result['boot_ms']}ms of a {result['budget_ms']}ms budget.",
            *self._evidence("component.py::MicroVM"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        try:
            MicroVM("i-2", "t1", devices=frozenset({"virtio-net", "pci-passthrough"}))
        except DeviceOutsideModel:
            findings[2] = self.satisfied(
                items[2],
                f"The device model is closed: only {len(MINIMAL_DEVICE_MODEL)} devices are permitted and a "
                "passthrough request is refused at construction, so attack surface cannot grow by config.",
                *self._evidence("component.py::MINIMAL_DEVICE_MODEL"))
        else:
            raise AssertionError('expected DeviceOutsideModel was not raised; the refusal this finding claims did not happen')
        vm = MicroVM("i-3", "t1", devices=frozenset({"serial"}))
        vm.boot(elapsed_ms=10)
        vm.stop()
        _verify(vm.destroyed, "instance survived stop")
        findings[5] = self.satisfied(
            items[5],
            "Stop destroys the instance, so its memory cannot be handed to another tenant without "
            "going through creation again.",
            *self._evidence("component.py::MicroVM.stop"))
        return findings

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        slow = MicroVM("i-4", "t1", devices=frozenset({"serial"}))
        try:
            slow.boot(elapsed_ms=BOOT_BUDGET_MS + 1)
        except BootBudgetExceeded:
            _verify(slow.state == "failed", "check failed: slow.state == 'failed'")
            findings[4] = self.satisfied(
                items[4],
                f"A cold boot past the {BOOT_BUDGET_MS}ms budget fails the instance rather than being "
                "quietly absorbed, so cold-start cost stays visible.",
                *self._evidence("component.py::MicroVM.boot"))
        else:
            raise AssertionError('expected BootBudgetExceeded was not raised; the refusal this finding claims did not happen')
        inv35 = sibling("INV-35")
        if inv35 is None:
            findings[0] = self.partial(
                items[0],
                "Boot time is measured and budgeted, but steady-state throughput is not.",
                note="INV-35 High-performance VM I/O is not installed here")
        else:
            regions = (inv35.MemoryRegion(0x10000, 0x100000),)
            queue = inv35.VirtQueue("vq0", regions)
            chain = {0: inv35.Descriptor(0, 0x10000, 4096)}
            moved = sum(queue.submit(chain, head=0)["bytes"] for _ in range(16))
            for _ in range(16):
                queue.complete(guest_wants_notification=False)
            _verify(moved == 16 * 4096 and queue.in_flight == 0, 'check failed: moved == 16 * 4096 and queue.in_flight == 0')
            findings[0] = self.satisfied(
                items[0],
                "Boot latency and steady-state throughput are now separately quantified: this runtime "
                f"budgets the {BOOT_BUDGET_MS}ms boot, while the INV-35 datapath moved {moved} bytes "
                "across 16 validated descriptors and drained the queue.",
                *self._evidence("component.py::MicroVM.boot"), "INV-35/VirtQueue")
        return findings

COMPONENT = MicrovmRuntimeComponent
