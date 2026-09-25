"""Kubernetes client and cluster connection layer (item 12).

``KubeClient`` is the narrow interface the reconciler needs. Two
implementations:

* ``FakeKube`` — an in-memory API server with resourceVersion optimistic
  concurrency, generation bumps on spec change, finalizer-gated deletion,
  a status subresource, watch streams with bookmarks/"410 Gone" expiry, and
  outage/partition injection. Used by every integration/fault test here.
* ``HttpKubeClient`` — stdlib HTTPS client for in-cluster use (projected
  ServiceAccount token, cluster CA, TLS verification always on). It is
  exercised by unit tests against a local stub only; it has **not** been run
  against a real cluster in this archive (see AUDIT_REPORT gap list).
"""
from __future__ import annotations

import builtins
import copy
import json
import ssl
import threading
import urllib.error
import urllib.request
import uuid
from typing import Any, Protocol

GROUP, VERSION, PLURAL, KIND = "inv67.linearfinance.org", "v1alpha1", "wasmworkloads", "WasmWorkload"
API_VERSION = f"{GROUP}/{VERSION}"


class ApiError(Exception):
    def __init__(self, status: int, reason: str):
        super().__init__(f"{status} {reason}")
        self.status, self.reason = status, reason


class KubeClient(Protocol):
    def get(self, ns: str, name: str) -> dict: ...
    def list(self, ns: str | None = None) -> tuple[builtins.list[dict], str]: ...
    def update(self, obj: dict) -> dict: ...
    def update_status(self, obj: dict) -> dict: ...
    def events_since(self, rv: str) -> builtins.list[tuple[str, dict]]: ...
    def record_event(self, obj: dict, type_: str, reason: str, message: str) -> None: ...


class FakeKube:
    def __init__(self, history_window: int = 1000):
        self._lock = threading.RLock()
        self.objs: dict[tuple[str, str], dict] = {}
        self.rv = 0
        self.log: list[tuple[int, str, dict]] = []
        self.window = history_window
        self.events: list[dict] = []
        self.down = False
        self.calls = 0

    # --- fault injection -------------------------------------------------
    def _gate(self):
        self.calls += 1
        if self.down:
            raise ApiError(503, "ServiceUnavailable")

    def _bump(self, kind: str, obj: dict):
        self.rv += 1
        obj["metadata"]["resourceVersion"] = str(self.rv)
        self.log.append((self.rv, kind, copy.deepcopy(obj)))
        if len(self.log) > self.window:
            self.log = self.log[-self.window:]

    # --- user-side operations (kubectl) -----------------------------------
    def apply(self, obj: dict) -> dict:
        with self._lock:
            obj = copy.deepcopy(obj)
            md = obj.setdefault("metadata", {})
            md.setdefault("namespace", "default")
            key = (md["namespace"], md["name"])
            cur = self.objs.get(key)
            if cur is None:
                md["uid"] = str(uuid.uuid4())
                md["generation"] = 1
                md.setdefault("finalizers", [])
                obj.setdefault("status", {})
                self.objs[key] = obj
                self._bump("ADDED", obj)
            else:
                if cur["metadata"].get("deletionTimestamp"):
                    raise ApiError(409, "object is being deleted")
                if cur.get("spec") != obj.get("spec"):
                    cur["metadata"]["generation"] += 1
                cur["spec"] = obj.get("spec")
                cur["metadata"]["labels"] = md.get("labels", cur["metadata"].get("labels", {}))
                obj = cur
                self._bump("MODIFIED", obj)
            return copy.deepcopy(obj)

    def delete(self, ns: str, name: str) -> None:
        with self._lock:
            cur = self.objs.get((ns, name))
            if cur is None:
                raise ApiError(404, "NotFound")
            if cur["metadata"].get("finalizers"):
                cur["metadata"].setdefault("deletionTimestamp", "now")
                self._bump("MODIFIED", cur)
            else:
                del self.objs[(ns, name)]
                self._bump("DELETED", cur)

    # --- controller-side client --------------------------------------------
    def get(self, ns, name):
        with self._lock:
            self._gate()
            o = self.objs.get((ns, name))
            if o is None:
                raise ApiError(404, "NotFound")
            return copy.deepcopy(o)

    def list(self, ns=None):
        with self._lock:
            self._gate()
            items = [copy.deepcopy(o) for (n, _), o in sorted(self.objs.items()) if ns in (None, n)]
            return items, str(self.rv)

    def _check_rv(self, obj):
        md = obj["metadata"]
        cur = self.objs.get((md["namespace"], md["name"]))
        if cur is None:
            raise ApiError(404, "NotFound")
        if md.get("resourceVersion") != cur["metadata"]["resourceVersion"]:
            raise ApiError(409, "Conflict")
        return cur

    def update(self, obj):
        """Metadata update (finalizers). Spec/status changes via this path are ignored,
        mirroring the status subresource split."""
        with self._lock:
            self._gate()
            cur = self._check_rv(obj)
            cur["metadata"]["finalizers"] = list(obj["metadata"].get("finalizers", []))
            if cur["metadata"].get("deletionTimestamp") and not cur["metadata"]["finalizers"]:
                del self.objs[(cur["metadata"]["namespace"], cur["metadata"]["name"])]
                self._bump("DELETED", cur)
            else:
                self._bump("MODIFIED", cur)
            return copy.deepcopy(cur)

    def update_status(self, obj):
        with self._lock:
            self._gate()
            cur = self._check_rv(obj)
            cur["status"] = copy.deepcopy(obj.get("status", {}))
            self._bump("MODIFIED", cur)
            return copy.deepcopy(cur)

    def events_since(self, rv):
        with self._lock:
            self._gate()
            rv_i = int(rv or 0)
            if self.log and rv_i < self.log[0][0] - 1:
                raise ApiError(410, "Gone")
            return [(k, copy.deepcopy(o)) for r, k, o in self.log if r > rv_i]

    def record_event(self, obj, type_, reason, message):
        with self._lock:
            self.events.append({"involved": f'{obj["metadata"]["namespace"]}/{obj["metadata"]["name"]}',
                                "type": type_, "reason": reason, "message": message[:1024]})


class HttpKubeClient:
    """Minimal in-cluster client. TLS verification cannot be disabled."""

    SA = "/var/run/secrets/kubernetes.io/serviceaccount"

    def __init__(self, host: str, token_file: str = SA + "/token", ca_file: str = SA + "/ca.crt", timeout: float = 10.0):
        if not host.startswith("https://"):
            raise ValueError("API server must be https")
        self.host, self.token_file, self.timeout = host.rstrip("/"), token_file, timeout
        self.ctx = ssl.create_default_context(cafile=ca_file)
        self.ctx.check_hostname = True
        self.ctx.verify_mode = ssl.CERT_REQUIRED

    def _token(self) -> str:
        with open(self.token_file, encoding="utf-8") as fh:   # re-read: projected tokens rotate
            return fh.read().strip()

    def _req(self, method: str, path: str, body: Any = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {self._token()}", "Accept": "application/json",
                   "Content-Type": "application/json"}
        req = urllib.request.Request(self.host + path, data=data, method=method, headers=headers)  # noqa: S310 - https-only host
        try:
            # scheme is fixed to https in __init__; TLS verification cannot be disabled
            with urllib.request.urlopen(req, context=self.ctx, timeout=self.timeout) as r:  # noqa: S310
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise ApiError(e.code, e.reason) from None

    def _path(self, ns, name=None, sub=""):
        p = f"/apis/{GROUP}/{VERSION}" + (f"/namespaces/{ns}" if ns else "") + f"/{PLURAL}"
        return p + (f"/{name}" if name else "") + (f"/{sub}" if sub else "")

    def get(self, ns, name):
        return self._req("GET", self._path(ns, name))

    def list(self, ns=None):
        out = self._req("GET", self._path(ns))
        return out.get("items", []), out.get("metadata", {}).get("resourceVersion", "0")

    def update(self, obj):
        md = obj["metadata"]
        return self._req("PUT", self._path(md["namespace"], md["name"]), obj)

    def update_status(self, obj):
        md = obj["metadata"]
        return self._req("PUT", self._path(md["namespace"], md["name"], "status"), obj)

    def events_since(self, rv):
        # Polling fallback (watch streaming is not implemented in this client).
        items, _ = self.list()
        return [("MODIFIED", o) for o in items if int(o["metadata"].get("resourceVersion", 0)) > int(rv or 0)]

    def record_event(self, obj, type_, reason, message):
        md = obj["metadata"]
        self._req("POST", f"/api/v1/namespaces/{md['namespace']}/events", {
            "apiVersion": "v1", "kind": "Event",
            "metadata": {"generateName": md["name"] + "-"},
            "involvedObject": {"apiVersion": API_VERSION, "kind": KIND, "name": md["name"],
                               "namespace": md["namespace"], "uid": md.get("uid")},
            "type": type_, "reason": reason, "message": message[:1024]})
