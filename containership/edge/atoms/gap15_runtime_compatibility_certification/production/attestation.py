"""Node identity and attestation binding (component 05).

A node quote is a signed ``GAP15_QUOTE/1`` document carrying node id,
attestation-key id, root-of-trust type, nonce, measurements (PCR-like map),
firmware version, secure-boot state, isolation layers (host/guest/
hypervisor/confidential) and ``quoted_at``. Verification checks, in order:
the quote signature under an attestation-key scope, nonce equality with the
certification session (anti-replay, MC-05-05), freshness (MC-05-04), the
measurement baseline, firmware minimum (anti-downgrade), secure boot, and
revoked endorsement keys / firmware (MC-05-08). The runtime profile identity is
then *derived* from the verified measured capabilities — a caller-provided
profile string is never trusted (MC-05-03). Nodes without hardware roots get
an explicit ``reduced-trust`` class or are rejected, never silently upgraded
(MC-05-06). Real GAP-02 quote formats (TPM2 / SEV-SNP / TDX) are an external
dependency (MC-05-02 blocker).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

from .capability import RuntimeProfile, capability
from .canonical import digest
from .signing import TrustStore, verify_payload
from .versions import parse_version

HW_ROOTS = {"tpm2", "sev-snp", "tdx", "cca"}


class AttestationError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass
class AttestationPolicy:
    baselines: dict = field(default_factory=dict)  # baseline id -> {pcr: value}
    min_firmware: str = "0.0.0"
    freshness_s: int = 300
    allow_reduced_trust: bool = False
    revoked_attestation_keys: set = field(default_factory=set)
    revoked_firmware: set = field(default_factory=set)


@dataclass(frozen=True)
class AttestationResult:
    ok: bool
    code: str
    node_id_hash: Optional[str] = None  # privacy: raw node id never leaves this module in results
    trust_class: Optional[str] = None
    profile: Optional[RuntimeProfile] = None
    quote_digest: Optional[str] = None

    def summary(self) -> dict:
        return {"ok": self.ok, "code": self.code, "node": self.node_id_hash, "trust_class": self.trust_class,
                "quote_digest": self.quote_digest}


def node_ref(node_id: str) -> str:
    return "node:" + hashlib.sha256(node_id.encode()).hexdigest()[:24]


def verify_quote(trust: TrustStore, quote: dict, signature: dict, *, nonce: str, now: int,
                 policy: AttestationPolicy, environment: str) -> AttestationResult:
    need = {"schema", "node_id", "ak_id", "root", "nonce", "measurements", "baseline", "firmware",
            "secure_boot", "layers", "quoted_at", "runtime"}
    if not isinstance(quote, dict) or set(quote) != need or quote.get("schema") != "GAP15_QUOTE/1":
        return AttestationResult(False, "E_ATT_SHAPE")
    sig = verify_payload(trust, signature, message_type="quote", environment=environment, payload=quote,
                         required_scope="attestation:quote")
    if not sig.ok:
        return AttestationResult(False, "E_ATT_" + sig.code[2:])
    if sig.key_id != quote["ak_id"] or quote["ak_id"] in policy.revoked_attestation_keys:
        return AttestationResult(False, "E_ATT_KEY_REVOKED" if quote["ak_id"] in policy.revoked_attestation_keys else "E_ATT_KEY_CONFUSION")
    if quote["nonce"] != nonce:
        return AttestationResult(False, "E_ATT_NONCE")
    if not isinstance(quote["quoted_at"], int) or quote["quoted_at"] > now or now - quote["quoted_at"] > policy.freshness_s:
        return AttestationResult(False, "E_ATT_STALE")
    root = quote["root"]
    if root not in HW_ROOTS:
        if not policy.allow_reduced_trust:
            return AttestationResult(False, "E_ATT_NO_HW_ROOT")
        trust_class = "reduced-trust"
    else:
        trust_class = "hardware-attested"
    base = policy.baselines.get(quote["baseline"])
    if base is None or quote["measurements"] != base:
        return AttestationResult(False, "E_ATT_MEASUREMENT")
    fw = quote["firmware"]
    if fw in policy.revoked_firmware:
        return AttestationResult(False, "E_ATT_FIRMWARE_REVOKED")
    if parse_version("semver", fw) < parse_version("semver", policy.min_firmware):
        return AttestationResult(False, "E_ATT_FIRMWARE_DOWNGRADE")
    if quote["secure_boot"] is not True and trust_class == "hardware-attested":
        return AttestationResult(False, "E_ATT_SECURE_BOOT")
    layers = quote["layers"]
    if not isinstance(layers, list) or not layers or any(l.get("kind") not in ("host", "hypervisor", "guest", "confidential") for l in layers):
        return AttestationResult(False, "E_ATT_LAYERS")
    rt = quote["runtime"]
    prov = "measured" if trust_class == "hardware-attested" else "claimed"
    caps = [
        capability("cpu.arch", rt["arch"], layer="hardware", provenance=prov),
        capability("os.family", rt["os"], layer="hardware", provenance=prov),
        capability("isolation", rt["isolation"], layer="security", provenance=prov),
        capability("runtime.name", rt["name"], layer="runtime", provenance="attested" if prov == "measured" else "claimed"),
        capability("runtime.version", rt["version"], layer="runtime", provenance="attested" if prov == "measured" else "claimed"),
        capability("wasi.preview", rt["wasi"], layer="runtime", provenance="attested" if prov == "measured" else "claimed"),
        capability("component_model", rt["component_model"], layer="runtime", provenance="attested" if prov == "measured" else "claimed"),
        capability("abi", rt["abi"], layer="runtime", provenance="attested" if prov == "measured" else "claimed"),
    ]
    for iface in rt.get("wit", []):
        caps.append(capability("wit.interface", iface, layer="runtime", provenance="attested" if prov == "measured" else "claimed"))
    profile = RuntimeProfile(caps)
    return AttestationResult(True, "OK", node_ref(quote["node_id"]), trust_class, profile, digest(quote))
