"""INV-38-C045 — Supply-chain verification: signed manifest + digest checks."""
from __future__ import annotations
import hashlib, hmac, json
from dataclasses import dataclass

class VerificationError(RuntimeError):
    code = "PK_BYPASS_ARTIFACT_UNVERIFIED"

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sign(manifest: dict, key: bytes) -> str:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()

def verify_signature(manifest: dict, signature: str, key: bytes) -> None:
    if not hmac.compare_digest(sign(manifest, key), signature):
        raise VerificationError("manifest signature mismatch")

def verify_artifacts(manifest: dict, artifacts: dict[str, bytes], signature: str, key: bytes) -> None:
    """Fail closed on missing/invalid provenance or signature (C045-T07)."""
    verify_signature(manifest, signature, key)
    for name, expected in manifest.get("digests", {}).items():
        if name not in artifacts:
            raise VerificationError(f"artifact {name} missing")
        if sha256_bytes(artifacts[name]) != expected:
            raise VerificationError(f"artifact {name} digest mismatch (tamper)")

@dataclass
class VulnPolicy:
    max_severity_allowed: str = "MEDIUM"
    _ORDER = ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")
    def blocks(self, severity: str) -> bool:
        return self._ORDER.index(severity) > self._ORDER.index(self.max_severity_allowed)
