"""Admission pipeline: immutable bytes -> verified seal (MC-001..MC-006, MC-008, MC-010 tied together).

Order (cheap and structural first, every step fail-closed, no side effects before GO):

  A0  bytes -> ImageBlob (size budget, sha256)                        UK_PARSE_TOO_LARGE
  A1  bound digest == blob digest                                       UK_DIGEST_MISMATCH
  A2  signature envelope verified against the trust root, provenance   UK_SIG_* / UK_PROVENANCE_*
      subject == blob digest, builder/toolchain approved
  A3  manifest strictly parsed; manifest digest == blob digest          UK_MANIFEST_INVALID
  A4  ELF parsed from the blob bytes under limits                       UK_PARSE_*
  A5  structural dynamic-linking check (PT_INTERP / DT_NEEDED)         UK_SEAL_DYNAMIC
  A6  facts derived from the binary (or, only for stripped images and only when enabled,
      from the *verified* attestation)                                 UK_SEAL_NO_EVIDENCE / UNKNOWN_TOOLCHAIN
  A7  toolchain: binary == manifest == provenance                       UK_SEAL_UNKNOWN_TOOLCHAIN
  A8  capabilities: multiprocess / dynload / debug                      UK_SEAL_MULTIPROCESS / DYNLOAD / DEBUG_SURFACE
  A9  single-address-space positive proof                               UK_SEAL_NOT_SAS
  A10 syscall set: manifest == binary; binary <= permitted              UK_SEAL_DRIFT / UK_SEAL_SYSCALL_FORBIDDEN
  A11 architecture: binary == manifest == site                          UK_SEAL_ARCH
  A12 boot contract (entry, W^X, memory)                                UK_BOOT_CONTRACT / UK_SEAL_WX
  A13 isolation plan from site policy                                   UK_ISOLATION_POLICY

The result is an ``AdmittedImage`` holding the blob itself, so execution cannot be handed
different bytes.  ``Decision`` records every step with the facts it used (MC-074).
"""
from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass, field
from types import MappingProxyType

from . import bootcontract, isolation as iso_mod, manifest as manifest_mod
from .errors import UkError
from .image import elf as elf_mod, facts as facts_mod
from .image.blob import ImageBlob
from .trust import signing

VERIFIER_VERSION = "inv27-admission/1.0.0"
SEAL_SCHEMA = "PK_UNIKERNEL_IMAGE/1"


@dataclass(frozen=True)
class SitePolicy:
    architecture: str
    permitted_syscalls: frozenset
    trust: signing.TrustRoot
    provenance: signing.ProvenancePolicy
    isolation: iso_mod.IsolationPolicy
    limits: elf_mod.Limits = elf_mod.Limits()
    allow_attested_facts: bool = False
    config_revision: str = "unversioned"


@dataclass
class Decision:
    image_ref: str | None = None
    steps: list = field(default_factory=list)
    outcome: str = "pending"
    code: str | None = None
    message: str | None = None
    started: float = field(default_factory=time.perf_counter)
    duration_ms: float = 0.0

    def step(self, sid: str, **facts) -> None:
        self.steps.append({"step": sid, "ok": True, **facts})

    def to_dict(self) -> dict:
        return {"schema": "PK_UNIKERNEL_DECISION/1", "verifier": VERIFIER_VERSION, "image": self.image_ref,
                "outcome": self.outcome, "code": self.code, "message": self.message,
                "duration_ms": round(self.duration_ms, 3), "steps": self.steps}


@dataclass(frozen=True)
class AdmittedImage:
    blob: ImageBlob
    manifest: manifest_mod.SealManifest
    facts: facts_mod.SealFacts
    plan: iso_mod.IsolationPlan
    seal: MappingProxyType
    decision: dict


def admit(image_bytes: bytes, *, bound_digest: str, manifest: dict | str | bytes, envelope: dict | None,
          policy: SitePolicy, tenant: str, now: dt.datetime | None = None) -> AdmittedImage:
    d = Decision()
    try:
        return _admit(d, image_bytes, bound_digest, manifest, envelope, policy, tenant, now)
    except UkError as e:
        d.outcome, d.code, d.message = ("refused" if e.outcome == "refused" else e.outcome), e.code, e.message
        e.details.setdefault("decision", d.to_dict())
        raise
    finally:
        d.duration_ms = (time.perf_counter() - d.started) * 1000
        if d.outcome == "pending":
            d.outcome = "error"


def _admit(d, image_bytes, bound_digest, manifest, envelope, policy, tenant, now) -> AdmittedImage:
    if not isinstance(tenant, str) or not tenant.strip():
        raise UkError("UK_FORBIDDEN", "tenant required")
    blob = ImageBlob.of(image_bytes, max_bytes=policy.limits.max_bytes)
    d.image_ref = blob.ref
    d.step("A0", size=blob.size, sha256=blob.sha256)
    blob.check(bound_digest)
    d.step("A1", bound=bound_digest)
    prov = signing.verify_envelope(envelope, image_ref=blob.ref, trust=policy.trust, policy=policy.provenance, now=now)
    st = prov.statement
    d.step("A2", keyid=prov.keyid, builder=st["builder"], toolchain=f"{st['toolchain']}@{st['toolchain_version']}",
           sig_backend=prov.backend, trust_root_version=policy.trust.version)
    m = manifest_mod.loads(manifest) if isinstance(manifest, (str, bytes)) else manifest_mod.parse(manifest)
    if m.digest != blob.ref:
        raise UkError("UK_MANIFEST_INVALID", "manifest image.digest does not name this image")
    d.step("A3", manifest_schema=manifest_mod.SCHEMA, name=m.name)
    e = elf_mod.parse(blob.data, policy.limits)
    d.step("A4", parser=e.parser_version, machine=e.machine, e_type=e.e_type, entry=hex(e.entry),
           symbols=len(e.symbols), build_id=e.build_id, work=e.work)
    if e.interp is not None or e.needed:
        raise UkError("UK_SEAL_DYNAMIC", "image is dynamically linked", interp=e.interp, needed=list(e.needed))
    d.step("A5", interp=None, needed=[])
    try:
        f = facts_mod.derive(e)
    except UkError as err:
        if err.code == "UK_SEAL_NO_EVIDENCE" and policy.allow_attested_facts and isinstance(st.get("attested_facts"), dict):
            f = facts_mod.from_attestation(e, st["attested_facts"])
        else:
            raise
    d.step("A6", facts_source=f.source, facts_version=f.facts_version, profile=f.profile_verifier)
    if not (f.toolchain == m.toolchain == st["toolchain"]):
        raise UkError("UK_SEAL_UNKNOWN_TOOLCHAIN", "toolchain disagreement",
                      binary=f.toolchain, manifest=m.toolchain, provenance=st["toolchain"])
    d.step("A7", toolchain=f.toolchain)
    for cat, code in (("multiprocess", "UK_SEAL_MULTIPROCESS"), ("dynload", "UK_SEAL_DYNLOAD"),
                      ("debug", "UK_SEAL_DEBUG_SURFACE")):
        hits = [c.evidence for c in f.capabilities if c.category == cat]
        if hits:
            raise UkError(code, f"{cat} capability linked into the image", evidence=hits)
    d.step("A8", capabilities=[])
    if not f.sas_proof["proven"]:
        raise UkError("UK_SEAL_NOT_SAS", "single-address-space not proven", proof=f.sas_proof)
    d.step("A9", proof=f.sas_proof["proof_type"], confidence=f.sas_proof["confidence"])
    drift = f.syscalls ^ m.syscalls
    if drift:
        raise UkError("UK_SEAL_DRIFT", "manifest syscall set differs from the binary",
                      only_in_binary=sorted(f.syscalls - m.syscalls), only_in_manifest=sorted(m.syscalls - f.syscalls))
    outside = f.syscalls - policy.permitted_syscalls
    if outside:
        raise UkError("UK_SEAL_SYSCALL_FORBIDDEN", "syscalls outside the site's permitted set", syscalls=sorted(outside))
    d.step("A10", syscalls=sorted(f.syscalls))
    if not (f.architecture == m.architecture == policy.architecture):
        raise UkError("UK_SEAL_ARCH", f"binary {f.architecture}, manifest {m.architecture}, site {policy.architecture}")
    d.step("A11", architecture=f.architecture)
    boot = bootcontract.enforce(e, m)
    d.step("A12", **boot)
    plan = iso_mod.plan(m.isolation, policy.isolation, tenant)
    d.step("A13", **plan.to_dict())
    seal = MappingProxyType({
        "schema": SEAL_SCHEMA, "image": m.name, "digest": blob.ref, "toolchain": f.toolchain,
        "architecture": f.architecture, "sealed": True, "syscalls": tuple(sorted(f.syscalls)),
        "syscall_count": len(f.syscalls), "facts_source": f.source, "sas_proof": f.sas_proof["proof_type"],
        "provenance_key": prov.keyid, "builder": st["builder"], "parser": e.parser_version,
        "verifier": VERIFIER_VERSION, "config_revision": policy.config_revision})
    d.outcome = "admitted"
    d.duration_ms = (time.perf_counter() - d.started) * 1000
    return AdmittedImage(blob, m, f, plan, seal, d.to_dict())
