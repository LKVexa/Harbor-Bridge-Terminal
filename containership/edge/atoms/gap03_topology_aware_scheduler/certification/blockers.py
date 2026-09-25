"""Explicit, reasoned blockers.  A check listed here is BLOCKED regardless of any
passing test: the test proves the local mechanism, but the check demands
something this archive cannot contain (a named human, a real adjacent system,
a production runner, key custody, an exercised procedure...)."""

OWNER = "BLK-OWNER: needs a named accountable owner/reviewer set (governance/OWNERS.json is UNASSIGNED)"
EXERCISE = "BLK-EXERCISE: runbook exists but the procedure has not been exercised in a production-like environment"
PROD_EVIDENCE = ("BLK-RELEASE: production evidence needs release-key custody (HSM/KMS) and a clean-environment CI run; "
                 "only a local digest-bound bundle was produced")
BENCH = "BLK-RUNNER: local measurement only; blocking thresholds need a controlled per-platform runner (thresholds are PROPOSED)"
NO_BENCH = "BLK-RUNNER: no representative-scale capacity test for this component on controlled hardware"
KMS = "BLK-KMS: production key custody/rotation requires an HSM/KMS integration not present in this archive"
REAL_ADJ = "BLK-ADJACENT: real adjacent implementation unavailable; only the schema-faithful conformance harness was exercised"
CI = "BLK-CI: requires an executed CI pipeline (ci/matrix.yml declared, not run)"
INFRA = "BLK-INFRA: requires deployment infrastructure (network/TLS/storage/LB) not present in this archive"
CONSENSUS = "BLK-CONSENSUS: production quorum store (etcd/ZK/Raft) integration absent; reference lease implementation only"
APPROVAL = "BLK-APPROVAL: requires named human approvals"
PROCESS = "BLK-PROCESS: recurring organisational process; no cadence evidence can exist yet"
MASTER = "BLK-SOURCE: MASTER.md is absent; see governance/MC-039_MASTER_md_provenance.json"

TEMPLATED = {2: OWNER, 24: EXERCISE, 30: PROD_EVIDENCE}

SPECIFIC = {
    "MC-001-CHK-015": CI,
    "MC-002-CHK-006": INFRA + " (mutual TLS / workload identity transport)",
    "MC-004-CHK-013": CONSENSUS + " (store is single-writer, not replicated)",
    "MC-005-CHK-015": NO_BENCH + " (multi-process/multi-replica load test)",
    "MC-006-CHK-007": CONSENSUS,
    "MC-006-CHK-012": EXERCISE + " (membership change / rolling upgrade / DR)",
    "MC-008-CHK-006": REAL_ADJ + " (the normative SCH-01 API belongs to SCH-01; only GAP-03's assumed contract is captured)",
    "MC-008-CHK-015": REAL_ADJ,
    "MC-008-CHK-017": INFRA + " (mTLS workload identity on the SCH-01 channel)",
    "MC-024-CHK-010": INFRA + " (dashboard/log/trace backend access control; explain+audit query authz verified locally)",
    "MC-040-CHK-017": KMS + " (signing-service authorization)",
    "MC-042-CHK-008": "BLK-CRYPTO: encryption at rest needs an approved cipher via KMS (stdlib has none); manifest is Ed25519-signed + sha256 per file",
    "MC-012-CHK-011": KMS,
    "MC-013-CHK-007": INFRA + " (OS/WORM enforcement that the service principal cannot delete audit files)",
    "MC-018-CHK-014": INFRA + " (deployment gates / LB registration wiring)",
    "MC-019-CHK-012": INFRA + " (scrape/export authentication)",
    "MC-020-CHK-014": INFRA + " (central export, TLS transport, access control)",
    "MC-021-CHK-015": REAL_ADJ + " (propagation across real SCH-01/state services)",
    "MC-023-CHK-014": CI + " (PromQL syntax validation needs a query engine in CI)",
    "MC-023-CHK-015": PROCESS,
    "MC-024-CHK-011": INFRA + " (encryption in transit/at rest, exporter credentials)",
    "MC-024-CHK-013": APPROVAL + " (data-processing agreements for export destinations)",
    "MC-030-CHK-006": NO_BENCH + " (workload model needs production arrival-rate / candidate-count / objective-mix distributions)",
    "MC-030-CHK-007": NO_BENCH + " (per-stage CPU/alloc/lock-contention profiling)",
    "MC-031-CHK-010": BENCH,
    "MC-031-CHK-012": CI + " (stable benchmark runners)",
    "MC-031-CHK-014": PROCESS + " (longitudinal trend data; trend.jsonl started)",
    "MC-032-CHK-008": INFRA + " (DNS/TLS/packet-loss injection needs a network test environment)",
    "MC-032-CHK-015": CI + " (nightly fault matrix)",
    "MC-034-CHK-006": REAL_ADJ + " (fixtures are hand-written from GAP-03's assumed contracts, not the peers' exact schemas)",
    "MC-034-CHK-008": REAL_ADJ,
    "MC-034-CHK-014": CI,
    "MC-035-CHK-008": CI + " (all Python/OS cells)",
    "MC-035-CHK-009": CI + " (all CPU architectures)",
    "MC-035-CHK-011": INFRA + " (TLS/storage/coordination client versions)",
    "MC-035-CHK-013": CI,
    "MC-035-CHK-014": CI,
    "MC-035-CHK-015": PROCESS,
    "MC-036-CHK-006": OWNER, "MC-036-CHK-007": OWNER, "MC-036-CHK-008": OWNER, "MC-036-CHK-009": OWNER,
    "MC-036-CHK-010": OWNER, "MC-036-CHK-012": INFRA + " (production endpoints/environments)", "MC-036-CHK-013": PROCESS,
    "MC-036-CHK-014": EXERCISE,
    "MC-037-CHK-013": APPROVAL, "MC-037-CHK-015": PROCESS,
    "MC-038-CHK-007": OWNER + " (per-requirement owner)",
    **{f"MC-039-CHK-{i:03d}": MASTER for i in range(6, 16)},
    "MC-040-CHK-008": "BLK-BUILDER: provenance generated but the builder identity is unverified (no trusted build service)",
    "MC-040-CHK-009": KMS + " (organisation-controlled signing service)",
    "MC-040-CHK-011": "BLK-ADVISORY: no sourced advisory feed; scan returns INDETERMINATE by design",
    "MC-040-CHK-012": "BLK-LICENSE: licence/compliance scanner not integrated",
    "MC-040-CHK-013": CI + " (build permissions / protected branches)",
    "MC-040-CHK-015": PROD_EVIDENCE,
    "MC-041-CHK-015": EXERCISE,
    "MC-042-CHK-010": INFRA + " (backup storage credentials / object lock / geo separation)",
    "MC-042-CHK-013": CI + " (periodic restore rehearsal automation)",
    "MC-042-CHK-014": INFRA + " (backup age / job monitoring)",
    "MC-043-CHK-008": OWNER + " (incident roles)", "MC-043-CHK-013": APPROVAL + " (communication templates approval)",
    "MC-043-CHK-015": EXERCISE,
    "MC-044-CHK-008": "BLK-ADVISORY: continuous advisory ingestion not connected",
    "MC-044-CHK-010": CI + " (protected emergency-release path)",
    "MC-044-CHK-014": INFRA + " (fleet patch-adoption tracking)", "MC-044-CHK-015": PROCESS,
    "MC-045-CHK-012": INFRA + " (owner notification channel)",
    "MC-046-CHK-008": PROD_EVIDENCE, "MC-046-CHK-009": PROD_EVIDENCE, "MC-046-CHK-010": EXERCISE,
    "MC-046-CHK-011": BENCH, "MC-046-CHK-012": CI, "MC-046-CHK-013": OWNER, "MC-046-CHK-015": APPROVAL,
}


def templated_blocker(mc: str, n: int, spec: dict, bound_tests: list[str]) -> str | None:
    if n in TEMPLATED:
        return TEMPLATED[n]
    if n == 19 and spec["crypto"]["requires_external_kms"]:
        return KMS
    if n == 28:
        return BENCH if bound_tests else NO_BENCH
    if n == 26 and mc in ("MC-008", "MC-009", "MC-010", "MC-011", "MC-034"):
        return REAL_ADJ
    return None
