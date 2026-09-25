"""Resilient DNS stub resolver (G12-B023) — RFC 1035 wire format, RFC 8767
serve-stale, RFC 2308 negative caching.

* Resolver ordering: sticky-best first (the last resolver that answered),
  then configured order; racing a second resolver starts after
  ``race_delay`` rather than in parallel from t=0, so retries do not multiply.
* Bounded per-query deadline and overall deadline; at most
  ``max_concurrent`` outstanding queries per lookup; one attempt per resolver
  per lookup (the retry budget lives here, not in the transport).
* Anti-spoofing: random 16-bit id, random source port, response must match
  id, question and the resolver's address.  A mismatch is DNS_MISMATCH.
* Negative cache for NXDOMAIN (SOA minimum, capped); positive cache honours
  TTL; stale answers are served only when every resolver failed and only
  until ``max_stale`` (RFC 8767 recommends 1-3 days; default 1 hour here).
* Split-horizon: ``zones`` routes names under an internal suffix to the
  internal resolvers only (internal names never leak to public resolvers).
* Every answer carries provenance: resolver, rcode, ttl, fresh|stale|negative.
"""
from __future__ import annotations

import os
import random
import select
import socket
import struct
import time
from dataclasses import dataclass, field

QTYPE = {"A": 1, "AAAA": 28, "SOA": 6}
MAX_CACHE = 1024


def encode_query(name: str, qtype: str, qid: int) -> bytes:
    labels = name.rstrip(".").split(".")
    if any(not 0 < len(l) < 64 for l in labels) or len(name) > 253:
        raise ValueError("invalid DNS name")
    q = b"".join(bytes([len(l)]) + l.encode("idna") for l in labels) + b"\x00"
    return struct.pack("!HHHHHH", qid, 0x0100, 1, 0, 0, 0) + q + struct.pack("!HH", QTYPE[qtype], 1)


def _skip_name(data: bytes, off: int) -> int:
    for _ in range(128):
        if off >= len(data):
            raise ValueError("truncated name")
        ln = data[off]
        if ln == 0:
            return off + 1
        if ln & 0xC0 == 0xC0:
            return off + 2
        off += 1 + ln
    raise ValueError("name too long / loop")


def _read_name(data: bytes, off: int) -> str:
    labels, jumps = [], 0
    while True:
        if off >= len(data) or jumps > 16:
            raise ValueError("bad name")
        ln = data[off]
        if ln == 0:
            return ".".join(labels).lower()
        if ln & 0xC0 == 0xC0:
            off = ((ln & 0x3F) << 8) | data[off + 1]
            jumps += 1
            continue
        labels.append(data[off + 1: off + 1 + ln].decode("ascii", "replace"))
        off += 1 + ln


def decode_response(data: bytes) -> dict:
    try:
        return _decode_response(data)
    except struct.error as exc:          # truncated fixed-size field (found by the DNS fuzzer)
        raise ValueError(f"truncated DNS message: {exc}") from None


def _decode_response(data: bytes) -> dict:
    if len(data) < 12:
        raise ValueError("short DNS message")
    qid, flags, qd, an, ns, ar = struct.unpack_from("!HHHHHH", data)
    if not flags & 0x8000:
        raise ValueError("not a response")
    off = 12
    questions = []
    for _ in range(qd):
        name = _read_name(data, off)
        off = _skip_name(data, off)
        qt, qc = struct.unpack_from("!HH", data, off)
        off += 4
        questions.append((name, qt))
    answers, soa_min = [], None
    for section, count in (("an", an), ("ns", ns)):
        for _ in range(count):
            off = _skip_name(data, off)
            if off + 10 > len(data):
                raise ValueError("truncated RR")
            rt, rc, ttl, rl = struct.unpack_from("!HHIH", data, off)
            off += 10
            rdata = data[off: off + rl]
            if len(rdata) != rl:
                raise ValueError("truncated rdata")
            if section == "an" and rt == 1 and rl == 4:
                answers.append(("A", socket.inet_ntoa(rdata), ttl))
            elif section == "an" and rt == 28 and rl == 16:
                answers.append(("AAAA", socket.inet_ntop(socket.AF_INET6, rdata) if hasattr(socket, "inet_ntop") else rdata.hex(), ttl))
            elif rt == 6 and rl >= 20:
                soa_min = min(ttl, struct.unpack_from("!I", rdata, rl - 4)[0])
            off += rl
    return {"id": qid, "rcode": flags & 0xF, "tc": bool(flags & 0x0200), "questions": questions,
            "answers": answers, "soa_min": soa_min}


def encode_response(query: bytes, answers: list[str], *, rcode: int = 0, ttl: int = 60, soa_min: int | None = None,
                    qid_override: int | None = None) -> bytes:
    """Server side for the lab/test resolver."""
    qid = struct.unpack_from("!H", query)[0] if qid_override is None else qid_override
    qend = _skip_name(query, 12) + 4
    question = query[12:qend]
    rrs = b""
    for a in answers:
        rrs += b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, ttl, 4) + socket.inet_aton(a)
    auth = b""
    if soa_min is not None:
        rdata = b"\x00\x00" + struct.pack("!IIIII", 1, 3600, 600, 86400, soa_min)
        auth = b"\xc0\x0c" + struct.pack("!HHIH", 6, 1, soa_min, len(rdata)) + rdata
    flags = 0x8180 | rcode
    return struct.pack("!HHHHHH", qid, flags, 1, len(answers), 1 if auth else 0, 0) + question + rrs + auth


@dataclass
class Answer:
    name: str
    addresses: list[str]
    rcode: str                # NOERROR | NXDOMAIN | SERVFAIL | TIMEOUT | MISMATCH
    reason: str
    source: str               # fresh | cache | stale | negative-cache | none
    resolver: str | None
    ttl: int = 0


@dataclass
class Resolver:
    servers: list[tuple[str, int]]
    zones: dict[str, list[tuple[str, int]]] = field(default_factory=dict)   # split-horizon
    query_timeout: float = 1.0
    overall_timeout: float = 3.0
    race_delay: float = 0.3
    max_concurrent: int = 2
    max_stale: float = 3600.0
    negative_cap: int = 300
    clock: object = time.monotonic
    cache: dict = field(default_factory=dict)
    preferred: tuple[str, int] | None = None
    queries_sent: int = 0

    def _servers_for(self, name: str) -> list[tuple[str, int]]:
        for suffix, servers in self.zones.items():
            if name == suffix or name.endswith("." + suffix):
                return list(servers)
        base = list(self.servers)
        if self.preferred in base:
            base.remove(self.preferred)
            base.insert(0, self.preferred)
        return base

    def resolve(self, name: str, qtype: str = "A") -> Answer:
        name = name.rstrip(".").lower()
        key = (name, qtype)
        now = self.clock()
        hit = self.cache.get(key)
        if hit and hit["expires"] > now:
            return Answer(name, hit["addresses"], hit["rcode"], "OK" if hit["rcode"] == "NOERROR" else "DNS_NXDOMAIN",
                          "negative-cache" if hit["rcode"] == "NXDOMAIN" else "cache", hit["resolver"])
        servers = self._servers_for(name)
        if not servers:
            return Answer(name, [], "SERVFAIL", "DNS_CONFIG", "none", None)
        result = self._query(name, qtype, servers)
        if result.rcode in ("NOERROR", "NXDOMAIN"):
            if len(self.cache) >= MAX_CACHE:
                self.cache.pop(next(iter(self.cache)))
            ttl = result.ttl if result.rcode == "NOERROR" else min(result.ttl or self.negative_cap, self.negative_cap)
            self.cache[key] = {"addresses": result.addresses, "rcode": result.rcode, "resolver": result.resolver,
                               "expires": now + ttl, "stored": now}
            return result
        # every resolver failed: RFC 8767 serve-stale within max_stale
        if hit and hit["rcode"] == "NOERROR" and now - hit["expires"] <= self.max_stale:
            return Answer(name, hit["addresses"], "NOERROR", "OK", "stale", hit["resolver"])
        return result

    def _query(self, name: str, qtype: str, servers: list[tuple[str, int]]) -> Answer:
        # deadlines always use the real monotonic clock; the injectable ``clock`` only
        # drives cache ages (a frozen test clock must never be able to hang a lookup)
        start = time.monotonic()
        end = start + self.overall_timeout
        socks: dict[socket.socket, tuple] = {}
        last = Answer(name, [], "TIMEOUT", "DNS_TIMEOUT", "none", None)
        idx = 0
        next_launch = start
        try:
            while time.monotonic() < end:
                now = time.monotonic()
                if idx < len(servers) and len(socks) < self.max_concurrent and (now >= next_launch or not socks):
                    srv = servers[idx]
                    idx += 1
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.bind(("0.0.0.0", 0))                       # random source port
                    qid = random.SystemRandom().randrange(65536)
                    try:
                        s.sendto(encode_query(name, qtype, qid), srv)
                        self.queries_sent += 1
                    except OSError:
                        s.close()
                        continue
                    socks[s] = (srv, qid, now + self.query_timeout)
                    next_launch = now + self.race_delay
                for s, (srv, qid, dl) in list(socks.items()):
                    if now >= dl:
                        s.close()
                        del socks[s]
                if not socks:
                    if idx >= len(servers):
                        break
                    continue
                wait = max(0.0, min([dl for (_, _, dl) in socks.values()] + [end, next_launch if idx < len(servers) else end]) - time.monotonic())
                r, _, _ = select.select(list(socks), [], [], wait)
                for s in r:
                    srv, qid, _ = socks[s]
                    try:
                        data, src = s.recvfrom(4096)
                    except OSError:
                        continue
                    try:
                        msg = decode_response(data)
                    except ValueError:
                        last = Answer(name, [], "SERVFAIL", "DEP_MALFORMED", "none", f"{srv[0]}:{srv[1]}")
                        continue
                    if tuple(src[:2]) != tuple(srv) or msg["id"] != qid or not msg["questions"] or \
                            msg["questions"][0] != (name, QTYPE[qtype]):
                        last = Answer(name, [], "MISMATCH", "DNS_MISMATCH", "none", f"{srv[0]}:{srv[1]}")
                        continue            # keep waiting for the genuine answer
                    rs = f"{srv[0]}:{srv[1]}"
                    if msg["rcode"] == 3:
                        self.preferred = srv
                        return Answer(name, [], "NXDOMAIN", "DNS_NXDOMAIN", "fresh", rs, msg["soa_min"] or self.negative_cap)
                    if msg["rcode"] == 2:
                        last = Answer(name, [], "SERVFAIL", "DNS_SERVFAIL", "none", rs)
                        s.close()
                        del socks[s]
                        continue
                    addrs = [a[1] for a in msg["answers"] if a[0] == qtype]
                    ttl = min([a[2] for a in msg["answers"]] or [0])
                    self.preferred = srv
                    return Answer(name, addrs, "NOERROR", "OK", "fresh", rs, ttl)
            return last
        finally:
            for s in socks:
                s.close()


class DnsServer:
    """Scriptable UDP DNS server for tests and the lab (answers, NXDOMAIN, SERVFAIL, silence, spoof)."""

    def __init__(self, bind=("127.0.0.1", 0), *, records: dict | None = None, mode: str = "answer", ttl: int = 60):
        import threading
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(bind)
        self.address = self.sock.getsockname()
        self.records, self.mode, self.ttl = records or {}, mode, ttl
        self.hits = 0
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        self._t.join(2)
        self.sock.close()

    def _run(self):
        while not self._stop.is_set():
            r, _, _ = select.select([self.sock], [], [], 0.05)
            if not r:
                continue
            q, src = self.sock.recvfrom(4096)
            self.hits += 1
            if self.mode == "silent":
                continue
            name = _read_name(q, 12)
            if self.mode == "servfail":
                self.sock.sendto(encode_response(q, [], rcode=2), src)
            elif self.mode == "spoof":
                self.sock.sendto(encode_response(q, ["6.6.6.6"], qid_override=(struct.unpack_from("!H", q)[0] + 1) % 65536), src)
            elif name in self.records:
                self.sock.sendto(encode_response(q, self.records[name], ttl=self.ttl), src)
            else:
                self.sock.sendto(encode_response(q, [], rcode=3, soa_min=30), src)
