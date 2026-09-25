"""Deterministic reference world used by tests, examples, benchmarks and the pk_core assessments (MC-092).

Everything here is synthetic and labelled so: toolchain names are real projects, but versions end
in ``-fixture``, artifact bytes are ``b"fixture-artifact:<ref>"`` and every review/certificate is
issued by fixture identities with ephemeral keys.  Nothing here is a claim about upstream projects.
"""
from __future__ import annotations

import datetime as dt
import hashlib

from .advisories import AdvisoryStore, sign_feed
from .binding import Binder, Inv27Adapter
from .certification import CertificationStore, issue
from .model import IntegrityIdentity, Limitation, ReviewRecord, SecurityResponse, ToolchainRecord, fmt_utc
from .observability import AuditLedger, Metrics, StructuredLogger
from .policy import default_policy
from .registry import Authorizer, Registry
from .rollout import RolloutController
from .selection import SelectionRequest, Selector, SiteCapabilities
from .service import Inv28Service
from .trust import KeyRing

NOW = dt.datetime(2026, 9, 23, 12, 0, 0, tzinfo=dt.timezone.utc)
EVIDENCE = hashlib.sha256(b"fixture-review-evidence").hexdigest()


def artifact_bytes(ref: str) -> bytes:
    return f"fixture-artifact:{ref}".encode()


def record(name, version="1.0.0-fixture", *, languages=("c",), runtimes=("posix-libc",), architectures=("x86_64",),
           devices=("virtio-net",), features=("net-stack",), hypervisors=("qemu-kvm",), providers=("generic-cloud",),
           abis=("posix-subset",), maturity="mature", contact="mailto:security@fixture.invalid", sla=72,
           reviewed_at=None, review_result="approved", interval_days=180, review=True, limitations=(),
           lifecycle="active", eol_date="", integrity=True, catalog_status="supported") -> ToolchainRecord:
    ref = f"{name}@{version}"
    return ToolchainRecord(
        name=name, version=version, languages=frozenset(languages), runtimes=frozenset(runtimes),
        architectures=frozenset(architectures), devices=frozenset(devices), features=frozenset(features),
        hypervisors=frozenset(hypervisors), providers=frozenset(providers), abis=frozenset(abis), maturity=maturity,
        security=SecurityResponse(contact_ref=contact, advisory_feed="fixture://feed" if contact else "",
                                  disclosure_policy_ref="fixture://disclosure" if contact else "",
                                  response_sla_hours=sla if contact else 0),
        review=ReviewRecord("fixture-reviewer", reviewed_at or fmt_utc(NOW - dt.timedelta(days=10)), review_result,
                            "fixture://review/" + ref, EVIDENCE, interval_days) if review else None,
        limitations=tuple(limitations), lifecycle=lifecycle, eol_date=eol_date,
        integrity=IntegrityIdentity("fixture://" + ref, hashlib.sha256(artifact_bytes(ref)).hexdigest(),
                                    signer="fixture-signer") if integrity else None,
        catalog_status=catalog_status)


def standard_records():
    return [
        record("mirageos", languages=("ocaml",), runtimes=("ocaml-native",), architectures=("x86_64", "aarch64"),
               hypervisors=("solo5-hvt", "qemu-kvm", "xen"), abis=("solo5",), features=("net-stack", "tls"),
               limitations=(Limitation("no-posix", "no POSIX layer", frozenset({"posix-binary"})),)),
        record("unikraft", languages=("c", "rust"), runtimes=("posix-libc", "rust-std"), maturity="beta",
               hypervisors=("qemu-kvm", "firecracker"), devices=("virtio-net", "virtio-blk"),
               limitations=(Limitation("smp-limited", "limited SMP", frozenset({"smp"})),)),
        record("rumprun", languages=("c",), maturity="mature", devices=("virtio-net", "virtio-blk"),
               hypervisors=("qemu-kvm", "xen"), features=("net-stack", "posix-subset")),
        record("nanos", languages=("c", "go"), runtimes=("linux-elf",), maturity="experimental", contact="",
               hypervisors=("qemu-kvm", "firecracker"), features=("net-stack", "smp", "linux-binary-compat")),
    ]


def world(*, records=None, with_certs=True, with_feed=True, policy=None, gap08=None, now=NOW):
    ring = KeyRing.ephemeral()
    metrics, logger, audit = Metrics(), StructuredLogger(), AuditLedger(clock=lambda: now)
    reg = Registry(ring, Authorizer.permissive("operator"), clock=lambda: now, audit=audit)
    for r in (records if records is not None else standard_records()):
        reg.register(r, actor="operator", expected_revision=reg.revision)
    certs = CertificationStore(ring)
    if with_certs:
        for r in reg.entries:
            if r.integrity is None:
                continue
            for arch in sorted(r.architectures):
                certs.ingest(issue(ring, toolchain=r.name, version=r.version,
                                   artifact_sha256=r.integrity.artifact_sha256, architecture=arch,
                                   issued_at=fmt_utc(now - dt.timedelta(days=1)),
                                   expires_at=fmt_utc(now + dt.timedelta(days=90))))
    adv = AdvisoryStore(ring)
    if with_feed:
        adv.ingest(sign_feed(ring, [], fmt_utc(now - dt.timedelta(hours=1))))
    rollout = RolloutController(gap08)
    sel = Selector(reg, policy or default_policy(), certifications=certs, advisories=adv, rollout=rollout,
                   binder=Binder(ring), metrics=metrics, logger=logger, audit=audit)
    svc = Inv28Service(registry=reg, selector=sel, clock=lambda: now)
    return {"ring": ring, "registry": reg, "certs": certs, "advisories": adv, "selector": sel, "service": svc,
            "rollout": rollout, "inv27": Inv27Adapter(ring, reg), "metrics": metrics, "logger": logger,
            "audit": audit, "now": now}


def request(**kw) -> SelectionRequest:
    base: dict = dict(workload_id="wl-1", tenant="tenant-a", environment="production", language="c",
                      architecture="x86_64")
    base.update(kw)
    return SelectionRequest(**base)


def site(site_id="edge-1", architectures=("x86_64",), hypervisors=("qemu-kvm",), providers=()):
    return SiteCapabilities(site_id, frozenset(architectures), frozenset(hypervisors), frozenset(providers))
