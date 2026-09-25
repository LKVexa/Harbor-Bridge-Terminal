"""INV-27 - Unikernel execution.

Unikernel execution is the single-address-space bet: the application and its kernel are linked into one image with no shell, no second process and no syscall surface to abuse. The isolation argument only holds if the image really is sealed, so this element verifies the seal rather than assuming it.

The component answers all 100 requirements of the INV-27 checklist.  Bands
whose defaults would merely restate the contract are overridden below so the
answer is produced by exercising the element's own behaviour.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build

def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``.

    Bare ``assert`` statements are stripped by the optimiser, which silently turned
    exercised checks into declared-only ones (and, where an assert carried a side
    effect, broke the element outright).  Every check goes through here instead.
    """
    if not condition:
        raise AssertionError(message)



from .runtime import DISQUALIFYING, SealInvalid, UnikernelImage, UnikernelInstance, run, verify_seal
from pathlib import Path as _Path

from .errors import UkError
from .image import elf as _elf, facts as _facts

_FIX = _Path(__file__).resolve().parent / "tests" / "fixtures"

#: Findings produced by exercising behaviour (the rest are pk_core declaration-derived defaults).
EXERCISED_BANDS = ["implementation[5]", "security[4]", "security[2]", "resilience[0]", "testing[0]"]


class UnikernelExecutionComponent(Component):
    """Master-applied component for INV-27."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        syscalls = frozenset({"read", "write", "clock_gettime"})
        image = UnikernelImage("svc", "mirageos", "x86_64", syscalls, syscalls)
        instance = run(image, tenant="t1", permitted=syscalls | {"exit"}, architecture="x86_64")
        _verify(instance.seal["sealed"] and instance.seal["syscall_count"] == 3, "check failed: instance.seal['sealed'] and instance.seal['syscall_count'] == 3")
        findings[5] = self.satisfied(
            items[5],
            f"Admission verifies the seal against the linked binary: {instance.seal['syscall_count']} "
            "syscalls, manifest and binary agreeing exactly.",
            *self._evidence("component.py::verify_seal"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        syscalls = frozenset({"read"})
        proven = []
        cases = [
            ("dynamic loading", UnikernelImage("a", "tc", "x86_64", syscalls, syscalls,
                                               features=frozenset({"dlopen"}))),
            ("multi-process", UnikernelImage("b", "tc", "x86_64", syscalls, syscalls,
                                             features=frozenset({"fork"}))),
            ("not single-address-space", UnikernelImage("c", "tc", "x86_64", syscalls, syscalls,
                                                        single_address_space=False)),
            ("manifest drift", UnikernelImage("d", "tc", "x86_64", syscalls,
                                              frozenset({"read", "socket"}))),
        ]
        for label, img in cases:
            try:
                verify_seal(img, permitted=syscalls | {"socket"}, architecture="x86_64")
            except SealInvalid:
                proven.append(label)
        _verify(len(proven) == 4, proven)
        findings[4] = self.satisfied(
            items[4],
            f"Four ways of breaking the seal are all refused: {', '.join(proven)}. The manifest is checked "
            "against the binary, so a claimed seal is never taken at face value.",
            *self._evidence("component.py::verify_seal"))
        ambient = 0
        for feature in ("shell", "exec", "Exec"):
            try:
                verify_seal(UnikernelImage("e", "tc", "x86_64", syscalls, syscalls,
                                           features=frozenset({feature})),
                            permitted=syscalls, architecture="x86_64")
            except SealInvalid:
                ambient += 1
        _verify(ambient == 3, "an image exposing shell/exec was admitted")
        # v4.3.0: the same refusals, derived from real binaries rather than caller-supplied features
        derived = []
        for name in ("uk_fork.elf", "uk_dlopen.elf"):
            f = _facts.derive(_elf.parse((_FIX / name).read_bytes()))
            derived.append(bool(f.capabilities) and not f.sas_proof["proven"])
        _verify(all(derived), "binary-derived capability detection missed a fork/dlopen image")
        findings[2] = self.satisfied(
            items[2],
            "A sealed image has no shell, no exec and no dynamic loading, so there is no ambient path to "
            "run code that was not linked in at build time.",
            *self._evidence("component.py::DISQUALIFYING"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        syscalls = frozenset({"read"})
        arm = UnikernelImage("svc", "tc", "aarch64", syscalls, syscalls)
        try:
            verify_seal(arm, permitted=syscalls, architecture="x86_64")
        except SealInvalid:
            findings[0] = self.satisfied(
                items[0],
                "An image built for a different architecture is refused at admission rather than failing "
                "opaquely at boot.",
                *self._evidence("component.py::verify_seal"))
        else:
            raise AssertionError('expected SealInvalid was not raised; the refusal this finding claims did not happen')
        return findings

    def assess_testing(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_testing(items)
        try:
            _elf.parse(b"\x7fELF" + b"\x00" * 12)
        except UkError as e:
            code = e.code
        else:
            raise AssertionError("truncated ELF was accepted")
        good = _facts.derive(_elf.parse((_FIX / "uk_good.elf").read_bytes()))
        _verify(code.startswith("UK_PARSE_") and good.sas_proof["proven"], "parser/facts behaviour check failed")
        findings[0] = self.satisfied(
            items[0],
            f"Unit behaviour exercised on real ELF fixtures: a truncated header is refused ({code}) and the "
            f"reference image yields a positive single-address-space proof with syscalls {sorted(good.syscalls)}.",
            *self._evidence("image/elf.py::parse", "image/facts.py::derive"))
        return findings

COMPONENT = UnikernelExecutionComponent
