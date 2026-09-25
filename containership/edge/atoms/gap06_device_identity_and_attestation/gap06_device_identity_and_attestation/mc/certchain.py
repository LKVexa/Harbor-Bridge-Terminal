"""MC-02: EK/AK certificate-chain validation.

Builds a path from leaf to a pinned trust anchor, checks every signature,
validity window, basicConstraints/pathLen, keyUsage and revocation (CRL set
supplied by the caller -- fetching CRLs/OCSP over the network is out of scope
and fails closed when ``require_revocation_info`` is set and none is present).
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from .errors import fail

MAX_DEPTH = 6
MAX_CERT_BYTES = 16 * 1024


def _x509():
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
        from cryptography.hazmat.primitives import hashes
    except ImportError as exc:
        raise fail("E_UNSUPPORTED_ALG", "cryptography unavailable") from exc
    return x509, ec, padding, rsa, hashes


def load(pem_or_der: bytes):
    x509, *_ = _x509()
    if len(pem_or_der) > MAX_CERT_BYTES:
        raise fail("E_CERT_CHAIN", "certificate too large")
    try:
        return (x509.load_pem_x509_certificate(pem_or_der) if pem_or_der.lstrip().startswith(b"-----")
                else x509.load_der_x509_certificate(pem_or_der))
    except Exception as exc:
        raise fail("E_CERT_CHAIN", "certificate parse failure") from exc


def _sig_ok(child, issuer) -> bool:
    x509, ec, padding, rsa, hashes = _x509()
    pub = issuer.public_key()
    try:
        if isinstance(pub, ec.EllipticCurvePublicKey):
            pub.verify(child.signature, child.tbs_certificate_bytes, ec.ECDSA(child.signature_hash_algorithm))
        elif isinstance(pub, rsa.RSAPublicKey):
            if pub.key_size < 2048:
                return False
            pub.verify(child.signature, child.tbs_certificate_bytes, padding.PKCS1v15(), child.signature_hash_algorithm)
        else:
            return False
        if child.signature_hash_algorithm is None or child.signature_hash_algorithm.name == "sha1":
            return False
        return True
    except Exception:
        return False


@dataclass
class TrustStore:
    anchors: list = field(default_factory=list)
    intermediates: list = field(default_factory=list)
    crls: list = field(default_factory=list)
    require_revocation_info: bool = False
    version: str = "anchors-v1"
    allow_test_roots: bool = False  # anchors minted by mc/simulator.py (O=GAP06-TEST-ONLY) are refused unless True

    def add_crl(self, crl) -> None:
        """Accept a CRL only if a known CA signed it (poisoned CRLs are refused)."""
        for ca in self.anchors + self.intermediates:
            if ca.subject == crl.issuer and crl.is_signature_valid(ca.public_key()):
                self.crls.append(crl)
                return
        raise fail("E_CERT_CHAIN", "CRL not signed by a known CA")

    def fingerprint_set(self) -> list:
        from cryptography.hazmat.primitives import hashes
        return sorted(a.fingerprint(hashes.SHA256()).hex() for a in self.anchors)


def validate(leaf, store: TrustStore, at: _dt.datetime, *, leaf_usage: str) -> list:
    """Return the validated chain [leaf, ..., anchor] or raise E_CERT_CHAIN/E_CERT_REVOKED."""
    x509, *_ = _x509()
    chain, cur = [leaf], leaf
    from cryptography.x509.oid import NameOID
    for a in store.anchors:
        orgs = [x.value for x in a.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)]
        if "GAP06-TEST-ONLY" in orgs and not store.allow_test_roots:
            raise fail("E_CERT_CHAIN", "test-only trust anchor present in a non-test trust store")
    anchors = {a.subject.public_bytes(): a for a in store.anchors}
    pool = list(store.intermediates)
    for depth in range(MAX_DEPTH):
        _window(cur, at)
        if depth == 0:
            _leaf_usage(cur, leaf_usage)
        _revocation(cur, store, at)
        anchor = anchors.get(cur.issuer.public_bytes())
        if anchor is not None and _sig_ok(cur, anchor):
            _window(anchor, at)
            _ca_ok(anchor, depth)
            return chain + [anchor]
        nxt = [c for c in pool if c.subject == cur.issuer and _sig_ok(cur, c)]
        if not nxt:
            raise fail("E_CERT_CHAIN", "no path to a trust anchor")
        cur = nxt[0]
        pool.remove(cur)
        _ca_ok(cur, depth)
        chain.append(cur)
    raise fail("E_CERT_CHAIN", "chain exceeds maximum depth")


def _window(c, at):
    if not (c.not_valid_before_utc <= at <= c.not_valid_after_utc):
        raise fail("E_CERT_CHAIN", "certificate outside validity window")


def _ca_ok(c, below: int):
    x509, *_ = _x509()
    try:
        bc = c.extensions.get_extension_for_class(x509.BasicConstraints).value
        ku = c.extensions.get_extension_for_class(x509.KeyUsage).value
    except x509.ExtensionNotFound:
        raise fail("E_CERT_CHAIN", "CA lacks basicConstraints/keyUsage")
    if not bc.ca or not ku.key_cert_sign:
        raise fail("E_CERT_CHAIN", "issuer is not a CA")
    if bc.path_length is not None and below > bc.path_length:
        raise fail("E_CERT_CHAIN", "pathLen constraint violated")


def _leaf_usage(c, usage):
    x509, *_ = _x509()
    try:
        bc = c.extensions.get_extension_for_class(x509.BasicConstraints).value
        ku = c.extensions.get_extension_for_class(x509.KeyUsage).value
    except x509.ExtensionNotFound:
        raise fail("E_CERT_CHAIN", "leaf lacks basicConstraints/keyUsage")
    if bc.ca:
        raise fail("E_CERT_CHAIN", "leaf must not be a CA")
    if usage == "ek" and not ku.key_encipherment:
        raise fail("E_CERT_CHAIN", "EK certificate lacks keyEncipherment")
    if usage == "ak" and not ku.digital_signature:
        raise fail("E_CERT_CHAIN", "AK certificate lacks digitalSignature")


def _revocation(c, store, at):
    relevant = [crl for crl in store.crls if crl.issuer == c.issuer]
    if not relevant:
        if store.require_revocation_info:
            raise fail("E_CERT_CHAIN", "no revocation information for issuer (fail closed)")
        return
    for crl in relevant:
        if crl.next_update_utc is not None and at > crl.next_update_utc and store.require_revocation_info:
            raise fail("E_CERT_CHAIN", "stale CRL (fail closed)")
        if crl.get_revoked_certificate_by_serial_number(c.serial_number) is not None:
            raise fail("E_CERT_REVOKED", "certificate is revoked")
