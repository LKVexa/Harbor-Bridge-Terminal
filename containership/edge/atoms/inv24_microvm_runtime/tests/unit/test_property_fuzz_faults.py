"""MC-050 property/fuzz, MC-033/MC-053 fault injection, MC-051 races (stdlib, seeded, reproducible)."""
import errno
import json
import os
import random
import signal
import time
import unittest
from unittest import mock

from inv24_microvm_runtime.tests.helpers import keyring, tmpdir
from inv24_microvm_runtime.tests.unit.test_firecracker_adapter import Fixture

from inv24_microvm_runtime import MicroVM
from inv24_microvm_runtime.errors import Inv24Error
from inv24_microvm_runtime.runtime import MINIMAL_DEVICE_MODEL
from inv24_microvm_runtime.schemas import validate
from inv24_microvm_runtime.security.audit import AuditLog
from inv24_microvm_runtime.security.identity import TokenAuthority

SEED = int(os.environ.get("INV24_FUZZ_SEED", "20260923"))
N = int(os.environ.get("INV24_FUZZ_ITERS", "3000"))
ALPHABET = "abcXYZ019-_ \t\n\x00\x7fé‮"
JUNK = [None, True, False, 0, -1, 1.5, float("nan"), "", "x", [], {}, set(), b"x", 2 ** 70, object()]


def rand_value(rng):
    k = rng.random()
    if k < 0.3:
        return rng.choice(JUNK)
    if k < 0.6:
        return "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 140)))
    if k < 0.9:
        return rng.randint(-5, 140_000)
    return frozenset(rng.sample(sorted(MINIMAL_DEVICE_MODEL | {"pci", "gpu", "virtio-fs"}), rng.randint(0, 4)))


class PropertyTest(unittest.TestCase):
    def test_construction_either_valid_or_typed_rejection(self):
        rng = random.Random(SEED)
        accepted = 0
        for _ in range(N):
            valid = {"name": "vm", "tenant": "t", "vcpus": 2, "memory_mib": 256, "devices": frozenset({"serial"})}
            # mutate a random subset of fields so both accept and reject paths are explored
            kw = {k: (rand_value(rng) if rng.random() < 0.35 else v) for k, v in valid.items()}
            try:
                vm = MicroVM(**kw)
            except (TypeError, ValueError, PermissionError):
                continue
            accepted += 1
            # invariants of every accepted object
            self.assertTrue(vm.devices <= MINIMAL_DEVICE_MODEL)
            self.assertTrue(1 <= vm.vcpus <= 32 and 32 <= vm.memory_mib <= 131072)
            validate(vm.create_record())
        self.assertGreater(accepted, 0)

    def test_random_lifecycle_sequences_preserve_invariants(self):
        rng = random.Random(SEED + 1)
        ops = ["boot", "boot_slow", "pause", "resume", "stop"]
        for _ in range(N // 3):
            vm = MicroVM("vm", "t")
            for op in rng.choices(ops, k=rng.randint(1, 8)):
                before = vm.state
                try:
                    if op == "boot":
                        vm.boot(elapsed_ms=rng.randint(0, 125))
                    elif op == "boot_slow":
                        vm.boot(elapsed_ms=rng.randint(126, 10_000))
                    else:
                        getattr(vm, op)()
                except (RuntimeError, ValueError, TypeError):
                    pass
                self.assertIn(vm.state, {"created", "running", "paused", "failed", "stopped"})
                if before == "stopped":
                    self.assertEqual(vm.state, "stopped")
                self.assertEqual(vm.destroyed, vm.state == "stopped")

    def test_schema_validator_never_crashes_on_junk(self):
        rng = random.Random(SEED + 2)
        keys = ["schema", "operation_key", "tenant", "workload", "vcpus", "devices", "deadline_ms", "zz"]
        for _ in range(N):
            payload = {rng.choice(keys): rand_value(rng) for _ in range(rng.randint(0, 8))}
            payload["schema"] = "PK_MICROVM_ADMISSION/1"
            try:
                validate(json.loads(json.dumps(payload, default=str)))
            except Inv24Error as e:
                self.assertEqual(e.code, "SCHEMA_VIOLATION")

    def test_token_parser_never_crashes_on_junk(self):
        auth = TokenAuthority(keyring())
        rng = random.Random(SEED + 3)
        good = auth.issue("s", "workload", {"microvm:create"})
        for _ in range(N):
            t = list(good)
            for _ in range(rng.randint(1, 5)):
                t[rng.randrange(len(t))] = rng.choice(ALPHABET + ".")
            with self.assertRaises(Inv24Error):
                auth.verify("".join(t) if "".join(t) != good else "x")


class FaultInjectionTest(unittest.TestCase):
    def test_vmm_killed_after_boot_is_detected_and_cleaned(self):
        f = Fixture()
        vm = MicroVM("vm1", "t1", devices={"serial"})
        f.adapter.launch(vm, [])
        proc = f.adapter.processes["vm1"]
        os.killpg(proc.proc.pid, signal.SIGKILL)
        deadline = time.time() + 3
        while proc.alive() and time.time() < deadline:
            time.sleep(0.01)
        self.assertFalse(proc.alive())
        rec = f.adapter.destroy(vm)
        self.assertTrue(rec["cleanup"]["socket_removed"])
        self.assertEqual(f.registry.owned_by("t1"), [])

    def test_disk_full_on_audit_append_surfaces_error(self):
        log = AuditLog(os.path.join(tmpdir(), "a.jsonl"), keyring())
        with mock.patch("os.write", side_effect=OSError(errno.ENOSPC, "No space left")):
            with self.assertRaises(OSError):
                log.append("e", "a", "ok")
        # chain head not advanced on failure; next append still verifies
        log.append("e", "a", "ok")
        self.assertEqual(log.verify()[1], 1)

    def test_dependency_outage_blocks_admission(self):
        from inv24_microvm_runtime.tests.unit.test_admission_resilience import Harness
        from inv24_microvm_runtime.resilience import CircuitBreaker
        h = Harness()
        br = CircuitBreaker("kvm", failure_threshold=1, reset_s=60)
        br.failure()
        h.ac.readiness = br.before
        with self.assertRaises(Inv24Error) as cm:
            h.ac.admit(h.req("op-outage01"))
        self.assertEqual((cm.exception.code, cm.exception.retryable), ("CIRCUIT_OPEN", True))
        self.assertEqual(h.launched, [])


if __name__ == "__main__":
    unittest.main()
