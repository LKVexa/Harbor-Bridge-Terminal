"""Generate schemas/*.schema.json (the typed public contracts). Deterministic; CI checks drift."""
import json
import pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
ID = r"^[A-Za-z0-9][A-Za-z0-9_.:@\-]{0,127}$"
HEX = r"^[0-9a-f]{64}$"
S = lambda **k: {"type": "string", **k}
IDS = S(pattern=ID)
def obj(props, req=None, extra=False, **k):
    return {"type": "object", "properties": props, "required": req if req is not None else sorted(props), "additionalProperties": extra, **k}
def doc(name, version, body, compat="additive-minor"):
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"urn:pk:inv66:{name}", "title": name,
            "x-version": version, "x-compat": compat, **body}

component = obj({"name": IDS,
                 "image": S(minLength=3, maxLength=2048, pattern=r"^[a-z0-9.\-:]+/[^\s@]+(@sha256:[0-9a-f]{64})?(:[^\s@/]+)?$"),
                 "signer": S(minLength=1, maxLength=512),
                 "signature": S(maxLength=4096),
                 "attestation": {"$ref": "#/$defs/statement"}},
                req=["name", "image", "signer"])
statement = obj({"schema": {"const": "PK_ECP_ARTIFACT_STATEMENT/1"}, "subject_digest": S(pattern=HEX),
                 "builder": S(maxLength=512), "source_repo": S(maxLength=2048), "source_rev": S(maxLength=128),
                 "sbom_digest": S(pattern=HEX), "signer": S(maxLength=512), "signature": S(maxLength=4096)},
                req=["schema", "subject_digest", "builder", "signer", "signature"])
schemas = {
"PK_ECP_ADMIT_REQUEST_1": doc("PK_ECP_ADMIT/1 request", "1.0.0", {**obj({
    "protocol": {"enum": ["PK_ECP_ADMIT/1"]}, "request_id": IDS, "idempotency_key": IDS,
    "tenant": IDS, "lattice": IDS, "deadline_ms": {"type": "integer", "minimum": 1, "maximum": 600000},
    "dry_run": {"type": "boolean"}, "traceparent": S(pattern=r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$"),
    "manifest": obj({"components": {"type": "array", "minItems": 1, "maxItems": 10000, "items": {"$ref": "#/$defs/component"}},
                     "app": IDS, "version": S(maxLength=128), "source": obj({"repo": S(maxLength=2048), "rev": S(maxLength=128), "path": S(maxLength=1024)}, req=["repo", "rev"])},
                    req=["components"])}, req=["protocol", "request_id", "tenant", "lattice", "manifest"]),
    "$defs": {"component": component, "statement": statement}}),
"PK_ECP_ADMIT_DECISION_1": doc("PK_ECP_ADMIT/1 decision", "1.0.0", obj({
    "protocol": {"const": "PK_ECP_ADMIT/1"}, "request_id": IDS, "decision_id": S(pattern=r"^dec-[0-9a-f]{32}$"),
    "admitted": {"type": "boolean"}, "state": {"enum": ["admitted", "rejected", "delivered", "delivery_pending", "dry_run"]},
    "tenant": IDS, "lattice": IDS, "principal": {"type": "object"},
    "reasons": {"type": "array", "items": obj({"code": S(pattern=r"^ECP_[A-Z_]+$"), "message": S(), "details": {"type": "object"}})},
    "manifest_sha256": {"type": ["string", "null"]}, "config_generation": S(pattern=HEX),
    "audit_seq": {"type": "integer", "minimum": 0}, "trace_id": S(pattern=r"^[0-9a-f]{32}$"),
    "latency_ms": {"type": "number", "minimum": 0}, "idempotent_replay": {"type": "boolean"}},
    req=["protocol", "request_id", "decision_id", "admitted", "state", "reasons", "config_generation", "audit_seq"])),
"PK_ECP_RBAC_REQUEST_1": doc("PK_ECP_RBAC/1 request", "1.0.0", {"oneOf": [
    obj({"protocol": {"const": "PK_ECP_RBAC/1"}, "op": {"enum": ["bind", "unbind"]}, "request_id": IDS,
         "binding": {"$ref": "#/$defs/binding"}, "if_revision": {"type": "integer", "minimum": 0},
         "reason": S(maxLength=256)}, req=["protocol", "op", "request_id", "binding"]),
    obj({"protocol": {"const": "PK_ECP_RBAC/1"}, "op": {"const": "list"}, "request_id": IDS, "scope": S(maxLength=512)}, req=["protocol", "op", "request_id"]),
    obj({"protocol": {"const": "PK_ECP_RBAC/1"}, "op": {"const": "check"}, "request_id": IDS,
         "subject": IDS, "capability": IDS, "scope": S(maxLength=512)})],
    "$defs": {"binding": {"$ref": "#/$defs/_b"}, "_b": None}}),
"PK_ECP_AUDIT_RECORD_2": doc("PK_ECP_AUDIT/2 record", "2.0.0", obj({
    "schema": {"const": "PK_ECP_AUDIT/2"}, "seq": {"type": "integer", "minimum": 1}, "prev": S(pattern=HEX), "hash": S(pattern=HEX),
    "ts": {"type": "number"}, "kind": S(pattern=r"^[a-z]+(\.[a-z_]+)*$"), "body": {"type": "object"},
    "sealed": obj({"alg": {"const": "AES-256-GCM"}, "kid": IDS, "n": S(), "ct": S()})},
    req=["schema", "seq", "prev", "hash", "ts", "kind"]), compat="major-bump-on-any-change"),
"PK_ECP_AUDIT_QUERY_1": doc("PK_ECP_AUDIT/1 query", "1.0.0", obj({
    "protocol": {"const": "PK_ECP_AUDIT/1"}, "request_id": IDS, "kind": S(maxLength=64), "tenant": IDS, "lattice": IDS,
    "outcome": {"type": "boolean"}, "from_seq": {"type": "integer", "minimum": 1}, "to_seq": {"type": "integer", "minimum": 1},
    "from_ts": {"type": "number"}, "to_ts": {"type": "number"}, "subject": S(maxLength=256), "request_ref": IDS,
    "decision_id": S(pattern=r"^dec-[0-9a-f]{32}$"),
    "limit": {"type": "integer", "minimum": 1, "maximum": 10000}}, req=["protocol", "request_id"])),
"PK_ECP_ERROR_1": doc("PK_ECP_ERROR/1", "1.0.0", obj({
    "schema": {"const": "PK_ECP_ERROR/1"}, "code": S(pattern=r"^ECP_[A-Z_]+$"), "wire": {"type": "integer"},
    "category": {"enum": ["input", "policy", "security", "auth", "resource", "dependency", "internal", "compatibility"]},
    "severity": {"enum": ["low", "medium", "high", "critical"]}, "retryable": {"type": "boolean"}, "http": {"type": "integer"},
    "message": S(maxLength=1024), "guidance": S(maxLength=1024), "details": {"type": "object"}, "request_id": IDS},
    req=["schema", "code", "wire", "category", "severity", "retryable", "http", "message", "guidance", "details"])),
"PK_ECP_CONFIG_1": doc("PK_ECP_CONFIG/1", "1.0.0", {**obj({
    "schema": {"const": "PK_ECP_CONFIG/1"}, "environment": {"enum": ["dev", "staging", "prod"]}, "site": IDS, "org": IDS,
    "limits": obj({"max_components": {"type": "integer", "minimum": 1, "maximum": 10000},
                   "max_manifest_bytes": {"type": "integer", "minimum": 1024, "maximum": 100000000},
                   "default_deadline_ms": {"type": "integer", "minimum": 1, "maximum": 600000},
                   "max_inflight": {"type": "integer", "minimum": 1, "maximum": 100000},
                   "audit_segment_records": {"type": "integer", "minimum": 10, "maximum": 10000000},
                   "retention_days": {"type": "integer", "minimum": 1, "maximum": 3650}}),
    "quotas": obj({"default": {"$ref": "#/$defs/quota"}, "tenants": {"type": "object", "additionalProperties": {"$ref": "#/$defs/quota"}}}, req=["default"]),
    "roles": {"type": "object", "additionalProperties": {"type": "array", "items": {"enum": ["admit", "admit.dry_run", "rbac.admin", "policy.admin", "config.activate", "config.approve", "audit.read", "audit.export", "quarantine", "inventory.read", "explain.read"]}, "uniqueItems": True}},
    "bindings": {"type": "array", "maxItems": 100000, "items": {"$ref": "#/$defs/binding"}},
    "registries": {"type": "array", "minItems": 1, "items": obj({"host": S(pattern=r"^[a-z0-9.\-]+(:[0-9]{1,5})?$"), "scope": S(maxLength=512)})},
    "signers": {"type": "array", "minItems": 1, "items": obj({"id": IDS, "public_key": S(minLength=40, maxLength=64), "scope": S(maxLength=512), "revoked": {"type": "boolean"}, "not_after": {"type": "number"}}, req=["id", "public_key", "scope"])},
    "provenance": obj({"require_digest": {"type": "boolean"}, "require_signature": {"type": "boolean"}, "require_attestation": {"type": "boolean"}, "trusted_builders": {"type": "array", "items": S(maxLength=512)}}),
    "policy": obj({"engine": {"enum": ["local", "external"]}, "rules": {"type": "array", "items": {"$ref": "#/$defs/rule"}}, "external_endpoint": S(maxLength=2048, pattern=r"^https?://[^\s]+$"), "external_policy_version": S(maxLength=128), "cache_ttl_s": {"type": "integer", "minimum": 0, "maximum": 3600}, "on_unavailable": {"enum": ["deny", "use_cached"]}}, req=["engine", "rules", "on_unavailable"]),
    "dual_authorization": obj({"config_activate": {"type": "integer", "minimum": 1, "maximum": 5}, "quarantine_release": {"type": "integer", "minimum": 1, "maximum": 5}}),
    "dependencies": {"type": "object", "additionalProperties": obj({"endpoint": S(maxLength=2048, pattern=r"^https?://[^\s]+$"), "required": {"type": "boolean"}, "timeout_ms": {"type": "integer", "minimum": 1, "maximum": 600000}}, req=["required"])},
    "secrets": {"type": "object", "additionalProperties": S(pattern=r"^(env|file|kms|vault):.{1,1024}$")},
    "telemetry": obj({"log_level": {"enum": ["debug", "info", "warning", "error"]}, "trace_sample_ratio": {"type": "number", "minimum": 0, "maximum": 1}, "log_retention_days": {"type": "integer", "minimum": 1, "maximum": 3650}, "metrics_retention_days": {"type": "integer", "minimum": 1, "maximum": 3650}, "redact_subjects": {"type": "boolean"}})},
    req=["schema", "environment", "site", "org", "limits", "quotas", "roles", "bindings", "registries", "signers", "provenance", "policy"]),
    "$defs": {
      "quota": obj({"rate_per_s": {"type": "number", "minimum": 0.001, "maximum": 100000}, "burst": {"type": "integer", "minimum": 1, "maximum": 1000000}, "max_inflight": {"type": "integer", "minimum": 1, "maximum": 100000}}),
      "binding": obj({"subject": S(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:@/\-]{0,255}$"), "group": IDS, "role": IDS, "scope": S(pattern=r"^[A-Za-z0-9_.\-]+(/[A-Za-z0-9_.\-]+){0,2}$"), "effect": {"enum": ["allow", "deny"]}}, req=["role", "scope", "effect"]),
      "rule": obj({"id": IDS, "effect": {"enum": ["deny", "require", "exempt"]}, "require_image_prefix": S(maxLength=2048), "targets": {"type": "array", "maxItems": 256, "items": IDS}, "priority": {"type": "integer", "minimum": 0, "maximum": 1000}, "class": {"enum": ["security", "residency", "availability", "slo", "cost"]},
                   "when": obj({"tenant": IDS, "lattice": IDS, "environment": IDS, "image_prefix": S(maxLength=2048), "component_name": IDS}, req=[]),
                   "message": S(maxLength=512)}, req=["id", "effect", "priority", "class", "when", "message"])}}),
"PK_ECP_HEALTH_1": doc("PK_ECP_HEALTH/1", "1.0.0", obj({
    "schema": {"const": "PK_ECP_HEALTH/1"}, "status": {"enum": ["ok", "degraded", "failing"]}, "ready": {"type": "boolean"},
    "version": S(), "protocols": {"type": "array", "items": S()}, "config_generation": {"type": ["string", "null"]},
    "role": {"enum": ["leader", "follower", "standalone"]}, "epoch": {"type": "integer"}, "journal_head": {"type": "integer"},
    "dependencies": {"type": "object"}, "mode": {"enum": ["normal", "degraded", "frozen"]}, "capabilities": {"type": "array", "items": S()},
    "site": {"type": ["string", "null"]}, "started_at": {"type": "number"}, "emergency": {"type": "object"}},
    req=["capabilities", "config_generation", "dependencies", "epoch", "journal_head", "mode", "protocols", "ready", "role",
         "schema", "status", "version"])),
"PK_ECP_INVENTORY_1": doc("PK_ECP_INVENTORY/1", "1.0.0", obj({
    "schema": {"const": "PK_ECP_INVENTORY/1"}, "items": {"type": "array", "items": obj({
        "tenant": IDS, "lattice": IDS, "app": IDS, "component": IDS, "image": S(), "manifest_sha256": S(pattern=HEX),
        "state": {"enum": ["proposed", "admitted", "rejected", "delivery_pending", "delivered", "rolled_back", "quarantined", "retired"]},
        "decision_id": S(), "updated_seq": {"type": "integer"}})}, "as_of_seq": {"type": "integer"}, "next_cursor": {"type": "integer"}},
    req=["schema", "items", "as_of_seq"])),
}
# fill RBAC binding def from config def
schemas["PK_ECP_RBAC_REQUEST_1"]["$defs"] = {"binding": schemas["PK_ECP_CONFIG_1"]["$defs"]["binding"]}
schemas["PK_ECP_ARTIFACT_STATEMENT_1"] = doc("PK_ECP_ARTIFACT_STATEMENT/1", "1.0.0", statement)

def render():
    return {f"{k}.schema.json": json.dumps(v, indent=1, sort_keys=True) + "\n" for k, v in schemas.items()}

if __name__ == "__main__":
    out = ROOT / "schemas"; out.mkdir(exist_ok=True)
    check = "--check" in sys.argv
    drift = []
    for name, text in render().items():
        p = out / name
        if check:
            if not p.exists() or p.read_text() != text: drift.append(name)
        else:
            p.write_text(text)
    if check:
        print("schema drift:" if drift else "schemas up to date", *drift); sys.exit(1 if drift else 0)
    print(f"wrote {len(schemas)} schemas")
