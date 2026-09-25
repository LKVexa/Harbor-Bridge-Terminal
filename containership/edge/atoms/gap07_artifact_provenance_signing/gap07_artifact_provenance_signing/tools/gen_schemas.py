"""Regenerate the v6 JSON Schemas under schemas/ from the code's own constants."""
import json
import os

import _path  # noqa: F401

from gap07_artifact_provenance_signing.algorithms import REGISTRY
from gap07_artifact_provenance_signing.signing import KINDS

S = "https://json-schema.org/draft/2020-12/schema"


def obj(id_, title, props, req=None):
    return {"$schema": S, "$id": f"urn:pk:{id_}", "title": title, "type": "object", "additionalProperties": False,
            "required": req or sorted(props), "properties": props}


def s(mx=512):
    return {"type": "string", "minLength": 1, "maxLength": mx}


INT0 = {"type": "integer", "minimum": 0}
B64U = {"type": "string", "pattern": "^[A-Za-z0-9_-]+$"}
HEX64 = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
NS = {"type": "object", "additionalProperties": False, "required": ["tenant", "site", "environment"],
      "properties": {k: s(128) for k in ("tenant", "site", "environment")}}

OUT = {
    "PK_SIGNATURE-3": obj("PK_SIGNATURE:3", "PK_SIGNATURE/3", {
        "v": {"const": 3}, "alg": {"enum": sorted(a for a, x in REGISTRY.items() if x.production)}, "kid": s(), "signer": s(),
        "tenant": s(128), "site": s(128), "env": s(128), "kind": {"enum": sorted(KINDS)}, "purpose": {"type": "string", "pattern": "^sign:[a-z-]+$"},
        "policy_domain": s(128), "digest_alg": {"enum": ["sha256", "sha512"]}, "digest": {"type": "string", "pattern": "^([0-9a-f]{64}|[0-9a-f]{128})$"},
        "issued_at": INT0, "nonce": {"type": ["string", "null"], "minLength": 16, "maxLength": 128},
        "refs": {"type": "array", "maxItems": 32, "uniqueItems": True, "items": s(256)}, "sig": B64U}),
    "PK_CERT-1": obj("PK_CERT:1", "PK_CERT/1", {
        "schema": {"const": "PK_CERT/1"}, "serial": s(), "issuer": s(), "subject": s(), "namespace": NS, "kid": s(), "alg": s(64), "spki": B64U,
        "usages": {"type": "array", "maxItems": 64, "items": {"type": "string"}}, "path_len": INT0,
        "name_constraints": {"type": "array", "items": {"type": "string"}}, "not_before": INT0, "not_after": INT0, "sig_alg": s(64), "sig": B64U}),
    "PK_CHECKPOINT-1": obj("PK_CHECKPOINT:1", "PK_CHECKPOINT/1", {
        "schema": {"const": "PK_CHECKPOINT/1"}, "origin": s(), "log_key_id": s(), "alg": s(64), "size": INT0, "root": B64U, "timestamp": INT0, "sig": B64U}),
    "PK_SIGNED_CONFIG-1": obj("PK_SIGNED_CONFIG:1", "PK_SIGNED_CONFIG/1", {
        "schema": {"const": "PK_SIGNED_CONFIG/1"},
        "type": {"enum": ["trust-snapshot", "trust-distribution", "trust-delta", "policy-bundle", "waiver", "break-glass"]},
        "kid": s(), "alg": s(64), "body_digest": HEX64, "body": {"type": "object"}, "sig": B64U}),
    "PK_TIME_ATTESTATION-1": obj("PK_TIME_ATTESTATION:1", "PK_TIME_ATTESTATION/1", {
        "schema": {"const": "PK_TIME_ATTESTATION/1"}, "authority": s(), "alg": s(64), "site": s(128), "device": s(128),
        "sequence": INT0, "time": INT0, "uncertainty_ms": INT0, "expires": INT0, "sig": B64U}),
    "PK_ARTIFACT_BUNDLE-1": obj("PK_ARTIFACT_BUNDLE:1", "PK_ARTIFACT_BUNDLE/1", {
        "schema": {"const": "PK_ARTIFACT_BUNDLE/1"},
        "artifact": {"type": "object", "required": ["digest", "kind"], "additionalProperties": False,
                     "properties": {"digest": {"type": "string", "pattern": "^sha256:[0-9a-f]{64}$"}, "kind": {"enum": sorted(KINDS)}}},
        "signatures": {"type": "array", "maxItems": 16, "items": {"$ref": "urn:pk:PK_SIGNATURE:3"}},
        "attestations": {"type": "array", "maxItems": 16, "items": {"type": "object", "required": ["payloadType", "payload", "signatures"]}},
        "transparency": {"type": "array", "items": {"type": "object", "required": ["envelope_digest", "evidence"]}},
        "registry": {"type": "object"}}),
    "PK_ADMISSION_DECISION-1": {
        "$schema": S, "$id": "urn:pk:PK_ADMISSION_DECISION:1", "title": "PK_ADMISSION_DECISION/1", "type": "object",
        "required": ["schema", "request_id", "outcome", "runnable", "code"],
        "properties": {"schema": {"const": "PK_ADMISSION_DECISION/1"}, "request_id": {"type": "string"},
                       "outcome": {"enum": ["allow", "deny", "defer", "error"]}, "runnable": {"type": "boolean"}, "code": {"type": "string"},
                       "digest": {"type": "string"}, "trust_generation": INT0, "trust_digest": HEX64, "decision_digest": HEX64},
        "allOf": [{"if": {"properties": {"runnable": {"const": True}}}, "then": {"properties": {"outcome": {"const": "allow"}}}}]},
}

if __name__ == "__main__":
    d = os.path.join(_path.ROOT, "schemas")
    for name, doc in OUT.items():
        with open(os.path.join(d, f"{name}.schema.json"), "w") as fh:
            json.dump(doc, fh, indent=2)
            fh.write("\n")
    print(len(OUT))
