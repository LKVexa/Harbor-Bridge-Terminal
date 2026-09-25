"""Shared test helpers (stdlib only)."""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv05_current_control_state_system.audit import AuditLog  # noqa: E402
from inv05_current_control_state_system.limits import Limits  # noqa: E402
from inv05_current_control_state_system.observability import Metrics, NullStream, StructuredLogger, Tracer  # noqa: E402
from inv05_current_control_state_system.security import Namespace, Principal  # noqa: E402
from inv05_current_control_state_system.service import ControlStateService, RequestContext  # noqa: E402
from inv05_current_control_state_system.store import ControlStore  # noqa: E402

AUDIT_KEY = b"k" * 32
NS_A = Namespace("acme", "prod", "site-a", "ctrl")
NS_B = Namespace("globex", "prod", "site-a", "ctrl")


class FakeClock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def principal(ns: Namespace = NS_A, *roles: str, name: str = "svc") -> Principal:
    return Principal(f"spiffe://inv05.local/tenant/{ns.tenant}/env/{ns.env}/site/{ns.site}/wl/{ns.workload}/{name}",
                     ns, frozenset(roles or ("writer",)))


def ctx(p: Principal, **kw) -> RequestContext:
    return RequestContext(p, **kw)


def make_service(limits: Limits | None = None, clock=None, **kw) -> ControlStateService:
    store = ControlStore(limits, **({"clock": clock} if clock else {}))
    svc = ControlStateService(store, audit=AuditLog(None, AUDIT_KEY), metrics=Metrics(),
                              logger=StructuredLogger(NullStream()), tracer=Tracer(1.0),
                              **({"clock": clock} if clock else {}), **kw)
    svc.bootstrapped = True
    return svc


def txn_body(compare=(), success=(), failure=(), **extra):
    return {"schema": "cstate.txn/1.1", "compare": list(compare), "success": list(success),
            "failure": list(failure), **extra}


def tmpdir() -> str:
    return tempfile.mkdtemp(prefix="inv05-test-")


def readb(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def writeb(path: str, data: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(data)


def make_pki(d: str, client_uris: dict[str, str], trust_domain_ca: str = "inv05-test-ca") -> dict[str, str]:
    """Generate a CA, a localhost server cert and SPIFFE client certs (ECDSA P-256)."""
    import datetime
    import ipaddress
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    now = datetime.datetime.now(datetime.timezone.utc)

    def key():
        return ec.generate_private_key(ec.SECP256R1())

    def write(name, k, c):
        kp, cp = os.path.join(d, name + ".key"), os.path.join(d, name + ".pem")
        with open(kp, "wb") as fh:
            fh.write(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()))
        os.chmod(kp, 0o600)
        with open(cp, "wb") as fh:
            fh.write(c.public_bytes(serialization.Encoding.PEM))
        return cp, kp

    ca_k = key()
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, trust_domain_ca)])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_k.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(minutes=5))
          .not_valid_after(now + datetime.timedelta(days=2))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .sign(ca_k, hashes.SHA256()))
    out = {}
    out["ca"], _ = write("ca", ca_k, ca)

    def leaf(name, sans, eku):
        k = key()
        c = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
             .issuer_name(ca_name).public_key(k.public_key()).serial_number(x509.random_serial_number())
             .not_valid_before(now - datetime.timedelta(minutes=5)).not_valid_after(now + datetime.timedelta(days=1))
             .add_extension(x509.SubjectAlternativeName(sans), critical=False)
             .add_extension(x509.ExtendedKeyUsage([eku]), critical=False)
             .sign(ca_k, hashes.SHA256()))
        return write(name, k, c)

    out["server"], out["server_key"] = leaf("server", [x509.DNSName("localhost"),
                                                        x509.IPAddress(ipaddress.ip_address("127.0.0.1"))],
                                            ExtendedKeyUsageOID.SERVER_AUTH)
    out["server2"], out["server2_key"] = leaf("server2", [x509.DNSName("localhost")], ExtendedKeyUsageOID.SERVER_AUTH)
    for name, uri in client_uris.items():
        out[name], out[name + "_key"] = leaf(name, [x509.UniformResourceIdentifier(uri)],
                                             ExtendedKeyUsageOID.CLIENT_AUTH)
    return out
