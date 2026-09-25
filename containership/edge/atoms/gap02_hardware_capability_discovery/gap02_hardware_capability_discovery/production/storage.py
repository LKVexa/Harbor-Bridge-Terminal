"""GAP02-MC-05 — Storage-device capability discovery (Linux /sys/block).

Collects no serial numbers, WWNs, labels, UUIDs, or contents."""
from __future__ import annotations

from typing import Any

from .errors import Code, Gap02Error
from .evidence import Host, ProbeEvidence, timed

BLK = "/sys/block"


def probe_storage(host: Host | None = None) -> dict[str, Any]:
    host = host or Host()
    out: dict[str, Any] = {"devices": []}

    def rd(p: str) -> str:
        return (host.read(p) or "").strip()

    def body() -> ProbeEvidence:
        if host.system != "Linux":
            raise Gap02Error(Code.UNSUPPORTED_PLATFORM, host.system)
        for d in host.listdir(BLK)[:512]:
            if d.startswith(("loop", "ram", "zram", "dm-", "md", "sr")):
                continue
            q = f"{BLK}/{d}/queue"
            sectors = rd(f"{BLK}/{d}/size")
            rot = rd(f"{q}/rotational")
            dmax = rd(f"{q}/discard_max_bytes")
            media = "nvme" if d.startswith("nvme") else ("hdd" if rot == "1" else "ssd" if rot == "0" else None)
            out["devices"].append({
                "name": d, "media": media,
                "capacity_bytes": int(sectors) * 512 if sectors.isdigit() else None,
                "discard": (int(dmax) > 0) if dmax.isdigit() else None,
                "queue_model": "multi-queue" if host.exists(f"{BLK}/{d}/mq") else None,
                "nr_requests": int(rd(f"{q}/nr_requests")) if rd(f"{q}/nr_requests").isdigit() else None,
                "removable": rd(f"{BLK}/{d}/removable") == "1",
                "write_cache": rd(f"{q}/write_cache") or None,
                "persistence": "volatile-cache" if rd(f"{q}/write_cache") == "write back" else
                               ("write-through" if rd(f"{q}/write_cache") == "write through" else None),
                "inline_encryption": host.exists(f"{q}/crypto"),
                "health": None,  # SMART requires privileged broker (MC-18)
            })
        return ProbeEvidence("storage.block", bool(out["devices"]), "kernel-attribute", BLK,
                             {"devices": len(out["devices"])})
    out["evidence"] = timed(body, "storage.block", BLK)
    ds = out["devices"]
    out["derived"] = [
        ProbeEvidence("storage.nvme", any(d["media"] == "nvme" for d in ds), "kernel-attribute", BLK),
        ProbeEvidence("storage.discard", any(d["discard"] for d in ds), "kernel-attribute", BLK),
    ] if out["evidence"].result is not None else []
    return out
