"""Dependency-free unit and adversarial tests for the hardened reference model."""
import json
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv71_heavy_agent_sandbox.sandbox import (  # noqa: E402
    BASE,
    BASE_DIGEST,
    EgressDenied,
    LimitExceeded,
    SessionClosed,
    canonicalize_host,
    digest,
    new_session,
)


class SandboxModelTest(unittest.TestCase):
    def test_clean_snapshot_isolation(self):
        first = new_session("s1")
        first.write("/tmp/private", b"secret")
        record = first.teardown()
        second = new_session("s2")
        self.assertTrue(record["verified"])
        self.assertTrue(record["audit_chain_valid"])
        self.assertNotIn("/tmp/private", second.fs)
        self.assertEqual(digest(second.fs), BASE_DIGEST)

    def test_digest_serialization_is_unambiguous(self):
        left = {"a": b"bc", "d": b"e"}
        right = {"a": b"b", "cd": b"e"}
        self.assertNotEqual(digest(left), digest(right))

    def test_base_snapshot_is_immutable(self):
        with self.assertRaises(TypeError):
            BASE["/tmp/mutate"] = b"x"  # type: ignore[index]

    def test_path_validation_rejects_escape_and_aliases(self):
        s = new_session("paths")
        for path in ("../escape", "relative", "/a/../b", "/a/./b", "/a//b", "/"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                s.write(path, b"x")

    def test_quota_update_is_atomic(self):
        s = new_session("quota", disk_quota=1000)
        s.write("/work/a", b"x" * 600)
        with self.assertRaises(LimitExceeded):
            s.write("/work/b", b"x" * 600)
        self.assertNotIn("/work/b", s.fs)
        self.assertEqual(len(s.fs["/work/a"]), 600)

    def test_file_quota(self):
        s = new_session("files", file_quota=1)
        s.write("/work/a", b"a")
        with self.assertRaises(LimitExceeded):
            s.write("/work/b", b"b")

    def test_egress_is_canonicalized_and_fail_closed(self):
        s = new_session("egress", allow=["PyPI.org."])
        s.connect("pypi.ORG")
        self.assertEqual(s.connections, ["pypi.org"])
        with self.assertRaises(EgressDenied):
            s.connect("example.com")
        for invalid in ("https://pypi.org", "pypi.org:443", " pypi.org"):
            with self.subTest(host=invalid), self.assertRaises(ValueError):
                canonicalize_host(invalid)

    def test_teardown_clears_guest_state_and_capabilities(self):
        s = new_session("teardown", allow=["pypi.org"])
        try:
            s.connect("blocked.example")
        except EgressDenied:
            pass
        record = s.teardown()
        self.assertTrue(record["verified"])
        self.assertEqual(s.fs, {})
        self.assertEqual(s.connections, [])
        self.assertEqual(s.denied, [])
        self.assertEqual(s.egress_allow, frozenset())
        with self.assertRaises(SessionClosed):
            s.write("/tmp/no", b"x")
        with self.assertRaises(SessionClosed):
            s.connect("pypi.org")

    def test_invalid_session_ids_and_limits_fail_closed(self):
        for sid in ("", "bad id", "/bad"):
            with self.subTest(sid=sid), self.assertRaises(ValueError):
                new_session(sid)
        with self.assertRaises(ValueError):
            new_session("limits", disk_quota=0)

    def test_audit_chain_detects_tampering(self):
        s = new_session("audit", allow=["pypi.org"])
        s.write("/tmp/a", b"x")
        s.connect("pypi.org")
        self.assertTrue(s.verify_audit_chain())
        event = s.audit[-1]
        object.__setattr__(event, "detail", "tampered")
        self.assertFalse(s.verify_audit_chain())

    def test_bounded_connection_history(self):
        s = new_session("bounded", allow=["pypi.org"], log_limit=2)
        for _ in range(4):
            s.connect("pypi.org")
        self.assertEqual(len(s.connections), 2)

    def test_teardown_record_matches_declared_required_schema_fields(self):
        schema = json.loads((PKG_DIR / "schemas" / "PK_HEAVYBOX_TEARDOWN_v1.schema.json").read_text())
        record = new_session("schema").teardown()
        self.assertTrue(set(schema["required"]).issubset(record))


if __name__ == "__main__":
    unittest.main()
