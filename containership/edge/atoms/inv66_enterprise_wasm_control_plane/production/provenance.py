"""Cryptographic signature and provenance verification (MC-029, MC-030; C045).

4.2.0 trusted the manifest's ``signer`` *string*.  Now, per component:

1. **Digest pinning** — the image reference must carry ``@sha256:<64 hex>`` when
   ``provenance.require_digest`` (mandatory in prod).  Tags alone are mutable.
2. **Signature** — ``signature`` is an Ed25519 signature, by the named signer's
   *configured public key*, over ``PK_ECP_SIG/1\\0 || image_digest || \\0 || component_name``.
   The signer must be approved for the target scope, unrevoked and unexpired.
   Binding the component name stops a valid signature for one component being
   replayed onto another name.
3. **Attestation** (when ``require_attestation``) — a ``PK_ECP_ARTIFACT_STATEMENT/1``
   whose ``subject_digest`` equals the image digest, whose ``builder`` is trusted,
   and which is itself signed by an approved signer over its canonical form.
4. **Registry resolution** (optional adapter) — a :class:`RegistryResolver` can
   confirm the digest exists in the registry; the bundled resolver is an
   in-memory index.  A live OCI registry client is OPEN_EXTERNAL.

Transparency-log inclusion proofs (Rekor-style) are not implemented; they are
recorded as an explicit gap in the waiver register (W-06).
"""
from __future__ import annotations

import re
from typing import Any, Optional, Protocol

from .config import Policy
from .errors import reason
from .keys import Signer as KeySigner, verify_sig
from .util import canonical_json

_DIGEST = re.compile(r"@sha256:([0-9a-f]{64})")
SIG_DOMAIN = b"PK_ECP_SIG/1\0"


def image_digest(image: str) -> Optional[str]:
    m = _DIGEST.search(image)
    return m.group(1) if m else None


def signing_payload(digest: str, name: str) -> bytes:
    return SIG_DOMAIN + digest.encode() + b"\0" + name.encode()


def sign_component(signer: KeySigner, image: str, name: str) -> str:
    d = image_digest(image)
    if d is None:
        raise ValueError("image must be digest-pinned to be signed")
    return signer.sign(signing_payload(d, name))


def statement_payload(stmt: dict[str, Any]) -> bytes:
    return b"PK_ECP_STMT/1\0" + canonical_json({k: v for k, v in stmt.items() if k != "signature"})


def sign_statement(signer: KeySigner, stmt: dict[str, Any]) -> dict[str, Any]:
    s = dict(stmt, signer=signer.key_id)
    s["signature"] = signer.sign(statement_payload(s))
    return s


class RegistryResolver(Protocol):
    def has_digest(self, registry: str, repository: str, digest: str) -> Optional[bool]: ...


class IndexResolver:
    def __init__(self, known: set[tuple[str, str, str]]):
        self.known = set(known)

    def has_digest(self, registry: str, repository: str, digest: str) -> Optional[bool]:
        return (registry, repository, digest) in self.known


def verify_component(policy: Policy, comp: dict[str, Any], target: tuple[str, ...], t: float, label: str,
                     resolver: Optional[RegistryResolver] = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (denial reasons, provenance evidence) for one component."""
    prov = policy.doc["provenance"]
    out: list[dict[str, Any]] = []
    ev: dict[str, Any] = {"component": label}
    image, name = comp.get("image", ""), comp.get("name", "")
    d = image_digest(image) if isinstance(image, str) else None
    ev["digest"] = d
    if d is None and prov.get("require_digest", True):
        out.append(reason("ECP_DIGEST_REQUIRED", f"{label}: image not pinned by sha256 digest", component=label))
    signer_id = comp.get("signer")
    signer = policy.signer_for(signer_id, target, t) if isinstance(signer_id, str) else None
    if signer is None:
        out.append(reason("ECP_SIGNER_NOT_APPROVED", f"{label}: signer {signer_id!r} not approved for scope",
                          component=label, signer=str(signer_id)[:128], scope="/".join(target)))
    if prov.get("require_signature", True):
        sig = comp.get("signature")
        if signer is not None:
            if not isinstance(sig, str) or d is None or not verify_sig(signer.public_key, sig, signing_payload(d, name)):
                out.append(reason("ECP_SIGNATURE_INVALID", f"{label}: signature does not verify for {signer.id}",
                                  component=label, signer=signer.id))
            else:
                ev["signature"] = {"signer": signer.id, "verified": True}
    if prov.get("require_attestation", False):
        st = comp.get("attestation")
        ok = False
        if isinstance(st, dict) and d is not None and st.get("subject_digest") == d:
            st_signer = st.get("signer")
            s2 = policy.signer_for(st_signer, target, t) if isinstance(st_signer, str) else None
            trusted = st.get("builder") in prov.get("trusted_builders", [])
            if s2 and trusted and isinstance(st.get("signature"), str) and \
                    verify_sig(s2.public_key, st["signature"], statement_payload(st)):
                ok = True
                ev["attestation"] = {"builder": st["builder"], "signer": s2.id, "source_rev": st.get("source_rev")}
        if not ok:
            out.append(reason("ECP_PROVENANCE_INVALID", f"{label}: attestation missing, untrusted or mismatched",
                              component=label))
    if resolver is not None and d is not None and "/" in image:
        reg, rest = image.split("/", 1)
        repo = rest.split("@", 1)[0].split(":", 1)[0]
        found = resolver.has_digest(reg.lower(), repo, d)
        ev["registry_resolved"] = found
        if found is not True:
            out.append(reason("ECP_PROVENANCE_INVALID", f"{label}: digest not present in registry", component=label,
                              registry=reg.lower()))
    return out, ev
