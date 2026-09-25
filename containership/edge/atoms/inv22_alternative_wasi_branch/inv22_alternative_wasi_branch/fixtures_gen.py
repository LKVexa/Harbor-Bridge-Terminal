"""Regenerate the portable conformance fixture corpus (MC-31).

``python -m inv22_alternative_wasi_branch.fixtures_gen`` writes fixtures/…
Each fixture is ``{"description", "expect", "document"}`` where ``expect`` is
``"ok"`` or the stable error code a conforming validator must return.
Certificate fixtures use a deterministic test-only Ed25519 key (seed below);
it is NOT a production key and is published only so verifiers can replay.
"""
from __future__ import annotations

import copy
import json
import pathlib

from . import canonical, matrix

PKG = pathlib.Path(__file__).resolve().parent
TEST_SEED = bytes(range(32))   # public, test-only


def _w(rel: str, description: str, expect: str, document) -> None:
    p = PKG / "fixtures" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"description": description, "expect": expect, "document": document},
                            indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _redigest(d):
    d["integrity"]["entries_digest"] = matrix.entries_digest(d["entries"])
    return d


def main() -> int:
    ref = json.loads((PKG / "data/matrix.json").read_text(encoding="utf-8"))
    _w("matrix/valid_reference.json", "committed reference matrix", "ok", ref)
    minimal = copy.deepcopy(ref)
    minimal["entries"] = [e for e in minimal["entries"] if e["interface"] == "wasi:sockets"]
    _w("matrix/valid_minimal.json", "one divergent entry", "ok", _redigest(minimal))
    d = copy.deepcopy(ref)
    d["contract"] = "PK_BRANCH_MATRIX/2"
    _w("matrix/forward_version.json", "unsupported future major version", "INV22.VERSION.UNSUPPORTED", d)
    d = copy.deepcopy(ref)
    d["entries"].append(copy.deepcopy(d["entries"][0]))
    _w("matrix/duplicate_entry.json", "duplicate interface id", "INV22.VALIDATION.SCHEMA", _redigest(d))
    d = copy.deepcopy(ref)
    d["entries"][1]["rationale"] = "edited after digest"
    _w("matrix/tampered.json", "entries changed without digest", "INV22.INTEGRITY.CORRUPT", d)
    d = copy.deepcopy(ref)
    d["entries"][0]["classification"] = "compatible"
    _w("matrix/unknown_enum.json", "classification outside the enum", "INV22.CLASSIFY.INVALID", _redigest(d))
    d = copy.deepcopy(ref)
    d["extra"] = True
    _w("matrix/unknown_field.json", "unknown top-level field", "INV22.VALIDATION.SCHEMA", d)

    base = {"contract": "PK_BRANCH_SHIM/1", "interface": "wasi:filesystem/types", "operation": "open-at",
            "source_branch": "standards", "target_branch": "fork", "encoding": "json-canonical",
            "correlation_id": "fx-1", "payload": {"open": ["create", "truncate"], "rights": ["write"]}}
    _w("shim/std_to_fork_ok.json", "shimmable translation; expect payload {oflags:9, rights_base:64}", "ok", base)
    rev = dict(base, source_branch="fork", target_branch="standards", payload={"oflags": 9, "rights_base": 64})
    _w("shim/fork_to_std_ok.json", "reverse translation; expect {open:[create,truncate], rights:[write]}", "ok", rev)
    _w("shim/identical_passthrough.json", "identical interface passes unchanged", "ok",
       dict(base, interface="wasi:clocks", payload={"now": 5}))
    _w("shim/divergent_refused.json", "divergent interface refused, no payload", "INV22.TRANSLATE.DIVERGENT",
       dict(base, interface="wasi:sockets", payload={}))
    _w("shim/unclassified_refused.json", "unclassified interface refused", "INV22.CLASSIFY.UNCLASSIFIED",
       dict(base, interface="wasi:http", payload={}))
    _w("shim/not_representable.json", "fork bit with no standards equivalent", "INV22.TRANSLATE.NOT_REPRESENTABLE",
       dict(rev, payload={"oflags": 16, "rights_base": 0}))
    _w("shim/unsupported_version.json", "unsupported contract version", "INV22.VERSION.UNSUPPORTED",
       dict(base, contract="PK_BRANCH_SHIM/9"))

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from . import cert
    except ImportError:
        return 0
    key = Ed25519PrivateKey.from_private_bytes(TEST_SEED)
    signer = cert.LocalSigner("test-key-1", "inv22-test-issuer", key)
    D = lambda c: "sha256:" + c * 64  # noqa: E731
    env = cert.issue(signer, cert_id="cert-fx-1", component_id="edge-handler", component_version="1.0.0",
                     artifact_digests=[D("a")], branch="standards", baselines={"standards": D("b"), "fork": D("c")},
                     matrix_digest=D("d"), evidence_digest=D("e"), issued_at=1_800_000_000, not_after=1_900_000_000)
    trust = {"schema": "PK_BRANCH_TRUST/1", "version": 1, "keys": [
        {"key_id": "test-key-1", "issuer": "inv22-test-issuer", "public_key": signer.public_b64(),
         "purposes": ["cert.sign"], "active_from": 0, "retired_at": None, "revoked": False}]}
    ctx = {"now": 1_850_000_000, "branch": "standards", "artifact_digest": D("a")}
    _w("cert/trust_store.json", "test-only trust store for the cert fixtures", "ok", trust)
    _w("cert/valid.json", "valid certificate; verify with context", "ok", {"envelope": env, "context": ctx})
    t = copy.deepcopy(env)
    t["payload"]["branch"] = "fork"
    _w("cert/tampered_branch.json", "payload edited after signing", "INV22.CERT.INVALID_SIGNATURE", {"envelope": t, "context": ctx})
    _w("cert/wrong_branch.json", "valid cert presented on the other branch", "INV22.CERT.UNCERTIFIED_BRANCH",
       {"envelope": env, "context": dict(ctx, branch="fork")})
    _w("cert/digest_mismatch.json", "different artifact", "INV22.CERT.DIGEST_MISMATCH",
       {"envelope": env, "context": dict(ctx, artifact_digest=D("f"))})
    _w("cert/expired.json", "after not_after", "INV22.CERT.EXPIRED", {"envelope": env, "context": dict(ctx, now=1_950_000_000)})
    u = copy.deepcopy(env)
    u["signature"]["key_id"] = "nobody"
    _w("cert/unknown_issuer.json", "key id not in trust store", "INV22.CERT.UNKNOWN_ISSUER", {"envelope": u, "context": ctx})
    v = copy.deepcopy(env)
    v["payload"]["contract"] = "PK_BRANCH_CERT/2"
    _w("cert/unsupported_version.json", "future certificate version", "INV22.VERSION.UNSUPPORTED", {"envelope": v, "context": ctx})
    s = copy.deepcopy(env)
    s["signature"]["value"] = "!!notbase64"
    _w("cert/malformed_signature.json", "signature is not base64", "INV22.CERT.INVALID_SIGNATURE", {"envelope": s, "context": ctx})
    print("fixtures regenerated;", canonical.digest(ref))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
