"""Deterministic integration harness (C030, C083): builds a GovernedRuntime wired to
contract-faithful INV-57/59/70/71 adapters with seeded fixtures and per-test isolation."""
import importlib
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

pkg = importlib.import_module(PKG_DIR.name)
M = {n: importlib.import_module(f"{PKG_DIR.name}.{n}") for n in (
    "config", "context", "errors", "governed", "lifecycle", "precedence", "retry", "runtime", "sandbox",
    "telemetry", "trust", "artifacts", "compat", "health", "explain", "backup", "redaction")}

TOOL_IMPLS = {
    "search_docs": lambda a: {"hits": 3},
    "run_python": lambda a: {"stdout": "ok"},
    "send_email": lambda a: {"queued": True},
    "delete_records": lambda a: {"deleted": 1},
}
FIXTURE_POLICY = {"alice": {"search_docs", "run_python", "send_email", "delete_records"},
                  "bob": {"search_docs"}}
TOPOLOGY = {"version": "topo-7", "taken_at": 0.0,
            "nodes": {"node-0": {"site": "site-a", "cluster": "c1", "provider": "lab"},
                      "node-1": {"site": "site-b", "cluster": "c2", "provider": "lab"}}}
RELEASE = {"app_version": "4.3.0", "release_id": "rel-2026-09-22", "artifact_digest": "sha256:test"}


def build(*, layers=None, faults=None, fast=True, node="node-0", durable=None, executor_id=None, clock=None):
    cfg = M["config"]
    eff = cfg.resolve(layers or [("base", {"schema_version": cfg.SCHEMA_VERSION, "residency": {"zone": "eu-1",
                                                                                               "allowed_failover_zones": ["eu-2"]}})])
    store = cfg.ConfigStore(eff, author="test-harness")
    sb = M["sandbox"]
    faults = faults or {}
    authz = sb.AuthorizationAdapter(FIXTURE_POLICY, faults.get("authz"))
    durable = durable or sb.DurableExecutionAdapter(faults.get("durable"))
    fast_sb = sb.SandboxAdapter("fast", TOOL_IMPLS, faults.get("fast")) if fast else None
    heavy_sb = sb.SandboxAdapter("heavy", TOOL_IMPLS, faults.get("heavy"))
    trust = M["trust"].TrustMonitor(max_queue=eff.get("offline.max_queue"))
    for dep in M["trust"].DEPENDENCY_MATRIX:
        trust.report(dep, M["trust"].Health.UP, version="v1")
    topo = M["telemetry"].TopologyAdapter(dict(TOPOLOGY, taken_at=__import__("time").time()))
    rt = M["governed"].GovernedRuntime(config=store, authz=authz, durable=durable, fast=fast_sb, heavy=heavy_sb,
                                       node=node, executor_id=executor_id, trust=trust, topology=topo,
                                       release=RELEASE, sleep=lambda s: None)
    return rt


def ctx(tenant="acme", timeout=30.0):
    return M["context"].CallContext.new(timeout=timeout, tenant=tenant)
