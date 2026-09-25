"""Minimal packet capture (AF_PACKET) writing classic libpcap files — used as
the "pcap or equivalent" evidence in the lab.  Linux + root only.

Run inside a lab node:  python3 pcap.py <iface> <seconds> <out.pcap> [max_packets]
"""
from __future__ import annotations

import select
import socket
import struct
import sys
import time

ETH_P_ALL = 0x0003


def capture(iface: str, seconds: float, out: str, max_packets: int = 5000, snaplen: int = 256) -> int:
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    s.bind((iface, 0))
    n = 0
    with open(out, "wb") as fh:
        fh.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, snaplen, 1))   # LINKTYPE_ETHERNET
        fh.flush()
        end = time.time() + seconds
        while time.time() < end and n < max_packets:
            r, _, _ = select.select([s], [], [], max(0.0, min(0.2, end - time.time())))
            if not r:
                continue
            data = s.recv(65535)
            t = time.time()
            cap = data[:snaplen]
            fh.write(struct.pack("<IIII", int(t), int((t % 1) * 1e6), len(cap), len(data)) + cap)
            fh.flush()
            n += 1
    s.close()
    return n


def summarize(path: str) -> dict:
    """Decode an Ethernet/IPv4 pcap into flow tuples (used to assert on evidence)."""
    flows: dict[tuple, int] = {}
    with open(path, "rb") as fh:
        data = fh.read()
    off = 24
    count = 0
    while off + 16 <= len(data):
        _, _, incl, _ = struct.unpack_from("<IIII", data, off)
        pkt = data[off + 16: off + 16 + incl]
        off += 16 + incl
        count += 1
        if len(pkt) < 34 or pkt[12:14] != b"\x08\x00":
            continue
        ihl = (pkt[14] & 0x0F) * 4
        proto = pkt[23]
        src, dst = socket.inet_ntoa(pkt[26:30]), socket.inet_ntoa(pkt[30:34])
        sport = dport = 0
        if proto in (6, 17) and len(pkt) >= 14 + ihl + 4:
            sport, dport = struct.unpack_from("!HH", pkt, 14 + ihl)
        key = ({6: "tcp", 17: "udp", 1: "icmp"}.get(proto, str(proto)), f"{src}:{sport}", f"{dst}:{dport}")
        flows[key] = flows.get(key, 0) + 1
    return {"packets": count, "flows": [{"proto": k[0], "src": k[1], "dst": k[2], "count": v} for k, v in sorted(flows.items())]}


if __name__ == "__main__":
    iface, secs, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    mx = int(sys.argv[4]) if len(sys.argv) > 4 else 5000
    print("capturing", flush=True)
    print(capture(iface, secs, out, mx))
