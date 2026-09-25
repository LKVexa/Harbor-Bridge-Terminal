"""INV-38-C042/C043 — Least-privilege / ambient-authority self checks (model)."""
from __future__ import annotations
from dataclasses import dataclass, field

# The only authority the steady-state data path is permitted to hold.
ALLOWED_CAPS = frozenset({"CAP_IPC_LOCK"})           # memory pinning only
FORBIDDEN_CAPS = frozenset({"CAP_SYS_ADMIN", "CAP_NET_ADMIN", "CAP_SYS_RAWIO", "CAP_DAC_OVERRIDE"})

@dataclass
class RuntimeAuthority:
    caps: frozenset[str]
    writable_paths: frozenset[str]
    open_device_nodes: frozenset[str]
    inherited_fds: frozenset[int] = frozenset()
    env_secrets: frozenset[str] = frozenset()

def check(auth: RuntimeAuthority, *, assigned_devices: frozenset[str]) -> list[str]:
    """Return a list of violations; empty means least-privilege holds."""
    v = []
    bad = (auth.caps & FORBIDDEN_CAPS)
    if bad:
        v.append(f"forbidden capabilities held: {sorted(bad)}")
    if not auth.caps <= ALLOWED_CAPS:
        extra = auth.caps - ALLOWED_CAPS
        v.append(f"capabilities beyond allowlist: {sorted(extra)}")
    stray = auth.open_device_nodes - assigned_devices
    if stray:
        v.append(f"device nodes outside assignment: {sorted(stray)}")
    if auth.inherited_fds:
        v.append(f"inherited file descriptors not sanitized: {sorted(auth.inherited_fds)}")
    if auth.env_secrets:
        v.append(f"secrets present in environment: {sorted(auth.env_secrets)}")
    return v

def fails_closed(auth: RuntimeAuthority, *, assigned_devices: frozenset[str]) -> bool:
    return bool(check(auth, assigned_devices=assigned_devices))
