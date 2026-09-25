"""Generate machine-readable artifacts from the code that enforces them.

Writes: schemas/*.schema.json, ERRORS.json, ops/lifecycle.json, ops/policy.json,
ops/metrics.json, examples/*.json, tests/fixtures/conformance/cases.json.
Tests fail if any of these drift from the code (tests/test_security_units.py,
tools/rtm.py). Run: ``python -m inv26_microvm_snapshotting.tools.gen_artifacts``.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from .. import config, errors, lifecycle, policy, schema, telemetry

PKG = Path(__file__).resolve().parents[1]
HEX = "a" * 64


def dump(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def capture_req(**o):
    d = {"schema": "PK_SNAPSHOT_CAPTURE_REQUEST/2", "snapshot_id": "s1", "tenant": "t1", "workload": "w1",
         "environment": "prod", "devices": ["virtio-block", "virtio-net"], "memory_mib": 256, "vm_id": "vm-1",
         "idempotency_key": "idem-0001"}
    d.update(o)
    return d


def restore_req(**o):
    d = {"schema": "PK_SNAPSHOT_RESTORE_REQUEST/2", "snapshot_id": "s1", "tenant": "t1", "workload": "w1",
         "environment": "prod", "devices": ["virtio-block", "virtio-net"], "target_vm_id": "vm-2",
         "grant": "<compact EdDSA grant>", "idempotency_key": "idem-0002"}
    d.update(o)
    return d


def manifest(**o):
    d = {"schema": "PK_SNAPSHOT_MANIFEST/1", "snapshot_id": "s1", "tenant": "t1", "workload": "w1",
         "environment": "prod", "site": "site-a", "fingerprint": HEX, "memory_mib": 256,
         "runtime": {"adapter": "firecracker", "version": "1.9", "arch": "x86_64"}, "capture_schema": "PK_SNAPSHOT/2",
         "generation": 1, "created_at": 1790000000000,
         "envelope": {"alg": "AES-256-GCM-CHUNKED/1", "key_id": "inv26-kek", "key_version": 1,
                      "wrapped_dek": "base64...", "chunk_size": 1048576, "chunks": 256,
                      "ciphertext_sha256": HEX, "plaintext_bytes": 268435456, "aad_schema": "PK_SNAPSHOT_AAD/1"}}
    d.update(o)
    return d


def restore_resp(**o):
    d = {"schema": "PK_SNAPSHOT_RESTORE/2", "snapshot_id": "s1", "tenant": "t1", "workload": "w1",
         "environment": "prod", "operation_id": "op-1", "restore_ms": 4.2, "budget_ms": 10.0, "within_budget": True,
         "entropy_reseeded": True, "entropy_proof_sha256": HEX, "state": "READY", "outcome": "success"}
    d.update(o)
    return d


def cases() -> list[dict]:
    C = []
    def add(name, sid, doc, valid):
        C.append({"name": name, "schema": sid, "doc": doc, "valid": valid})
    add("capture-minimal", "PK_SNAPSHOT_CAPTURE_REQUEST/2", capture_req(), True)
    add("capture-complete", "PK_SNAPSHOT_CAPTURE_REQUEST/2",
        capture_req(site="site-a", deadline_ms=5000, traceparent="00-" + "1" * 32 + "-" + "2" * 16 + "-01"), True)
    add("capture-duplicate-devices", "PK_SNAPSHOT_CAPTURE_REQUEST/2", capture_req(devices=["a", "a"]), False)
    add("capture-string-devices", "PK_SNAPSHOT_CAPTURE_REQUEST/2", capture_req(devices="virtio-net"), False)
    add("capture-empty-devices", "PK_SNAPSHOT_CAPTURE_REQUEST/2", capture_req(devices=[]), False)
    add("capture-malformed-id", "PK_SNAPSHOT_CAPTURE_REQUEST/2", capture_req(tenant="../t2"), False)
    add("capture-uppercase-id", "PK_SNAPSHOT_CAPTURE_REQUEST/2", capture_req(snapshot_id="S1"), False)
    add("capture-bool-memory", "PK_SNAPSHOT_CAPTURE_REQUEST/2", capture_req(memory_mib=True), False)
    add("capture-zero-memory", "PK_SNAPSHOT_CAPTURE_REQUEST/2", capture_req(memory_mib=0), False)
    add("capture-unknown-field", "PK_SNAPSHOT_CAPTURE_REQUEST/2", capture_req(skip_checks=True), False)
    add("capture-old-schema", "PK_SNAPSHOT_CAPTURE_REQUEST/2", capture_req(schema="PK_SNAPSHOT_CAPTURE_REQUEST/1"), False)
    add("restore-minimal", "PK_SNAPSHOT_RESTORE_REQUEST/2", restore_req(), True)
    add("restore-missing-grant", "PK_SNAPSHOT_RESTORE_REQUEST/2",
        {k: v for k, v in restore_req().items() if k != "grant"}, False)
    add("restore-cross-tenant-shape-valid", "PK_SNAPSHOT_RESTORE_REQUEST/2", restore_req(tenant="t2"), True)
    add("restore-short-idem", "PK_SNAPSHOT_RESTORE_REQUEST/2", restore_req(idempotency_key="x"), False)
    add("restore-deadline-too-long", "PK_SNAPSHOT_RESTORE_REQUEST/2", restore_req(deadline_ms=10 ** 6), False)
    add("manifest-valid", "PK_SNAPSHOT_MANIFEST/1", manifest(), True)
    add("manifest-bad-fingerprint", "PK_SNAPSHOT_MANIFEST/1", manifest(fingerprint="abc"), False)
    add("manifest-weak-alg", "PK_SNAPSHOT_MANIFEST/1",
        manifest(envelope=dict(manifest()["envelope"], alg="AES-128-CBC")), False)
    add("manifest-unknown-adapter", "PK_SNAPSHOT_MANIFEST/1",
        manifest(runtime={"adapter": "qemu", "version": "8", "arch": "x86_64"}), False)
    add("restore-response-valid", "PK_SNAPSHOT_RESTORE/2", restore_resp(), True)
    add("restore-response-no-reseed", "PK_SNAPSHOT_RESTORE/2", restore_resp(entropy_reseeded=False), False)
    add("restore-response-not-ready", "PK_SNAPSHOT_RESTORE/2", restore_resp(state="RESEEDING"), False)
    add("restore-response-nan-ms", "PK_SNAPSHOT_RESTORE/2", restore_resp(restore_ms=float("inf")), False)
    add("error-valid", "PK_SNAPSHOT_ERROR/1",
        {"schema": "PK_SNAPSHOT_ERROR/1", "code": "SNAP_TENANT_MISMATCH", "number": 1101,
         "outcome": "policy_rejection", "retryable": False, "message": "restore refused by security boundary",
         "correlation_id": "c1"}, True)
    add("error-leaks-extra-field", "PK_SNAPSHOT_ERROR/1",
        {"schema": "PK_SNAPSHOT_ERROR/1", "code": "SNAP_INTERNAL", "number": 9999, "outcome": "terminal_failure",
         "retryable": False, "message": "internal error", "correlation_id": "c1", "traceback": "..."}, False)
    return [c for c in C if c["name"] != "restore-response-nan-ms"] + [
        {"name": "restore-response-negative-ms", "schema": "PK_SNAPSHOT_RESTORE/2",
         "doc": restore_resp(restore_ms=-1), "valid": False}]


def main() -> None:
    schema.write_schema_files(PKG / "schemas")
    dump(PKG / "ERRORS.json", errors.catalog_document())
    dump(PKG / "ops" / "lifecycle.json", lifecycle.model_document())
    dump(PKG / "ops" / "policy.json", policy.document())
    dump(PKG / "ops" / "metrics.json", {"schema": "PK_SNAPSHOT_METRICS_CATALOG/1",
                                         "metrics": {k: {"type": t, "unit": u, "labels": l}
                                                     for k, (t, u, l) in telemetry.METRICS.items()},
                                         "max_series_per_metric": telemetry.MAX_SERIES_PER_METRIC})
    prod = config.example()
    dump(PKG / "examples" / "config.production.json", prod)
    strict = copy.deepcopy(prod)
    strict.update({"tier": "far-edge", "quotas": dict(prod["quotas"], max_snapshots_per_tenant=10,
                                                      max_bytes_per_tenant=8 << 30, max_memory_mib=2048, max_devices=8),
                   "admission": {"max_inflight": 4, "max_queue": 4, "per_tenant": 1, "tenant_rate_per_s": 1.0,
                                 "tenant_burst": 2.0},
                   "telemetry": {"log_level": "warning", "trace_sample_ratio": 0.01}})
    dump(PKG / "examples" / "config.restrictive.json", strict)
    for c in cases():
        if c["valid"]:
            dump(PKG / "examples" / f"{c['name']}.json", c["doc"])
    dump(PKG / "tests" / "fixtures" / "conformance" / "cases.json", cases())


if __name__ == "__main__":
    main()
