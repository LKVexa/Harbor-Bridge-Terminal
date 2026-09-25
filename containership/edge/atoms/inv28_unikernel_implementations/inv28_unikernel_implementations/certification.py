"""Consumption of GAP-15 runtime-compatibility certification (MC-042, MC-097).

GAP-15 owns certification; INV-28 only *consumes* it.  A certificate says "toolchain X@V, whose
release artifact has digest D, was tested for runtime profile P on architecture A under hypervisor
H, valid until T", signed with a key the operator trusts for purpose ``gap15``.

:class:`CertificationStore` holds verified certificates only - ``ingest`` refuses anything
unsigned, mis-signed, expired-at-issue, or malformed.  ``lookup`` answers for an exact
(ref, artifact digest, architecture[, runtime][, hypervisor]) tuple; a certificate for a different
artifact digest never matches (anti-substitution, MC-098).  A store configured with a remote
``source`` that is unavailable raises ``SEL_DEPENDENCY_UNAVAILABLE`` - selection then refuses
production rather than proceeding uncertified.
"""
from __future__ import annotations

import datetime as dt
import threading
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property

from .errors import Inv28Error, Reason, ValidationError
from .model import fmt_utc, parse_utc, sha256_hex, text, token
from .trust import KeyRing

SCHEMA = "PK_RUNTIME_CERT/1"
MAX_CERTS = 10_000


@dataclass(frozen=True)
class Certificate:
    cert_id: str
    toolchain: str
    version: str
    artifact_sha256: str
    architecture: str
    runtime: str          # "" = any runtime of the toolchain
    hypervisor: str       # "" = hypervisor-independent
    issuer: str
    issued_at: str
    expires_at: str
    signature: dict

    @property
    def ref(self) -> str:
        return f"{self.toolchain}@{self.version}"

    def payload(self) -> dict:
        return {"schema": SCHEMA, "cert_id": self.cert_id, "toolchain": self.toolchain, "version": self.version,
                "artifact_sha256": self.artifact_sha256, "architecture": self.architecture,
                "runtime": self.runtime, "hypervisor": self.hypervisor, "issuer": self.issuer,
                "issued_at": self.issued_at, "expires_at": self.expires_at}

    def to_dict(self) -> dict:
        return {**self.payload(), "signature": self.signature}

    def valid_at(self, now: dt.datetime) -> bool:
        return self._window[0] <= now <= self._window[1]

    @cached_property
    def _window(self):
        return parse_utc(self.issued_at, "issued_at"), parse_utc(self.expires_at, "expires_at")


def issue(ring: KeyRing, *, toolchain, version, artifact_sha256, architecture, runtime="", hypervisor="",
          issuer="gap15-reference", issued_at, expires_at, cert_id=None) -> dict:
    """Test/fixture helper that plays GAP-15's issuing side.  Production certificates come from GAP-15."""
    body = {"schema": SCHEMA, "toolchain": toolchain, "version": version, "artifact_sha256": artifact_sha256,
            "architecture": architecture, "runtime": runtime, "hypervisor": hypervisor, "issuer": issuer,
            "issued_at": issued_at, "expires_at": expires_at}
    body["cert_id"] = cert_id or "cert-" + sha256_hex(body)[:16]
    return {**body, "signature": ring.sign("gap15", body)}


class CertificationStore:
    def __init__(self, ring: KeyRing, *, source: Callable[[], list] | None = None):
        self._ring = ring
        self._source = source
        self._certs: dict[str, Certificate] = {}
        self._index: dict[tuple, tuple] = {}     # (ref, artifact, arch) -> certs; keeps lookup O(1) per candidate
        self._digest_memo: str | None = None
        self._lock = threading.RLock()

    def ingest(self, doc: dict) -> Certificate:
        if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
            raise ValidationError(f"certificate schema must be {SCHEMA}", code=Reason.CERTIFICATION_INVALID)
        sig = doc.get("signature")
        body = {k: v for k, v in doc.items() if k != "signature"}
        if not self._ring.verify("gap15", body, sig):
            raise ValidationError("certificate signature invalid or key untrusted", code=Reason.CERTIFICATION_INVALID)
        try:
            issued, expires = parse_utc(doc["issued_at"], "issued_at"), parse_utc(doc["expires_at"], "expires_at")
            if expires <= issued:
                raise ValidationError("certificate expires before it is issued", code=Reason.CERTIFICATION_INVALID)
            cert = Certificate(
                cert_id=text(doc["cert_id"], "cert_id"), toolchain=text(doc["toolchain"], "toolchain"),
                version=text(doc["version"], "version"), artifact_sha256=text(doc["artifact_sha256"], "artifact"),
                architecture=token(doc["architecture"], "architecture"),
                runtime=token(doc["runtime"], "runtime") if doc.get("runtime") else "",
                hypervisor=token(doc["hypervisor"], "hypervisor") if doc.get("hypervisor") else "",
                issuer=text(doc["issuer"], "issuer"), issued_at=fmt_utc(issued), expires_at=fmt_utc(expires),
                signature=sig if isinstance(sig, dict) else {})
        except KeyError as exc:
            raise ValidationError(f"certificate missing {exc}", code=Reason.CERTIFICATION_INVALID) from None
        with self._lock:
            if len(self._certs) >= MAX_CERTS and cert.cert_id not in self._certs:
                raise Inv28Error(Reason.REGISTRY_FULL, "certificate store full")
            self._certs[cert.cert_id] = cert
            # copy-on-write index: readers take the current reference lock-free (see lookup)
            index: dict = {}
            for c in self._certs.values():
                index.setdefault((c.ref, c.artifact_sha256, c.architecture), []).append(c)
            self._index = {k: tuple(v) for k, v in index.items()}
            self._digest_memo = None
        return cert

    def refresh(self) -> int:
        """Pull from the configured GAP-15 source; unavailable source fails closed."""
        if self._source is None:
            return 0
        try:
            docs = self._source()
        except Exception as exc:  # noqa: BLE001 - any source failure is "dependency unavailable"
            raise Inv28Error(Reason.DEPENDENCY_UNAVAILABLE, f"GAP-15 source unavailable: {exc}") from None
        return sum(1 for d in docs if self.ingest(d) is not None)

    def lookup(self, *, ref: str, artifact_sha256: str, architecture: str, runtime: str = "",
               hypervisor: str = "", now: dt.datetime):
        """Return the matching valid certificate with the smallest cert_id (deterministic), or None.

        Lock-free: ``_index`` is replaced wholesale on ingest (copy-on-write), so a reader sees either the
        old or the new immutable index.  Per-candidate locking here caused a 4-5x throughput collapse
        under 4 threads (lock convoy with the GIL) - found by tools/soak.py."""
        hits = [c for c in self._index.get((ref, artifact_sha256, architecture), ())
                if (not c.runtime or c.runtime == runtime) and (not c.hypervisor or c.hypervisor == hypervisor)
                and c.valid_at(now)]
        return min(hits, key=lambda c: c.cert_id) if hits else None

    @property
    def digest(self) -> str:
        with self._lock:
            if self._digest_memo is None:
                self._digest_memo = sha256_hex(sorted(self._certs))
            return self._digest_memo

    def __len__(self):
        return len(self._certs)
