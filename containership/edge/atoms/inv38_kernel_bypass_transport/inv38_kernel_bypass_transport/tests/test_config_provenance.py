from inv38_kernel_bypass_transport import config_provenance as cp
def _rec():
    return cp.ProvenanceRecord(config_id="c1", schema_version="config-provenance/1",
        semver="1.0.0", author="a", created_at="2026-09-22", environment="prod",
        source_revision="deadbeef", content={"ring_size": 8, "key": "SECRET"})
def test_secret_redacted_in_history():
    e = _rec().to_history_entry()
    assert e["content_redacted"]["key"] == "<redacted>"
    assert e["content_redacted"]["ring_size"] == 8
def test_digest_binds_content():
    r = _rec(); d = r.digest
    assert cp.detect_drift({"ring_size": 8, "key": "SECRET"}, {"ring_size": 9, "key": "SECRET"})
    assert not cp.detect_drift({"ring_size": 8}, {"ring_size": 8})
