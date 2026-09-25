"""C032-C035 declarative config + overlays, C036 provenance, C037-C038 atomic activation/rollback."""
import json
import tempfile
import threading
import unittest

from _pkg import configuration as K, security as X, PKG_DIR


class LoaderTest(unittest.TestCase):
    def test_defaults_valid_and_overlays(self):
        base = K.load_layers()
        self.assertEqual(base["schema_version"], 1)
        edge = K.load_layers(PKG_DIR / "config" / "overlays" / "far-edge.json")
        self.assertEqual(edge["tier"], "far-edge")
        self.assertEqual(edge["stream"]["max_credit"], 64)
        self.assertEqual(edge["tenants"], base["tenants"])  # untouched keys inherited
        cfg = K.to_stream_config(edge)
        self.assertEqual((cfg.max_credit, cfg.max_buffer), (64, 64))

    def test_every_shipped_overlay_validates(self):
        for p in sorted((PKG_DIR / "config" / "overlays").glob("*.json")):
            K.load_layers(p)

    def test_fail_closed_on_invalid(self):
        bad = [{"stream": {"max_credit": 0}}, {"stream": {"max_credit": True}}, {"surprise": 1},
               {"environment": "moon"}, {"stream": {"max_credit": 1, "max_buffer": 1000}},
               {"tenants": {"t": {"max_streams": 1}}}, {"site": "UPPER"}, {"schema_version": 2}]
        for layer in bad:
            with self.assertRaises(K.ConfigInvalid, msg=layer):
                K.load_layers(layer)
        with self.assertRaises(K.ConfigInvalid): K.load_layers("/nonexistent.json")
        with self.assertRaises(K.ConfigInvalid): K.load_layers([1])
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{not json")
        with self.assertRaises(K.ConfigInvalid): K.load_layers(f.name)

    def test_errors_are_specific(self):
        try:
            K.load_layers({"stream": {"max_credit": -5}})
        except K.ConfigInvalid as e:
            self.assertTrue(any("max_credit" in m for m in e.details["errors"]))


class ActivationTest(unittest.TestCase):
    def test_provenance_and_rollback(self):
        audit = X.AuditLedger()
        m = K.ConfigManager(audit=audit)
        d0 = m.provenance.digest
        p = m.activate({"stream": {"max_credit": 8, "max_buffer": 8}}, author="ops@example", source_revision="abc123",
                       reason="tighten")
        self.assertEqual(p.author, "ops@example"); self.assertTrue(p.digest.startswith("sha256:"))
        self.assertEqual(m.current["stream"]["max_credit"], 8)
        self.assertEqual(set(p.as_dict()), {"author", "source_revision", "sources", "digest", "activated_at", "reason"})
        m.rollback(author="ops@example", reason="revert")
        self.assertEqual(m.provenance.digest, d0)
        with self.assertRaises(K.ActivationFailed): m.rollback(author="x", reason="nothing left")
        self.assertEqual([e.kind for e in audit.events], ["config.activate", "config.rollback"])

    def test_invalid_candidate_never_swaps(self):
        m = K.ConfigManager()
        before = m.current
        with self.assertRaises(K.ConfigInvalid):
            m.activate({"stream": {"max_credit": 0}}, author="a", source_revision="r", reason="x")
        with self.assertRaises(K.ConfigInvalid):
            m.activate({}, author="", source_revision="r", reason="x")
        self.assertEqual(m.current, before)

    def test_health_probe_failure_auto_rolls_back(self):
        m = K.ConfigManager()
        before = m.provenance.digest
        with self.assertRaises(K.ActivationFailed):
            m.activate({"stream": {"max_credit": 2, "max_buffer": 2}}, author="a", source_revision="r", reason="x",
                       health_probe=lambda cfg: False)
        self.assertEqual(m.provenance.digest, before)
        def boom(cfg): raise RuntimeError("probe crashed")
        with self.assertRaises(K.ActivationFailed):
            m.activate({}, author="a", source_revision="r", reason="x", health_probe=boom)
        self.assertEqual(m.provenance.digest, before)

    def test_readers_never_see_partial_config(self):
        m = K.ConfigManager()
        seen = set(); stop = threading.Event()
        def reader():
            while not stop.is_set():
                c = m.current["stream"]
                seen.add((c["max_credit"], c["max_buffer"]))
        t = threading.Thread(target=reader); t.start()
        for i in range(1, 60):
            m.activate({"stream": {"max_credit": i, "max_buffer": i}}, author="a", source_revision=str(i), reason="x")
        stop.set(); t.join()
        self.assertTrue(all(a == b for a, b in seen), "a reader observed a mixed configuration")

    def test_schema_file_is_valid_json_schema_shape(self):
        schema = json.loads((PKG_DIR / "config" / "stream-config.schema.json").read_text())
        self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
