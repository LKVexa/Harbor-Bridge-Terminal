"""Command line and wiring for the INV-07 controller.

    python -m inv07_gitops_transition_layer.components.cli config-validate CONFIG.json
    python -m inv07_gitops_transition_layer.components.cli verify   CONFIG.json --ref refs/heads/main
    python -m inv07_gitops_transition_layer.components.cli sync     CONFIG.json --ref refs/heads/main [--target-dir DIR]
    python -m inv07_gitops_transition_layer.components.cli status   CONFIG.json
    python -m inv07_gitops_transition_layer.components.cli backup   CONFIG.json DEST
    python -m inv07_gitops_transition_layer.components.cli restore  BACKUP DEST
    python -m inv07_gitops_transition_layer.components.cli audit-verify CONFIG.json

Exit codes: 0 ok, 2 refused/denied (trust/policy/ref), 3 failed (dependency/apply),
4 frozen, 64 usage/config error.  Output is one JSON document on stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from .fsutil import load_json, read_bytes, read_text  # noqa: F401
from . import config as cfgmod
from .apply import Transaction  # noqa: F401  (re-export for operators' scripts)
from .audit import AuditLedger
from .controller import Controller
from .errors import ConfigRejected, GitOpsError
from .gitrepo import GitRepository
from .keys import SecretResolver
from .lease import FileLease
from .operations import FreezeRegistry, OfflinePolicy, TimeAuthority
from .policy import PolicyEngine
from .refpolicy import FreshnessGuard, RefPolicy
from .resilience import CircuitBreaker, RetryBudget, RetryPolicy
from .signing import TrustRoots
from .state import ControllerState, backup, restore
from .target import DirectoryTarget
from .telemetry import EventLog, ExplainStore, Registry, Tracer, standard_metrics
from .tenancy import ResidencyPolicy, TenantScope


def load_config(path: str, environ=None) -> dict:
    doc = cfgmod.merge(cfgmod.DEFAULTS, load_json(path), cfgmod.from_env(environ or os.environ))
    return cfgmod.validate(doc)


def build(doc: dict, *, base_dir: str, target=None, time_source=None, node: str = "node-1",
          allow_file_repos: bool = False, policy_bundle: bytes | None = None, event_sink=None,
          provenance_verifier=None) -> Controller:
    ten = doc["tenancy"]
    scope = TenantScope(ten["tenant"], ten["site"], root=base_dir, namespaces=tuple(ten["allowed_namespaces"]))
    residency = ResidencyPolicy(region=ten["region"], allowed_regions=tuple(ten["allowed_regions"]), site=ten["site"])
    sd = scope.path(doc["controller"]["state_dir"])
    os.makedirs(sd, exist_ok=True)
    audit = AuditLedger(os.path.join(sd, "audit.jsonl"), clock=time.time)
    trust_path = doc["trust"]["trust_roots_file"]
    trust = TrustRoots.load(trust_path if os.path.isabs(trust_path) else os.path.join(base_dir, trust_path))
    repo_cfg = doc["repository"]
    resolver = SecretResolver()
    cred = None
    if repo_cfg.get("credential_ref"):
        scope.check_secret_ref(repo_cfg["credential_ref"])
        cred = lambda: resolver.resolve(repo_cfg["credential_ref"]).reveal().decode()  # noqa: E731
    repo = GitRepository(repo_cfg["url"], scope.path("mirror.git"), allowed_hosts=repo_cfg.get("allowed_hosts", []),
                         allow_file=allow_file_repos, root_commit=repo_cfg.get("root_commit"),
                         depth=repo_cfg["fetch_depth"], timeout=repo_cfg["timeout_seconds"], credential=cred,
                         max_blob_bytes=doc["limits"]["max_manifest_bytes"])
    lim = doc["limits"]
    metrics = standard_metrics(Registry())
    ts = time_source or (lambda: (time.time(), time.time()))
    policy = PolicyEngine(trust)
    if policy_bundle is not None:
        policy.load(policy_bundle, now=int(ts()[0]))
    tgt = target or DirectoryTarget(scope.path("target"), allow_delete=doc["controller"]["prune"],
                                    namespaces=tuple(ten["allowed_namespaces"]))
    ctl = Controller(
        repo=repo, refpolicy=RefPolicy(repo_cfg["url"], tuple(repo_cfg["approved_refs"])), trust=trust,
        target=tgt, state=ControllerState(os.path.join(sd, "journal")), audit=audit,
        freezes=FreezeRegistry(os.path.join(sd, "freezes.json"), audit=audit),
        lease=FileLease(scope.path("lease"), "controller", node=node, ttl=doc["controller"]["lease_ttl_seconds"]),
        timeauth=TimeAuthority(ts, max_sync_age=60), offline=OfflinePolicy(
            doc["controller"]["offline_mode"], max_cached_ref_age=doc["controller"]["max_cached_ref_age_seconds"]),
        tenancy=scope, policy=policy, metrics=metrics,
        events=EventLog(event_sink, tenant=ten["tenant"], site=ten["site"], level=doc["telemetry"]["log_level"],
                        metrics=metrics),
        tracer=Tracer(), explain=ExplainStore(os.path.join(sd, "explain.jsonl")),
        freshness=FreshnessGuard(os.path.join(sd, "freshness.json"),
                                 max_commit_age=doc["trust"]["max_commit_age_seconds"]),
        retry=RetryPolicy(max_attempts=lim["retry_max_attempts"], base=lim["retry_base_seconds"],
                          cap=lim["retry_cap_seconds"], budget=RetryBudget(1.0, 10.0)),
        breaker=CircuitBreaker("git", threshold=lim["breaker_threshold"], cooldown=lim["breaker_cooldown_seconds"]),
        require_provenance=doc["trust"]["require_provenance"], allowed_builders=("https://pk.example/builders/review",),
        prune=doc["controller"]["prune"], limits={**lim, "max_resources": doc["controller"]["max_resources"]},
        residency=residency, provenance_verifier=provenance_verifier)
    ctl.recover()
    return ctl


EXIT = {"applied": 0, "no_change": 0, "duplicate": 0, "read_only": 0, "refused": 2, "failed": 3, "frozen": 4}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="inv07")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("config-validate", "verify", "sync", "status", "audit-verify"):
        p = sub.add_parser(c)
        p.add_argument("config")
        p.add_argument("--ref", default="refs/heads/main")
        p.add_argument("--base-dir", default=".")
        p.add_argument("--policy-bundle")
    b = sub.add_parser("backup")
    b.add_argument("config")
    b.add_argument("dest")
    b.add_argument("--base-dir", default=".")
    r = sub.add_parser("restore")
    r.add_argument("backup")
    r.add_argument("dest")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "restore":
            print(json.dumps(restore(a.backup, a.dest), sort_keys=True))
            return 0
        doc = load_config(a.config)
        if a.cmd == "config-validate":
            print(json.dumps({"valid": True, "digest": cfgmod.digest(doc)}))
            return 0
        if a.cmd == "backup":
            sd = os.path.join(a.base_dir, doc["tenancy"]["tenant"], doc["tenancy"]["site"], doc["controller"]["state_dir"])
            print(json.dumps(backup(sd, a.dest), sort_keys=True))
            return 0
        bundle = read_bytes(a.policy_bundle) if getattr(a, "policy_bundle", None) else None
        ctl = build(doc, base_dir=a.base_dir, policy_bundle=bundle)
        if a.cmd == "status":
            print(json.dumps(ctl.status(), sort_keys=True))
            return 0
        if a.cmd == "audit-verify":
            print(json.dumps(ctl.audit.verify(), sort_keys=True))
            return 0
        if a.cmd == "verify":
            from .signing import verify_commit
            ctl.repo.fetch()
            oid = ctl.repo.resolve(a.ref)
            v = verify_commit(ctl.repo.read_commit(oid), ctl.trust, ref=a.ref, now=int(time.time()))
            print(json.dumps({"schema": "PK_GITOPS_VERIFY/1", "ref": a.ref, "oid": oid, "result": "verified",
                              "signer": {"key_id": v.key_id, "algorithm": v.algorithm, "identity": v.identity},
                              "trust_digest": v.trust_digest, "at": time.time()}, sort_keys=True))
            return 0
        rec = ctl.reconcile(a.ref)
        print(json.dumps(rec, sort_keys=True))
        return EXIT.get(rec["outcome"], 3)
    except ConfigRejected as exc:
        print(json.dumps(exc.envelope(), sort_keys=True))
        return 64
    except GitOpsError as exc:
        print(json.dumps(exc.envelope(), sort_keys=True))
        return 3


if __name__ == "__main__":
    sys.exit(main())
