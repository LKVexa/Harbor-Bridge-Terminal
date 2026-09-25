"""Kubernetes admission adapter (validating webhook) over the 4.3.0 engine.

Checklist item served: 3 (production binding that calls the evaluator before
execution) - the AdmissionReview v1 translation, pod-template extraction for
every workload kind, and a TLS-capable HTTP server. Registering it with a real
API server (ValidatingWebhookConfiguration, failurePolicy: Fail, CA bundle) is
the integration half and stays BLOCKED without a cluster.
"""
from __future__ import annotations

import json
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

from .engine import Engine

MAX_BODY = 3 * 1024 * 1024
TEMPLATE_PATHS = {
    "Pod": ("spec",),
    "Deployment": ("spec", "template", "spec"),
    "ReplicaSet": ("spec", "template", "spec"),
    "StatefulSet": ("spec", "template", "spec"),
    "DaemonSet": ("spec", "template", "spec"),
    "Job": ("spec", "template", "spec"),
    "ReplicationController": ("spec", "template", "spec"),
    "CronJob": ("spec", "jobTemplate", "spec", "template", "spec"),
}


def _m(v: object) -> Mapping:
    return v if isinstance(v, Mapping) else {}


def extract_pod_spec(obj: object) -> tuple[str | None, Mapping | None]:
    if not isinstance(obj, Mapping):
        return None, None
    kind = obj.get("kind")
    path = TEMPLATE_PATHS.get(kind) if isinstance(kind, str) else None
    if path is None:
        return kind if isinstance(kind, str) else None, None
    cur: Any = obj
    for p in path:
        cur = cur.get(p) if isinstance(cur, Mapping) else None
    return kind, cur if isinstance(cur, Mapping) else None


def review(engine: Engine, body: object, cluster_scope: Mapping[str, str]) -> dict:
    """Translate one AdmissionReview; every failure path answers allowed=false."""
    uid = body.get("request", {}).get("uid") if isinstance(body, Mapping) and isinstance(body.get("request"), Mapping) else None
    uid = uid if isinstance(uid, str) and len(uid) <= 128 else ""

    def answer(allowed: bool, msg: str, code: int, extra: dict | None = None) -> dict:
        resp = {"uid": uid, "allowed": allowed, "status": {"code": code, "message": msg[:1024]}}
        if extra:
            resp["auditAnnotations"] = {k: str(v)[:256] for k, v in extra.items()}
        return {"apiVersion": "admission.k8s.io/v1", "kind": "AdmissionReview", "response": resp}

    if not isinstance(body, Mapping) or body.get("apiVersion") != "admission.k8s.io/v1" \
            or body.get("kind") != "AdmissionReview" or not uid:
        return answer(False, "INV-03: malformed AdmissionReview", 400)
    req = body["request"]
    if not isinstance(req, Mapping):
        return answer(False, "INV-03: malformed request", 400)
    if req.get("operation") not in ("CREATE", "UPDATE"):
        return answer(True, "INV-03: operation not evaluated", 200)
    kind, pod = extract_pod_spec(req.get("object"))
    if pod is None:
        return answer(False, f"INV-03: unsupported or malformed object kind {kind!r}", 400)
    ns = req.get("namespace") if isinstance(req.get("namespace"), str) else ""
    meta = _m(_m(req.get("object")).get("metadata"))
    name = meta.get("name") if isinstance(meta.get("name"), str) else (
        req.get("name") if isinstance(req.get("name"), str) else "<generated>")
    decision = engine.decide({
        "workload": f"{ns}/{kind}/{name}", "pod": pod,
        "scope": {"tenant": ns or "cluster", "environment": str(cluster_scope.get("environment", "")),
                  "site": str(cluster_scope.get("site", ""))},
        "facts": {"namespace_default_deny": _m(cluster_scope.get("default_deny")).get(ns) is True},
        "traceparent": _m(meta.get("annotations")).get("traceparent"),
    })
    if decision["admit"]:
        return answer(True, "INV-03: admitted", 200, {"inv03/decision": decision["decision_id"],
                                                       "inv03/baseline": decision.get("baseline_digest", "")})
    detail = "; ".join(decision["failed"] or decision["errors"])
    return answer(False, f"INV-03 {decision['reason']}: {detail}", 403, {"inv03/decision": decision["decision_id"]})


def make_server(engine: Engine, host: str, port: int, cluster_scope: Mapping[str, str],
                certfile: str | None = None, keyfile: str | None = None) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                n = -1
            if not (0 < n <= MAX_BODY) or self.path != "/validate":
                out = review(engine, None, cluster_scope)
            else:
                try:
                    out = review(engine, json.loads(self.rfile.read(n)), cluster_scope)
                except (ValueError, UnicodeDecodeError):
                    out = review(engine, None, cluster_scope)
            data = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802
            if self.path in ("/healthz", "/readyz"):
                ready = engine.baselines.active() is not None
                self.send_response(200 if ready or self.path == "/healthz" else 503)
                self.end_headers()
                self.wfile.write(b"ok" if ready else b"no baseline")
            elif self.path == "/metrics":
                data = engine.metrics.prometheus().encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *a):  # structured logger handles logging
            pass

    srv = ThreadingHTTPServer((host, port), Handler)
    if certfile:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(certfile, keyfile)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    return srv


WEBHOOK_CONFIGURATION = {
    "apiVersion": "admissionregistration.k8s.io/v1",
    "kind": "ValidatingWebhookConfiguration",
    "metadata": {"name": "inv03-container-hardening"},
    "webhooks": [{
        "name": "inv03.hardening.pk",
        "failurePolicy": "Fail",
        "sideEffectClass": "None",
        "admissionReviewVersions": ["v1"],
        "timeoutSeconds": 5,
        "clientConfig": {"service": {"namespace": "inv03-system", "name": "inv03-webhook", "path": "/validate"},
                         "caBundle": "<SET-AT-INSTALL>"},
        "rules": [{"apiGroups": ["", "apps", "batch"], "apiVersions": ["v1"], "operations": ["CREATE", "UPDATE"],
                   "resources": ["pods", "pods/ephemeralcontainers", "deployments", "replicasets", "statefulsets",
                                 "daemonsets", "jobs", "cronjobs", "replicationcontrollers"]}],
        "namespaceSelector": {"matchExpressions": [{"key": "inv03.exempt-system", "operator": "DoesNotExist"}]},
    }],
}
