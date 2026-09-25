"""Configuration contract (MC-xx-11 for every component, MC-44-03, MC-44-05, MC-44-06).

One schema covers every component's settings with types, ranges, secure
defaults, secret *references* (never values) and deprecated keys. Unknown
keys are rejected; secrets supplied inline are rejected.
"""
from __future__ import annotations

import re

CONFIG_VERSION = "GAP15-CONFIG/1"

# key: (type, default, (min, max) | allowed set | None, component, description)
CONFIG_SCHEMA: dict = {
    "environment": (str, None, None, "25", "canonical environment label (required)"),
    "partitions": (list, None, None, "25", "tenant/environment/site keys served (required)"),
    "data_dir": (str, "./data", None, "01", "directory for the SQLite store (0700)"),
    "store.synchronous": (str, "FULL", {"FULL", "EXTRA"}, "01", "SQLite durability; NORMAL/OFF are refused"),
    "ledger.checkpoint_every": (int, 1000, (1, 1_000_000), "02", "events between signed checkpoints"),
    "signing.algorithms": (list, ["ed25519"], None, "03", "approved signature algorithms"),
    "signing.key_provider": (str, "hsm", {"hsm", "kms", "tpm", "development"}, "03", "private-key boundary"),
    "signing.key_ref": (str, None, None, "03", "secret reference, e.g. kms://… or file:///run/secrets/… (required)"),
    "provenance.require_sbom": (bool, True, None, "04", "reject evidence without a matching SBOM"),
    "attestation.freshness_s": (int, 300, (30, 3600), "05", "maximum quote age"),
    "attestation.allow_reduced_trust": (bool, False, None, "05", "admit nodes without hardware roots as reduced-trust"),
    "time.max_skew_s": (int, 5, (1, 60), "06", "maximum source disagreement"),
    "time.required_confidence": (str, "medium", {"high", "medium"}, "06", "minimum confidence for decisions"),
    "time.offline_grace_s": (int, 3600, (0, 86400), "06", "holdover grace; never extends hard expiry"),
    "authn.max_token_lifetime_s": (int, 900, (60, 3600), "07", "upper bound on token lifetime"),
    "authn.revocation_max_age_s": (int, 300, (30, 3600), "07", "stale revocation lists fail closed"),
    "authz.policy_ref": (str, None, None, "08", "signed policy bundle reference (required)"),
    "schema.reject_unknown_fields": (bool, True, None, "09", "must stay true for security-sensitive payloads"),
    "ingest.max_body_bytes": (int, 262144, (1024, 4194304), "10", "per-envelope size limit"),
    "ingest.max_batch_items": (int, 100, (1, 1000), "10", "batch cardinality"),
    "concurrency.max_retries": (int, 5, (0, 20), "11", "optimistic-conflict retry budget"),
    "audit.export_dir": (str, "./audit-export", None, "12", "independent checkpoint export target"),
    "revocation.max_staleness_s": (int, 60, (1, 3600), "13", "revocation propagation SLO"),
    "api.listen": (str, "127.0.0.1:8443", None, "14", "host:port"),
    "api.tls_cert_ref": (str, None, None, "14", "certificate reference (required outside development)"),
    "api.request_deadline_s": (int, 10, (1, 120), "14", "per-request deadline"),
    "api.max_concurrent": (int, 64, (1, 4096), "14", "concurrency gate"),
    "recovery.rpo_s": (int, 0, (0, 86400), "15", "ledger RPO target (0 = synchronous)"),
    "recovery.rto_s": (int, 900, (60, 86400), "15", "restore RTO target"),
    "negotiation.allow_experimental": (bool, False, None, "16", "preview features need explicit opt-in"),
    "capability.recognised_extensions": (list, [], None, "17", "vendor extension fields policy trusts"),
    "versions.ruleset": (str, "GAP15-VERSION-RULES/1.0.0", None, "18", "pinned compatibility-rule revision"),
    "features.graph_ref": (str, "file:///etc/gap15/feature-graph.json", None, "19", "feature prerequisite/conflict graph"),
    "lifecycle.warning_horizon_s": (int, 30 * 86400, (0, 365 * 86400), "20", "advance-warning window for deadlines"),
    "explain.max_page": (int, 200, (10, 1000), "28", "explain history page cap"),
    "alerts.max_page_silence_s": (int, 14400, (60, 14400), "29", "maximum silence for paging alerts"),
    "admission.max_staleness_s": (int, 60, (0, 3600), "30", "maximum age of an admission decision at launch"),
    "conflict.quarantine": (bool, True, None, "31", "quarantine scope on high-severity conflicts"),
    "certification.ttl_s": (int, 500, (60, 31_536_000), "21", "positive certification TTL (v4.2.0 default 500)"),
    "scheduler.lab_quota": (dict, {"default": 4}, None, "22", "concurrent recert jobs per lab"),
    "policy.ref": (str, None, None, "23", "signed precedence policy reference"),
    "offline.max_age_s": (int, 86400, (60, 604800), "24", "offline bundle hard lifetime"),
    "metrics.token_ref": (str, None, None, "26", "secret reference protecting /metrics"),
    "tracing.sample_ratio": (float, 0.05, (0.0, 1.0), "27", "head sampling; errors always kept"),
    "rate.per_principal_rps": (int, 50, (1, 100000), "32", "token bucket rate"),
    "rate.global_rps": (int, 2000, (1, 1000000), "32", "global bucket rate"),
}
REQUIRED = {"environment", "partitions", "signing.key_ref", "authz.policy_ref"}
DEPRECATED = {"certification.ttl": "certification.ttl_s"}
SECRET_REF = re.compile(r"^(kms|hsm|vault|file)://[^\s]+$")
SECRETISH = re.compile(r"(?i)(password|secret|private_key|token)$")


def validate_config(cfg: dict, *, development: bool = False) -> list:
    problems = []
    for k in cfg:
        if k in DEPRECATED:
            problems.append(f"{k} is deprecated; use {DEPRECATED[k]}")
        elif k not in CONFIG_SCHEMA:
            problems.append(f"unknown key {k}")
        elif SECRETISH.search(k):
            problems.append(f"{k}: inline secrets are refused; use a *_ref")
    for k in REQUIRED:
        if k not in cfg:
            problems.append(f"missing required {k}")
    for k, v in cfg.items():
        if k not in CONFIG_SCHEMA:
            continue
        typ, _, rng, _, _ = CONFIG_SCHEMA[k]
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if not isinstance(v, typ) or (typ is int and isinstance(v, bool)):
            problems.append(f"{k}: expected {typ.__name__}")
            continue
        if isinstance(rng, tuple) and not rng[0] <= v <= rng[1]:
            problems.append(f"{k}: {v} outside {rng}")
        if isinstance(rng, set) and v not in rng:
            problems.append(f"{k}: {v!r} not in {sorted(rng)}")
        if k.endswith("_ref") and not SECRET_REF.match(v):
            problems.append(f"{k}: must be a secret reference (kms://, hsm://, vault://, file://)")
    if not development:
        if cfg.get("signing.key_provider") == "development":
            problems.append("signing.key_provider=development is refused outside development")
        if "api.tls_cert_ref" not in cfg:
            problems.append("api.tls_cert_ref is required outside development")
        if cfg.get("schema.reject_unknown_fields") is False:
            problems.append("schema.reject_unknown_fields may not be disabled")
    return problems


def defaults() -> dict:
    return {k: v[1] for k, v in CONFIG_SCHEMA.items() if v[1] is not None}


def component_sections() -> dict:
    out: dict = {}
    for k, (_, _, _, comp, _) in CONFIG_SCHEMA.items():
        out.setdefault(comp, []).append(k)
    return out
