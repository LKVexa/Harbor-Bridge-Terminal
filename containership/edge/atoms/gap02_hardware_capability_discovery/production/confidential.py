"""GAP02-MC-08 — Confidential-computing probes.

Two tiers per technology:
  ``cc.<tech>.enabled``  — kernel/firmware enablement proven by kernel attribute
  ``cc.<tech>.attested`` — present ONLY when a caller-supplied verifier (GAP-06)
                           validates fresh attestation evidence bound to the
                           report nonce. Without a verifier it is unprobed.
"""
from __future__ import annotations

from typing import Any, Callable, Protocol

from .errors import Code, Gap02Error
from .evidence import Host, ProbeEvidence, timed

TECH = {
    # tech: (host-side enablement attribute, guest-side device)
    "sev": ("/sys/module/kvm_amd/parameters/sev", "/dev/sev-guest"),
    "sev-es": ("/sys/module/kvm_amd/parameters/sev_es", "/dev/sev-guest"),
    "sev-snp": ("/sys/module/kvm_amd/parameters/sev_snp", "/dev/sev-guest"),
    "tdx": ("/sys/module/kvm_intel/parameters/tdx", "/dev/tdx_guest"),
    "sgx": (None, "/dev/sgx_enclave"),
    "cca": (None, "/sys/kernel/config/tsm/report"),
}


class AttestationVerifier(Protocol):
    def __call__(self, tech: str, nonce: bytes) -> bool: ...


def probe_confidential(host: Host | None = None, *, nonce: bytes = b"",
                       verifier: Callable[[str, bytes], bool] | None = None) -> dict[str, Any]:
    host = host or Host()
    ev: list[ProbeEvidence] = []
    for tech, (param, guestdev) in TECH.items():
        def body(tech=tech, param=param, guestdev=guestdev) -> ProbeEvidence:
            if host.system != "Linux":
                raise Gap02Error(Code.UNSUPPORTED_PLATFORM, host.system)
            if param and (v := (host.read(param) or "").strip()):
                return ProbeEvidence(f"cc.{tech}.enabled", v in ("Y", "1"), "kernel-attribute", param)
            if host.exists(guestdev):
                return ProbeEvidence(f"cc.{tech}.enabled", True, "kernel-attribute", guestdev,
                                     {"role": "guest-or-enclave"})
            raise Gap02Error(Code.PROBE_UNAVAILABLE, f"{tech}: no enablement attribute")
        e = timed(body, f"cc.{tech}.enabled", tech)
        ev.append(e)
        if e.result is True and verifier is not None and len(nonce) >= 16:
            try:
                ok = verifier(tech, nonce)
                ev.append(ProbeEvidence(f"cc.{tech}.attested", bool(ok) if isinstance(ok, bool) else None,
                                        "attested", "gap06-verifier", {"nonce_len": len(nonce)},
                                        None if isinstance(ok, bool) else Code.MALFORMED_RESPONSE.value))
            except Exception as x:  # noqa: BLE001
                ev.append(ProbeEvidence(f"cc.{tech}.attested", None, "observation", "gap06-verifier",
                                        {"detail": type(x).__name__}, Code.DEPENDENCY_FAILURE.value))
        else:
            ev.append(ProbeEvidence(f"cc.{tech}.attested", None, "observation", "gap06-verifier",
                                    {}, Code.UNATTESTED.value))
    return {"evidence": ev}
