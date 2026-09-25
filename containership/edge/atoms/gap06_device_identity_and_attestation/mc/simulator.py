"""TEST-ONLY software attester.  Produces TPM-format quotes, event logs and an
EK/AK certificate chain from software keys.  It is NOT a TPM and its output
must never be accepted outside tests: every certificate it mints carries the
subject O=GAP06-TEST-ONLY and ``certchain.validate`` refuses any trust store
containing such an anchor unless ``TrustStore.allow_test_roots=True``.
"""
from __future__ import annotations

import datetime as _dt
import hashlib

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.x509.oid import NameOID

from . import tpm

TEST_ORG = "GAP06-TEST-ONLY"


def _name(cn):
    return x509.Name([x509.NameAttribute(NameOID.ORGANIZATION_NAME, TEST_ORG), x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def make_cert(subject_cn, subject_key, issuer_cn, issuer_key, *, ca: bool, days=365, not_before=None, path_len=None,
              key_usage="ca", serial=None):
    nb = not_before or _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc)
    b = (x509.CertificateBuilder().subject_name(_name(subject_cn)).issuer_name(_name(issuer_cn))
         .public_key(subject_key.public_key()).serial_number(serial or x509.random_serial_number())
         .not_valid_before(nb).not_valid_after(nb + _dt.timedelta(days=days))
         .add_extension(x509.BasicConstraints(ca=ca, path_length=path_len if ca else None), critical=True))
    if key_usage == "ca":
        ku = dict(digital_signature=False, key_cert_sign=True, crl_sign=True)
    elif key_usage == "ek":
        ku = dict(digital_signature=False, key_cert_sign=False, crl_sign=False, key_encipherment=True)
    else:
        ku = dict(digital_signature=True, key_cert_sign=False, crl_sign=False)
    full = dict(digital_signature=False, content_commitment=False, key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False)
    full.update(ku)
    b = b.add_extension(x509.KeyUsage(**full), critical=True)
    return b.sign(issuer_key, hashes.SHA256())


class SoftTPM:
    def __init__(self, name: str, root_key=None, root_cert=None):
        self.name = name
        self.root_key = root_key or ec.generate_private_key(ec.SECP256R1())
        self.root_cert = root_cert or make_cert("test-root", self.root_key, "test-root", self.root_key, ca=True, days=3650)
        self.ek = ec.generate_private_key(ec.SECP256R1())
        self.ek_cert = make_cert(f"ek-{name}", self.ek, "test-root", self.root_key, ca=False, key_usage="ek")
        self.ak = ec.generate_private_key(ec.SECP256R1())
        self.pcrs = {("sha256", i): b"\0" * 32 for i in range(24)}
        self.events = []
        self.clock = tpm.ClockInfo(1000, 1, 0, True)
        self.firmware = 0x0001000200030004

    @property
    def ak_public_pem(self) -> bytes:
        return self.ak.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    @property
    def ak_name(self) -> bytes:
        der = self.ak.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        return b"\x00\x0b" + hashlib.sha256(der).digest()

    def extend(self, pcr: int, data: bytes, event_type: int = 0x0D):
        d = hashlib.sha256(data).digest()
        self.pcrs[("sha256", pcr)] = hashlib.sha256(self.pcrs[("sha256", pcr)] + d).digest()
        self.events.append((pcr, event_type, {"sha256": d}, data))

    def event_log(self) -> bytes:
        return tpm.build_event_log(self.events)

    def tick(self, n=10):
        self.clock = tpm.ClockInfo(self.clock.clock + n, self.clock.reset_count, self.clock.restart_count, True)

    def sign_raw(self, message: bytes) -> bytes:
        return self.ak.sign(message, ec.ECDSA(hashes.SHA256()))

    def quote(self, nonce: bytes, pcrs=(0, 1, 2, 7)):
        self.tick()
        sel = (("sha256", tuple(pcrs)),)
        comp = tpm.pcr_composite(sel, self.pcrs)
        attest = tpm.build_attest(nonce=nonce, signer=self.ak_name, clock=self.clock, firmware=self.firmware,
                                  selection=sel, pcr_digest=comp)
        der = self.ak.sign(attest, ec.ECDSA(hashes.SHA256()))
        r, s = utils.decode_dss_signature(der)
        sig = (tpm.TPM_ALG_ECDSA).to_bytes(2, "big") + (0x000B).to_bytes(2, "big")
        sig += (32).to_bytes(2, "big") + r.to_bytes(32, "big") + (32).to_bytes(2, "big") + s.to_bytes(32, "big")
        return attest, sig, {p: self.pcrs[("sha256", p)] for p in pcrs}
