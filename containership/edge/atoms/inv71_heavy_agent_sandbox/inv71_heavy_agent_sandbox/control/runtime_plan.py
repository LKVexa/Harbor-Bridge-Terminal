"""Firecracker/jailer launch plan, host enforcement rendering and teardown
reconciliation (INV71-X003, C017-IMP-04, C021-IMP-03, C032, C042, C043, C046, C057-IMP-03).

This module renders - it does not execute.  It turns a verified effective
configuration and a verified artifact set into:

* the Firecracker VM config document (boot source, read-only root drive, a
  per-session writable overlay drive, machine config with SMT off, one TAP);
* the jailer argv (dedicated uid/gid, chroot, cgroup v2 limits, new PID ns,
  netns, resource limits);
* an nftables ruleset for the session TAP: default drop, allow only the
  capability-bound destination tuples;
* the exact set of host resources the session owns.

``reconcile`` compares that owned set against an *observed* host inventory
(supplied by the node agent's probes in production, by fixtures in tests) and
classifies leaks and orphans; a teardown is VERIFIED only when nothing owned is
still observed.  No Firecracker binary, KVM device or root privilege is used
here, and nothing in this module is evidence that a real microVM boundary works.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import ipaddress
import re
from typing import Iterable, Mapping

from .errors import ControlError

JAIL_BASE = "/srv/jailer"
NETNS_DIR = "/var/run/netns"
UID_BASE, UID_SPAN = 200_000, 65_536
_SID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _slug(sid: str) -> str:
    if not _SID.fullmatch(sid):
        raise ControlError("VALIDATION.MALFORMED_REQUEST", "sid")
    return "hb-" + hashlib.sha256(sid.encode()).hexdigest()[:12]


@dataclass(frozen=True)
class Plan:
    sid: str
    slug: str
    uid: int
    vm_config: dict
    jailer_argv: tuple[str, ...]
    cgroup: Mapping[str, str]
    nft: str
    owned: frozenset[tuple[str, str]]  # (kind, identifier)


def plan_session(sid: str, cfg: Mapping, artifacts: Mapping[str, Mapping[str, str]],
                 allowed: Iterable[tuple[str, int, str]] = ()) -> Plan:
    for cls in ("firecracker", "jailer", "guest_kernel", "guest_rootfs"):
        a = artifacts.get(cls)
        if not a or not re.fullmatch(r"[0-9a-f]{64}", a.get("sha256", "")):
            raise ControlError("ARTIFACT.UNAPPROVED_VERSION", f"{cls} not verified")
    if cfg.get("host.devices") or cfg.get("host.mounts") or cfg.get("host.debug_console"):
        raise ControlError("CONFIG.FORBIDDEN_OVERRIDE", "host passthrough")
    slug = _slug(sid)
    uid = UID_BASE + int(hashlib.sha256(sid.encode()).hexdigest(), 16) % UID_SPAN
    root = f"{JAIL_BASE}/firecracker/{slug}/root"
    tap = f"tap{slug[3:14]}"[:15]  # IFNAMSIZ 16 incl NUL
    vm = {
        "boot-source": {"kernel_image_path": "vmlinux",
                        "boot_args": "console=off reboot=k panic=1 pci=off nomodules ro"},
        "drives": [
            {"drive_id": "rootfs", "path_on_host": "rootfs.ext4", "is_root_device": True, "is_read_only": True},
            {"drive_id": "overlay", "path_on_host": "overlay.ext4", "is_root_device": False, "is_read_only": False,
             "rate_limiter": {"ops": {"size": int(cfg["session.iops"]), "refill_time": 1000}}},
        ],
        "machine-config": {"vcpu_count": int(cfg["session.vcpu"]), "mem_size_mib": int(cfg["session.mem_mib"]),
                           "smt": False, "track_dirty_pages": False},
        "network-interfaces": [{
            "iface_id": "eth0", "host_dev_name": tap,
            "guest_mac": "06:00:" + ":".join(slug[3 + i:5 + i] for i in range(0, 8, 2)),
            "tx_rate_limiter": {"bandwidth": {"size": int(cfg["session.net_mbps"]) * 125_000, "refill_time": 1000}},
        }],
        "logger": {"log_path": "fc.log", "level": "Warning"},
    }
    cg = {"cpu.max": f"{int(cfg['session.vcpu']) * 100000} 100000",
          "memory.max": str(int(cfg["session.mem_mib"]) * (1 << 20) + (64 << 20)),  # + VMM overhead allowance
          "memory.swap.max": "0",
          "pids.max": str(int(cfg["session.pids_max"]))}
    argv = ("jailer", "--id", slug, "--exec-file", f"/opt/heavybox/{artifacts['firecracker']['sha256']}/firecracker",
            "--uid", str(uid), "--gid", str(uid), "--chroot-base-dir", JAIL_BASE,
            "--netns", f"{NETNS_DIR}/{slug}", "--new-pid-ns", "--cgroup-version", "2",
            *sum((("--cgroup", f"{k}={v}") for k, v in sorted(cg.items())), ()),
            "--resource-limit", f"no-file={int(cfg['session.fds_max'])}",
            "--resource-limit", f"fsize={int(cfg['session.disk_bytes'])}",
            "--", "--config-file", "vm.json", "--no-api")  # built-in seccomp filters stay on (never --no-seccomp)
    rules = ["table inet " + slug + " {", "  chain fwd {", "    type filter hook forward priority 0; policy drop;",
             f'    iifname "{tap}" ct state established,related accept']
    for addr, port, proto in allowed:
        ip = ipaddress.ip_address(addr)
        fam = "ip6" if ip.version == 6 else "ip"
        if proto not in ("tcp", "udp") or not 0 < int(port) < 65536:
            raise ControlError("POLICY.EGRESS_DENIED", "bad tuple")
        rules.append(f'    iifname "{tap}" {fam} daddr {ip.compressed} {proto} dport {int(port)} ct state new accept')
    rules += [f'    iifname "{tap}" counter drop', "  }", "}"]
    owned = frozenset({("process", f"firecracker:{slug}"), ("cgroup", f"/sys/fs/cgroup/firecracker/{slug}"),
                       ("netns", f"{NETNS_DIR}/{slug}"), ("tap", tap), ("nft_table", slug),
                       ("overlay", f"{root}/overlay.ext4"), ("chroot", root), ("socket", f"{root}/run/firecracker.socket"),
                       ("lease", sid)})
    return Plan(sid, slug, uid, vm, argv, cg, "\n".join(rules) + "\n", owned)


@dataclass(frozen=True)
class Reconciliation:
    verified: bool
    leaked: tuple[tuple[str, str], ...]
    orphans: tuple[tuple[str, str], ...]


def reconcile(plans: Iterable[Plan], observed: Iterable[tuple[str, str]], *, closing: Iterable[str]) -> Reconciliation:
    """Leaked = resources of a closing session still observed.  Orphans = observed
    heavybox resources owned by no known plan (e.g. after a node crash)."""
    plans = list(plans)
    obs = set(observed)
    closing = set(closing)
    leaked = sorted(r for p in plans if p.sid in closing for r in p.owned if r in obs)
    known = set().union(*(p.owned for p in plans)) if plans else set()
    orphans = sorted(r for r in obs if r not in known and ("hb-" in r[1] or r[0] == "tap" and r[1].startswith("tap")))
    return Reconciliation(not leaked, tuple(leaked), tuple(orphans))
