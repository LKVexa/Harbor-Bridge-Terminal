"""GAP02-MC-09 — Cross-platform secure-device probes (TPM 2.0 / secure element)."""
from __future__ import annotations

import os
from typing import Any

from .errors import Code, Gap02Error
from .evidence import Host, ProbeEvidence, timed


def probe_tpm(host: Host | None = None) -> dict[str, Any]:
    host = host or Host()
    out: dict[str, Any] = {}

    def body() -> ProbeEvidence:
        if host.system == "Linux":
            major = (host.read("/sys/class/tpm/tpm0/tpm_version_major") or "").strip()
            if not major:
                if host.exists("/dev/tpm0"):
                    raise Gap02Error(Code.MALFORMED_RESPONSE, "tpm device without version attribute")
                return ProbeEvidence("tpm2", False, "kernel-attribute", "/sys/class/tpm")
            banks = [b.replace("pcr-", "") for b in host.listdir("/sys/class/tpm/tpm0") if b.startswith("pcr-")]
            rm = "/dev/tpmrm0"
            usable = host.exists(rm) and host.access(rm, os.R_OK | os.W_OK)
            out.update({"version": major, "pcr_banks": sorted(banks), "resource_manager": host.exists(rm),
                        "usable_by_agent": usable,
                        "secure_boot": None})  # EFI var read requires broker
            if major != "2":
                return ProbeEvidence("tpm2", False, "kernel-attribute", "tpm_version_major", {"version": major})
            if not usable:
                raise Gap02Error(Code.PRIVILEGE_DENIED, "/dev/tpmrm0 not accessible to agent")
            return ProbeEvidence("tpm2", True, "kernel-attribute", "tpm_version_major+tpmrm0",
                                 {"pcr_banks": sorted(banks)})
        if host.system == "Windows":
            ps = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            rc, o = host.run((ps, "-NoProfile", "-NonInteractive", "-Command",
                              "$t=Get-Tpm; \"$($t.TpmPresent) $($t.TpmReady)\""), timeout=8.0)
            v = o.split()
            if rc != 0 or len(v) != 2:
                raise Gap02Error(Code.PRIVILEGE_DENIED if rc else Code.MALFORMED_RESPONSE, "Get-Tpm")
            if v == ["True", "False"]:
                raise Gap02Error(Code.PROBE_UNAVAILABLE, "TPM present but not ready")
            return ProbeEvidence("tpm2", v == ["True", "True"], "api-bit", "Get-Tpm")
        if host.system == "Darwin":
            raise Gap02Error(Code.UNSUPPORTED_PLATFORM, "Secure Enclave has no TPM 2.0 interface")
        raise Gap02Error(Code.UNSUPPORTED_PLATFORM, host.system)
    out["evidence"] = timed(body, "tpm2", "tpm")
    return out
