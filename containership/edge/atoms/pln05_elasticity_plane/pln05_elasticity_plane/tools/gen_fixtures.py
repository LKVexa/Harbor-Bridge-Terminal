"""Generate the immutable protocol fixture corpus (MC-08).

Run once per schema version; the output is committed and its manifest pins a
sha256 per file.  ``tests/contract/test_fixtures.py`` fails if any fixture is
edited without regenerating the manifest.  Timestamps are expressed relative to
``now`` via the ``x-fixture-age-s`` extension so fixtures stay valid forever:
the harness substitutes ``observed_at = now - age``.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "protocol"


def demand(**kw):
    base = {"schema": "PK_DEMAND/1", "message_id": "msg-00000001", "tenant": "t1", "site": "dub",
            "workload": "w1", "source": "r1", "seq": 1, "observed_at": "@now", "utilisation": 0.5}
    base.update(kw)
    return base


def limits(**kw):
    base = {"schema": "PK_CAPACITY_LIMITS/1", "revision": 1, "tenant": "t1", "site": "dub",
            "workload": "w1", "floor": 0, "ceiling": 8, "scale_up_at": 0.75, "scale_down_at": 0.25,
            "grace_samples": 3, "issuer": "intent_plane-1", "issued_at": "@now"}
    base.update(kw)
    return base


def target(**kw):
    base = {"schema": "PK_CAPACITY_TARGET/1", "decision_id": "dec-00000001", "tenant": "t1",
            "site": "dub", "workload": "w1", "target": 4, "previous": 2, "outcome": "scale-up",
            "reason_code": "R_SCALE_UP", "reason": "scale-up", "floor": 0, "ceiling": 8, "epoch": 1,
            "fencing_token": 1, "config_checksum": "0" * 64, "demand_message_id": "msg-00000001",
            "decided_at": "@now"}
    base.update(kw)
    return base


def drop(d, k):
    d = dict(d)
    d.pop(k)
    return d


VALID = {
    "demand_nominal": ("PK_DEMAND", demand()),
    "demand_zero_load": ("PK_DEMAND", demand(utilisation=0)),
    "demand_max": ("PK_DEMAND", demand(utilisation=1000, confidence=1)),
    "demand_oversubscribed": ("PK_DEMAND", demand(utilisation=1.7)),
    "demand_min_ids": ("PK_DEMAND", demand(tenant="a", site="b", workload="c", source="d", message_id="abcdefgh")),
    "demand_with_trace": ("PK_DEMAND", demand(traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01", correlation_id="corr-0001")),
    "demand_forward_extension": ("PK_DEMAND", dict(demand(), **{"x-vendor-hint": {"burst": True}})),
    "limits_nominal": ("PK_CAPACITY_LIMITS", limits()),
    "limits_scale_to_zero": ("PK_CAPACITY_LIMITS", limits(floor=0, ceiling=0)),
    "limits_floor_equals_ceiling": ("PK_CAPACITY_LIMITS", limits(floor=5, ceiling=5)),
    "limits_max": ("PK_CAPACITY_LIMITS", limits(ceiling=1000000, grace_samples=1000)),
    "target_nominal": ("PK_CAPACITY_TARGET", target()),
    "target_at_floor": ("PK_CAPACITY_TARGET", target(target=0, previous=0, outcome="constrained-hold", reason_code="R_AT_FLOOR")),
    "target_at_ceiling": ("PK_CAPACITY_TARGET", target(target=8, previous=8, outcome="constrained-hold", reason_code="R_AT_CEILING")),
}

INVALID = {
    # (family, payload-or-raw-string, expected code, side effect)
    "demand_missing_" + k: ("PK_DEMAND", drop(demand(), k), "E_SCHEMA_FIELD" if k != "schema" else "E_SCHEMA_VERSION")
    for k in ["schema", "message_id", "tenant", "site", "workload", "source", "seq", "observed_at", "utilisation"]
}
INVALID.update({
    "limits_missing_" + k: ("PK_CAPACITY_LIMITS", drop(limits(), k), "E_SCHEMA_FIELD")
    for k in ["revision", "tenant", "site", "workload", "floor", "ceiling", "scale_up_at", "scale_down_at", "grace_samples", "issuer", "issued_at"]
})
INVALID.update({
    "target_missing_" + k: ("PK_CAPACITY_TARGET", drop(target(), k), "E_SCHEMA_FIELD")
    for k in ["decision_id", "target", "outcome", "reason_code", "epoch", "fencing_token", "config_checksum"]
})
INVALID.update({
    "demand_util_negative": ("PK_DEMAND", demand(utilisation=-0.1), "E_SCHEMA_FIELD"),
    "demand_util_too_large": ("PK_DEMAND", demand(utilisation=1000.5), "E_SCHEMA_FIELD"),
    "demand_util_string": ("PK_DEMAND", demand(utilisation="0.5"), "E_SCHEMA_FIELD"),
    "demand_util_bool": ("PK_DEMAND", demand(utilisation=True), "E_SCHEMA_FIELD"),
    "demand_seq_float": ("PK_DEMAND", demand(seq=1.5), "E_SCHEMA_FIELD"),
    "demand_seq_negative": ("PK_DEMAND", demand(seq=-1), "E_SCHEMA_FIELD"),
    "demand_confidence_high": ("PK_DEMAND", demand(confidence=1.01), "E_SCHEMA_FIELD"),
    "demand_tenant_uppercase": ("PK_DEMAND", demand(tenant="T1"), "E_SCHEMA_FIELD"),
    "demand_tenant_path": ("PK_DEMAND", demand(tenant="../t2"), "E_SCHEMA_FIELD"),
    "demand_tenant_too_long": ("PK_DEMAND", demand(tenant="a" * 65), "E_SCHEMA_FIELD"),
    "demand_message_id_short": ("PK_DEMAND", demand(message_id="abc"), "E_SCHEMA_FIELD"),
    "demand_bad_traceparent": ("PK_DEMAND", demand(traceparent="01-xyz"), "E_SCHEMA_FIELD"),
    "demand_unknown_version": ("PK_DEMAND", demand(schema="PK_DEMAND/2"), "E_SCHEMA_VERSION"),
    "demand_wrong_family": ("PK_DEMAND", demand(schema="PK_CAPACITY_LIMITS/1"), "E_SCHEMA_VERSION"),
    "demand_unknown_critical_field": ("PK_DEMAND", demand(priority=9), "E_SCHEMA_UNKNOWN_CRITICAL"),
    "demand_observed_negative": ("PK_DEMAND", demand(observed_at=-1), "E_SCHEMA_FIELD"),
    "limits_floor_gt_ceiling": ("PK_CAPACITY_LIMITS", limits(floor=9, ceiling=8), "E_SCHEMA_FIELD"),
    "limits_thresholds_inverted": ("PK_CAPACITY_LIMITS", limits(scale_up_at=0.2, scale_down_at=0.6), "E_SCHEMA_FIELD"),
    "limits_threshold_one": ("PK_CAPACITY_LIMITS", limits(scale_up_at=1.0), "E_SCHEMA_FIELD"),
    "limits_threshold_zero": ("PK_CAPACITY_LIMITS", limits(scale_down_at=0), "E_SCHEMA_FIELD"),
    "limits_negative_floor": ("PK_CAPACITY_LIMITS", limits(floor=-1), "E_SCHEMA_FIELD"),
    "limits_ceiling_too_large": ("PK_CAPACITY_LIMITS", limits(ceiling=1000001), "E_SCHEMA_FIELD"),
    "limits_ceiling_float": ("PK_CAPACITY_LIMITS", limits(ceiling=8.0), "E_SCHEMA_FIELD"),
    "limits_grace_zero": ("PK_CAPACITY_LIMITS", limits(grace_samples=0), "E_SCHEMA_FIELD"),
    "limits_revision_zero": ("PK_CAPACITY_LIMITS", limits(revision=0), "E_SCHEMA_FIELD"),
    "target_outside_envelope": ("PK_CAPACITY_TARGET", target(target=9), "E_SCHEMA_FIELD"),
    "target_bad_outcome": ("PK_CAPACITY_TARGET", target(outcome="scale-sideways"), "E_SCHEMA_FIELD"),
    "target_bad_reason_code": ("PK_CAPACITY_TARGET", target(reason_code="scale up"), "E_SCHEMA_FIELD"),
    "target_bad_checksum": ("PK_CAPACITY_TARGET", target(config_checksum="xyz"), "E_SCHEMA_FIELD"),
    "raw_nan": ("PK_DEMAND", '{"schema":"PK_DEMAND/1","message_id":"msg-00000001","tenant":"t1","site":"dub","workload":"w1","source":"r1","seq":1,"observed_at":"@now","utilisation":NaN}', "E_SCHEMA_MALFORMED"),
    "raw_infinity": ("PK_DEMAND", '{"schema":"PK_DEMAND/1","message_id":"msg-00000001","tenant":"t1","site":"dub","workload":"w1","source":"r1","seq":1,"observed_at":"@now","utilisation":Infinity}', "E_SCHEMA_MALFORMED"),
    "raw_duplicate_key": ("PK_DEMAND", '{"schema":"PK_DEMAND/1","utilisation":0.1,"utilisation":0.9}', "E_SCHEMA_MALFORMED"),
    "raw_not_object": ("PK_DEMAND", '[1,2,3]', "E_SCHEMA_MALFORMED"),
    "raw_truncated": ("PK_DEMAND", '{"schema":"PK_DEMAND/1",', "E_SCHEMA_MALFORMED"),
    "raw_deep_nesting": ("PK_DEMAND", '{"x-a":' * 50 + '1' + '}' * 50, "E_SCHEMA_TOO_DEEP"),
    "raw_oversized": ("PK_DEMAND", '{"x-pad":"' + "a" * 17000 + '"}', "E_SCHEMA_TOO_LARGE"),
    "raw_invalid_utf8": ("PK_DEMAND", "b64:/w==", "E_SCHEMA_MALFORMED"),
})

# Sequences exercised against a live plane (boundary + ordering semantics).
SEQUENCES = {
    "stale_timestamp": {"messages": [{"age_s": 31}], "expect": ["E_STALE_INPUT"]},
    "future_skew": {"messages": [{"age_s": -6}], "expect": ["E_FUTURE_SKEW"]},
    "duplicate_message": {"messages": [{"message_id": "dup-00000001", "seq": 1}, {"message_id": "dup-00000001", "seq": 2}], "expect": ["OK", "E_DUPLICATE"]},
    "reordered_sequence": {"messages": [{"seq": 5}, {"seq": 4}], "expect": ["OK", "E_OUT_OF_ORDER"]},
    "replayed_after_restart_window": {"messages": [{"seq": 7, "message_id": "rep-00000007"}, {"seq": 7, "message_id": "rep-00000007"}], "expect": ["OK", "E_DUPLICATE"]},
    "wrong_tenant_credential": {"messages": [{"tenant": "t2"}], "expect": ["E_AUTHZ_SCOPE"]},
    "wrong_site_credential": {"messages": [{"site": "ams"}], "expect": ["E_AUTHZ_SCOPE"]},
    "spoofed_source": {"messages": [{"source": "r9"}], "expect": ["E_AUTHZ_SCOPE"]},
}


def main() -> None:
    manifest = {"schema_versions": {"PK_DEMAND": 1, "PK_CAPACITY_LIMITS": 1, "PK_CAPACITY_TARGET": 1},
                "valid": {}, "invalid": {}, "sequences": {}}
    for sub in ("valid", "invalid", "sequences"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    for name, (fam, body) in VALID.items():
        data = (json.dumps(body, indent=1, sort_keys=True) + "\n").encode()
        (OUT / "valid" / f"{name}.json").write_bytes(data)
        manifest["valid"][name] = {"family": fam, "expect": "OK", "side_effect": "none (decode only)",
                                   "sha256": hashlib.sha256(data).hexdigest()}
    for name, (fam, body, code) in INVALID.items():
        if isinstance(body, str):
            data = body.encode()
            ext = "raw"
        else:
            data = (json.dumps(body, indent=1, sort_keys=True) + "\n").encode()
            ext = "json"
        (OUT / "invalid" / f"{name}.{ext}").write_bytes(data)
        manifest["invalid"][name] = {"family": fam, "file": f"{name}.{ext}", "expect": code,
                                     "side_effect": "rejected before any state mutation",
                                     "sha256": hashlib.sha256(data).hexdigest()}
    for name, seq in SEQUENCES.items():
        data = (json.dumps(seq, indent=1, sort_keys=True) + "\n").encode()
        (OUT / "sequences" / f"{name}.json").write_bytes(data)
        manifest["sequences"][name] = {"sha256": hashlib.sha256(data).hexdigest(), "expect": seq["expect"]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"valid={len(VALID)} invalid={len(INVALID)} sequences={len(SEQUENCES)}")


if __name__ == "__main__":
    main()
