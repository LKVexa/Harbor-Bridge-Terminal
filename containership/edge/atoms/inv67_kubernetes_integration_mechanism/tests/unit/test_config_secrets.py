"""Config schema/provenance/atomic activation+rollback, secrets, bootstrap (items 18-22)."""
import json
import os
import tempfile
import unittest

import _support as S

C = S.config


class Config(unittest.TestCase):
    def test_defaults_valid_and_schema_conformant(self):
        cfg = C.validate({})
        schema = json.loads((S.PKG_DIR / "schemas/INV67_CONFIG_v1.schema.json").read_text())
        self.assertEqual(S.mod("schema").errors(schema, cfg), [])

    def test_rejections(self):
        bad = [{"nope": 1}, {"maxInflight": 0}, {"maxInflight": True}, {"retry": {"base": 5, "cap": 1}},
               {"retry": {"zzz": 1}}, {"downstream": {"endpoint": "http://plain"}},
               {"downstream": {"tokenSecretRef": "hunter2"}}, {"schema": "OTHER/1"},
               {"telemetry": {"logLevel": "loud"}}, {"leaseDurationSec": 1}, {"tenantInflight": {"a": -1}}]
        for b in bad:
            with self.subTest(b=b):
                with self.assertRaises(C.ConfigError):
                    C.validate(b)

    def test_atomic_activation_provenance_and_rollback(self):
        log = S.audit.AuditLog()
        st = C.ConfigStore({}, audit=log)
        d0 = C.digest(st.active)
        with self.assertRaises(C.ConfigError):
            st.activate({"maxInflight": -5}, source="cm/v2", activator="alice")
        self.assertEqual(C.digest(st.active), d0)       # untouched on failure
        with self.assertRaises(C.ConfigError):
            st.activate({"maxInflight": 5}, source="cm/v3", activator="alice", probe=lambda c: False)
        self.assertEqual(C.digest(st.active), d0)
        rec = st.activate({"maxInflight": 5}, source="cm/v4", activator="alice")
        self.assertEqual(rec.previous, d0)
        self.assertEqual(st.active["maxInflight"], 5)
        st.rollback(activator="bob")
        self.assertEqual(C.digest(st.active), d0)
        self.assertEqual([h.result.split(":")[0] for h in st.history],
                         ["activated", "rejected", "rejected", "activated", "rolled-back"])
        self.assertTrue(S.audit.AuditLog.verify(log.records)[0])


class Secrets(unittest.TestCase):
    def test_memory_and_redaction(self):
        p = S.secrets.MemorySecretProvider({"tok": "s3cr3t"})
        s = p.get("secretRef:tok")
        self.assertEqual(s.reveal(), "s3cr3t")
        self.assertNotIn("s3cr3t", repr(s) + str(s))
        with self.assertRaises(S.secrets.SecretError):
            p.get("secretRef:missing")
        for bad in ("tok", "secretRef:../etc/passwd", "secretRef:UPPER", None):
            with self.assertRaises(S.secrets.SecretError):
                p.get(bad)

    def test_file_provider_permissions_and_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "tok")
            with open(path, "w") as fh:
                fh.write("v\n")
            os.chmod(path, 0o600)
            fp = S.secrets.FileSecretProvider(d)
            self.assertEqual(fp.get("secretRef:tok").reveal(), "v")
            os.chmod(path, 0o644)
            with self.assertRaises(S.secrets.SecretError):
                fp.get("secretRef:tok")


class Bootstrap(unittest.TestCase):
    def test_ordered_fail_fast_and_success(self):
        B = S.mod("bootstrap")
        with tempfile.TemporaryDirectory() as d:
            cfgp = os.path.join(d, "c.json")
            S.write_json(cfgp, {"downstream": {"endpoint": ""}})
            rec = B.run(cfgp, secret_root=None, state_dir=d)
            self.assertFalse(rec["ok"])
            self.assertEqual(rec["steps"][-1]["name"], "downstream-endpoint")
            S.write_json(cfgp, {"downstream": {"endpoint": "https://sch01.example", "tokenSecretRef": "secretRef:tok"}})
            sec = os.path.join(d, "sec"); os.mkdir(sec)
            with open(os.path.join(sec, "tok"), "w") as fh:
                fh.write("x")
            os.chmod(os.path.join(sec, "tok"), 0o600)
            rec = B.run(cfgp, secret_root=sec, state_dir=d)
            self.assertTrue(rec["ok"], rec)
            self.assertEqual([s["name"] for s in rec["steps"]], list(B.STEPS))
            self.assertNotIn('"x"', json.dumps(rec))
            rec2 = B.run(cfgp, secret_root=sec, state_dir=d)
            self.assertEqual(rec["digest"], rec2["digest"])   # deterministic


if __name__ == "__main__":
    unittest.main()
