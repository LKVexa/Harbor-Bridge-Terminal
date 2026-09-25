"""Network-namespace NAT lab (G12-H088, G12-H089) — stdlib only, Linux, root.

Builds real kernel topologies: each node is a network namespace held open by
an ``unshare -n`` process, links are veth pairs created over raw rtnetlink,
NAT is the kernel's netfilter (``iptables -t nat``), loss is injected with
``-m statistic``.  Nothing is simulated in userspace: STUN/TURN/hole-punch
traffic crosses real conntrack NAT.

Topologies are declared as data (``TOPOLOGIES``) so they are version
controlled; ``Lab.teardown`` kills every namespace holder, which removes the
namespaces, their veths, routes, iptables rules and sockets even after an
aborted run (the kernel reaps a namespace with its last reference).

Declared limits (reported NOT-EVIDENCED, never emulated): the build host
kernel has no IPv6 (``AF_INET6`` -> EAFNOSUPPORT), and ``tc``/netem is absent,
so delay, jitter, reordering, duplication, corruption, bandwidth, queue depth
and MTU-shaping impairments are unavailable; only packet loss is injected.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))

# --- rtnetlink ---------------------------------------------------------------------
RTM_NEWLINK, RTM_NEWADDR, RTM_NEWROUTE = 16, 20, 24
NLM_F_REQUEST, NLM_F_ACK, NLM_F_EXCL, NLM_F_CREATE = 1, 4, 0x200, 0x400
IFLA_IFNAME, IFLA_MTU, IFLA_LINKINFO, IFLA_NET_NS_FD = 3, 4, 18, 28
IFLA_INFO_KIND, IFLA_INFO_DATA, VETH_INFO_PEER = 1, 2, 1
IFA_LOCAL, IFA_ADDRESS = 2, 1
RTA_DST, RTA_OIF, RTA_GATEWAY = 1, 4, 5
IFF_UP = 1


def _nla(t: int, d: bytes) -> bytes:
    ln = 4 + len(d)
    return struct.pack("HH", ln, t) + d + b"\0" * ((-ln) % 4)


def _nl(msgtype: int, flags: int, body: bytes) -> None:
    s = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 0)
    try:
        s.bind((0, 0))
        s.send(struct.pack("IHHII", 16 + len(body), msgtype, flags | NLM_F_REQUEST | NLM_F_ACK, 1, 0) + body)
        r = s.recv(65536)
        err = struct.unpack("i", r[16:20])[0]
        if err:
            raise OSError(-err, os.strerror(-err))
    finally:
        s.close()


def _ifinfo(index=0, flags=0, change=0):
    return struct.pack("BxHiII", 0, 0, index, flags, change)


def veth(name: str, peer: str, peer_ns_pid: int | None = None) -> None:
    peer_attrs = _ifinfo() + _nla(IFLA_IFNAME, peer.encode() + b"\0")
    fd = None
    if peer_ns_pid is not None:
        fd = os.open(f"/proc/{peer_ns_pid}/ns/net", os.O_RDONLY)
        peer_attrs += _nla(IFLA_NET_NS_FD, struct.pack("I", fd))
    try:
        body = _ifinfo() + _nla(IFLA_IFNAME, name.encode() + b"\0") + _nla(
            IFLA_LINKINFO, _nla(IFLA_INFO_KIND, b"veth") + _nla(IFLA_INFO_DATA, _nla(VETH_INFO_PEER, peer_attrs)))
        _nl(RTM_NEWLINK, NLM_F_CREATE | NLM_F_EXCL, body)
    finally:
        if fd is not None:
            os.close(fd)


def up(name: str, mtu: int | None = None) -> None:
    extra = _nla(IFLA_MTU, struct.pack("I", mtu)) if mtu else b""
    _nl(RTM_NEWLINK, 0, _ifinfo(socket.if_nametoindex(name), IFF_UP, IFF_UP) + extra)


def addr(name: str, cidr: str) -> None:
    ip, plen = cidr.split("/")
    body = struct.pack("BBBBI", socket.AF_INET, int(plen), 0, 0, socket.if_nametoindex(name))
    raw = socket.inet_aton(ip)
    _nl(RTM_NEWADDR, NLM_F_CREATE | NLM_F_EXCL, body + _nla(IFA_LOCAL, raw) + _nla(IFA_ADDRESS, raw))


def route(dst: str, via: str) -> None:
    ip, plen = (dst.split("/") + ["0"])[:2] if dst != "default" else ("0.0.0.0", "0")
    body = struct.pack("BBBBBBBBI", socket.AF_INET, int(plen), 0, 0, 254, 3, 0, 1, 0)  # main, boot, universe, unicast
    attrs = _nla(RTA_GATEWAY, socket.inet_aton(via))
    if int(plen):
        attrs += _nla(RTA_DST, socket.inet_aton(ip))
    _nl(RTM_NEWROUTE, NLM_F_CREATE | NLM_F_EXCL, body + attrs)


# --- topology description -------------------------------------------------------------
# Every topology: two clients (a, b) each behind its own NAT router, one "internet" node
# (inet) that forwards between the routers and hosts STUN on two IPs + TURN.
NAT_PROFILES = {
    # name: (description, iptables nat rules for the router's outside interface)
    "eim_apdf": ("endpoint-independent mapping, address+port-dependent filtering (port-restricted cone)",
                 ["-t nat -A POSTROUTING -o {out} -j MASQUERADE"]),
    "apdm": ("address+port-dependent mapping (symmetric NAT)",
             ["-t nat -A POSTROUTING -o {out} -j MASQUERADE --random-fully"]),
    "eim_eif": ("endpoint-independent mapping and filtering (full cone, static forward of the client port)",
                ["-t nat -A POSTROUTING -o {out} -p udp --sport 40000 -j SNAT --to-source {out_ip}:40000",
                 "-t nat -A POSTROUTING -o {out} -j MASQUERADE",
                 "-t nat -A PREROUTING -i {out} -p udp --dport 40000 -j DNAT --to-destination {client}:40000"]),
    "udp_blocked": ("TCP-only egress: UDP dropped at the router",
                    ["-t nat -A POSTROUTING -o {out} -j MASQUERADE", "-A FORWARD -p udp -j DROP"]),
    "lossy30": ("port-restricted cone with 30 % random packet loss on forwarded traffic",
                ["-t nat -A POSTROUTING -o {out} -j MASQUERADE",
                 "-A FORWARD -m statistic --mode random --probability 0.30 -j DROP"]),
    "none": ("no NAT (routed public addressing)", []),
}

TOPOLOGIES = {
    "two_nat": {
        "doc": "a --[natA]-- inet --[natB]-- b; inet hosts STUN on 198.51.100.254 and 192.0.2.254, TURN on 198.51.100.254",
        "links": [
            ("a", "a0", "10.1.0.2/24", "ra", "ra_in", "10.1.0.1/24"),
            ("ra", "ra_out", "198.51.100.1/24", "inet", "i_a", "198.51.100.254/24"),
            ("b", "b0", "10.2.0.2/24", "rb", "rb_in", "10.2.0.1/24"),
            ("rb", "rb_out", "192.0.2.1/24", "inet", "i_b", "192.0.2.254/24"),
        ],
        "routes": {"a": [("default", "10.1.0.1")], "b": [("default", "10.2.0.1")],
                   "ra": [("default", "198.51.100.254")], "rb": [("default", "192.0.2.254")]},
        "forward": ["ra", "rb", "inet"],
        "nat": {"ra": ("ra_out", "198.51.100.1", "10.1.0.2"), "rb": ("rb_out", "192.0.2.1", "10.2.0.2")},
    },
    "cgnat": {
        "doc": "a --[home NAT]-- 100.64.0.0/10 --[carrier NAT]-- inet; b public",
        "links": [
            ("a", "a0", "192.168.1.2/24", "ra", "ra_in", "192.168.1.1/24"),
            ("ra", "ra_out", "100.64.0.2/24", "cg", "cg_in", "100.64.0.1/24"),
            ("cg", "cg_out", "198.51.100.1/24", "inet", "i_a", "198.51.100.254/24"),
            ("b", "b0", "192.0.2.1/24", "inet", "i_b", "192.0.2.254/24"),
        ],
        "routes": {"a": [("default", "192.168.1.1")], "ra": [("default", "100.64.0.1")],
                   "cg": [("default", "198.51.100.254")], "b": [("default", "192.0.2.254")]},
        "forward": ["ra", "cg", "inet"],
        "nat": {"ra": ("ra_out", "100.64.0.2", "192.168.1.2"), "cg": ("cg_out", "198.51.100.1", "100.64.0.2")},
    },
}


@dataclass
class Lab:
    topology: str
    nat_a: str = "eim_apdf"
    nat_b: str = "eim_apdf"
    nodes: dict[str, subprocess.Popen] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)

    # nodes are namespaces held by `unshare -n sleep`
    def _node(self, name: str) -> int:
        if name not in self.nodes:
            p = subprocess.Popen(["unshare", "-n", "sleep", "86400"])
            for _ in range(200):
                if os.readlink(f"/proc/{p.pid}/ns/net") != os.readlink("/proc/self/ns/net"):
                    break
                time.sleep(0.005)
            self.nodes[name] = p
        return self.nodes[name].pid

    def ns_exec(self, node: str, argv: list[str], **kw) -> subprocess.CompletedProcess:
        return subprocess.run(["nsenter", f"--net=/proc/{self.nodes[node].pid}/ns/net", *argv],
                              capture_output=True, text=True, **kw)

    def ns_python(self, node: str, code: str, timeout: float = 30) -> dict:
        """Run python in a node; the snippet must print one JSON object last."""
        env = dict(os.environ, PYTHONPATH=os.path.dirname(os.path.dirname(HERE)) + os.pathsep + os.environ.get("PYTHONPATH", ""),
                   PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run(["nsenter", f"--net=/proc/{self.nodes[node].pid}/ns/net", sys.executable, "-B", "-c", code],
                           capture_output=True, text=True, timeout=timeout, env=env)
        if r.returncode:
            raise RuntimeError(f"{node}: {r.stderr[-2000:]}")
        return json.loads(r.stdout.strip().splitlines()[-1])

    def ns_spawn(self, node: str, code: str) -> subprocess.Popen:
        env = dict(os.environ, PYTHONPATH=os.path.dirname(os.path.dirname(HERE)), PYTHONDONTWRITEBYTECODE="1")
        return subprocess.Popen(["nsenter", f"--net=/proc/{self.nodes[node].pid}/ns/net", sys.executable, "-B", "-c", code],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)

    def _in(self, node: str, fn: str, *args) -> None:
        code = f"import sys; sys.path.insert(0, {HERE!r}); import netlab; netlab.{fn}(*{args!r})"
        r = subprocess.run(["nsenter", f"--net=/proc/{self.nodes[node].pid}/ns/net", sys.executable, "-B", "-c", code],
                           capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"{node} {fn}{args}: {r.stderr.strip().splitlines()[-1]}")
        self.log.append(f"{node}: {fn}{args}")

    def build(self) -> "Lab":
        topo = TOPOLOGIES[self.topology]
        for a, ai, aip, b, bi, bip in topo["links"]:
            self._node(a)
            pid_b = self._node(b)
            self._in(a, "veth", ai, bi, pid_b)
            self._in(a, "up", ai)
            self._in(a, "addr", ai, aip)
            self._in(b, "up", bi)
            self._in(b, "addr", bi, bip)
        for n in self.nodes:
            self._in(n, "up", "lo")
        for n, rts in topo["routes"].items():
            for dst, via in rts:
                self._in(n, "route", dst, via)
        for n in topo["forward"]:
            self.ns_exec(n, ["sysctl", "-qw", "net.ipv4.ip_forward=1"])
        profiles = {"ra": self.nat_a, "rb": self.nat_b, "cg": "eim_apdf"}
        for router, (out, out_ip, client) in topo["nat"].items():
            for rule in NAT_PROFILES[profiles[router]][1]:
                argv = ["iptables", *rule.format(out=out, out_ip=out_ip, client=client).split()]
                r = self.ns_exec(router, argv)
                if r.returncode:
                    raise RuntimeError(f"{router}: {' '.join(argv)}: {r.stderr}")
                self.log.append(f"{router}: {' '.join(argv)}")
        if "inet" in self.nodes:
            self._in("inet", "addr", "i_a", "198.51.100.253/24")  # second STUN IP (RFC 5780 alternate)
        return self

    def describe(self) -> dict:
        topo = TOPOLOGIES[self.topology]
        return {"topology": self.topology, "doc": topo["doc"], "nat_a": [self.nat_a, NAT_PROFILES[self.nat_a][0]],
                "nat_b": [self.nat_b, NAT_PROFILES[self.nat_b][0]], "links": topo["links"],
                "gateway_rules": [l for l in self.log if "iptables" in l], "kernel": os.uname().release}

    def conntrack(self, router: str) -> str:
        try:
            return self.ns_exec(router, ["cat", "/proc/net/nf_conntrack"]).stdout
        except Exception:
            return ""

    def teardown(self) -> list[str]:
        for p in self.nodes.values():
            try:
                p.send_signal(signal.SIGKILL)
                p.wait(timeout=5)
            except Exception:
                pass
        leftovers = [n for n, p in self.nodes.items() if os.path.exists(f"/proc/{p.pid}")]
        self.nodes.clear()
        return leftovers

    def __enter__(self):
        try:
            return self.build()
        except Exception:
            self.teardown()
            raise

    def __exit__(self, *a):
        self.teardown()


def available() -> tuple[bool, str]:
    """Probe whether this host can run the lab (root, netns, veth, iptables)."""
    if os.geteuid() != 0:
        return False, "not root"
    for tool in ("unshare", "nsenter", "iptables", "sysctl"):
        if subprocess.run(["which", tool], capture_output=True).returncode:
            return False, f"{tool} missing"
    try:
        with Lab("two_nat", "none", "none") as lab:
            lab.ns_exec("a", ["true"])
    except Exception as exc:
        return False, f"lab build failed: {exc}"
    return True, "ok"
