"""Dependency-free tests for the INV-27 admission/runtime security boundary."""
from __future__ import annotations

import importlib.util
import pathlib
import types
import unittest

RUNTIME = pathlib.Path(__file__).resolve().parents[1] / "runtime.py"
spec = importlib.util.spec_from_file_location("inv27_runtime_under_test", RUNTIME)
assert spec and spec.loader
runtime = importlib.util.module_from_spec(spec)
# dataclasses consult sys.modules while decorating classes.
import sys
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)


class RuntimeSecurityTest(unittest.TestCase):
    def image(self, **changes):
        values = dict(
            name="svc",
            toolchain="mirageos",
            architecture="x86_64",
            declared_syscalls=frozenset({"read", "write"}),
            linked_syscalls=frozenset({"read", "write"}),
        )
        values.update(changes)
        return runtime.UnikernelImage(**values)

    def test_valid_image_is_admitted_with_immutable_seal(self):
        seal = runtime.verify_seal(
            self.image(), permitted=frozenset({"read", "write"}), architecture="x86_64"
        )
        self.assertTrue(seal["sealed"])
        self.assertEqual(seal["syscalls"], ("read", "write"))
        with self.assertRaises(TypeError):
            seal["sealed"] = False

    def test_disqualifying_features_are_case_insensitive(self):
        for feature in ("fork", "EXEC", "Dlopen", "Ptrace", "SHELL"):
            with self.subTest(feature=feature), self.assertRaises(runtime.SealInvalid):
                runtime.verify_seal(
                    self.image(features=frozenset({feature})),
                    permitted=frozenset({"read", "write"}),
                    architecture="x86_64",
                )

    def test_manifest_drift_fails_closed(self):
        with self.assertRaises(runtime.SealInvalid):
            runtime.verify_seal(
                self.image(linked_syscalls=frozenset({"read"})),
                permitted=frozenset({"read", "write"}),
                architecture="x86_64",
            )

    def test_unpermitted_syscall_fails_closed(self):
        with self.assertRaises(runtime.SealInvalid):
            runtime.verify_seal(
                self.image(), permitted=frozenset({"read"}), architecture="x86_64"
            )

    def test_architecture_mismatch_fails_closed(self):
        with self.assertRaises(runtime.SealInvalid):
            runtime.verify_seal(
                self.image(), permitted=frozenset({"read", "write"}), architecture="aarch64"
            )

    def test_malformed_sets_and_entries_are_rejected(self):
        malformed = [
            dict(declared_syscalls=["read", "write"]),
            dict(linked_syscalls=frozenset({"read", 7})),
            dict(features=frozenset({""})),
        ]
        for changes in malformed:
            with self.subTest(changes=changes), self.assertRaises(runtime.SealInvalid):
                runtime.verify_seal(
                    self.image(**changes),
                    permitted=frozenset({"read", "write"}),
                    architecture="x86_64",
                )

    def test_nonempty_identity_fields_are_required(self):
        for field in ("name", "toolchain", "architecture"):
            with self.subTest(field=field), self.assertRaises(runtime.SealInvalid):
                runtime.verify_seal(
                    self.image(**{field: "   "}),
                    permitted=frozenset({"read", "write"}),
                    architecture="x86_64",
                )
        with self.assertRaises(runtime.SealInvalid):
            runtime.run(
                self.image(), tenant="   ",
                permitted=frozenset({"read", "write"}), architecture="x86_64"
            )

    def test_single_address_space_is_strict_boolean(self):
        with self.assertRaises(runtime.SealInvalid):
            runtime.verify_seal(
                self.image(single_address_space=1),
                permitted=frozenset({"read", "write"}), architecture="x86_64"
            )

    def test_stop_is_idempotent_but_rejects_corrupt_state(self):
        inst = runtime.run(
            self.image(), tenant="t1",
            permitted=frozenset({"read", "write"}), architecture="x86_64"
        )
        self.assertEqual(inst.stop(), "stopped")
        self.assertEqual(inst.stop(), "stopped")
        inst.state = "corrupt"
        with self.assertRaises(RuntimeError):
            inst.stop()


if __name__ == "__main__":
    unittest.main()
