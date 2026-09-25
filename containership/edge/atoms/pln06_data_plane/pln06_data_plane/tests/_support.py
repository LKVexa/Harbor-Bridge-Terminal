"""Shared fixtures for the PLN-06 production test suites (stdlib only)."""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess  # nosec B404 - used only to call openssl for test certificates
import sys
import tempfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pln06_data_plane import DataPlane  # noqa: E402
from pln06_data_plane.integrations import ReferenceRuntime  # noqa: E402
from pln06_data_plane.lifecycle import TransferJournal  # noqa: E402
from pln06_data_plane.security import AuditLedger, Authenticator, KeyRing, LabelAuthority  # noqa: E402
from pln06_data_plane.service import GovernedDataPlane  # noqa: E402
from pln06_data_plane.transports import InProcessAdapter, SharedMemoryAdapter, shm_reader  # noqa: E402

ALL_WORKLOAD_CAPS = ("transfer.submit", "transfer.complete", "transport.use.inline",
                     "transport.use.local", "transport.use.bulk")
OPERATOR_CAPS = ("control.freeze", "policy.update", "policy.rollback", "diagnostics.read", "audit.read",
                 "transfer.complete.any")


class Env:
    """Builds a fully wired GovernedDataPlane in a temp directory."""

    def __init__(self, residency=None, adapters=None, **kw):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="pk06-"))
        self.keys = KeyRing()
        self.keys.add("k1")
        self.authn = Authenticator(self.keys)
        self.labels = LabelAuthority(self.keys)
        self.audit = AuditLedger(self.keys, self.dir / "audit.jsonl")
        self.journal = TransferJournal(self.dir / "journal.jsonl")
        self.runtime = ReferenceRuntime()
        self.received: list[bytes] = []
        if adapters is None:
            adapters = {
                "component-model-inprocess": InProcessAdapter(lambda d, v: self.received.append(bytes(v))),
                "shared-memory": SharedMemoryAdapter(shm_reader),
            }
        self.plane = DataPlane(residency or {"eu": {"public", "pii"}, "us": {"public"}},
                               inflight_limit=kw.pop("inflight_limit", 8), per_tenant_inflight_limit=kw.pop("ptl", 4))
        self.svc = GovernedDataPlane(self.plane, keyring=self.keys, authenticator=self.authn, labels=self.labels,
                                     audit=self.audit, journal=self.journal, adapters=adapters,
                                     runtime=self.runtime, **kw)

    def cred(self, tenant="t1", caps=ALL_WORKLOAD_CAPS, kind="workload", **kw):
        return self.authn.issue(f"{kind}-{tenant}", kind, caps, tenant=tenant, **kw)

    def op(self):
        return self.authn.issue("oncall", "operator", OPERATOR_CAPS)

    def label(self, data, classification="public", tenant="t1"):
        from pln06_data_plane.integrity import sha256_hex
        return self.labels.issue(classification=classification, digest=sha256_hex(data), tenant=tenant)

    def send(self, data=b"x" * 10, tenant="t1", classification="public", destination="eu", **kw):
        return self.svc.submit(self.cred(tenant), workload="w", data=data, classification=classification,
                               destination=destination, label=self.label(data, classification, tenant), **kw)

    def close(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def tls_contexts(tmp: pathlib.Path):
    """Create a throwaway CA-less self-signed server cert and client context (mTLS) using openssl."""
    import ssl
    openssl = shutil.which("openssl")
    if openssl is None:
        return None
    for who in ("server", "client"):
        subprocess.run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",  # nosec B603
                        "-subj", f"/CN={who}.pk06.test", "-addext", f"subjectAltName=DNS:{who}.pk06.test",
                        "-keyout", str(tmp / f"{who}.key"), "-out", str(tmp / f"{who}.crt")],
                       check=True, capture_output=True)
    srv = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    srv.minimum_version = ssl.TLSVersion.TLSv1_2
    srv.load_cert_chain(tmp / "server.crt", tmp / "server.key")
    srv.verify_mode = ssl.CERT_REQUIRED
    srv.load_verify_locations(tmp / "client.crt")
    cli = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    cli.minimum_version = ssl.TLSVersion.TLSv1_2
    cli.load_verify_locations(tmp / "server.crt")
    cli.load_cert_chain(tmp / "client.crt", tmp / "client.key")
    return srv, cli


# ---------------------------------------------------------------- tiny JSON-Schema subset validator
def validate_schema(instance, schema, path="$"):
    """Validates the 2020-12 keywords used by ./schemas (no external dependency)."""
    errors = []
    t = schema.get("type")
    types = t if isinstance(t, list) else ([t] if t else [])
    pytypes = {"object": dict, "string": str, "integer": int, "array": list, "boolean": bool,
               "null": type(None), "number": (int, float)}
    if types:
        ok = any(isinstance(instance, pytypes[x]) and not (x in ("integer", "number") and isinstance(instance, bool))
                 for x in types)
        if not ok:
            return [f"{path}: type {type(instance).__name__} not in {types}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: const")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: enum")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path}: minLength")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: pattern")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: minimum")
    if isinstance(instance, dict):
        for r in schema.get("required", []):
            if r not in instance:
                errors.append(f"{path}: missing {r}")
        props = schema.get("properties", {})
        for k, v in instance.items():
            if k in props:
                errors += validate_schema(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected {k}")
            elif isinstance(schema.get("additionalProperties"), dict):
                errors += validate_schema(v, schema["additionalProperties"], f"{path}.{k}")
    if isinstance(instance, list) and "items" in schema:
        for i, v in enumerate(instance):
            errors += validate_schema(v, schema["items"], f"{path}[{i}]")
    return errors


def load_schema(name):
    return json.loads((PKG_DIR / "schemas" / name).read_text(encoding="utf-8"))
