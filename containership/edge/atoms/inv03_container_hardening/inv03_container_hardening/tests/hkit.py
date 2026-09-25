"""Shared test kit for the 4.3.0 hardening runtime (no pk_core needed)."""
from __future__ import annotations

import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.dont_write_bytecode = True

from inv03_container_hardening.hardening.authority import (  # noqa: E402
    Authorizer, ExceptionStore, Principal)
from inv03_container_hardening.hardening.baseline import (  # noqa: E402
    BaselineStore, Keyring, default_document, sign_baseline)
from inv03_container_hardening.hardening.core import AuditLedger, TrustedClock  # noqa: E402
from inv03_container_hardening.hardening.engine import Engine  # noqa: E402
from inv03_container_hardening.hardening.runtime import RuntimeInventory  # noqa: E402

SIGN_KEY = b"s" * 32
SEAL_KEY = b"a" * 32
PROFILE_DIGEST = "sha256:" + "ab" * 32


class FakeTime:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def hardened_pod():
    return copy.deepcopy({
        "runtimeClassName": "gvisor",
        "hostUsers": False,
        "securityContext": {"runAsNonRoot": True, "runAsUser": 10001, "runAsGroup": 10001,
                            "seccompProfile": {"type": "RuntimeDefault"},
                            "appArmorProfile": {"type": "RuntimeDefault"}},
        "volumes": [{"name": "tmp", "emptyDir": {"sizeLimit": "64Mi"}},
                    {"name": "cfg", "configMap": {"name": "app"}}],
        "containers": [{
            "name": "app", "image": "registry.example/app@sha256:" + "0" * 64,
            "securityContext": {"readOnlyRootFilesystem": True, "privileged": False,
                                "allowPrivilegeEscalation": False,
                                "capabilities": {"drop": ["ALL"], "add": []}},
            "resources": {"limits": {"cpu": "500m", "memory": "256Mi", "ephemeral-storage": "1Gi"}},
            "volumeMounts": [{"name": "tmp", "mountPath": "/tmp"}, {"name": "cfg", "mountPath": "/etc/app", "readOnly": True}],
        }],
    })


ADMIN = Principal("alice", "human", frozenset({"security-admin"}))
APPROVER = Principal("bob", "human", frozenset({"approver"}))
REQUESTER = Principal("carol", "human", frozenset({"developer"}))
SERVICE = Principal("svc-ci", "service", frozenset({"approver", "evaluator"}))
ROLES = {
    "security-admin": {"baseline.install", "baseline.rollback", "emergency.toggle", "exception.revoke",
                       "quarantine.execute", "evaluate"},
    "approver": {"exception.approve", "exception.revoke"},
    "developer": {"exception.request", "evaluate"},
    "evaluator": {"evaluate"},
}


def build(tmpdir=None, doc=None, clock_src=None, report_node=True):
    ft = clock_src or FakeTime()
    clock = TrustedClock(ft)
    kr = Keyring({"release-signer": SIGN_KEY})
    ledger = AuditLedger(os.path.join(tmpdir, "audit.jsonl") if tmpdir else None, SEAL_KEY)
    authz = Authorizer(ROLES)
    store = BaselineStore(os.path.join(tmpdir, "baseline.json") if tmpdir else None, kr)
    d = doc or default_document()
    d.setdefault("seccomp_profiles", {})
    store.activate(sign_baseline(d, kr, "release-signer"), store.epoch)
    exc = ExceptionStore(ledger, clock, authz, max_ttl=30 * 86400)
    rt = RuntimeInventory({"gvisor": "runsc"}, {"runsc": (20240101, 0)})
    if report_node:
        rt.report("node-1", "runsc", "runsc version release-20240807.0", True, int(ft()))
    eng = Engine(store, exc, clock, ledger, rt, authz)
    return eng, ft, kr


def request(pod=None, workload="team-a/Deployment/api", node=None, **extra):
    r = {"workload": workload, "pod": pod if pod is not None else hardened_pod(),
         "scope": {"tenant": "team-a", "environment": "prod", "site": "eu1"},
         "facts": {"namespace_default_deny": True}}
    if node:
        r["node"] = node
    r.update(extra)
    return r
