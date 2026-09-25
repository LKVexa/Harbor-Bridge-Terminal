"""GAP02-MC-06 — NIC capability discovery (Linux /sys/class/net).

Never reads ``address``/``broadcast``/IP state. Physical vs virtual is proven by
the presence of a backing ``device`` link (kernel attribute)."""
from __future__ import annotations

from typing import Any

from .errors import Code, Gap02Error
from .evidence import Host, ProbeEvidence, timed

NET = "/sys/class/net"
FORBIDDEN_ATTRS = frozenset({"address", "broadcast", "perm_addr"})


def probe_nics(host: Host | None = None) -> dict[str, Any]:
    host = host or Host()
    out: dict[str, Any] = {"nics": []}

    def rd(p: str) -> str:
        assert p.rsplit("/", 1)[-1] not in FORBIDDEN_ATTRS
        return (host.read(p) or "").strip()

    def body() -> ProbeEvidence:
        if host.system != "Linux":
            raise Gap02Error(Code.UNSUPPORTED_PLATFORM, host.system)
        for n in host.listdir(NET)[:256]:
            b = f"{NET}/{n}"
            physical = host.exists(f"{b}/device")
            speed = rd(f"{b}/speed")
            try:
                speed_v = int(speed) if int(speed) > 0 else None
            except ValueError:
                speed_v = None
            numa = rd(f"{b}/device/numa_node")
            out["nics"].append({
                "name": n, "physical": physical,
                "operstate": rd(f"{b}/operstate") or None,
                "carrier": {"1": True, "0": False}.get(rd(f"{b}/carrier")),
                "speed_mbps": speed_v, "mtu": int(rd(f"{b}/mtu")) if rd(f"{b}/mtu").isdigit() else None,
                "rx_queues": len([q for q in host.listdir(f"{b}/queues") if q.startswith("rx-")]),
                "sriov_totalvfs": int(rd(f"{b}/device/sriov_totalvfs")) if rd(f"{b}/device/sriov_totalvfs").isdigit() else 0,
                "numa_node": int(numa) if numa.lstrip("-").isdigit() and int(numa) >= 0 else None,
                "ptp": bool(host.listdir(f"{b}/device/ptp")),
                "rdma": bool(host.listdir(f"{b}/device/infiniband")),
                "offloads": None,  # ethtool features require netlink/ioctl via broker (MC-18)
            })
        return ProbeEvidence("network.nic", any(x["physical"] for x in out["nics"]), "kernel-attribute", NET,
                             {"nics": len(out["nics"])})
    out["evidence"] = timed(body, "network.nic", NET)
    phys = [x for x in out["nics"] if x["physical"]]
    if out["evidence"].result is not None:
        out["derived"] = [
            ProbeEvidence("network.rss", any(x["rx_queues"] > 1 for x in phys), "kernel-attribute", NET),
            ProbeEvidence("network.sriov", any(x["sriov_totalvfs"] > 0 for x in phys), "kernel-attribute", NET),
            ProbeEvidence("network.rdma", any(x["rdma"] for x in phys), "kernel-attribute", NET),
            ProbeEvidence("network.ptp", any(x["ptp"] for x in phys), "kernel-attribute", NET),
        ]
    else:
        out["derived"] = []
    return out
