"""Shared test fixtures: real ELF images, a test trust root, signed provenance and manifests.

The Ed25519 seeds below are TEST-ONLY constants (derived from fixed labels) and are listed in
ops/IDENTITY_INVENTORY.json as such; they must never appear in a production trust root.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE.parent
sys.dont_write_bytecode = True
if str(PKG.parent) not in sys.path:
    sys.path.insert(0, str(PKG.parent))
if str(PKG / "_vendor") not in sys.path:
    sys.path.append(str(PKG / "_vendor"))

PKGNAME = PKG.name
import importlib  # noqa: E402

inv27 = importlib.import_module(PKGNAME)
admission = importlib.import_module(f"{PKGNAME}.admission")
signing = importlib.import_module(f"{PKGNAME}.trust.signing")
ed25519 = importlib.import_module(f"{PKGNAME}.trust.ed25519")
isolation = importlib.import_module(f"{PKGNAME}.isolation")
errors = importlib.import_module(f"{PKGNAME}.errors")
elf = importlib.import_module(f"{PKGNAME}.image.elf")
facts = importlib.import_module(f"{PKGNAME}.image.facts")
UkError = errors.UkError

FIX = HERE / "fixtures"
NOW = dt.datetime(2026, 9, 23, 12, 0, tzinfo=dt.timezone.utc)
SEED = hashlib.sha256(b"inv27-test-builder-key").digest()
ROGUE_SEED = hashlib.sha256(b"inv27-test-rogue-key").digest()
PUB = ed25519.public_key(SEED)
KEYID = "test-builder-2026"
BUILDER = "pk-reference-builder"
PERMITTED = frozenset({"read", "write", "clock_gettime", "solo5.console_write", "solo5.clock_monotonic"})
TOOLCHAIN_VERSION = {"unikraft": "0.17.0", "solo5": "0.9.0"}


def image(name: str) -> bytes:
    return (FIX / name).read_bytes()


def ref(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def trust_root(**overrides) -> "signing.TrustRoot":
    key = {"keyid": KEYID, "public_hex": PUB.hex(), "builders": [BUILDER],
           "not_before": "2026-01-01T00:00:00+00:00", "not_after": "2027-01-01T00:00:00+00:00", "revoked": False}
    key.update(overrides)
    return signing.TrustRoot.from_dict({"schema": "PK_UNIKERNEL_TRUST_ROOT/1", "version": 7, "keys": [key]},
                                       fetched_at=NOW - dt.timedelta(hours=1))


def prov_policy() -> "signing.ProvenancePolicy":
    return signing.ProvenancePolicy(frozenset({BUILDER}), {"unikraft": frozenset({"0.17.0"}),
                                                           "solo5": frozenset({"0.9.0"})})


def policy(**kw) -> "admission.SitePolicy":
    base = dict(architecture="x86_64", permitted_syscalls=PERMITTED, trust=trust_root(), provenance=prov_policy(),
                isolation=isolation.IsolationPolicy(frozenset({"none", "tap"}), frozenset({"br-t1"}),
                                                    frozenset({"serial", "virtio-net", "virtio-rng"}), frozenset(),
                                                    {"t1": frozenset({"br-t1"})}),
                config_revision="test-rev-1")
    base.update(kw)
    return admission.SitePolicy(**base)


def statement(data: bytes, toolchain: str = "unikraft", **kw) -> dict:
    st = {"schema": signing.SCHEMA, "subject": {"digest": ref(data), "name": "svc"}, "builder": BUILDER,
          "toolchain": toolchain, "toolchain_version": TOOLCHAIN_VERSION[toolchain],
          "source": {"uri": "git+https://example.invalid/svc", "digest": "sha256:" + "ab" * 32},
          "built_at": "2026-09-22T00:00:00Z"}
    st.update(kw)
    return st


def envelope(data: bytes, toolchain: str = "unikraft", seed: bytes = SEED, keyid: str = KEYID, **kw) -> dict:
    return signing.sign_envelope(statement(data, toolchain, **kw), seed, keyid)


def manifest(data: bytes, toolchain: str = "unikraft", syscalls=None, **kw) -> dict:
    if syscalls is None:
        syscalls = ["read", "write", "clock_gettime"] if toolchain == "unikraft" else \
            ["solo5.console_write", "solo5.clock_monotonic"]
    m = {"schema": "PK_UNIKERNEL_SEAL_MANIFEST/1", "image": {"name": "svc", "digest": ref(data)},
         "toolchain": toolchain, "architecture": "x86_64", "syscalls": list(syscalls),
         "boot": {"memory_mib": 32, "vcpus": 1, "cmdline": "console=ttyS0", "ready_marker": "INV27-READY"},
         "isolation": {"network": "none", "devices": ["serial"], "storage": []}}
    for k, v in kw.items():
        m[k] = v
    return m


def admit(name: str = "uk_good.elf", *, data: bytes | None = None, toolchain: str = "unikraft", pol=None,
          env=..., man=None, tenant: str = "t1", bound=None):
    data = image(name) if data is None else data
    return admission.admit(data, bound_digest=bound or ref(data),
                           manifest=man if man is not None else manifest(data, toolchain),
                           envelope=envelope(data, toolchain) if env is ... else env,
                           policy=pol or policy(), tenant=tenant, now=NOW)
