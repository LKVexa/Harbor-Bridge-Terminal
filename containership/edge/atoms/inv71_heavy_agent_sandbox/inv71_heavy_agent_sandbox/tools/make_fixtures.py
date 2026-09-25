"""Generate the versioned conformance fixture bundle (C029, C082-IMP-04).

Runs one deterministic scenario through the reference controller with fake
adjacent layers (INV-69 router, INV-24 runtime/host observer, INV-26 snapshot
provider, GAP-09 observability sink) and writes:

  fixtures/valid/*.json      records every implementation must emit/accept
  fixtures/invalid/*.json    records every implementation must reject
  fixtures/golden/*.bin      canonical bytes for hashed/signed structures
  fixtures/MANIFEST.json     fixture version + sha256 of every file

Deterministic: fixed clock, fixed keys, fixed nonces.  Re-running must produce
byte-identical output (tests/test_conformance.py checks that).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
sys.path.insert(0, str(PKG / "tests"))

FIXTURE_VERSION = "1.0.0"


class FakeINV26Snapshots:
    """INV-26 stand-in: serves the one clean base snapshot digest."""
    def base_digest(self) -> str:
        from inv71_heavy_agent_sandbox.sandbox import BASE_DIGEST
        return BASE_DIGEST


class FakeGAP09Sink:
    """GAP-09 stand-in: collects egress/teardown records and metric exposition."""
    def __init__(self) -> None:
        self.records: list[dict] = []


class FakeINV69Router:
    """INV-69 stand-in: routes a high-risk tool call to the heavy sandbox."""
    def __init__(self, controller, ta) -> None:
        self.c, self.ta = controller, ta

    def run_tool(self, sid: str, host: str):
        from _harness import token
        from inv71_heavy_agent_sandbox.control.resilience import Shape
        s = self.c.create(token(self.ta, nonce=f"{sid}-c"), sid=sid, tenant="t1", shape=Shape(1, 512),
                          idempotency_key=f"idem-{sid}", correlation_id=f"corr-{sid}", release="tool@1.0.0")
        e = self.c.connect(token(self.ta, nonce=f"{sid}-e"), sid=sid, host=host, port=443)
        t = self.c.teardown(token(self.ta, nonce=f"{sid}-t"), sid=sid, epoch=s["epoch"])
        return s, e, t


def generate(out: pathlib.Path) -> dict[str, str]:
    import tempfile
    from _harness import build
    from inv71_heavy_agent_sandbox.control.config import canonical_bytes, merge
    from inv71_heavy_agent_sandbox.control.errors import REGISTRY, ControlError

    with tempfile.TemporaryDirectory() as d:
        c, ta, clock, res, host, anchors = build(d)
        sink = FakeGAP09Sink()
        router = FakeINV69Router(c, ta)
        s, e, t = router.run_tool("fx-1", "pypi.org")
        try:
            c.connect(__import__("_harness").token(ta, nonce="deny"), sid="fx-1", host="pypi.org", port=443)
        except ControlError:
            pass
        sink.records.extend(c.egress.decisions)
        status = c.status(privileged=True)
        assert_base = FakeINV26Snapshots().base_digest() == s["base_digest"]
        audit_lines = pathlib.Path(c.audit.path).read_text().splitlines()

    valid = {
        "session_v2.json": s,
        "teardown_v2.json": t,
        "egress_v2_allow.json": sink.records[0],
        "status_v1.json": status,
        "config_v1.json": {"schema": "PK_HEAVYBOX_CONFIG/1", "values": merge({})},
        "errors_v1.json": [ControlError(k).to_record(correlation_id="corr-x") for k in sorted(REGISTRY)],
        "audit_stream.jsonl.json": [json.loads(l) for l in audit_lines],
        "lifecycle_expected.json": ["VALIDATING", "ALLOCATING", "STARTING", "READY", "RUNNING", "DRAINING",
                                    "STOPPING", "VERIFYING_TEARDOWN", "CLOSED"],
        "adjacent_harness.json": {"INV-69": "FakeINV69Router.run_tool", "INV-24": "runtime_plan.plan_session + Host observer",
                                  "INV-26": "FakeINV26Snapshots.base_digest", "GAP-09": "FakeGAP09Sink",
                                  "base_digest_matches": assert_base},
    }
    invalid = {
        "session_v2_bad_state.json": {**s, "state": "RUNNING_FOREVER"},
        "session_v2_extra_field.json": {**s, "debug": True},
        "session_v2_bad_sid.json": {**s, "sid": "../etc"},
        "teardown_v2_unverified.json": {**t, "verified": False},
        "teardown_v2_leaked.json": {**t, "leaked": [["tap", "tapx"]]},
        "egress_v2_bad_decision.json": {**sink.records[0], "decision": "maybe"},
        "error_v1_bad_code.json": {**valid["errors_v1.json"][0], "code": "lower.case"},
        "status_v1_bad_state.json": {**status, "state": "FINE"},
    }
    golden = {
        "canonical_config.bin": canonical_bytes(valid["config_v1.json"]),
        "canonical_session.bin": canonical_bytes(s),
    }
    files: dict[str, bytes] = {}
    for k, v in valid.items():
        files[f"valid/{k}"] = (json.dumps(v, indent=2, sort_keys=True) + "\n").encode()
    for k, v in invalid.items():
        files[f"invalid/{k}"] = (json.dumps(v, indent=2, sort_keys=True) + "\n").encode()
    for k, v in golden.items():
        files[f"golden/{k}"] = v
    digests = {k: hashlib.sha256(v).hexdigest() for k, v in sorted(files.items())}
    manifest = {"schema": "PK_HEAVYBOX_FIXTURES/1", "fixture_version": FIXTURE_VERSION, "files": digests,
                "bundle_sha256": hashlib.sha256(canonical_bytes(digests)).hexdigest()}
    files["MANIFEST.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    for k, v in files.items():
        p = out / k
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(v)
    return digests


if __name__ == "__main__":
    generate(PKG / "fixtures")
    print("fixtures written")
