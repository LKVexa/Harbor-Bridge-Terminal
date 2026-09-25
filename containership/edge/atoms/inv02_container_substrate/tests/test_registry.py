"""Standalone tests for the INV-02 registry integrity model.

These tests do not require pk_core; they load registry.py directly so integrity and
reference-policy checks still execute in a partial checkout.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import subprocess
import unittest
from concurrent.futures import ThreadPoolExecutor

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inv02_registry_under_test", PKG_DIR / "registry.py")
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery failure
    raise RuntimeError("could not load registry.py")
REG = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REG
SPEC.loader.exec_module(REG)

IntegrityError = REG.IntegrityError
LimitExceeded = REG.LimitExceeded
Limits = REG.Limits
MutableTagRefused = REG.MutableTagRefused
QuarantinedDigest = REG.QuarantinedDigest
Registry = REG.Registry
UnknownReference = REG.UnknownReference
ValidationError = REG.ValidationError
digest = REG.digest
parse_reference = REG.parse_reference


class RegistryTest(unittest.TestCase):
    def test_package_base_import_does_not_require_pk_core(self):
        code = (
            "import inv02_container_substrate as p; "
            "print(p.__version__); print(p.Registry.__name__)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(PKG_DIR.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = (PKG_DIR / "VERSION").read_text().strip()
        self.assertEqual(result.stdout.splitlines(), [expected, "Registry"])

    def test_digest_is_canonical_sha256(self):
        self.assertEqual(
            digest(b"abc"),
            "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )
        with self.assertRaises(ValidationError):
            digest("abc")

    def test_push_pull_and_layer_deduplication(self):
        reg = Registry()
        first = reg.push("team/api", "1", [b"base", b"app-one"])
        second = reg.push("team/worker", "1", [b"base", b"app-two"])
        self.assertNotEqual(first, second)
        self.assertEqual(reg.pull(first), [b"base", b"app-one"])
        self.assertEqual(reg.stats()["layer_blob_count"], 3)
        self.assertEqual(reg.blobs[digest(b"base")], b"base")

    def test_protected_environment_tag_policy_has_no_case_or_prod_alias_bypass(self):
        reg = Registry()
        manifest = reg.push("api", "1.0", [b"base", b"app"])
        for environment in ("production", "PRODUCTION", " prod ", "Prod"):
            with self.subTest(environment=environment):
                with self.assertRaises(MutableTagRefused):
                    reg.resolve("api:1.0", environment)
        self.assertEqual(reg.resolve(f"api@{manifest}", "production"), manifest)
        self.assertEqual(reg.resolve("api:1.0", "staging"), manifest)

    def test_digest_resolution_requires_known_manifest(self):
        reg = Registry()
        unknown = digest(b"not stored")
        with self.assertRaises(UnknownReference):
            reg.resolve(unknown, "production")
        with self.assertRaises(UnknownReference):
            reg.resolve(f"api@{unknown}", "production")

    def test_digest_resolution_rejects_known_non_manifest_blob(self):
        reg = Registry()
        layer = b"ordinary-layer-bytes"
        layer_digest = digest(layer)
        reg.blobs[layer_digest] = layer
        with self.assertRaises(IntegrityError):
            reg.resolve(layer_digest, "production")

    def test_reference_parser_handles_registry_ports_and_rejects_ambiguous_input(self):
        parsed = parse_reference("registry.example:5000/team/api:release-1")
        self.assertEqual(parsed.kind, "tag")
        self.assertEqual(parsed.name, "registry.example:5000/team/api")
        self.assertEqual(parsed.tag, "release-1")
        for reference in (
            "api",
            " api:1",
            "api:1 ",
            "api@@sha256:" + "0" * 64,
            "api@sha256:1234",
            "/api:1",
            "api/:1",
        ):
            with self.subTest(reference=reference):
                with self.assertRaises(ValidationError):
                    parse_reference(reference)

    def test_tag_movement_cannot_rewrite_digest_pinned_content(self):
        reg = Registry()
        old = reg.push("api", "latest", [b"base", b"good"])
        reg.push("api", "latest", [b"base", b"new"])
        self.assertNotEqual(reg.resolve("api:latest", "staging"), old)
        self.assertEqual(reg.pull(old), [b"base", b"good"])
        self.assertEqual(reg.provenance[-1].previous_manifest_digest, old)

    def test_repush_heals_corrupt_content_under_digest_key(self):
        reg = Registry()
        manifest = reg.push("api", "1", [b"base", b"app"])
        base_digest = digest(b"base")
        reg.blobs[base_digest] = b"corrupt"
        with self.assertRaises(IntegrityError):
            reg.pull(manifest)
        reg.push("api", "1", [b"base", b"app"])
        self.assertEqual(reg.blobs[base_digest], b"base")
        self.assertEqual(reg.pull(manifest), [b"base", b"app"])

    def test_repush_heals_non_bytes_backing_value(self):
        reg = Registry()
        base_digest = digest(b"base")
        reg.blobs[base_digest] = "not-bytes"
        manifest = reg.push("api", "1", [b"base", b"app"])
        self.assertEqual(reg.blobs[base_digest], b"base")
        self.assertEqual(reg.pull(manifest), [b"base", b"app"])

    def test_malformed_manifest_and_descriptors_fail_closed(self):
        reg = Registry()
        malformed = b"not-json"
        malformed_digest = digest(malformed)
        reg.blobs[malformed_digest] = malformed
        with self.assertRaises(IntegrityError):
            reg.pull(malformed_digest)

        bad_doc = json.dumps(
            {
                "schemaVersion": 1,
                "mediaType": REG.MANIFEST_MEDIA_TYPE,
                "layers": [{"digest": "sha256:bad", "size": 3}],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        bad_digest = digest(bad_doc)
        reg.blobs[bad_digest] = bad_doc
        with self.assertRaises(IntegrityError):
            reg.pull(bad_digest)

    def test_legacy_v4_1_manifest_remains_readable(self):
        reg = Registry()
        layer = b"legacy"
        layer_digest = digest(layer)
        reg.blobs[layer_digest] = layer
        legacy_manifest = json.dumps({"layers": [layer_digest]}).encode()
        manifest_digest = digest(legacy_manifest)
        reg.blobs[manifest_digest] = legacy_manifest
        self.assertEqual(reg.pull(manifest_digest), [layer])

    def test_resource_limits_are_enforced_and_logs_are_bounded(self):
        limits = Limits(
            max_layers_per_image=2,
            max_layer_bytes=16,
            max_image_bytes=32,
            max_manifest_bytes=4096,
            max_reference_length=128,
            max_resolution_records=2,
            max_provenance_records=2,
        )
        reg = Registry(limits=limits)
        with self.assertRaises(LimitExceeded):
            reg.push("api", "1", [b"a", b"b", b"c"])
        with self.assertRaises(LimitExceeded):
            reg.push("api", "1", [b"x" * 17])

        for i in range(3):
            reg.push("api", str(i), [b"base", str(i).encode()])
            reg.resolve(f"api:{i}", "staging")
        self.assertEqual(len(reg.provenance), 2)
        self.assertEqual(len(reg.resolutions), 2)

    def test_quarantine_blocks_manifest_and_layer_until_released(self):
        reg = Registry()
        manifest = reg.push("api", "1", [b"base", b"app"])
        reg.quarantine(manifest, "security hold")
        with self.assertRaises(QuarantinedDigest):
            reg.resolve(f"api@{manifest}", "production")
        with self.assertRaises(QuarantinedDigest):
            reg.pull(manifest)
        reg.release_quarantine(manifest)
        self.assertEqual(reg.pull(manifest), [b"base", b"app"])

        layer_digest = digest(b"app")
        reg.quarantine(layer_digest, "layer advisory")
        with self.assertRaises(QuarantinedDigest):
            reg.pull(manifest)

    def test_custom_immutable_environment_policy(self):
        reg = Registry(immutable_tag_environments=frozenset({"release"}))
        reg.push("api", "1", [b"base"])
        with self.assertRaises(MutableTagRefused):
            reg.resolve("api:1", "RELEASE")
        self.assertEqual(reg.resolve("api:1", "production"), reg.tags["api:1"])

    def test_concurrent_push_resolve_and_pull_are_consistent(self):
        reg = Registry()

        def work(i: int) -> tuple[str, bytes]:
            name = f"svc{i}"
            payload = f"app-{i}".encode()
            manifest = reg.push(name, "1", [b"shared-base", payload])
            resolved = reg.resolve(f"{name}:1", "staging")
            self.assertEqual(resolved, manifest)
            self.assertEqual(reg.pull(resolved), [b"shared-base", payload])
            return manifest, payload

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(work, range(32)))
        self.assertEqual(len({manifest for manifest, _ in results}), 32)
        self.assertEqual(reg.stats()["layer_blob_count"], 33)


if __name__ == "__main__":
    unittest.main()
