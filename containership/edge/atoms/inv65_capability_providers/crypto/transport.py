"""Transport security configuration (M19): TLS 1.3 server contexts with mandatory
client certificates (mTLS).  Plain HTTP is allowed only when explicitly marked
``insecure_loopback_for_tests`` and bound to 127.0.0.1."""
from __future__ import annotations

import ssl


def server_context(cert_file: str, key_file: str, client_ca_file: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(cert_file, key_file)
    ctx.load_verify_locations(client_ca_file)
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


def client_context(ca_file: str, cert_file: str, key_file: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_verify_locations(ca_file)
    ctx.load_cert_chain(cert_file, key_file)
    return ctx


def assert_bind_allowed(host: str, tls: bool, insecure_loopback_for_tests: bool) -> None:
    if tls:
        return
    if not insecure_loopback_for_tests or host not in ("127.0.0.1", "::1", "localhost"):
        raise PermissionError("plaintext transport refused: TLS/mTLS required outside loopback tests")
