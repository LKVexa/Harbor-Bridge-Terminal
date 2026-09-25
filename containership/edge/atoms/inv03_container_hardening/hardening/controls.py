"""INV-03 4.3.0 control set, evaluated over a Kubernetes-shaped PodSpec.

Every predicate returns a list of violation strings (empty = pass). Predicates
never raise on hostile input: the evaluator converts an exception into a
violation, so a crash can never become an admission.

Checklist items served: 1, 4 (policy half), 5-15, 32 (profile identity), 11.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

JsonMap = Mapping[str, Any]

SENSITIVE_HOST_PATHS = (
    "/", "/proc", "/sys", "/dev", "/etc", "/root", "/boot", "/var/lib/kubelet",
    "/var/lib/containerd", "/var/lib/docker", "/var/run", "/run",
    "/var/run/docker.sock", "/run/containerd/containerd.sock", "/run/crio/crio.sock",
)
RUNTIME_SOCKET_SUFFIXES = ("docker.sock", "containerd.sock", "crio.sock", "cri-dockerd.sock")
SAFE_SYSCTLS = frozenset({
    "kernel.shm_rmid_forced", "net.ipv4.ip_local_port_range", "net.ipv4.tcp_syncookies",
    "net.ipv4.ping_group_range", "net.ipv4.ip_unprivileged_port_start",
    "net.ipv4.ip_local_reserved_ports", "net.ipv4.tcp_keepalive_time",
    "net.ipv4.tcp_fin_timeout", "net.ipv4.tcp_keepalive_intvl", "net.ipv4.tcp_keepalive_probes",
})
ALLOWED_VOLUME_TYPES = frozenset({
    "configMap", "secret", "emptyDir", "projected", "downwardAPI",
    "persistentVolumeClaim", "ephemeral", "csi",
})
REQUIRED_LIMITS = ("cpu", "memory", "ephemeral-storage")


def _m(v: object) -> JsonMap:
    return v if isinstance(v, Mapping) else {}


def _l(v: object) -> list:
    return list(v) if isinstance(v, (list, tuple)) else []


def all_containers(pod: JsonMap) -> list[tuple[str, JsonMap]]:
    out: list[tuple[str, JsonMap]] = []
    for field in ("initContainers", "containers", "ephemeralContainers"):
        for i, c in enumerate(_l(pod.get(field))):
            cm = _m(c)
            name = cm.get("name") if isinstance(cm.get("name"), str) else f"{field}[{i}]"
            out.append((f"{field}/{name}", cm))
    return out


def _sc(pod: JsonMap, c: JsonMap, key: str) -> Any:
    """Container securityContext wins over pod securityContext (Kubernetes rule)."""
    csc, psc = _m(c.get("securityContext")), _m(pod.get("securityContext"))
    return csc[key] if key in csc else psc.get(key)


# --- item 1 / 4: sandbox runtime class -------------------------------------
def runtime_class(pod: JsonMap, ctx: JsonMap) -> list[str]:
    allowed = set(_l(ctx.get("sandbox_runtime_classes")))
    rc = pod.get("runtimeClassName")
    if not isinstance(rc, str) or not rc:
        return ["runtimeClassName absent; sandboxed runtime is mandatory"]
    if rc not in allowed:
        return [f"runtimeClassName {rc!r} not in sandbox allowlist {sorted(allowed)}"]
    return []


# --- baseline controls carried from 4.2.0, now per container ---------------
def non_root(pod: JsonMap, ctx: JsonMap) -> list[str]:
    """Item 11: a named user is admissible only if a resolver proves a non-zero UID."""
    v: list[str] = []
    resolved = _m(ctx.get("resolved_uids"))  # image-db resolver output: {container: uid}
    for name, c in all_containers(pod):
        uid = _sc(pod, c, "runAsUser")
        if isinstance(uid, bool) or not isinstance(uid, int):
            ruid = resolved.get(name)
            if isinstance(ruid, int) and not isinstance(ruid, bool) and ruid > 0:
                continue
            v.append(f"{name}: runAsUser not a numeric UID and no resolver proof of non-zero UID")
            continue
        if uid <= 0:
            v.append(f"{name}: runAsUser {uid} is root")
        if _sc(pod, c, "runAsNonRoot") is not True:
            v.append(f"{name}: runAsNonRoot must be true")
        gid = _sc(pod, c, "runAsGroup")
        if isinstance(gid, int) and not isinstance(gid, bool) and gid == 0:
            v.append(f"{name}: runAsGroup 0 is the root group")
    return v


def read_only_root(pod: JsonMap, ctx: JsonMap) -> list[str]:
    return [f"{n}: readOnlyRootFilesystem must be true"
            for n, c in all_containers(pod) if _m(c.get("securityContext")).get("readOnlyRootFilesystem") is not True]


def not_privileged(pod: JsonMap, ctx: JsonMap) -> list[str]:
    return [f"{n}: privileged must be explicitly false"
            for n, c in all_containers(pod) if _m(c.get("securityContext")).get("privileged") is not False]


def drop_all_capabilities(pod: JsonMap, ctx: JsonMap) -> list[str]:
    v = []
    for n, c in all_containers(pod):
        caps = _m(_m(c.get("securityContext")).get("capabilities"))
        drop, add = caps.get("drop"), caps.get("add", [])
        if not isinstance(drop, list) or "ALL" not in drop:
            v.append(f"{n}: capabilities.drop must contain ALL")
        if not isinstance(add, list) or add:
            v.append(f"{n}: capabilities.add must be empty")
    return v


def seccomp(pod: JsonMap, ctx: JsonMap) -> list[str]:
    """Item 32: Localhost profiles must name a registered, digest-pinned profile."""
    v = []
    registry = _m(ctx.get("seccomp_profiles"))  # {localhostProfile: sha256}
    for n, c in all_containers(pod):
        prof = _m(_sc(pod, c, "seccompProfile"))
        t = prof.get("type")
        if t == "RuntimeDefault":
            continue
        if t == "Localhost":
            lp = prof.get("localhostProfile")
            if not isinstance(lp, str) or lp not in registry:
                v.append(f"{n}: Localhost seccomp profile {lp!r} not in the verified profile registry")
            continue
        v.append(f"{n}: seccompProfile.type must be RuntimeDefault or Localhost (got {t!r})")
    return v


# --- item 5 ----------------------------------------------------------------
def no_privilege_escalation(pod: JsonMap, ctx: JsonMap) -> list[str]:
    return [f"{n}: allowPrivilegeEscalation must be explicitly false"
            for n, c in all_containers(pod) if _m(c.get("securityContext")).get("allowPrivilegeEscalation") is not False]


# --- item 6 / 12 -----------------------------------------------------------
def host_namespaces(pod: JsonMap, ctx: JsonMap) -> list[str]:
    v = [f"{k} must be false or absent" for k in ("hostPID", "hostIPC", "hostNetwork")
         if pod.get(k) not in (None, False)]
    if pod.get("shareProcessNamespace") is True and not ctx.get("allow_share_process_namespace"):
        v.append("shareProcessNamespace is not allowed by the baseline")
    return v


def user_namespace(pod: JsonMap, ctx: JsonMap) -> list[str]:
    if not ctx.get("require_user_namespace"):
        return []
    return [] if pod.get("hostUsers") is False else ["hostUsers must be false (user-namespace remapping required)"]


# --- item 7 ----------------------------------------------------------------
def host_devices(pod: JsonMap, ctx: JsonMap) -> list[str]:
    allowed = set(_l(ctx.get("device_allowlist")))
    v = []
    for n, c in all_containers(pod):
        for d in _l(c.get("volumeDevices")):
            p = _m(d).get("devicePath")
            if p not in allowed:
                v.append(f"{n}: device {p!r} not in device allowlist")
        for r in _m(_m(c.get("resources")).get("limits")):
            if "/" in r and r not in allowed and not r.startswith(("hugepages-",)):
                v.append(f"{n}: extended device resource {r!r} not allowlisted")
    return v


# --- item 8 ----------------------------------------------------------------
def host_mounts(pod: JsonMap, ctx: JsonMap) -> list[str]:
    v = []
    allowed_ro = set(_l(ctx.get("hostpath_readonly_allowlist")))
    hostpath_vols = {}
    for vol in _l(pod.get("volumes")):
        vm = _m(vol)
        hp = _m(vm.get("hostPath"))
        if hp:
            path = hp.get("path")
            hostpath_vols[vm.get("name")] = path
            if not isinstance(path, str):
                v.append(f"volume {vm.get('name')!r}: hostPath without a path")
                continue
            norm = "/" + "/".join(p for p in path.split("/") if p not in ("", "."))
            if ".." in path.split("/"):
                v.append(f"volume {vm.get('name')!r}: hostPath traversal {path!r}")
            elif norm.endswith(RUNTIME_SOCKET_SUFFIXES):
                v.append(f"volume {vm.get('name')!r}: runtime socket {path!r} is forbidden")
            elif norm not in allowed_ro:
                if any(norm == s or norm.startswith(s.rstrip('/') + '/') for s in SENSITIVE_HOST_PATHS):
                    v.append(f"volume {vm.get('name')!r}: sensitive host path {path!r}")
                else:
                    v.append(f"volume {vm.get('name')!r}: hostPath {path!r} not allowlisted")
    for n, c in all_containers(pod):
        for mnt in _l(c.get("volumeMounts")):
            mm = _m(mnt)
            if mm.get("mountPropagation") in ("Bidirectional", "HostToContainer"):
                v.append(f"{n}: mountPropagation {mm.get('mountPropagation')} forbidden")
            if mm.get("name") in hostpath_vols and mm.get("readOnly") is not True:
                v.append(f"{n}: hostPath mount {mm.get('name')!r} must be readOnly")
    return v


# --- item 9 ----------------------------------------------------------------
def kernel_surface(pod: JsonMap, ctx: JsonMap) -> list[str]:
    allowed = SAFE_SYSCTLS | set(_l(ctx.get("extra_sysctls")))
    v = [f"sysctl {_m(s).get('name')!r} not in allowlist"
         for s in _l(_m(pod.get("securityContext")).get("sysctls")) if _m(s).get("name") not in allowed]
    for n, c in all_containers(pod):
        pm = _m(c.get("securityContext")).get("procMount")
        if pm not in (None, "Default"):
            v.append(f"{n}: procMount {pm!r} unmasks /proc")
    return v


# --- item 10 ---------------------------------------------------------------
def mac_profile(pod: JsonMap, ctx: JsonMap) -> list[str]:
    registry = set(_l(ctx.get("apparmor_profiles")))
    v = []
    for n, c in all_containers(pod):
        ap = _m(_sc(pod, c, "appArmorProfile"))
        se = _m(_sc(pod, c, "seLinuxOptions"))
        t = ap.get("type")
        if t == "RuntimeDefault":
            continue
        if t == "Localhost" and ap.get("localhostProfile") in registry:
            continue
        if se.get("type") and se.get("type") not in ("spc_t", "unconfined_t"):
            continue
        if t == "Unconfined" or se.get("type") in ("spc_t", "unconfined_t"):
            v.append(f"{n}: MAC profile is unconfined")
        else:
            v.append(f"{n}: no verified AppArmor/SELinux profile")
    return v


# --- item 13 ---------------------------------------------------------------
def writable_volumes(pod: JsonMap, ctx: JsonMap) -> list[str]:
    v = []
    max_empty = ctx.get("max_emptydir_bytes", 1 << 30)
    for vol in _l(pod.get("volumes")):
        vm = _m(vol)
        kinds = [k for k in vm if k != "name"]
        if not kinds or (kinds[0] not in ALLOWED_VOLUME_TYPES and kinds[0] != "hostPath"):
            v.append(f"volume {vm.get('name')!r}: type {kinds[:1]} not allowlisted")
        if "emptyDir" in vm:
            lim = _m(vm["emptyDir"]).get("sizeLimit")
            size = parse_quantity(lim)
            if size is None or size > max_empty:
                v.append(f"volume {vm.get('name')!r}: emptyDir needs sizeLimit <= {max_empty} bytes")
    return v


# --- item 14 ---------------------------------------------------------------
def resources(pod: JsonMap, ctx: JsonMap) -> list[str]:
    v = []
    for n, c in all_containers(pod):
        if n.startswith("ephemeralContainers/"):
            continue  # Kubernetes forbids resources on ephemeral containers
        lim = _m(_m(c.get("resources")).get("limits"))
        for r in REQUIRED_LIMITS:
            if parse_quantity(lim.get(r)) is None:
                v.append(f"{n}: resources.limits.{r} required")
    if ctx.get("require_pid_limit") and not isinstance(ctx.get("node_pid_limit"), int):
        v.append("node pod PID limit unknown; required by baseline")
    return v


# --- item 15 ---------------------------------------------------------------
def network_isolation(pod: JsonMap, ctx: JsonMap) -> list[str]:
    ns_policies = ctx.get("namespace_default_deny")
    if ns_policies is True:
        return []
    return ["namespace has no verified default-deny NetworkPolicy (ingress+egress)"]


_UNITS = {"": 1, "k": 10**3, "M": 10**6, "G": 10**9, "T": 10**12,
          "Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "m": 0.001}


def parse_quantity(q: object) -> float | None:
    if isinstance(q, bool):
        return None
    if isinstance(q, (int, float)):
        return float(q) if q > 0 else None
    if not isinstance(q, str) or not q or len(q) > 32:
        return None
    for suf in sorted(_UNITS, key=len, reverse=True):
        if suf and q.endswith(suf):
            num = q[: -len(suf)]
            break
    else:
        suf, num = "", q
    try:
        val = float(num) * _UNITS[suf]
    except ValueError:
        return None
    return val if val > 0 and val == val and val != float("inf") else None


CONTROLS_43: dict[str, Callable[[JsonMap, JsonMap], list[str]]] = {
    "sandbox-runtime": runtime_class,
    "non-root": non_root,
    "read-only-root": read_only_root,
    "not-privileged": not_privileged,
    "no-privilege-escalation": no_privilege_escalation,
    "drop-all-capabilities": drop_all_capabilities,
    "seccomp": seccomp,
    "host-namespaces": host_namespaces,
    "user-namespace": user_namespace,
    "host-devices": host_devices,
    "host-mounts": host_mounts,
    "kernel-surface": kernel_surface,
    "mac-profile": mac_profile,
    "writable-volumes": writable_volumes,
    "resources": resources,
    "network-isolation": network_isolation,
}
