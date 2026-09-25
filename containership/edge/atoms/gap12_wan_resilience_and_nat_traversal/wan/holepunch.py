"""UDP hole punching with authenticated rendezvous (G12-A004).

A rendezvous service (the GAP-12 control plane in production; the lab's
``Rendezvous`` here) hands both peers a ticket: session id, both reflexive
endpoints, a start time, an expiry and an HMAC tag under a key the
rendezvous shares with each peer.  Punch packets carry the session id and an
HMAC so a third party that sprays the mapped port cannot complete the punch.

Schedule: a bounded number of probes (``MAX_PROBES``) at a randomised interval
inside ``[INTERVAL_MIN, INTERVAL_MAX]`` until ``window`` expires.  The socket is
always closed on failure; on success it is handed to the caller.

Failure attribution (``PunchResult.cause``):
  coordination   - ticket invalid/expired, or peer never started (no packet at all
                   and the rendezvous reports the peer absent)
  nat_filtering  - our probes left (the socket saw no error) but nothing valid arrived
                   while the peer confirms it sent to our mapped endpoint
  mapping_change - valid packets arrived from an endpoint other than the ticket's
                   (the peer's NAT allocated a different mapping for us)
  local_firewall - sendto() failed locally (EPERM / EACCES)
  unreachable    - ICMP / ENETUNREACH style errors

Low-TTL priming (``prime_ttl``): before the full-TTL probes, a few packets are
sent with a small TTL so they open our own NAT mapping but expire before they
reach the peer's NAT.  Without it, a probe that arrives at the peer's NAT
first creates an inbound conntrack entry and the peer's own outbound mapping
is forced onto a different port (observed in the lab with Linux MASQUERADE:
the "endpoint-independent" mapping silently became 40000 -> 39928).
"""
from __future__ import annotations

import errno
import hashlib
import hmac
import json
import os
import random
import select
import socket
import time
from dataclasses import dataclass

MAGIC = b"G12P"
MAX_PROBES = 40
INTERVAL_MIN, INTERVAL_MAX = 0.02, 0.08


@dataclass(frozen=True)
class Ticket:
    session: str
    me: tuple[str, int]
    peer: tuple[str, int]
    start: float
    expires: float
    tag: str

    def body(self) -> bytes:
        return json.dumps([self.session, list(self.me), list(self.peer), self.start, self.expires],
                          separators=(",", ":")).encode()


class Rendezvous:
    """Issues authenticated tickets; one key per enrolled peer."""

    def __init__(self, keys: dict[str, bytes], clock=time.time):
        self.keys, self.clock = keys, clock

    def issue(self, a: str, a_ep, b: str, b_ep, *, delay: float = 0.2, window: float = 3.0) -> tuple[Ticket, Ticket]:
        sid = os.urandom(8).hex()
        start = self.clock() + delay
        out = []
        for who, me, peer in ((a, a_ep, b_ep), (b, b_ep, a_ep)):
            t = Ticket(sid, tuple(me), tuple(peer), start, start + window, "")
            tag = hmac.new(self.keys[who], t.body(), hashlib.sha256).hexdigest()
            out.append(Ticket(sid, tuple(me), tuple(peer), start, start + window, tag))
        return out[0], out[1]


def verify_ticket(t: Ticket, key: bytes, now: float) -> bool:
    good = hmac.compare_digest(hmac.new(key, t.body(), hashlib.sha256).hexdigest(), t.tag)
    return good and t.start - 5 <= now <= t.expires


def _punch_packet(t: Ticket, session_key: bytes, seq: int) -> bytes:
    body = MAGIC + bytes.fromhex(t.session) + seq.to_bytes(4, "big")
    return body + hmac.new(session_key, body, hashlib.sha256).digest()[:16]


def _valid(data: bytes, t: Ticket, session_key: bytes) -> bool:
    if len(data) != 32 or not data.startswith(MAGIC) or data[4:12] != bytes.fromhex(t.session):
        return False
    return hmac.compare_digest(hmac.new(session_key, data[:16], hashlib.sha256).digest()[:16], data[16:])


@dataclass
class PunchResult:
    ok: bool
    cause: str
    remote: tuple[str, int] | None
    sent: int
    received_valid: int
    received_invalid: int
    elapsed: float


def punch(sock: socket.socket, ticket: Ticket, *, ticket_key: bytes, session_key: bytes,
          clock=time.time, rng: random.Random | None = None, peer_reported_sending: bool | None = None,
          prime_ttl: int | None = None, prime_count: int = 3) -> PunchResult:
    """Run the punch schedule on an already-bound socket (the one STUN mapped)."""
    rng = rng or random.Random()
    t0 = clock()
    if not verify_ticket(ticket, ticket_key, t0):
        return PunchResult(False, "coordination", None, 0, 0, 0, 0.0)
    while clock() < ticket.start:
        time.sleep(min(0.01, ticket.start - clock()))
    sent = valid = invalid = 0
    if prime_ttl is not None:
        if not 1 <= prime_ttl <= 16:
            raise ValueError("prime_ttl must be 1..16")
        old_ttl = sock.getsockopt(socket.IPPROTO_IP, socket.IP_TTL)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, prime_ttl)
        try:
            for i in range(prime_count):
                try:
                    sock.sendto(_punch_packet(ticket, session_key, 0xFFFF0000 + i), ticket.peer)
                except OSError:
                    pass
        finally:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, old_ttl)
        time.sleep(0.25)   # let the peer prime too before full-TTL probes
    remote = None
    got_from_other = None
    local_error = None
    confirmed_at = None
    while clock() < ticket.expires:
        if sent < MAX_PROBES and (confirmed_at is None or clock() - confirmed_at < 0.3):
            try:
                sock.sendto(_punch_packet(ticket, session_key, sent), ticket.peer)
                sent += 1
            except OSError as exc:
                local_error = exc.errno
                if exc.errno in (errno.EPERM, errno.EACCES):
                    break
        wait = rng.uniform(INTERVAL_MIN, INTERVAL_MAX)
        r, _, _ = select.select([sock], [], [], wait)
        if r:
            try:
                data, src = sock.recvfrom(2048)
            except OSError as exc:
                local_error = exc.errno
                continue
            if _valid(data, ticket, session_key):
                valid += 1
                if tuple(src[:2]) == tuple(ticket.peer):
                    remote = tuple(src[:2])
                    confirmed_at = confirmed_at or clock()
                else:
                    got_from_other = tuple(src[:2])
            else:
                invalid += 1
        if remote is not None and confirmed_at is not None and clock() - confirmed_at >= 0.3:
            break  # keep sending briefly so the peer's side opens too, then stop
    elapsed = clock() - t0
    if remote is not None:
        return PunchResult(True, "ok", remote, sent, valid, invalid, elapsed)
    if local_error in (errno.EPERM, errno.EACCES):
        cause = "local_firewall"
    elif local_error in (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ECONNREFUSED):
        cause = "unreachable"
    elif got_from_other is not None:
        cause = "mapping_change"
    elif peer_reported_sending is False:
        cause = "coordination"
    else:
        cause = "nat_filtering"
    return PunchResult(False, cause, got_from_other, sent, valid, invalid, elapsed)
