"""MC-08 - Requirement-to-evidence traceability matrix (source of TRACEABILITY.json).

Run ``python -m pln02_application_plane.tools.traceability`` to regenerate.
Statuses (honest, fail-closed):

* ``IMPLEMENTED``      - code/docs + passing tests in this archive satisfy every local acceptance criterion.
* ``PARTIAL``          - implemented here; named acceptance criteria need evidence this archive cannot produce.
* ``BLOCKED_OWNER``    - needs an owner decision, approval, named person, or source material.
* ``BLOCKED_EXTERNAL`` - needs an external estate, environment, CI runner or deployment.

Only ``IMPLEMENTED`` (or an approved, unexpired exception) counts toward GO.
"""
from __future__ import annotations

import json
import pathlib
import re

PKG = pathlib.Path(__file__).resolve().parents[1]

MC = {
 "MC-01": ("Original master source archive", "BLOCKED_OWNER", [], ["docs/source/SOURCE_RECOVERY_RECORD.md", "docs/source/MASTER.provenance.json"], [],
           ["MASTER.md not supplied; recovery unresolved (recorded, nothing reconstructed)."]),
 "MC-02": ("ADR and accountable ownership", "BLOCKED_OWNER", ["C009", "C010"], ["docs/adr/ADR-PLN02-001-application-plane-architecture.md", "docs/adr/ADR_INDEX.md", "docs/governance/OWNERSHIP.yaml", "docs/governance/ESCALATION.md"], [],
           ["ADR state is Proposed: approval by quorum not recorded.", "Named owners are UNASSIGNED."]),
 "MC-03": ("Normative requirements specification", "PARTIAL", ["C011", "C012", "C013", "C014", "C015"], ["docs/spec/REQUIREMENTS.md"], ["MC24MC25Store", "MC15Integration"],
           ["Spec awaits approval under ADR-PLN02-001."]),
 "MC-04": ("Version policy, negotiation, compatibility", "IMPLEMENTED", ["C016", "C027", "C093"], ["versioning.py", "docs/spec/COMPATIBILITY.md"], ["MC04Versioning"], []),
 "MC-05": ("Capacity, quota, fairness, admission", "PARTIAL", ["C017", "C028", "C054", "C067", "C069"], ["admission.py"], ["MC05Admission", "MC24MC25Store"],
           ["Quotas are per replica; estate-wide quota coordination needs a shared store."]),
 "MC-06": ("Disconnected catalogue cache / GAP-04", "PARTIAL", ["C018", "C048", "C056", "C089"], ["catalogue.py"], ["MC06MC33Disconnected"],
           ["GAP-04 exercised through a lease mock only."]),
 "MC-07": ("Constraint precedence and conflicts", "IMPLEMENTED", ["C019", "C055"], ["policy.py"], ["MC07MC28Policy"], []),
 "MC-08": ("Traceability and acceptance record", "IMPLEMENTED", ["C020", "C090", "C100"], ["tools/traceability.py", "TRACEABILITY.json", "tools/gate.py"], ["gate:self"], []),
 "MC-09": ("OAM adapter", "IMPLEMENTED", ["C011", "C021"], ["oam.py"], ["MC09OAM", "ParserFuzz", "FuzzRegressions"], []),
 "MC-10": ("WIT parser and type checker", "PARTIAL", ["C021", "C022", "C027", "C084", "C085"], ["wit.py"], ["MC10WIT", "ParserFuzz"],
           ["WIT subset only; no differential conformance against the reference wasm-tools parser (TD-003)."]),
 "MC-11": ("Boundary authentication and trust bootstrap", "PARTIAL", ["C023", "C044", "C048"], ["trust.py"], ["MC11Authentication"],
           ["Caller tokens implemented; node/peer mTLS and attestation belong to the hosting transport (external)."]),
 "MC-12": ("Capability entitlement / authorization", "IMPLEMENTED", ["C024", "C042", "C046"], ["policy.py", "service.py"], ["MC12Entitlement", "MC15Integration"], []),
 "MC-13": ("Timeout, cancellation, retry, idempotency", "IMPLEMENTED", ["C025", "C053"], ["context.py", "service.py"], ["MC13Context", "MC15Integration"], []),
 "MC-14": ("Wire-level error schema", "IMPLEMENTED", ["C026"], ["errors.py", "schemas/PK_ERROR-1.schema.json"], ["MC14Errors", "SchemaConformance"], []),
 "MC-15": ("Adjacent-layer integration harness", "PARTIAL", ["C030", "C083"], ["tests/test_faults_and_integration.py"], ["MC15Integration"],
           ["All six peers are contract-faithful mocks; no live PLN-01/INV-65/PLN-03/SCH-01/INV-11/GAP-04."]),
 "MC-16": ("Reproducible build and dependency lock", "IMPLEMENTED", ["C031", "C032", "C040", "C093"], ["pyproject.toml", "requirements.lock", "docs/operations/RUNBOOKS.md"], ["gate:build"], []),
 "MC-17": ("Configuration, provenance, activation, rollback", "IMPLEMENTED", ["C033", "C034", "C035", "C036", "C037", "C038"], ["config.py", "schemas/PK_PLANE_CONFIG-1.schema.json"], ["MC17Config"], []),
 "MC-18": ("Secrets, encryption, key lifecycle", "PARTIAL", ["C039", "C047", "C048"], ["secret_refs.py", "trust.py"], ["MC18Secrets", "MC11Authentication"],
           ["KMS binding and encryption in transit/at rest are deployment-provided (external)."]),
 "MC-19": ("Threat model and adversarial plan", "PARTIAL", ["C041", "C050", "C087"], ["docs/security/THREAT_MODEL.md"], ["MC11Authentication", "MC12Entitlement", "MC21SupplyChain", "MC22Audit"],
           ["Security review sign-off not recorded."]),
 "MC-20": ("Ambient authority reduction / isolation", "BLOCKED_EXTERNAL", ["C043", "C046"], ["docs/security/ISOLATION_PROFILE.md"], [],
           ["Profile written; no deployment attestation that it is applied."]),
 "MC-21": ("Artifact signature, provenance, supply chain", "PARTIAL", ["C045"], ["trust.py", ".github/workflows/ci.yml"], ["MC21SupplyChain"],
           ["Default HMAC is symmetric (TD-002); SBOM/attestation generation runs only in unexecuted CI."]),
 "MC-22": ("Tamper-evident audit ledger", "IMPLEMENTED", ["C049"], ["audit.py"], ["MC22Audit", "MC15Integration"], []),
 "MC-23": ("Failure catalogue, health, stall detection", "IMPLEMENTED", ["C051", "C052"], ["observability.py", "docs/operations/FAILURE_CATALOGUE.md"], ["MC30Observability", "MC06MC33Disconnected"], []),
 "MC-24": ("Failover, split-brain, quarantine/freeze/disable", "PARTIAL", ["C055", "C058", "C059"], ["store.py", "service.py"], ["MC24MC25Store"],
           ["Fencing is single-process per store root (TD-001); multi-process HA needs an external lease."]),
 "MC-25": ("Revision store and durable lifecycle", "IMPLEMENTED", ["C004", "C032", "C057", "C095"], ["store.py", "docs/operations/RUNBOOKS.md"], ["MC24MC25Store"], []),
 "MC-26": ("Tenant/environment/site context", "IMPLEMENTED", ["C006", "C046", "C064", "C073"], ["context.py", "store.py", "service.py"], ["MC13Context", "MC15Integration"], []),
 "MC-27": ("Provider catalogue client", "IMPLEMENTED", ["C004", "C021", "C036", "C044", "C045", "C051"], ["catalogue.py", "schemas/PK_SIGNED_CATALOGUE-1.schema.json"], ["MC06MC33Disconnected"], []),
 "MC-28": ("Provider selection and explain", "IMPLEMENTED", ["C019", "C076", "C077"], ["policy.py", "service.py"], ["MC07MC28Policy", "MC15Integration"], []),
 "MC-29": ("Performance baseline and regression suite", "PARTIAL", ["C061", "C062", "C063", "C064", "C065", "C066", "C067", "C068", "C069", "C070"], ["tools/bench.py", "perf/THRESHOLDS.json", "evidence/perf_baseline.json"], ["gate:bench"],
           ["Single reference host only; constrained-edge power/thermal (C068) not measured."]),
 "MC-30": ("Runtime observability", "IMPLEMENTED", ["C071", "C072", "C073", "C074", "C075", "C076", "C077", "C078"], ["observability.py", "service.py"], ["MC30Observability", "MC15Integration"], []),
 "MC-31": ("Telemetry governance, dashboards, alerts", "PARTIAL", ["C079", "C080"], ["docs/operations/TELEMETRY_GOVERNANCE.md", "docs/operations/alerts.json", "docs/operations/dashboards.json"], [],
           ["Definitions only; not deployed to a monitoring backend."]),
 "MC-32": ("Fuzz, property, concurrency, security tests", "IMPLEMENTED", ["C081", "C082", "C085", "C086", "C087"], ["tests/test_fuzz_property.py", "tests/corpus"], ["ResolverProperties", "ParserFuzz", "FuzzRegressions", "MC24MC25Store"], []),
 "MC-33": ("Fault injection, partition, reconnect", "PARTIAL", ["C060", "C089"], ["tests/test_faults_and_integration.py"], ["MC06MC33Disconnected", "MC24MC25Store"],
           ["In-process fault injection only; no real network/site partition campaign."]),
 "MC-34": ("Cross-platform / protocol CI matrix", "BLOCKED_EXTERNAL", ["C084", "C093"], [".github/workflows/ci.yml", "docs/spec/COMPATIBILITY.md"], [],
           ["Matrix defined (3 OS x 5 Python); only Linux/3.11 executed here."]),
 "MC-35": ("Benchmark, soak, fleet-scale environment", "BLOCKED_EXTERNAL", ["C088"], ["tools/bench.py"], ["gate:bench"],
           ["Short single-host soak only; fleet-scale environment not available."]),
 "MC-36": ("CI/CD production gate and release evidence", "PARTIAL", ["C070", "C090", "C100"], ["tools/gate.py", ".github/workflows/ci.yml"], ["gate:self"],
           ["Gate is fail-closed and runs locally; pk_core full-estate run and signed attestation are external."]),
 "MC-37": ("Canary, rollout, rollback, emergency disable", "PARTIAL", ["C092", "C096"], ["docs/operations/RUNBOOKS.md", "store.py", "config.py", "service.py"], ["MC24MC25Store", "MC17Config"],
           ["Controls exist and are tested; no production drill executed."]),
 "MC-38": ("Support, vulnerability, incident, review governance", "BLOCKED_OWNER", ["C091", "C094", "C097", "C098", "C099"], ["docs/governance/GOVERNANCE.md", "docs/governance/registers"], [],
           ["Policy written; no on-call owner, review or exercise evidence."]),
 "MC-39": ("License, NOTICE, distribution policy", "BLOCKED_OWNER", [], ["LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md", "REUSE.toml", "docs/release/DISTRIBUTION_POLICY.md"], ["gate:legal"],
           ["Owner chose to leave the licence unresolved; LICENSE records 'owner decision pending'."]),
}

BASELINE = {  # v4.2 artifacts already covering these requirements
    "C001": ["contract.py", "README.md"], "C002": ["contract.py", "README.md"], "C003": ["contract.py"],
    "C005": ["contract.py"], "C007": ["contract.py"], "C008": ["contract.py", "README.md"],
    "C029": ["tests/fixtures", "tests/corpus", "schemas"],
}


def build() -> dict:
    checklist = json.loads((PKG / "CHECKLIST.json").read_text("utf-8"))
    req_map = {}
    for item in checklist["items"]:
        cid = item["check_id"].split("-")[-1]
        mcs = sorted(k for k, v in MC.items() if cid in v[2])
        req_map[item["check_id"]] = {"dimension": item["dimension"], "mc": mcs, "baseline": BASELINE.get(cid, [])}
    aps = sorted(set(re.findall(r"AP-REQ-\d{3}", (PKG / "docs/spec/REQUIREMENTS.md").read_text("utf-8"))))
    return {
        "schema": "PLN02-TRACEABILITY/1", "package_version": (PKG / "VERSION").read_text().strip(),
        "statuses": ["IMPLEMENTED", "PARTIAL", "BLOCKED_OWNER", "BLOCKED_EXTERNAL"],
        "components": {k: {"title": t, "status": s, "requirements": r, "artifacts": a, "tests": te, "open_acceptance": o}
                       for k, (t, s, r, a, te, o) in MC.items()},
        "requirements": req_map,
        "normative_requirements": aps,
        "orphans": sorted(k for k, v in req_map.items() if not v["mc"] and not v["baseline"]),
    }


if __name__ == "__main__":
    doc = build()
    (PKG / "TRACEABILITY.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", "utf-8")
    counts = {}
    for c in doc["components"].values():
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    print(json.dumps({"orphans": doc["orphans"], "status_counts": counts}))
