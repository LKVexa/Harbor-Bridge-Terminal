"""MC-015 - confidential, mutually authenticated transport profile for descriptors.

``PK_DESCRIPTOR/2`` gives integrity/authenticity of the descriptor, not
confidentiality and not peer authentication.  Any descriptor that crosses a
process or host boundary MUST travel over this profile (or an equivalent the
security owner approves in ``WAIVERS.json``):

* TLS 1.3 only, stdlib ``ssl``; no compression, no renegotiation;
* mutual X.509 authentication against a pinned private CA;
* optional peer-identity pin (exact DNS SAN / common name);
* length-prefixed frames bounded to ``MAX_FRAME`` bytes;
* the receiver re-authenticates the descriptor with ``from_wire`` - the channel
  never substitutes for descriptor authentication.

``send_descriptor``/``recv_descriptor`` refuse plain sockets, TLS < 1.3 and
unauthenticated peers (fail closed with ``InsecureChannel``).
"""
from __future__ import annotations

import json
import ssl
import struct

PROFILE = "PK_DESCRIPTOR_TRANSPORT/1"
MAX_FRAME = 4096


class InsecureChannel(ConnectionError):
    code = "insecure_channel"


def _base(purpose, ca_file, cert_file, key_file) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER if purpose == "server" else ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    ctx.options |= ssl.OP_NO_COMPRESSION
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_verify_locations(cafile=ca_file)
    ctx.load_cert_chain(cert_file, key_file)
    return ctx


def server_context(*, ca_file: str, cert_file: str, key_file: str) -> ssl.SSLContext:
    return _base("server", ca_file, cert_file, key_file)


def client_context(*, ca_file: str, cert_file: str, key_file: str) -> ssl.SSLContext:
    ctx = _base("client", ca_file, cert_file, key_file)
    ctx.check_hostname = True
    return ctx


def _peer_names(cert: dict) -> set[str]:
    names = {v for k, v in cert.get("subjectAltName", ()) if k == "DNS"}
    for rdn in cert.get("subject", ()):
        for k, v in rdn:
            if k == "commonName":
                names.add(v)
    return names


def assert_secure(sock, *, peer_identity: str | None = None) -> None:
    if not isinstance(sock, ssl.SSLSocket):
        raise InsecureChannel("descriptor transport requires TLS; plain socket refused")
    if sock.version() != "TLSv1.3":
        raise InsecureChannel(f"descriptor transport requires TLSv1.3, got {sock.version()}")
    cert = sock.getpeercert()
    if not cert:
        raise InsecureChannel("peer is not authenticated")
    if peer_identity is not None and peer_identity not in _peer_names(cert):
        raise InsecureChannel("peer identity does not match pinned identity")


def _recv_exact(sock, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("channel closed mid-frame")
        buf += chunk
    return buf


def send_descriptor(sock, descriptor, *, peer_identity: str | None = None) -> None:
    assert_secure(sock, peer_identity=peer_identity)
    body = json.dumps({"profile": PROFILE, "descriptor": descriptor.to_wire()}, separators=(",", ":")).encode()
    if len(body) > MAX_FRAME:
        raise ValueError("descriptor frame exceeds MAX_FRAME")
    sock.sendall(struct.pack(">I", len(body)) + body)


def recv_descriptor(sock, table, *, peer_identity: str | None = None):
    """Receive one frame and authenticate it against ``table`` (fail closed)."""
    assert_secure(sock, peer_identity=peer_identity)
    (n,) = struct.unpack(">I", _recv_exact(sock, 4))
    if n > MAX_FRAME:
        raise InsecureChannel("oversized frame refused")
    try:
        frame = json.loads(_recv_exact(sock, n))
    except (ValueError, UnicodeDecodeError) as exc:
        raise InsecureChannel("malformed frame") from exc
    if type(frame) is not dict or set(frame) != {"profile", "descriptor"} or frame["profile"] != PROFILE:  # noqa: E721
        raise InsecureChannel("unexpected frame structure")
    return table.from_wire(frame["descriptor"])
