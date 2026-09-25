"""Deterministic, idempotent production bootstrap (MC-029).

Order (each step idempotent; reruns converge to the same result):

1. validate the effective configuration and runtime self-test;
2. resolve trust material (TLS files, token/audit/data keys) through the
   secret provider -- *before* any privileged listener is opened (MC-029-02);
3. open/recover durable storage and verify backend identity/version (MC-029-03);
4. create the initial namespace/policy markers under the reserved system
   namespace with ``EXISTS == false`` compares, so reruns are no-ops (MC-029-04/05);
5. write ``bootstrap.json`` -- versions, digests, identities and check results
   (MC-029-06).

Usage::

    python -m inv05_current_control_state_system.bootstrap --config base.json [--env env.json] [--site site.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from typing import Any

from . import __version__
from .audit import AuditLog
from .backend import LocalBackend, runtime_self_test
from .backup import CompactionController
from .config import EffectiveConfig, build, load_layers
from .errors import InvalidArgument
from .observability import Metrics, StructuredLogger, Tracer
from .security import Authorizer, SecretProvider, derive_key
from .service import BUILD_INFO, ControlStateService
from .store import Compare, Put
from .wal import DurableStore, Keyring, Sealer

SYSTEM_PREFIX = "/_sys/"


def build_service(cfg: EffectiveConfig, secrets: SecretProvider, *, log_stream: Any = None) -> tuple[ControlStateService, dict[str, Any]]:
    checks: dict[str, Any] = {"runtime": runtime_self_test()}
    if not checks["runtime"]["ok"]:
        raise InvalidArgument("runtime self-test failed: " + "; ".join(checks["runtime"]["problems"]))
    data_key = secrets.get(cfg["storage.data_key"])
    audit_key = secrets.get(cfg["audit.key"])
    sealer = None
    if cfg["storage.encrypt_at_rest"]:
        sealer = Sealer(Keyring({"dk1": derive_key(data_key, "wal")}, "dk1"))
    os.makedirs(cfg["storage.data_dir"], mode=0o700, exist_ok=True)
    tracer = Tracer(cfg["telemetry.trace_ratio"])
    with tracer.span("cstate.recovery", op="recovery") as rec_span:
        durable = DurableStore.open(cfg["storage.data_dir"], limits=cfg.limits(), durability=cfg["storage.durability"],
                                    group_commit=cfg["storage.group_commit"], sealer=sealer)
        rec_span.set(revision=durable.store.revision, records=durable.report.records_replayed)
    checks["recovery"] = durable.report.to_dict()
    backend = LocalBackend(durable.store)
    checks["backend"] = backend.identity()
    logger = StructuredLogger(log_stream if log_stream is not None else sys.stderr, level=cfg["telemetry.log_level"])
    audit = AuditLog(cfg["audit.path"], derive_key(audit_key, "audit"))
    metrics = Metrics(cfg["telemetry.max_series_per_metric"])
    svc = ControlStateService(durable.store, audit=audit, authorizer=Authorizer(), metrics=metrics, logger=logger,
                              tracer=tracer, config_hash=cfg.sha256,
                              site_epoch=cfg["node.site_epoch"], durable=durable)
    svc.compactor = CompactionController(
        durable.store, retain_revisions=cfg["compaction.retain_revisions"],
        safety_margin=cfg["compaction.safety_margin_revisions"], min_interval_s=cfg["compaction.min_interval_s"],
        watch_floor=lambda: min((w._resume_point() for w in list(svc.hub._watchers.values())), default=None),
        on_compact=lambda rev, n: audit.record("compaction", "scheduled", actor="compaction-controller",
                                               revision=rev, dropped=n))
    # step 4: deterministic system markers (idempotent via EXISTS==false)
    markers = {SYSTEM_PREFIX + "bootstrap/version": __version__,
               SYSTEM_PREFIX + "bootstrap/node": cfg["node.name"],
               SYSTEM_PREFIX + "bootstrap/site": cfg["node.site"],
               SYSTEM_PREFIX + "policy/version": svc.authz.policy.version}
    created = []
    for k, v in markers.items():
        res = durable.store.txn([Compare(k, "EXISTS", "==", False)], [Put(k, v)], actor="bootstrap")
        if res.succeeded:
            created.append(k)
    checks["markers_created"] = created
    svc.bootstrapped = True
    audit.record("recovery", "bootstrap", actor="bootstrap", revision=durable.store.revision,
                 config_sha256=cfg.sha256, created=len(created))
    logger.log("INFO", "CS1200", "recovery completed", **{k: v for k, v in durable.report.to_dict().items()
                                                           if isinstance(v, (int, bool))})
    artifact = {"schema": "cstate.bootstrap/1", "completed_unix": int(time.time()), "build": BUILD_INFO,
                "config_sha256": cfg.sha256, "config_provenance": dict(cfg.provenance),
                "node": cfg["node.name"], "site": cfg["node.site"], "site_epoch": cfg["node.site_epoch"],
                "revision": durable.store.revision, "encrypt_at_rest": bool(sealer),
                "audit_anchor": audit.anchor(), "checks": checks}
    artifact["sha256"] = hashlib.sha256(json.dumps(artifact, sort_keys=True).encode()).hexdigest()
    with open(os.path.join(cfg["storage.data_dir"], "bootstrap.json"), "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2, sort_keys=True)
    return svc, artifact


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="INV-05 bootstrap")
    ap.add_argument("--config", required=True)
    ap.add_argument("--env")
    ap.add_argument("--site")
    ap.add_argument("--secret-dir")
    ap.add_argument("--dry-run", action="store_true", help="validate config and exit")
    a = ap.parse_args(argv)
    layers = {"base": a.config}
    if a.env:
        layers["environment"] = a.env
    if a.site:
        layers["site"] = a.site
    cfg = load_layers(layers)
    if a.dry_run:
        print(json.dumps({"ok": True, "config_sha256": cfg.sha256, "effective": cfg.redacted()}, indent=2))
        return 0
    svc, art = build_service(cfg, SecretProvider(a.secret_dir))
    print(json.dumps({"ok": True, "bootstrap_sha256": art["sha256"], "revision": art["revision"]}))
    svc.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
