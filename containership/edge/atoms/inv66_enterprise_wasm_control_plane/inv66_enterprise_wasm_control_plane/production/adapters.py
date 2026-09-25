"""Adjacent-layer adapters (MC-019, MC-020, MC-021).

Deployment manager (INV-63) — delivery contract ``PK_ECP_DELIVER/1``:

    PUT {endpoint}/v1/apps/{tenant}/{lattice}/{app}
        headers: Idempotency-Key: <decision_id>, traceparent
        body:    {"decision_id", "manifest_sha256", "manifest", "audit_seq"}
    2xx -> {"accepted": true, "revision": <str>}          (delivered)
    409 -> already have this decision_id (idempotent)     (delivered)
    4xx -> permanent refusal                               (rejected, non-retryable)
    5xx / timeout / connection error -> ECP_DELIVERY_FAILED (retryable)

Delivery is *at-least-once with idempotent receipt*: the decision id is the
idempotency key, so a retry after a lost acknowledgement cannot double-deploy.
The admission is journaled **before** delivery; a crash between the two leaves
the manifest ``delivery_pending`` and :meth:`Service.redeliver_pending` resumes it.

This HTTP contract is INV-66's assumption about INV-63.  wasmCloud's own wadm
speaks NATS; a wadm bridge is OPEN_EXTERNAL (no lattice is available here), and
the suites exercise the contract against a local stub server instead.

GitOps (MC-021): :class:`GitOpsIngestor` reads desired-state manifests from a
directory checkout at a *pinned commit* (``git rev-parse`` output or an explicit
revision), records ``source.repo/rev/path`` on every request, and submits each
through the normal admission path — GitOps gets no bypass.
"""
from __future__ import annotations

import json
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional, Protocol

from .errors import EcpError


class DeploymentManager(Protocol):
    def deliver(self, tenant: str, lattice: str, app: str, payload: dict[str, Any], headers: dict[str, str],
                timeout_s: float) -> dict[str, Any]: ...


class InMemoryDeploymentManager:
    """Conformant reference receiver: idempotent on decision_id; failure injection for tests."""

    def __init__(self) -> None:
        self.apps: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.received: dict[str, dict[str, Any]] = {}
        self.fail_next = 0
        self.refuse = False
        self.calls = 0
        self.headers_seen: list[dict[str, str]] = []
        self._lock = threading.Lock()

    def deliver(self, tenant, lattice, app, payload, headers, timeout_s):
        with self._lock:
            self.calls += 1
            self.headers_seen.append(dict(headers))
            if self.fail_next > 0:
                self.fail_next -= 1
                raise EcpError("ECP_DELIVERY_FAILED", "deployment manager unavailable", dependency="deployment")
            if self.refuse:
                raise EcpError("ECP_POLICY_DENIED", "deployment manager refused manifest", dependency="deployment")
            did = payload["decision_id"]
            if did in self.received:
                return {"accepted": True, "revision": self.received[did]["revision"], "duplicate": True}
            rev = f"r{len(self.received) + 1}"
            self.received[did] = {"revision": rev, **payload}
            self.apps[(tenant, lattice, app)] = {"revision": rev, "manifest_sha256": payload["manifest_sha256"]}
            return {"accepted": True, "revision": rev}


def require_http_url(endpoint: str, what: str) -> str:
    """Only http(s) endpoints: urllib would otherwise happily open file:// or ftp:// URLs."""
    u = urllib.parse.urlparse(endpoint if isinstance(endpoint, str) else "")
    if u.scheme not in ("http", "https") or not u.netloc:
        raise EcpError("ECP_CONFIG_INVALID", f"{what} endpoint must be an http(s) URL", field="endpoint")
    return endpoint


class HttpDeploymentManager:
    def __init__(self, endpoint: str):
        self.endpoint = require_http_url(endpoint, "deployment manager").rstrip("/")

    def deliver(self, tenant, lattice, app, payload, headers, timeout_s):
        q = urllib.parse.quote
        url = f"{self.endpoint}/v1/apps/{q(tenant, safe='')}/{q(lattice, safe='')}/{q(app, safe='')}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT",  # noqa: S310
                                     headers={"Content-Type": "application/json",
                                              "Idempotency-Key": payload["decision_id"], **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 - scheme checked in __init__
                body = json.loads(resp.read(1_000_000) or b"{}")
                return {"accepted": True, "revision": str(body.get("revision", ""))[:128]}
        except urllib.error.HTTPError as e:
            if e.code == 409:
                return {"accepted": True, "revision": "", "duplicate": True}
            if 400 <= e.code < 500:
                raise EcpError("ECP_POLICY_DENIED", "deployment manager refused manifest",
                               dependency="deployment", observed=e.code) from None
            raise EcpError("ECP_DELIVERY_FAILED", "deployment manager error", dependency="deployment",
                           observed=e.code) from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise EcpError("ECP_DELIVERY_FAILED", "deployment manager unreachable", dependency="deployment") from None


class GitOpsIngestor:
    """Desired state from a repository checkout at a pinned revision."""

    def __init__(self, checkout: Path, repo_url: str, *, tenant: str, lattice: str, glob: str = "apps/*.json"):
        self.checkout = Path(checkout)
        self.repo_url = repo_url
        self.tenant = tenant
        self.lattice = lattice
        self.glob = glob

    def revision(self) -> str:
        try:
            out = subprocess.run(["git", "-C", str(self.checkout), "rev-parse", "HEAD"], capture_output=True,
                                 text=True, timeout=10, check=True)
            return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            raise EcpError("ECP_DEPENDENCY_UNAVAILABLE", "cannot resolve checkout revision", dependency="gitops") from None

    def requests(self, revision: Optional[str] = None) -> list[dict[str, Any]]:
        rev = revision or self.revision()
        out = []
        for p in sorted(self.checkout.glob(self.glob)):
            try:
                manifest = json.loads(p.read_text())
            except ValueError:
                raise EcpError("ECP_MANIFEST_INVALID", "desired-state file is not JSON",
                               field=p.name[:128]) from None
            rel = p.relative_to(self.checkout).as_posix()
            manifest = {**manifest, "source": {"repo": self.repo_url, "rev": rev, "path": rel}}
            out.append({"protocol": "PK_ECP_ADMIT/1", "request_id": f"gitops-{rev[:12]}-{p.stem}"[:128],
                        "idempotency_key": f"gitops-{rev}-{rel}"[:128].replace("/", "_"),
                        "tenant": self.tenant, "lattice": self.lattice, "manifest": manifest})
        return out
