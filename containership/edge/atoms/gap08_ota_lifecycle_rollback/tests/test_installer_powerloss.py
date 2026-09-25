"""Components 7 and 36: transactional A/B installer and simulated power-loss certification.

Cuts power at *every* named durable step of stage/activate/boot/confirm/rollback
and asserts the post-reboot invariant: the node boots a slot whose bytes match
its recorded digest, and that digest is either the old or the new image —
never a torn mix.  This is a filesystem-level simulation on the build host;
certification on constrained edge hardware (real power cuts, eMMC/NAND
behaviour) remains an open item (see docs/CHECKLIST_STATUS.md).
"""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import _path  # noqa: F401
from gap08_ota_lifecycle_rollback.errors import ArtifactMismatch, IllegalTransition
from gap08_ota_lifecycle_rollback.installer import ABInstaller, SimulatedPowerLoss

OLD = b"image-v1" * 100
NEW = b"image-v2" * 120
D_OLD = "sha256:" + hashlib.sha256(OLD).hexdigest()
D_NEW = "sha256:" + hashlib.sha256(NEW).hexdigest()
STEPS = ["stage.write", "stage.fsync", "stage.rename", "stage.digest", "activate.write", "boot.write",
         "confirm.write"]


def fresh():
    ins = ABInstaller(Path(tempfile.mkdtemp()))
    ins.provision(OLD, D_OLD)
    return ins


def full_update(ins):
    ins.stage(NEW, D_NEW)
    ins.activate(D_NEW)
    ins.boot()
    ins.confirm()


def post_reboot_ok(tc, ins):
    ins.crash_at = None
    ins.boot()
    slot = ins.ctl()["booted"]
    data = (ins.root / "slots" / slot / "payload").read_bytes()
    digest = ins.slot_digest(slot)
    tc.assertIn(digest, (D_OLD, D_NEW))
    tc.assertEqual("sha256:" + hashlib.sha256(data).hexdigest(), digest)
    tc.assertTrue(ins.invariant_ok())


class InstallerTest(unittest.TestCase):
    def test_happy_update_and_rollback(self):
        ins = fresh()
        full_update(ins)
        self.assertEqual(ins.running_digest(), D_NEW)
        ins.rollback()
        ins.boot()
        self.assertEqual(ins.running_digest(), D_OLD)

    def test_unconfirmed_boot_auto_reverts(self):
        ins = fresh()
        ins.stage(NEW, D_NEW)
        ins.activate(D_NEW)
        for _ in range(ins.boot_tries):
            self.assertEqual(ins.boot(), "B")       # tentative boots, never confirmed (e.g. crash loop)
        self.assertEqual(ins.boot(), "A")           # tries exhausted -> bootloader reverts
        self.assertEqual(ins.running_digest(), D_OLD)

    def test_digest_mismatch_never_activates(self):
        ins = fresh()
        with self.assertRaises(ArtifactMismatch):
            ins.stage(NEW, D_OLD)
        with self.assertRaises(IllegalTransition):
            ins.activate(D_NEW)
        post_reboot_ok(self, ins)

    def test_power_loss_at_every_step(self):
        for step in STEPS:
            for occurrence in (1, 2):
                with self.subTest(step=step, occurrence=occurrence):
                    ins = fresh()
                    seen = {"n": 0}

                    def cut(s, step=step, occurrence=occurrence):
                        if s == step:
                            seen["n"] += 1
                            if seen["n"] == occurrence:
                                raise SimulatedPowerLoss(s)
                    ins.crash_at = cut
                    try:
                        full_update(ins)
                    except SimulatedPowerLoss:
                        pass
                    post_reboot_ok(self, ins)
                    # and the node can always complete a clean update afterwards
                    ins.crash_at = None
                    if ins.ctl()["active"] == "A" and ins.ctl()["pending"] is None:
                        full_update(ins)
                        self.assertEqual(ins.running_digest(), D_NEW)

    def test_power_loss_during_rollback(self):
        ins = fresh()
        full_update(ins)
        ins.crash_at = lambda s: (_ for _ in ()).throw(SimulatedPowerLoss(s)) if s == "rollback.write" else None
        with self.assertRaises(SimulatedPowerLoss):
            ins.rollback()
        post_reboot_ok(self, ins)


if __name__ == "__main__":
    unittest.main()
