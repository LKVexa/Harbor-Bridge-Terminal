"""Per-item assessments for the 2,704-item missing-components checklist.

Status vocabulary (M48-011):
  PASS            implemented, verified by linked evidence in this release
  PARTIAL         implemented or documented, but the item's full wording is not met
  FAIL            evaluated and does not meet the requirement
  OPEN            not implemented
  BLOCKED_HUMAN   needs a named person / governance decision (cannot be self-certified)
  BLOCKED_INFRA   needs infrastructure absent from this build (CI fleet, multi-arch, certified engines, HSM)

Rules: component-specific items (007-016, 027-031) are assessed individually in
SPECIFIC; generic items (001-006, 017-026, 032-052) come from GENERIC rules keyed
by component class, with per-item overrides.  A PASS always names evidence.
"""
from __future__ import annotations

T = "tests/test_prod.py"
TF = "tests/test_faults.py"
DEC, TC, ADM = "prod/decoder.py", "prod/typecheck.py", "prod/admission.py"

# component class: CODE = implemented + tested; PART = partial/doc; NONE = not built; HUMAN = governance
CLASS = {
    **{m: "CODE" for m in ["M01", "M02", "M03", "M04", "M05", "M07", "M08", "M09", "M10", "M11", "M12", "M13",
                           "M17", "M22", "M27", "M29", "M32", "M33", "M34", "M35", "M36", "M37", "M39", "M42",
                           "M43", "M44", "M46", "M48", "M49", "M51", "M52"]},
    **{m: "PART" for m in ["M06", "M14", "M15", "M16", "M18", "M21", "M23", "M24", "M25", "M26", "M28", "M30",
                           "M31", "M38", "M40", "M41", "M45", "M47"]},
    "M19": "NONE", "M20": "NONE", "M50": "HUMAN",
}

PRIMARY = {  # main implementation evidence per component
    "M01": DEC, "M02": TC, "M03": TC, "M04": ADM + ":CapabilityManifest", "M05": "prod/registry.py",
    "M06": "prod/registry.py:engines", "M07": "prod/digest.py", "M08": "prod/attest.py", "M09": "prod/cache.py",
    "M10": ADM + ":Gate.admit", "M11": ADM + ":Gate.execute", "M12": "prod/errors.py; schemas/PK_VALIDATION_FAILURE-1.json",
    "M13": "prod/limits.py", "M14": "prod/fuzz.py", "M15": "prod/differential.py", "M16": "docs/DETERMINISM.md",
    "M17": "prod/hostimports.py", "M18": "prod/hostimports.py:DEFAULT_CONTRACT_DOC", "M19": "docs/INTEGRATION.md#M19",
    "M20": "docs/DETERMINISM.md", "M21": "docs/INTEGRATION.md#M21", "M22": "prod/registry.py; prod/attest.py:sign_bundle",
    "M23": "docs/INTEGRATION.md#M23", "M24": "docs/INTEGRATION.md#M24", "M25": "docs/INTEGRATION.md#M25",
    "M26": "docs/INTEGRATION.md#M26", "M27": "prod/telemetry.py:AuditStream", "M28": "docs/THREAT_MODEL.md#M28",
    "M29": "prod/bench.py; evidence/benchmark.json", "M30": "prod/bench.py:gate; evidence/perf_gate.json",
    "M31": "tools/evidence.py:step_soak; evidence/soak.json", "M32": TF, "M33": ADM + ":Gate.health",
    "M34": "prod/telemetry.py:Metrics", "M35": "prod/telemetry.py:JsonFormatter", "M36": "prod/telemetry.py:parse_traceparent",
    "M37": "prod/telemetry.py:explain", "M38": "ops/alerts.yml; ops/dashboard.json", "M39": "prod/canary.py",
    "M40": "docs/OPERATIONS.md#M40", "M41": "docs/OPERATIONS.md#M41", "M42": "prod/config_store.py",
    "M43": ADM + ":Gate.activate; prod/config_store.py", "M44": "prod/config_store.py:reconstruct",
    "M45": "pyproject.toml; requirements.lock", "M46": "evidence/sbom.cdx.json", "M47": "evidence/build_metadata.json",
    "M48": "TRACEABILITY.json; CHECKLIST_STATUS.json", "M49": "docs/adr/", "M50": "OWNERS.yaml",
    "M51": "prod/waivers.py; waivers/WAIVERS.json", "M52": "prod/gate.py; evidence/production_gate.json",
}

SCHEMA_OWNERS = {"M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M10", "M12", "M17", "M18", "M22",
                 "M27", "M33", "M52"}
GATE_PATH = {"M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09", "M10", "M11", "M12", "M13", "M17", "M18"}
CRITICAL_PERF = {"M01", "M02", "M03", "M10", "M13", "M29", "M30"}


def generic(comp: str, n: int) -> tuple[str, str, str]:
    c = CLASS[comp]
    ev = PRIMARY[comp]
    if n == 1:
        return "BLOCKED_HUMAN", "OWNERS.yaml", "owner/security reviewer/operator are TBD - must be named by the organisation"
    if c == "HUMAN":
        return "BLOCKED_HUMAN", "OWNERS.yaml", "governance component: requires named people and approvals"
    if c == "NONE" and n < 50:
        return "OPEN", ev, "component not implemented in v4.3.0"
    code = c == "CODE"
    if n == 2:
        return ("PASS" if code else "PARTIAL"), "docs/DESIGN.md#3; " + ev, "" if code else "requirements documented at summary level only"
    if n == 3:
        return ("PASS" if code else "PARTIAL"), "docs/DESIGN.md#1; docs/THREAT_MODEL.md", ""
    if n == 4:
        if comp in SCHEMA_OWNERS:
            return "PASS", "schemas/; tests/test_prod.py:SchemaConformanceTest", ""
        return "PARTIAL", ev, "no dedicated JSON schema for this component's interface"
    if n == 5:
        return ("PASS" if comp in GATE_PATH | {"M22", "M42", "M43"} else "PARTIAL"), \
            "prod/attest.py:FIELDS; prod/admission.py:Gate.validate (cache key)", ""
    if n == 6:
        return ("PASS" if comp in GATE_PATH else "PARTIAL"), "prod/limits.py:Limits", ""
    if n == 17:
        return ("PASS" if code else "PARTIAL"), "frozen dataclasses in " + ev, ""
    if n == 18:
        return ("PASS" if code else "PARTIAL"), "prod/errors.py:boundary; " + T + ":test_internal_error_is_refusal", ""
    if n == 19:
        return ("PASS" if comp in GATE_PATH else "PARTIAL"), \
            T + ":test_nondeterministic_failures_not_cached; " + TF + ":test_deadline_mid_validation", ""
    if n == 20:
        if comp in {"M09", "M43"}:
            return "PASS", "docs/DESIGN.md#4; " + T + ":test_thread_safety", ""
        return "PARTIAL", "docs/DESIGN.md#4", "documented; no component-specific race test"
    if n == 21:
        return "PARTIAL", "docs/THREAT_MODEL.md", "authored by implementer; independent security review pending (named reviewer TBD)"
    if n == 22:
        return ("PASS" if code else "PARTIAL"), ev + "; tests/test_faults.py", ""
    if n == 23:
        return ("PASS" if comp in GATE_PATH else "PARTIAL"), "prod/limits.py; " + DEC + ":Reader.count", \
            "Python ints cannot wrap; all sizes checked against remaining bytes before slicing"
    if n == 24:
        return "PARTIAL", "docs/THREAT_MODEL.md", "deployment privileges (service identity, fs, keys) not defined - no deployment exists"
    if n == 25:
        return ("PASS" if code else "PARTIAL"), "prod/errors.py:sanitize; evidence/static_scan.json; " + T + ":test_sanitize_and_bounds", ""
    if n == 26:
        return ("PASS" if comp in GATE_PATH | {"M27", "M34", "M35", "M37"} else "PARTIAL"), \
            T + ":test_explain_and_no_raw_bytes; docs/OPERATIONS.md", ""
    if n == 32:
        return "PARTIAL", "evidence/coverage.json", "line coverage measured (~94% prod); not every normative branch individually enumerated"
    if n == 33:
        return ("PASS" if code else "PARTIAL"), T + ":AdmissionTest, SchemaConformanceTest", ""
    if n == 34:
        return ("PASS" if code else "PARTIAL"), "FINDINGS.md", "every defect found in this pass has a named regression test"
    if n == 35:
        return ("PASS" if code else "PARTIAL"), "evidence/tests.json (normal and -O runs)", ""
    if n == 36:
        return "PARTIAL", "evidence/coverage.json", "measured; manual review of uncovered security branches needs the security reviewer"
    if n == 37:
        return ("PASS" if comp in GATE_PATH | {"M34"} else "PARTIAL"), "prod/telemetry.py:Metrics; " + T + ":test_metrics_cardinality", ""
    if n == 38:
        return ("PASS" if comp in GATE_PATH | {"M35", "M36"} else "PARTIAL"), "verdict trace_id/span_id; prod/telemetry.py", ""
    if n == 39:
        return ("PASS" if comp in GATE_PATH | {"M22", "M27", "M42", "M43"} else "PARTIAL"), \
            "prod/telemetry.py:AuditStream; " + T + ":test_health_and_audit_chain", ""
    if n == 40:
        return ("PASS" if comp == "M33" else "PARTIAL"), ADM + ":Gate.health", "readiness covers bundle + self-test, not each dependency"
    if n == 41:
        return "PARTIAL", "ops/alerts.yml; docs/OPERATIONS.md#M40", "alerts link runbooks; owners TBD; not deployed"
    if n == 42:
        return ("PASS" if comp in {"M05", "M22", "M42", "M43", "M44"} else "PARTIAL"), "docs/OPERATIONS.md#M42", ""
    if n == 43:
        if comp in CRITICAL_PERF:
            return "FAIL", "evidence/perf_gate.json", "p99 ~2.4 s at 4 MiB vs SLO 20 ms (ADR-0006)"
        return "PARTIAL", "evidence/benchmark.json; evidence/soak.json", ""
    if n == 44:
        return ("PASS" if code else "PARTIAL"), "docs/DESIGN.md; docs/adr/", ""
    if n == 45:
        return ("PASS" if code else "PARTIAL"), "README.md; docs/OPERATIONS.md", ""
    if n == 46:
        return "PASS", "TRACEABILITY.json; CHECKLIST_STATUS.json", ""
    if n == 47:
        return ("PASS" if code else "PARTIAL"), "evidence/ (bound to release digest)", ""
    if n == 48:
        return "PARTIAL", "evidence/static_scan.json", "stdlib AST scan clean; ruff/mypy/bandit/pip-audit unavailable (no PyPI)"
    if n == 49:
        return "BLOCKED_INFRA", "tools/ci.sh", "CI script provided; no clean CI runner available in this build"
    raise KeyError(n)


# ---------------------------------------------------------------- specific items
P, PA, F, O, BH, BI = "PASS", "PARTIAL", "FAIL", "OPEN", "BLOCKED_HUMAN", "BLOCKED_INFRA"
S: dict[str, tuple[str, str, str]] = {}


def s(item, status, ev, note=""):
    S[item] = (status, ev, note)


# M01
s("M01-007", P, DEC + ":decode header; " + T + ":test_header")
s("M01-008", P, DEC + ":Reader._uleb/_sleb; " + T + ":test_leb128", "width+unused-bit checks; spec permits non-minimal in-width encodings (tested)")
s("M01-009", P, DEC + "; " + T + ":test_section_rules")
s("M01-010", P, DEC + " cross-section checks; tests/oracle_corpus.py *_oob cases", "tags refused as UNSUPPORTED_PROPOSAL")
s("M01-011", P, DEC + ":Reader.bytes_/count", "Python ints do not wrap; every length checked against remaining bytes")
s("M01-012", P, DEC + ":Reader.count/name; prod/limits.py; " + T + ":test_vector_bombs_and_limits")
s("M01-013", P, "InvalidModule.offset/section; ParsedModule offsets; " + T + ":test_immutable_parse_and_offsets")
s("M01-014", P, "frozen ParsedModule; " + T + ":test_immutable_parse_and_offsets")
s("M01-015", P, "UNKNOWN_SECTION / UNKNOWN_OPCODE / UNSUPPORTED_PROPOSAL paths; " + T + ":test_negative_typing")
s("M01-016", P, "sub-Readers bounded per section; evidence/fuzz_campaign.json (0 crashes)")
s("M01-027", P, "tests/wasmgen.py:seeds; " + T + ":test_seed_corpus_valid")
s("M01-028", P, T + ":test_header, test_section_rules")
s("M01-029", P, T + ":test_leb128, test_vector_bombs_and_limits")
s("M01-030", PA, "prod/fuzz.py; evidence/fuzz_campaign.json", "structure-aware mutation fuzzing, not coverage-guided; no sanitizer needed for pure Python but no native build exists")
s("M01-031", PA, "evidence/fuzz_campaign.json differential", "one independent reference (V8); checklist requires two")
# M02
s("M02-007", P, TC + ":_validate_body (explicit operand + control stacks)")
s("M02-008", P, T + ":test_negative_typing, test_unreachable_polymorphism; tests/oracle_corpus.py")
s("M02-009", P, TC + ":_check_const/_module_level; oracle_corpus g_* cases")
s("M02-010", P, "oracle_corpus call*/table*/elem* cases")
s("M02-011", P, "oracle_corpus mem*/loads_stores/data*; alignment test", "memory64/multi-memory refused (not enabled)")
s("M02-012", P, DEC + " import/export checks; " + T + ":test_utf8_and_exports")
s("M02-013", PA, TC + ":_UNSUPPORTED table; prod/registry.py", "proposal gates are a static table in the validator, not generated from the M05 registry")
s("M02-014", P, "prod/errors.py:Code; " + T + ":test_negative_typing")
s("M02-015", P, T + ":test_deep_nesting_is_iterative_and_bounded")
s("M02-016", P, TC + ":TypedFacts (frozen)")
s("M02-027", PA, "tests/oracle_corpus.py (judged against V8)", "official WebAssembly spec testsuite (.wast) not imported - no network/wabt")
s("M02-028", PA, "prod/fuzz.py mutation of generated valid bodies", "offset-exact single-mutation assertions not systematic")
s("M02-029", P, "oracle_corpus; FeatureTest; SIMD refusal tests")
s("M02-030", PA, "evidence/fuzz_campaign.json", "single reference implementation")
s("M02-031", P, "evidence/tests.json -O run identical")
# M03
s("M03-007", P, "prod/registry.py DEFAULT_BUNDLE_DOC.features")
s("M03-008", PA, TC + " feature evidence points", "mapping is hand-written; no generated completeness proof")
s("M03-009", P, TC + ":validate_module - facts from decoder/typechecker only")
s("M03-010", PA, "docs/DESIGN.md#M03", "presence == requirement (conservative); no reachability analysis")
s("M03-011", PA, "prod/registry.py", "no implication/transitive-closure rules defined (none needed for current set)")
s("M03-012", P, "verdict['used'] sorted; attestation features sorted")
s("M03-013", P, "unknown -> UNKNOWN_OPCODE/UNSUPPORTED_PROPOSAL; unregistered -> FEATURE_REFUSED")
s("M03-014", P, "TypedFacts.evidence; " + T + ":test_evidence_offsets")
s("M03-015", P, "custom payloads never read; ADR-0003")
s("M03-016", PA, T + ":test_default_bundle_and_kernel_consistent", "no automated branch->feature consistency check")
s("M03-027", P, T + ":test_byte_derived_features")
s("M03-028", PA, "seeds multi-feature", "no transitive implications exist to test")
s("M03-029", P, T + ":test_binding_manifest (declaration changes, bytes fixed)")
s("M03-030", P, "oracle_corpus fc_unknown/unknown_op/typed_select_v128")
s("M03-031", BI, "", "no broad real-world corpus / independent feature tooling available offline")
# M04
s("M04-007", P, ADM + ":CapabilityManifest (single container; custom sections ignored)")
s("M04-008", P, "CapabilityManifest.digest (canonical JSON)")
s("M04-009", PA, ADM, "bound to module digest; issuer identity / validity window not in manifest")
s("M04-010", O, "", "manifests are not signed; they can only narrow what is accepted (used ⊆ declared) so no escalation, but issuer trust is absent")
s("M04-011", O, "", "issuer authorization model not implemented")
s("M04-012", PA, T + ":test_binding_manifest (other digest)", "tenant/validity not modelled")
s("M04-013", PA, "docs/DESIGN.md#M04", "")
s("M04-014", P, ADM + ":_validate_uncached; " + T + ":test_binding_manifest")
s("M04-015", PA, "cache key includes manifest digest", "manifest digest not yet a field of the attestation")
s("M04-016", O, "", "")
s("M04-027", PA, T + ":test_binding_manifest", "")
s("M04-028", P, T + ":test_binding_manifest (manifest for other digest)")
s("M04-029", P, "single-source contract (no precedence) - docs/DESIGN.md#M04")
s("M04-030", O, "", "no signed declarations yet")
s("M04-031", O, "", "")
# M05
s("M05-007", PA, "schemas/PK_ISA_POLICY_BUNDLE-1.json", "no opcode mappings/revision commits in registry")
s("M05-008", PA, "spec_id 'wasm-core-2.0'", "pinned by label, not by spec commit hash")
s("M05-009", P, "features vs host contract (M17/M18) are separate artifacts")
s("M05-010", P, "prod/registry.py:load_bundle; RegistryTest")
s("M05-011", P, "prod/attest.py:sign_bundle/open_signed_bundle; ConfigTest")
s("M05-012", O, "", "lookup tables hand-maintained")
s("M05-013", PA, "status field standard/phase-4/unsupported", "")
s("M05-014", P, "bundle revision in attestation, cache key, health")
s("M05-015", P, "engines.features reference registered IDs")
s("M05-016", BH, "", "")
s("M05-027", P, T + ":test_strict_schema")
s("M05-028", O, "", "")
s("M05-029", P, "prod/config_store.py:reconstruct; ConfigTest")
s("M05-030", P, T + ":test_stale_config_blocks_execution_and_rollback")
s("M05-031", O, "", "")
# M06
for i in (7, 9, 10, 12, 15, 16, 27, 29, 31):
    s(f"M06-{i:03d}", BI, "prod/registry.py (placeholder engine)", "no certified real engine build to describe")
s("M06-008", P, "engines.features use registry IDs")
s("M06-011", P, "engine status 'revoked' refused; ADM")
s("M06-013", P, ADM + " engine intersection; " + T + ":test_profile_refusals")
s("M06-014", P, "engine in attestation + cache key")
s("M06-028", P, T + ":test_nan_canonicalisation_required, test_profile_refusals")
s("M06-030", PA, "signed bundle tamper test ConfigTest", "")
# M07
s("M07-007", P, "prod/digest.py; ADR-0003")
s("M07-008", P, "'sha256:' prefix")
s("M07-009", PA, "prod/digest.py", "one-shot hashing (module <= 4 MiB held in memory already)")
s("M07-010", P, ADM + ":Gate.validate first step")
s("M07-011", P, "no filename/path API exists")
s("M07-012", P, "prod/digest.py:parse_digest; DigestTest")
s("M07-013", P, "verdict size_bytes + digest")
s("M07-014", P, "full digests everywhere")
s("M07-015", O, "", "no dual-hash migration rules")
s("M07-016", P, ADM + ":Gate.execute")
s("M07-027", P, "DigestTest; test_attestation_cannot_be_moved")
s("M07-028", O, "", "no streaming implementation to compare")
s("M07-029", P, "DigestTest")
s("M07-030", O, "", "")
s("M07-031", P, T + ":test_toctou")
# M08
s("M08-007", P, "prod/attest.py:FIELDS; schemas/PK_VALIDATION_ATTESTATION-1.json")
s("M08-008", PA, "reject verdicts carry M12 failure", "reject verdicts are not signed")
s("M08-009", P, "canonical_json + canonical re-check in verify")
s("M08-010", BI, "prod/attest.py:Signer", "in-memory key; production needs HSM/KMS")
s("M08-011", P, "ttl, expires_at, skew; test_foreign_key_and_revocation_and_expiry")
s("M08-012", PA, "engine/profile bound", "tenant not bound")
s("M08-013", PA, "Verifier trusted map + revoke", "historical verification of rotated keys not implemented")
s("M08-014", P, "AuditStream hash chain")
s("M08-015", P, "verdict must equal 'accept' in signed payload; tamper test")
s("M08-016", P, "schema string versioned independently")
s("M08-027", P, T + ":test_attestation_cannot_be_moved (payload edit)")
s("M08-028", PA, T + ":test_foreign_key_and_revocation_and_expiry; " + TF + ":test_verifier_clock_skew", "wrong-tenant n/a")
s("M08-029", O, "", "single implementation")
s("M08-030", P, T + ":test_attestation_cannot_be_moved (malformed)")
s("M08-031", O, "", "")
# M09
s("M09-007", P, ADM + " cache key")
s("M09-008", P, "accept re-signed on each hit; cached record keyed on all inputs")
s("M09-009", P, "only deterministic outcomes cached; test_nondeterministic_failures_not_cached")
s("M09-010", P, "key is digest + revisions")
s("M09-011", P, "HMAC integrity; " + TF + ":test_cache_corruption_cannot_admit", "in-memory only (no persistent cache)")
s("M09-012", PA, "ADR-0005", "tenant id not in key (open decision)")
s("M09-013", P, "revision in key + epoch")
s("M09-014", P, "bump_epoch on activation")
s("M09-015", PA, "capacity bound + LRU", "no per-tenant occupancy")
s("M09-016", PA, "hits/misses/evictions/integrity_failures attributes", "not exported as Prometheus series")
s("M09-027", PA, T + ":test_cache_semantics (profile change)", "not every input varied individually")
s("M09-028", P, TF + ":test_cache_corruption_cannot_admit")
s("M09-029", P, T + ":test_thread_safety")
s("M09-030", O, "", "")
s("M09-031", O, "", "")
# M10
s("M10-007", PA, ADM + ":Gate.execute", "in-process choke point; real engine integration absent")
s("M10-008", PA, ADM + ":admit", "tenant context absent")
s("M10-009", P, "attest.verify expect bindings")
s("M10-010", P, "verification failure -> exception, no ticket")
s("M10-011", P, "no bypass API in package")
s("M10-012", P, "AdmissionTicket carries immutable bytes")
s("M10-013", P, "admission.* / execution.* audit events")
s("M10-014", P, "docs/DESIGN.md; tests for cache/revocation/rotation")
s("M10-015", O, "", "no AOT artifacts")
s("M10-016", P, "Verifier.revoke + epoch bump; RB-04")
s("M10-027", PA, T + ":test_toctou (non-ticket refused)", "real engine entry points absent")
s("M10-028", P, T + ":test_attestation_cannot_be_moved")
s("M10-029", PA, TF, "")
s("M10-030", PA, "execute(object()) refused", "")
s("M10-031", PA, T + ":test_accept_attest_admit_execute + audit chain", "no artifact retrieval stage")
# M11
s("M11-007", P, "bytes snapshot in ticket")
s("M11-008", P, "bytes-only API; no paths")
s("M11-009", P, "Gate.execute re-hash")
s("M11-010", PA, "", "no storage layer")
s("M11-011", O, "", "no AOT")
s("M11-012", PA, "no filesystem API", "n/a until a storage layer exists")
s("M11-013", O, "", "")
s("M11-014", P, "ticket.module_digest")
s("M11-015", P, "execution.refused DIGEST_MISMATCH audit event")
s("M11-016", PA, "docs/THREAT_MODEL.md T-05", "")
s("M11-027", PA, T + ":test_toctou (buffer mutation)", "file race not applicable")
s("M11-028", O, "", "")
s("M11-029", P, T + ":test_toctou")
s("M11-030", O, "", "")
s("M11-031", O, "", "")
# M12
s("M12-007", PA, "schemas/PK_VALIDATION_FAILURE-1.json", "no category/severity/retryable fields")
s("M12-008", P, "prod/errors.py:Code (stable string values)")
s("M12-009", P, "sanitize + bounded detail")
s("M12-010", PA, "", "")
s("M12-011", PA, "", "first failure only (documented)")
s("M12-012", P, "@boundary; FaultInjectionTest")
s("M12-013", PA, "DETERMINISTIC_REJECTS", "no explicit retryable flag")
s("M12-014", PA, "validator.py kernel retained", "no mapping table ValidationFailed/FeatureRefused -> codes")
s("M12-015", P, "SchemaConformanceTest")
s("M12-016", P, "schemas/")
s("M12-027", PA, "SchemaConformanceTest", "")
s("M12-028", P, "fuzz + sanitize tests")
s("M12-029", O, "", "")
s("M12-030", PA, "", "")
s("M12-031", PA, "explain + schema tests", "")
# M13
s("M13-007", PA, "prod/limits.py:Limits", "versioned (revision hash) but not signed separately")
s("M13-008", P, "max_steps, max_control_depth, max_operand_stack")
s("M13-009", P, "Reader.count before allocation")
s("M13-010", P, "iterative validator")
s("M13-011", PA, "", "no per-tenant quotas")
s("M13-012", P, "LIMIT_EXCEEDED detail names dimension")
s("M13-013", P, "Governor deadline; test_deadline_mid_validation")
s("M13-014", O, "", "no service concurrency model")
s("M13-015", P, "no decompression accepted (n/a)")
s("M13-016", P, "limits_revision in attestation + cache key")
s("M13-027", PA, T + ":test_vector_bombs_and_limits", "not every limit has below/above fixtures")
s("M13-028", P, T + ":test_leb128")
s("M13-029", P, "deep nesting + vector bombs")
s("M13-030", O, "", "")
s("M13-031", P, "limits revision in cache key")
# M14
s("M14-007", PA, "prod/fuzz.py (end-to-end target)", "no per-stage targets")
s("M14-008", P, "tests/wasmgen.py:seeds + mutators")
s("M14-009", P, "fuzz.gen_module typed generator")
s("M14-010", PA, "crash/nondeterminism/slowest recorded", "no per-input memory cap")
s("M14-011", O, "", "no minimizer")
s("M14-012", BI, "", "spec corpora need network")
s("M14-013", PA, "", "managed runtime; no native component")
s("M14-014", PA, "evidence/coverage.json", "")
s("M14-015", P, "nondeterminism check in oracle")
s("M14-016", P, "FuzzSmokeTest in unittest")
s("M14-027", PA, TF, "no deliberate infinite-loop mutant")
s("M14-028", PA, "evidence/fuzz_campaign.json", "campaign measured in minutes, not sustained")
s("M14-029", P, "FINDINGS.md regressions")
s("M14-030", BI, "", "single architecture")
s("M14-031", P, "prod/gate.py consumes crash count")
# M15
s("M15-007", PA, "prod/differential.py (V8)", "second reference (wasmtime/wabt) not installable offline")
s("M15-008", P, "classes FALSE_ACCEPT/PROPOSAL_GAP/LIMIT_GAP/FALSE_REJECT")
s("M15-009", P, "PROPOSAL_GAP classification")
s("M15-010", P, "accept/reject primary")
s("M15-011", PA, "reproducers stored by seed", "")
s("M15-012", PA, "tests/oracle_corpus.py:KNOWN_DIVERGENCE; DIFFERENTIAL_DISPOSITIONS.md", "owner/expiry TBD")
s("M15-013", PA, "", "no real-world corpus")
s("M15-014", P, "fuzz invalid inputs")
s("M15-015", PA, "node version in SBOM", "")
s("M15-016", P, "FINDINGS.md")
s("M15-027", O, "", "")
s("M15-028", P, "PROPOSAL_GAP tests")
s("M15-029", BI, "", "")
s("M15-030", PA, "evidence/fuzz_campaign.json", "")
s("M15-031", P, "DIFFERENTIAL_DISPOSITIONS.md")
# M16 / M17 / M18
s("M16-007", P, "docs/DETERMINISM.md")
s("M16-009", P, "NaN rule enforced; test_nan_canonicalisation_required")
s("M16-010", P, "simd/relaxed refused in deterministic profile")
s("M16-011", P, "threads refused")
s("M16-012", P, "host contract classes")
s("M16-030", P, T + ":test_profile_refusals")
for i in (27, 28, 29):
    s(f"M16-{i:03d}", BI, "", "needs certified engines to execute modules")
s("M16-031", BH, "", "")
s("M17-007", P, "PK_HOST_IMPORT_CONTRACT/1")
s("M17-008", P, "deny-by-default classify")
s("M17-010", P, "no wildcard default")
s("M17-012", PA, "names + kinds checked", "function signatures not checked against contract")
s("M17-015", P, "profile allowed_import_classes")
s("M17-027", PA, "HostImportTest", "signature/handle tests absent")
s("M17-029", P, T + ":test_profile_refusals")
s("M18-008", P, "DEFAULT_CONTRACT_DOC")
s("M18-011", P, "clock/random nondeterministic")
s("M18-027", PA, "HostImportTest (path_open denied)", "")
# M22 / M27 / M29 / M30 / M32-M37 / M39 / M42-M44 / M46 / M48 / M49 / M51 / M52
s("M22-007", P, "schemas/PK_ISA_POLICY_BUNDLE-1.json")
s("M22-008", P, "canonical_json + Ed25519")
s("M22-009", P, "load_bundle referential checks")
s("M22-010", P, "epoch monotonic")
s("M22-012", BH, "", "")
s("M22-013", P, "activate refuses epoch <= active")
s("M22-014", P, "open_signed_bundle")
s("M22-015", P, "ConfigStore")
s("M22-027", P, "RegistryTest.test_strict_schema")
s("M22-028", P, "ConfigTest tamper")
s("M22-030", P, "ConfigTest (failed activation leaves old config)")
s("M22-031", P, "ConfigStore.reconstruct")
s("M27-007", P, "schemas/PK_AUDIT_EVENT-1.json")
s("M27-009", P, "hash chain")
s("M27-011", P, "sanitised fields")
s("M27-013", P, TF + ":test_audit_sink_failure_propagates")
s("M27-027", PA, "SchemaConformanceTest audit events", "")
s("M27-028", P, T + ":test_health_and_audit_chain")
s("M27-029", P, TF + ":test_audit_sink_failure_propagates")
s("M27-030", P, "sanitize tests")
s("M29-008", P, "bench.run sizes 1 KiB..~4 MiB")
s("M29-015", P, "evidence/benchmark.json")
s("M29-016", PA, "", "end-to-end validate only")
s("M29-011", PA, "python/machine recorded", "")
s("M30-007", P, "bench.gate slo_p99_ms")
s("M30-012", P, "exceptions fail the run")
s("M30-016", P, "prod/gate.py reads perf_gate")
s("M30-030", P, "prod/gate.py: missing evidence -> BLOCKED")
s("M32-008", P, TF)
s("M32-011", P, TF + ":test_audit_sink_failure_propagates")
s("M32-012", P, TF + ":test_verifier_clock_skew")
s("M32-028", P, TF)
s("M32-029", P, TF + ":test_cache_corruption_cannot_admit")
s("M33-007", PA, "", "single health() method")
s("M33-008", P, "health returns validator, bundle revision, epoch")
s("M33-012", P, "health reads active bundle")
s("M33-027", PA, "", "")
s("M34-007", P, "Metrics")
s("M34-027", P, T + ":test_metrics_cardinality")
s("M35-009", P, "JsonFormatter sanitize")
s("M35-014", P, "outcome refuse vs error")
s("M35-027", P, "sanitize tests")
s("M36-007", P, "W3C traceparent")
s("M36-010", P, "malformed -> fresh trace; test_traceparent")
s("M36-028", P, T + ":test_traceparent")
s("M37-008", P, "explain()")
s("M37-009", P, "explain reason line")
s("M37-016", P, "REMEDIES never suggest bypass")
s("M37-027", PA, T + ":test_explain_and_no_raw_bytes", "")
s("M39-010", P, "canary.compare decision rule")
s("M39-012", PA, "rollback-by-roll-forward (RB-05)", "")
s("M39-013", P, "epoch monotonic")
s("M39-015", P, "per-request snapshot of bundle/contract")
s("M39-027", P, TF + ":CanaryTest")
s("M42-009", P, "open_signed_bundle on activate + reconstruct")
s("M42-010", P, "append-only store")
s("M42-012", P, "hash-chained records")
s("M42-015", P, "reconstruct(epoch)")
s("M42-028", P, "ConfigTest")
s("M42-030", P, "ConfigTest tamper")
s("M43-008", P, "signature -> schema -> epoch -> swap")
s("M43-010", P, "single-reference swap under lock")
s("M43-011", P, "per-request snapshot")
s("M43-013", P, "ConfigTest")
s("M43-029", P, "ConfigTest")
s("M43-030", P, "test_stale_config... rollback refused")
s("M44-013", P, "cache loss only costs performance (cache is derived)")
s("M44-028", P, "bump_epoch clears cache; tests")
s("M46-007", P, "CycloneDX 1.5 JSON")
s("M46-011", PA, "licenses from installed metadata", "")
s("M48-007", PA, "TRACEABILITY.json", "dimension-level mapping for the 100 base requirements")
s("M48-011", P, "this vocabulary")
s("M48-012", P, "status computed per item, not inherited")
s("M48-016", P, "CHECKLIST_STATUS.json + .md from one dataset")
s("M48-027", P, "tools/checklist_status.py asserts 2,704 unique IDs and 100 base IDs")
s("M48-031", P, "prod/gate.py consumes status; no override flag")
s("M49-007", P, "docs/adr/ADR-0001..0006")
s("M49-013", BH, "", "decision owners TBD")
s("M51-007", P, "prod/waivers.py schema")
s("M51-008", P, "expires required")
s("M51-011", BH, "", "")
s("M51-014", P, "prod/gate.py ignores expired waivers")
s("M51-031", P, "NEVER_WAIVABLE prefixes; WaiverTest")
s("M52-007", PA, "prod/gate.py policy", "gate policy not separately signed")
s("M52-008", P, "prod/gate.py")
s("M52-009", P, "stale/missing evidence -> BLOCKED")
s("M52-013", P, "waiver evaluation")
s("M52-014", P, "evidence/production_gate.json")
s("M52-015", PA, "bound to release digest", "result not signed (no release key)")
s("M52-016", BI, "", "no delivery system to integrate")
s("M52-027", P, "tests/test_gate.py")
s("M52-028", P, "tests/test_gate.py")


def specific(item: str, comp: str, n: int) -> tuple[str, str, str]:
    if item in S:
        return S[item]
    c = CLASS[comp]
    if c == "HUMAN":
        return BH, "OWNERS.yaml", "requires named people/approvals"
    if c == "NONE":
        return O, PRIMARY[comp], "component not implemented"
    if c == "CODE":
        return PA, PRIMARY[comp], "component implemented; this item not individually evidenced"
    return O if n >= 27 else PA, PRIMARY[comp], "partial component; item not implemented" if n >= 27 else "documented only"
