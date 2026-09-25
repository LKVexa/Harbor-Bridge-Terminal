"""MC-04: workload identity attestation.

A workload identity is issued only when (a) the hosting node holds a valid,
unexpired, non-quarantined verdict at a level >= the workload's trust class,
(b) the workload's image/config digest is in the tenant's allow-list, and
(c) the request names the tenant the workload belongs to.  The resulting
``WorkloadToken`` is Ed25519-signed by the service key and binds
(workload, tenant, node, node verdict binding, image digest, expiry).  Its
lifetime never exceeds the node verdict's remaining lifetime.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from . import algorithms as alg
from .errors import fail

RANK = {"untrusted": 0, "software": 1, "hardware": 2}


@dataclass
class WorkloadIssuer:
    keystore: object
    key_name: str
    principal: str = "gap06-workload"
    max_ttl: float = 900.0

    def issue(self, *, workload: str, tenant: str, node: str, node_verdict: dict, quarantined: bool,
              image_digest: str, allowed_images: dict, trust_class: str, now: float) -> dict:
        if trust_class not in RANK or trust_class == "untrusted":
            raise fail("E_SCHEMA", "trust_class must be software|hardware")
        if quarantined:
            raise fail("E_FORBIDDEN", "host node is quarantined")
        if not node_verdict or node_verdict.get("node") != node or now >= node_verdict["expires_at"]:
            raise fail("E_FORBIDDEN", "host node has no valid verdict")
        if RANK[node_verdict["level"]] < RANK[trust_class]:
            raise fail("E_FORBIDDEN", "host attestation level below workload trust class")
        if image_digest not in allowed_images.get(tenant, set()):
            raise fail("E_MEASUREMENT_REJECTED", "workload image not allowed for tenant")
        exp = min(now + self.max_ttl, node_verdict["expires_at"])
        claims = {"schema": "GAP06-WORKLOAD/1", "workload": workload, "tenant": tenant, "node": node,
                  "node_binding": node_verdict["binding"], "image": image_digest, "class": trust_class,
                  "iat": now, "exp": exp}
        body = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
        kid = f"{self.key_name}/v{self.keystore._versions[self.key_name]}"
        sig = self.keystore.sign(kid, body, principal=self.principal)
        return {"claims": claims, "kid": kid, "sig": sig.hex()}

    @staticmethod
    def verify(token: dict, public_keys: dict, *, now: float, tenant: str) -> dict:
        body = json.dumps(token["claims"], sort_keys=True, separators=(",", ":")).encode()
        pem = public_keys.get(token["kid"])
        if pem is None:
            raise fail("E_UNKNOWN_KEY", "unknown workload token key")
        alg.verify(alg.load_public_key(pem), "ed25519", bytes.fromhex(token["sig"]), body)
        c = token["claims"]
        if now >= c["exp"]:
            raise fail("E_CHALLENGE_EXPIRED", "workload token expired")
        if c["tenant"] != tenant:
            raise fail("E_TENANT_BOUNDARY", "workload token for another tenant")
        return c
