"""Argo CD / Flux controller adapters (component 05).

INV-07 can run as the reconciler itself (``controller.py`` + a ``Target``)
or *delegate* reconciliation to an existing GitOps controller.  In delegate
mode INV-07 still owns verification, ref policy, provenance, freeze and
audit, and hands the controller an **immutable OID**, never a branch name, so
the downstream controller cannot follow an unverified head.

``ArgoCDAdapter`` / ``FluxAdapter`` render the controller's custom resource
pinned to the verified OID (Argo ``Application.spec.source.targetRevision``;
Flux ``GitRepository.spec.ref.commit`` + ``Kustomization``) and normalise the
controller's reported status into one vocabulary:

``Synced``/``Ready`` -> ``converged`` ; ``OutOfSync`` -> ``drifted`` ;
``Progressing`` -> ``in_progress`` ; ``Degraded``/``Failed``/``Stalled`` ->
``failed`` ; missing/unknown -> ``unknown`` (never treated as success).

Normalisation also refuses a status whose observed revision is not the OID we
pinned (a controller reporting success for some other commit is ``failed``).
Operations are bounded: a status poll has a deadline and a maximum number of
polls.  Talking to a live Argo CD / Flux installation needs a cluster and is
BLOCKED in this archive (see docs/COMPATIBILITY.md).
"""
from __future__ import annotations

import time

from .errors import DeadlineExceeded, Malformed

STATES = ("converged", "drifted", "in_progress", "failed", "unknown")


class ArgoCDAdapter:
    def render(self, *, name: str, repo_url: str, oid: str, path: str, dest_ns: str, project: str = "default") -> dict:
        if len(oid) not in (40, 64):
            raise Malformed("Argo CD targetRevision must be a full commit OID")
        return {"apiVersion": "argoproj.io/v1alpha1", "kind": "Application",
                "metadata": {"name": name, "namespace": "argocd",
                             "annotations": {"pk.gitops/verified-oid": oid}},
                "spec": {"project": project,
                         "source": {"repoURL": repo_url, "targetRevision": oid, "path": path},
                         "destination": {"server": "https://kubernetes.default.svc", "namespace": dest_ns},
                         "syncPolicy": {"automated": {"prune": False, "selfHeal": True},
                                        "syncOptions": ["ServerSideApply=true", "FailOnSharedResource=true"]}}}

    def normalise(self, app: dict, *, oid: str) -> dict:
        st = app.get("status") or {}
        sync = (st.get("sync") or {}).get("status")
        health = (st.get("health") or {}).get("status")
        rev = (st.get("sync") or {}).get("revision")
        if rev and rev != oid:
            return {"state": "failed", "reason": "controller reports a different revision", "revision": rev}
        if health in ("Degraded", "Missing") or (st.get("operationState") or {}).get("phase") in ("Failed", "Error"):
            return {"state": "failed", "reason": f"health={health}", "revision": rev}
        if sync == "Synced" and health == "Healthy" and rev == oid:
            return {"state": "converged", "reason": "Synced/Healthy", "revision": rev}
        if sync == "OutOfSync":
            return {"state": "drifted", "reason": "OutOfSync", "revision": rev}
        if health == "Progressing":
            return {"state": "in_progress", "reason": "Progressing", "revision": rev}
        return {"state": "unknown", "reason": f"sync={sync} health={health}", "revision": rev}


class FluxAdapter:
    def render(self, *, name: str, repo_url: str, oid: str, path: str, namespace: str = "flux-system") -> list[dict]:
        if len(oid) not in (40, 64):
            raise Malformed("Flux ref.commit must be a full commit OID")
        return [{"apiVersion": "source.toolkit.fluxcd.io/v1", "kind": "GitRepository",
                 "metadata": {"name": name, "namespace": namespace},
                 "spec": {"url": repo_url, "interval": "1m", "ref": {"commit": oid},
                          "verify": {"mode": "HEAD", "secretRef": {"name": f"{name}-trust"}}}},
                {"apiVersion": "kustomize.toolkit.fluxcd.io/v1", "kind": "Kustomization",
                 "metadata": {"name": name, "namespace": namespace},
                 "spec": {"interval": "5m", "path": path, "prune": False, "wait": True, "timeout": "5m",
                          "sourceRef": {"kind": "GitRepository", "name": name}}}]

    def normalise(self, ks: dict, *, oid: str) -> dict:
        st = ks.get("status") or {}
        conds = {c.get("type"): c for c in st.get("conditions", []) if isinstance(c, dict)}
        ready = conds.get("Ready", {})
        rev = st.get("lastAppliedRevision") or ""
        rev_oid = rev.split(":")[-1].split("/")[-1] if rev else None
        if rev_oid and rev_oid != oid:
            return {"state": "failed" if ready.get("status") == "True" else "in_progress",
                    "reason": "applied revision differs from pinned OID", "revision": rev_oid}
        if conds.get("Stalled", {}).get("status") == "True" or ready.get("reason") in ("ReconciliationFailed",
                                                                                      "BuildFailed", "HealthCheckFailed"):
            return {"state": "failed", "reason": ready.get("reason", "Stalled"), "revision": rev_oid}
        if ready.get("status") == "True" and rev_oid == oid:
            return {"state": "converged", "reason": "Ready", "revision": rev_oid}
        if conds.get("Reconciling", {}).get("status") == "True" or ready.get("status") == "Unknown":
            return {"state": "in_progress", "reason": "Reconciling", "revision": rev_oid}
        return {"state": "unknown", "reason": str(ready.get("reason")), "revision": rev_oid}


def wait_converged(poll, normalise, *, oid: str, deadline_s: float, interval: float = 2.0, max_polls: int = 600,
                   sleep=time.sleep, clock=time.monotonic) -> dict:
    end = clock() + deadline_s
    for _ in range(max_polls):
        st = normalise(poll(), oid=oid)
        if st["state"] in ("converged", "failed"):
            return st
        if clock() + interval > end:
            break
        sleep(interval)
    raise DeadlineExceeded("controller did not converge before deadline", oid=oid)
