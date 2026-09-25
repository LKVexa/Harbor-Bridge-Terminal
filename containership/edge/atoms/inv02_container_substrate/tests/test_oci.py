"""MC01 / MC14 / MC57 — OCI image spec parsing and platform selection."""
import json
import unittest

from inv02_container_substrate import oci
from inv02_container_substrate.tests.fixtures import make_image, make_index, sha


class OCIManifestTests(unittest.TestCase):
    def setUp(self):
        self.img = make_image([[("etc/", "dir"), ("etc/os-release", "file", b"ID=test\n")]])

    def test_parses_valid_manifest_and_config(self):
        m = oci.parse_manifest(self.img["manifest"], expected_media_type=oci.MT_MANIFEST)
        self.assertIsInstance(m, oci.ImageManifest)
        self.assertEqual(len(m.layers), 1)
        cfg = oci.ImageConfig.parse(self.img["config"])
        oci.verify_config_matches(m, cfg)
        self.assertEqual(str(cfg.platform), "linux/amd64")

    def test_content_type_mismatch_fails_closed(self):
        with self.assertRaises(oci.OCIError):
            oci.parse_manifest(self.img["manifest"], expected_media_type=oci.MT_INDEX)

    def test_rejects_malformed_documents(self):
        good = json.loads(self.img["manifest"])
        cases = [
            b"[]", b"\xff\xfe", b'{"schemaVersion":2,"schemaVersion":2}',
            json.dumps({**good, "schemaVersion": 1}).encode(),
            json.dumps({**good, "layers": [{"mediaType": "x/y", "digest": "sha256:zz", "size": 1}]}).encode(),
            json.dumps({**good, "layers": [{"mediaType": "x/y", "digest": "md5:" + "0" * 32, "size": 1}]}).encode(),
            json.dumps({**good, "layers": [{"mediaType": "x/y", "digest": sha(b""), "size": -1}]}).encode(),
            json.dumps({**good, "manifests": []}).encode(),
            json.dumps({**good, "mediaType": "application/unknown"}).encode(),
            ('{"schemaVersion":2,"a":' + "[" * 40 + "1" + "]" * 40 + "}").encode(),
        ]
        for raw in cases:
            with self.subTest(raw=raw[:60]):
                with self.assertRaises(oci.OCIError):
                    oci.parse_manifest(raw)

    def test_config_diff_id_mismatch(self):
        m = oci.parse_manifest(self.img["manifest"])
        cfg = json.loads(self.img["config"])
        cfg["rootfs"]["diff_ids"].append(sha(b"x"))
        with self.assertRaises(oci.OCIError):
            oci.verify_config_matches(m, oci.ImageConfig.parse(json.dumps(cfg).encode()))

    def test_artifact_manifest_requires_artifact_type(self):
        empty = b"{}"
        doc = {"schemaVersion": 2, "mediaType": oci.MT_MANIFEST,
               "config": {"mediaType": oci.MT_EMPTY, "digest": sha(empty), "size": 2}, "layers": []}
        with self.assertRaises(oci.OCIError):
            oci.parse_manifest(json.dumps(doc).encode())
        doc["artifactType"] = "application/vnd.example.sbom+json"
        doc["subject"] = {"mediaType": oci.MT_MANIFEST, "digest": self.img["digest"], "size": len(self.img["manifest"])}
        m = oci.parse_manifest(json.dumps(doc).encode())
        self.assertTrue(m.is_artifact)
        self.assertEqual(m.subject.digest, self.img["digest"])
        self.assertEqual(sha(empty), oci.EMPTY_JSON_DIGEST)

    def test_descriptor_embedded_data_verified(self):
        import base64
        d = {"mediaType": "x/y", "digest": sha(b"hi"), "size": 2, "data": base64.b64encode(b"hi").decode()}
        self.assertEqual(oci.Descriptor.parse(d).data, b"hi")
        d["data"] = base64.b64encode(b"ho").decode()
        with self.assertRaises(oci.OCIError):
            oci.Descriptor.parse(d)


class PlatformSelectionTests(unittest.TestCase):
    def setUp(self):
        self.amd = make_image([[("a", "file", b"amd")]], arch="amd64")
        self.arm7 = make_image([[("a", "file", b"arm7")]], arch="arm", variant="v7")
        self.arm6 = make_image([[("a", "file", b"arm6")]], arch="arm", variant="v6")
        self.arm64 = make_image([[("a", "file", b"arm64")]], arch="arm64", variant="v8")
        self.index = oci.parse_manifest(make_index([(self.amd, "linux", "amd64", None), (self.arm6, "linux", "arm", "v6"),
                                                    (self.arm7, "linux", "arm", "v7"), (self.arm64, "linux", "arm64", "v8")]))

    def pick(self, s):
        return oci.select_platform(self.index, oci.Platform.from_string(s)).digest

    def test_exact_and_compatible_matches(self):
        self.assertEqual(self.pick("linux/amd64"), self.amd["digest"])
        self.assertEqual(self.pick("linux/x86_64"), self.amd["digest"])
        self.assertEqual(self.pick("linux/arm/v7"), self.arm7["digest"])
        self.assertEqual(self.pick("linux/arm64"), self.arm64["digest"])
        self.assertEqual(self.pick("linux/aarch64/v8"), self.arm64["digest"])

    def test_v6_host_never_gets_v7(self):
        self.assertEqual(self.pick("linux/arm/v6"), self.arm6["digest"])

    def test_no_cross_os_or_arch_fallback(self):
        for p in ("windows/amd64", "linux/s390x", "linux/arm/v5"):
            with self.subTest(p=p), self.assertRaises(oci.NoMatchingPlatform):
                self.pick(p)


if __name__ == "__main__":
    unittest.main()
