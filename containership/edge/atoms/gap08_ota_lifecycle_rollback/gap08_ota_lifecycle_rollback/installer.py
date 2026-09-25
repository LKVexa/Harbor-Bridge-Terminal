"""Node-side transactional A/B installer (component 7) with power-loss hooks (component 36).

Layout under ``root``::

    slots/A/payload   slots/B/payload     # images, each with .digest
    bootctl.json                          # {active, pending, tries_left, confirmed_digest}

Protocol (each step is atomic: temp + fsync + rename + dir fsync):

1. ``stage``    — stream the image into the *inactive* slot, verify digest, commit;
2. ``activate`` — set ``pending=<inactive>, tries_left=N``; active slot untouched;
3. ``boot``     — bootloader: if ``pending`` and tries remain, decrement and boot it
                  *tentatively*; if tries are exhausted, drop ``pending`` (auto-revert);
4. ``confirm``  — health-checked userspace promotes pending -> active;
5. ``rollback`` — drop pending or swap back to the previous confirmed slot.

A power loss at any point leaves ``bootctl.json`` either old or new and a
bootable, digest-valid active slot; ``crash_at`` lets certification tests cut
power at every named step.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .common import canonical_json
from .errors import ArtifactMismatch, IllegalTransition

STEPS = ("stage.write", "stage.fsync", "stage.rename", "activate.write", "boot.write", "confirm.write",
         "rollback.write")


class SimulatedPowerLoss(BaseException):
    """Raised by the crash hook; BaseException so ordinary handlers cannot swallow it."""


@dataclass
class ABInstaller:
    root: Path
    boot_tries: int = 2
    crash_at: Callable[[str], None] | None = None

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        for s in ("A", "B"):
            (self.root / "slots" / s).mkdir(parents=True, exist_ok=True)

    # ---- durable helpers ------------------------------------------------------
    def _hook(self, step: str) -> None:
        if self.crash_at is not None:
            self.crash_at(step)

    def _atomic(self, path: Path, data: bytes, step: str) -> None:
        tmp = path.with_name(path.name + ".tmp")
        fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        self._hook(step)
        os.replace(tmp, path)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

    @property
    def _ctl(self) -> Path:
        return self.root / "bootctl.json"

    def ctl(self) -> dict:
        if not self._ctl.exists():
            return {"active": "A", "pending": None, "tries_left": 0, "booted": "A"}
        return json.loads(self._ctl.read_bytes())

    def _write_ctl(self, ctl: dict, step: str) -> None:
        self._atomic(self._ctl, canonical_json(ctl), step)

    def slot_digest(self, slot: str) -> str | None:
        p = self.root / "slots" / slot / "payload.digest"
        return p.read_text().strip() if p.exists() else None

    @staticmethod
    def other(slot: str) -> str:
        return "B" if slot == "A" else "A"

    # ---- factory provisioning -------------------------------------------------
    def provision(self, payload: bytes, digest: str) -> None:
        import hashlib
        if "sha256:" + hashlib.sha256(payload).hexdigest() != digest:
            raise ArtifactMismatch("factory image digest mismatch")
        d = self.root / "slots" / "A"
        (d / "payload").write_bytes(payload)
        (d / "payload.digest").write_text(digest)
        self._write_ctl({"active": "A", "pending": None, "tries_left": 0, "booted": "A"}, "provision")

    # ---- protocol -------------------------------------------------------------
    def stage(self, payload: bytes, digest: str) -> str:
        import hashlib
        ctl = self.ctl()
        if ctl["pending"] is not None:
            raise IllegalTransition("an update is already pending")
        slot = self.other(ctl["active"])
        d = self.root / "slots" / slot
        # invalidate the slot's digest first so a torn payload can never look valid
        (d / "payload.digest").unlink(missing_ok=True)
        tmp = d / "payload.tmp"
        fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            self._hook("stage.write")
            os.write(fd, payload)
            self._hook("stage.fsync")
            os.fsync(fd)
        finally:
            os.close(fd)
        if "sha256:" + hashlib.sha256(tmp.read_bytes()).hexdigest() != digest:
            tmp.unlink()
            raise ArtifactMismatch("staged bytes do not match the verified digest")
        self._hook("stage.rename")
        os.replace(tmp, d / "payload")
        self._atomic(d / "payload.digest", digest.encode(), "stage.digest")
        return slot

    def activate(self, digest: str) -> None:
        ctl = self.ctl()
        slot = self.other(ctl["active"])
        if self.slot_digest(slot) != digest:
            raise IllegalTransition("inactive slot does not hold the staged digest")
        self._write_ctl({**ctl, "pending": slot, "tries_left": self.boot_tries}, "activate.write")

    def boot(self) -> str:
        """Bootloader decision; returns the slot booted."""
        ctl = self.ctl()
        if ctl["pending"] and ctl["tries_left"] > 0 and self.slot_digest(ctl["pending"]):
            ctl = {**ctl, "tries_left": ctl["tries_left"] - 1, "booted": ctl["pending"]}
        else:
            ctl = {**ctl, "pending": None, "tries_left": 0, "booted": ctl["active"]}
        self._write_ctl(ctl, "boot.write")
        return ctl["booted"]

    def confirm(self) -> None:
        ctl = self.ctl()
        if not ctl["pending"] or ctl["booted"] != ctl["pending"]:
            raise IllegalTransition("nothing tentatively booted to confirm")
        self._write_ctl({"active": ctl["pending"], "pending": None, "tries_left": 0, "booted": ctl["pending"]},
                        "confirm.write")

    def rollback(self) -> None:
        ctl = self.ctl()
        if ctl["pending"]:
            new = {**ctl, "pending": None, "tries_left": 0}
        else:
            prev = self.other(ctl["active"])
            if not self.slot_digest(prev):
                raise IllegalTransition("no previous confirmed slot to roll back to")
            new = {"active": prev, "pending": None, "tries_left": 0, "booted": ctl["booted"]}
        self._write_ctl(new, "rollback.write")

    def running_digest(self) -> str | None:
        return self.slot_digest(self.ctl()["booted"])

    def invariant_ok(self) -> bool:
        ctl = self.ctl()
        return self.slot_digest(ctl["active"]) is not None
