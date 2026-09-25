"""Adjacent-layer integration adapters (MC-019 / MC-020 / MC-033).

Each dependency is a narrow ``Protocol`` plus a production HTTP(S) adapter and
an in-process reference implementation used by tests and air-gapped installs:

* GAP-13 policy engine   -> :class:`PolicyEngine` (``HttpPolicyEngine``, ``RulePolicyEngine``)
* INV-63 deployment mgr  -> :class:`DeploymentManager` (``HttpDeploymentManager``, ``InMemoryDeploymentManager``)
* INV-64 application model -> :func:`manifest_from_application`
* audit anchoring (WORM) -> :class:`FileWormSink`

HTTP adapters speak JSON over HTTPS with mTLS (``ssl.SSLContext`` supplied by
the caller), a per-call timeout derived from the request deadline, and send
``traceparent`` and ``Idempotency-Key`` headers.  All are wrapped by
:func:`resilience.call_with_policy` in :mod:`service`.
"""
from __future__ import annotations

import json
import os
import pathlib
import ssl
import threading
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from .canonical import canonical_json
from .errors import fail


# --------------------------------------------------------------------- policy
@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    policy_version: str
    rule: str | None = None
    message: str = ""


class PolicyEngine(Protocol):
    def evaluate(self, input_doc: dict, timeout_s: float, traceparent: str) -> PolicyDecision: ...


class RulePolicyEngine:
    """Deterministic local rules; used when GAP-13 is embedded or for tests.

    rules: list of {"id", "deny_if": {"environment": "...", "lattice_prefix": "...",
    "max_components": N, "image_contains": "..."}}
    """

    def __init__(self, rules: list[dict], version: str):
        self.rules = rules
        self.version = version

    def evaluate(self, input_doc: dict, timeout_s: float, traceparent: str) -> PolicyDecision:
        for rule in self.rules:
            cond = rule.get("deny_if", {})
            hit = True
            if "environment" in cond:
                hit &= input_doc.get("environment") == cond["environment"]
            if "lattice_prefix" in cond:
                hit &= str(input_doc.get("lattice", "")).startswith(cond["lattice_prefix"])
            if "max_components" in cond:
                hit &= len(input_doc["manifest"]["components"]) > cond["max_components"]
            if "image_contains" in cond:
                hit &= any(cond["image_contains"] in c.get("image", "") for c in input_doc["manifest"]["components"])
            if hit and cond:
                return PolicyDecision(False, self.version, rule["id"], rule.get("message", "denied by rule"))
        return PolicyDecision(True, self.version)


def _post_json(url: str, body: dict, timeout_s: float, headers: dict[str, str], ctx: ssl.SSLContext | None) -> dict:
    req = urllib.request.Request(url, data=canonical_json(body), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=max(0.001, timeout_s), context=ctx) as resp:  # noqa: S310
        raw = resp.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("response too large")
        return json.loads(raw)


class HttpPolicyEngine:
    """GAP-13 over HTTPS.  The response must echo the pinned bundle version."""

    def __init__(self, url: str, pinned_version: str, ssl_context: ssl.SSLContext | None = None):
        if not url.startswith("https://") and not url.startswith("http://127.0.0.1"):
            raise ValueError("policy engine URL must be https")
        self.url, self.pinned, self.ctx = url, pinned_version, ssl_context

    def evaluate(self, input_doc: dict, timeout_s: float, traceparent: str) -> PolicyDecision:
        out = _post_json(self.url, {"input": input_doc}, timeout_s, {"traceparent": traceparent}, self.ctx)
        ver = out.get("policy_version")
        if ver != self.pinned:
            raise fail("POLICY_UNAVAILABLE", f"policy bundle {ver!r} is not the pinned {self.pinned!r}")
        if not isinstance(out.get("allowed"), bool):
            raise fail("POLICY_UNAVAILABLE", "malformed policy response")
        return PolicyDecision(out["allowed"], ver, out.get("rule"), out.get("message", ""))


# ----------------------------------------------------------------- deployment
@dataclass(frozen=True)
class DeliveryAck:
    delivery_id: str
    accepted: bool
    remote_ref: str = ""


class DeploymentManager(Protocol):
    def deliver(self, delivery_id: str, lattice: str, manifest: dict, timeout_s: float,
                traceparent: str) -> DeliveryAck: ...


class InMemoryDeploymentManager:
    """Reference INV-63 double: idempotent on ``delivery_id``; can inject failures."""

    def __init__(self):
        self.received: dict[str, dict] = {}
        self.fail_next = 0
        self._lock = threading.Lock()

    def deliver(self, delivery_id, lattice, manifest, timeout_s, traceparent):
        with self._lock:
            if self.fail_next > 0:
                self.fail_next -= 1
                raise ConnectionError("injected deployment-manager outage")
            self.received.setdefault(delivery_id, {"lattice": lattice, "manifest": manifest})
            return DeliveryAck(delivery_id, True, f"inv63:{delivery_id}")


class HttpDeploymentManager:
    def __init__(self, url: str, ssl_context: ssl.SSLContext | None = None):
        self.url, self.ctx = url, ssl_context

    def deliver(self, delivery_id, lattice, manifest, timeout_s, traceparent):
        out = _post_json(self.url, {"delivery_id": delivery_id, "lattice": lattice, "manifest": manifest},
                         timeout_s, {"traceparent": traceparent, "Idempotency-Key": delivery_id}, self.ctx)
        if out.get("delivery_id") != delivery_id:
            raise ValueError("ack for a different delivery")
        return DeliveryAck(delivery_id, bool(out.get("accepted")), str(out.get("ref", "")))


# ----------------------------------------------------------- INV-64 app model
def manifest_from_application(app: dict) -> dict:
    """Normalise an INV-64 application-model document into an admission manifest."""
    if not isinstance(app, dict) or app.get("apiVersion") != "core.oam.dev/v1beta1" or app.get("kind") != "Application":
        raise fail("SCHEMA_INVALID", "not an INV-64 Application (core.oam.dev/v1beta1)")
    comps = []
    for c in app.get("spec", {}).get("components", []):
        props = c.get("properties", {})
        comps.append({k: v for k, v in {
            "name": c.get("name"), "image": props.get("image"),
            "signer": props.get("signer"), "signature": props.get("signature"),
            "attestations": props.get("attestations")}.items() if v is not None})
    meta = app.get("metadata", {})
    return {"name": meta.get("name", "app"), "version": str(meta.get("annotations", {}).get("version", "0")),
            "components": comps}


# ------------------------------------------------------------- audit anchors
class FileWormSink:
    """Append-only anchor sink on a separate volume (object-lock bucket in prod)."""

    def __init__(self, path: str | os.PathLike):
        self.path = pathlib.Path(path)

    def publish(self, anchor: dict) -> None:
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, canonical_json(anchor) + b"\n")
            os.fsync(fd)
        finally:
            os.close(fd)

    def read(self) -> list[dict]:
        return [json.loads(l) for l in self.path.read_text().splitlines()] if self.path.exists() else []
