"""Live-state reader and applier (component 06).

``Target`` is the control-plane port.  Every write carries:

* ``expected_version`` -- optimistic concurrency precondition
  (``resourceVersion``); a mismatch is ``Conflict`` (retryable after re-read);
* ``epoch`` -- the lease fencing token checked by ``FenceGate``;
* field ownership -- objects carry ``metadata.annotations["pk.gitops/managed-by"]``;
  an object owned by someone else is never overwritten or deleted
  (``Conflict``), which is how INV-05's live control store and humans keep
  their own objects;
* destructive safety -- ``delete`` requires ``allow_delete`` (config
  ``controller.prune``) *and* our ownership *and* the version precondition.

Implementations:

``DirectoryTarget``
  a durable, file-backed control store (one JSON file per resource, atomic
  replace, per-resource version counter).  It is a genuine applier -- used for
  air-gapped/edge sites and as the reference target in tests.
``KubernetesTarget``
  server-side apply over the Kubernetes REST API (``PATCH`` with
  ``application/apply-patch+yaml``, ``fieldManager=inv07-gitops``,
  ``force=false``; ``DELETE`` with ``preconditions.resourceVersion``).  The
  HTTP transport is injected; with no cluster in this archive it is exercised
  only against a recording transport, so its production acceptance is BLOCKED.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import threading
import urllib.parse
from typing import Callable, Protocol

from .fsutil import load_json, read_bytes, read_text  # noqa: F401
from .canonical import canonicalize
from .errors import Conflict, Malformed, TargetUnavailable, TenantViolation
from .lease import FenceGate

OWNER_ANN = "pk.gitops/managed-by"
REV_ANN = "pk.gitops/revision"


def rid_str(rid: tuple) -> str:
    return "/".join(x or "_" for x in rid)


def obj_digest(obj: dict) -> str:
    o = copy.deepcopy(obj)
    md = o.get("metadata", {})
    for k in ("resourceVersion", "uid", "generation", "creationTimestamp", "managedFields"):
        md.pop(k, None)
    anns = md.get("annotations", {})
    anns.pop(REV_ANN, None)
    if not anns:
        md.pop("annotations", None)
    o.pop("status", None)
    return hashlib.sha256(canonicalize(o).encode()).hexdigest()


class Target(Protocol):
    def list(self) -> dict: ...
    def apply(self, rid: tuple, obj: dict, *, expected_version: str | None, epoch: int, owner: str,
              dry_run: bool = False) -> str: ...
    def delete(self, rid: tuple, *, expected_version: str, epoch: int, owner: str, compensate: bool = False) -> None: ...


class DirectoryTarget:
    def __init__(self, root: str, *, fence_path: str | None = None, allow_delete: bool = False,
                 namespaces: tuple[str, ...] | None = None, fail: Callable[[str, tuple], None] | None = None) -> None:
        self.root = root
        os.makedirs(root, exist_ok=True)
        self.fence = FenceGate(fence_path or os.path.join(root, ".fence"))
        self.allow_delete, self.namespaces = allow_delete, namespaces
        self._lock = threading.RLock()
        self._fail = fail  # fault-injection hook for tests

    def _path(self, rid: tuple) -> str:
        name = hashlib.sha256(rid_str(rid).encode()).hexdigest()[:32]
        return os.path.join(self.root, name + ".json")

    def _ns_ok(self, rid: tuple) -> None:
        if self.namespaces is not None and rid[2] and rid[2] not in self.namespaces:
            raise TenantViolation("namespace outside the tenant's allowed set", namespace=rid[2])

    def list(self) -> dict:
        with self._lock:
            out = {}
            for fn in os.listdir(self.root):
                if fn.endswith(".json"):
                    doc = load_json(os.path.join(self.root, fn))
                    out[tuple(doc["rid"])] = (doc["obj"], doc["version"])
            return out

    def get(self, rid: tuple):
        p = self._path(rid)
        if not os.path.exists(p):
            return None, None
        doc = load_json(p)
        return doc["obj"], doc["version"]

    def apply(self, rid, obj, *, expected_version, epoch, owner, dry_run=False):
        with self._lock:
            self._ns_ok(rid)
            if self._fail:
                self._fail("apply", rid)
            self.fence.check(epoch)
            cur, ver = self.get(rid)
            if cur is not None:
                cur_owner = cur.get("metadata", {}).get("annotations", {}).get(OWNER_ANN)
                if cur_owner != owner:
                    raise Conflict("object owned by another manager", rid=rid_str(rid), owner=str(cur_owner))
            if ver != expected_version:
                raise Conflict("resourceVersion precondition failed", rid=rid_str(rid))
            new = copy.deepcopy(obj)
            new.setdefault("metadata", {}).setdefault("annotations", {})[OWNER_ANN] = owner
            nv = str(int(ver or 0) + 1)
            if dry_run:
                return nv
            tmp = self._path(rid) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"rid": list(rid), "obj": new, "version": nv}, fh, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self._path(rid))
            return nv

    def delete(self, rid, *, expected_version, epoch, owner, compensate=False):
        with self._lock:
            if not self.allow_delete and not compensate:
                raise Conflict("deletion disabled (controller.prune=false)", rid=rid_str(rid))
            if self._fail:
                self._fail("delete", rid)
            self.fence.check(epoch)
            cur, ver = self.get(rid)
            if cur is None:
                return
            if cur.get("metadata", {}).get("annotations", {}).get(OWNER_ANN) != owner:
                raise Conflict("refusing to delete an object we do not own", rid=rid_str(rid))
            if ver != expected_version:
                raise Conflict("resourceVersion precondition failed", rid=rid_str(rid))
            os.unlink(self._path(rid))

    # out-of-band mutation helper (tests / drift simulation)
    def tamper(self, rid, mutate):
        with self._lock:
            cur, ver = self.get(rid)
            mutate(cur)
            with open(self._path(rid), "w") as fh:
                json.dump({"rid": list(rid), "obj": cur, "version": str(int(ver) + 1)}, fh)


_PLURAL = {"Deployment": "deployments", "Service": "services", "ConfigMap": "configmaps", "Secret": "secrets",
           "Namespace": "namespaces", "ServiceAccount": "serviceaccounts", "Role": "roles",
           "RoleBinding": "rolebindings", "StatefulSet": "statefulsets", "DaemonSet": "daemonsets",
           "Ingress": "ingresses", "NetworkPolicy": "networkpolicies", "Job": "jobs", "CronJob": "cronjobs"}
_CLUSTER_SCOPED = {"Namespace", "ClusterRole", "ClusterRoleBinding", "CustomResourceDefinition"}


class KubernetesTarget:
    """Server-side-apply adapter.  ``transport(method, path, headers, body) -> (status, bytes)``."""

    FIELD_MANAGER = "inv07-gitops"

    def __init__(self, transport, *, fence: FenceGate, allow_delete: bool = False,
                 namespaces: tuple[str, ...] | None = None) -> None:
        self.t, self.fence, self.allow_delete, self.namespaces = transport, fence, allow_delete, namespaces

    def path(self, api_version: str, kind: str, ns: str, name: str) -> str:
        if kind not in _PLURAL and kind not in _CLUSTER_SCOPED:
            raise Malformed("kind not in the supported discovery table", kind=kind)
        plural = _PLURAL.get(kind, kind.lower() + "s")
        base = f"/api/{api_version}" if "/" not in api_version else f"/apis/{api_version}"
        for part in (ns, name):
            if part and not re.fullmatch(r"[a-z0-9]([-a-z0-9.]*[a-z0-9])?", part):
                raise Malformed("unsafe path component")
        mid = f"/namespaces/{ns}" if ns and kind not in _CLUSTER_SCOPED else ""
        return f"{base}{mid}/{plural}/{urllib.parse.quote(name)}"

    def apply(self, rid, obj, *, expected_version, epoch, owner, dry_run=False):
        if self.namespaces is not None and rid[2] and rid[2] not in self.namespaces:
            raise TenantViolation("namespace outside the tenant's allowed set", namespace=rid[2])
        self.fence.check(epoch)
        body = copy.deepcopy(obj)
        md = body.setdefault("metadata", {})
        md.setdefault("annotations", {})[OWNER_ANN] = owner
        if expected_version:
            md["resourceVersion"] = expected_version
        q = f"?fieldManager={self.FIELD_MANAGER}&force=false" + ("&dryRun=All" if dry_run else "")
        st, data = self.t("PATCH", self.path(obj["apiVersion"], obj["kind"], rid[2], rid[3]) + q,
                          {"Content-Type": "application/apply-patch+yaml"}, json.dumps(body).encode())
        if st == 409:
            raise Conflict("server-side apply conflict", rid=rid_str(rid))
        if st >= 500 or st == 0:
            raise TargetUnavailable("control plane unavailable", status=st)
        if st >= 400:
            raise Conflict("control plane rejected apply", status=st, rid=rid_str(rid))
        return json.loads(data or b"{}").get("metadata", {}).get("resourceVersion", "")

    def delete(self, rid, *, expected_version, epoch, owner, compensate=False):
        if not self.allow_delete and not compensate:
            raise Conflict("deletion disabled (controller.prune=false)", rid=rid_str(rid))
        self.fence.check(epoch)
        kind = rid[1]
        api = (rid[0] + "/v1") if rid[0] else "v1"
        body = {"kind": "DeleteOptions", "apiVersion": "v1", "preconditions": {"resourceVersion": expected_version},
                "propagationPolicy": "Foreground"}
        st, _ = self.t("DELETE", self.path(api, kind, rid[2], rid[3]), {"Content-Type": "application/json"},
                       json.dumps(body).encode())
        if st == 409:
            raise Conflict("delete precondition failed", rid=rid_str(rid))
        if st >= 500 or st == 0:
            raise TargetUnavailable("control plane unavailable", status=st)

    def list(self) -> dict:  # pragma: no cover - needs a cluster
        raise TargetUnavailable("KubernetesTarget.list requires a live cluster (label-selector watch)")
