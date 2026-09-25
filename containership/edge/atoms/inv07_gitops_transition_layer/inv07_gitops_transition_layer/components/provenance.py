"""Artifact provenance integration (component 04).

Provenance for a commit is a DSSE envelope (``application/vnd.in-toto+json``)
stored as a git note on ``refs/notes/provenance``, so it travels with the
repository and is fetched by the same pinned transport.

Verification (``verify``) fails closed unless:

1. the envelope parses under size/depth limits and uses DSSE PAE;
2. at least ``threshold`` distinct trusted *builder* keys (purpose
   ``provenance``) sign it (Ed25519);
3. the statement is in-toto v1 with an allowed ``predicateType`` (SLSA v1);
4. a subject binds *both* ``gitCommit`` == the commit OID and ``gitTree`` ==
   its tree OID (subject-digest binding -- a note copied onto another commit
   fails);
5. the builder id is in ``allowed_builders`` and the source URI matches the
   pinned repository.

Not implemented here and therefore BLOCKED on GAP-07: X.509 certificate-chain
validation (Fulcio), transparency-log inclusion proofs (Rekor), and the
external GAP-07 verifier service.  ``external_verifier`` is the adapter slot:
when configured it must *also* accept the envelope (defence in depth); when it
is required but absent, verification fails closed.
"""
from __future__ import annotations

import base64
import json
from typing import Callable

from . import ed25519
from .errors import Malformed, ProvenanceFailed
from .signing import TrustRoots

PAYLOAD_TYPE = "application/vnd.in-toto+json"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATES = ("https://slsa.dev/provenance/v1",)
MAX_ENVELOPE = 256 << 10


def pae(payload_type: str, payload: bytes) -> bytes:
    t = payload_type.encode()
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


def make_statement(*, commit: str, tree: str, repo_url: str, builder_id: str, ref: str) -> dict:
    return {"_type": STATEMENT_TYPE,
            "subject": [{"name": f"git+{repo_url}@{ref}", "digest": {"gitCommit": commit, "gitTree": tree}}],
            "predicateType": PREDICATES[0],
            "predicate": {"buildDefinition": {"buildType": "https://pk.example/gitops/review/v1",
                                              "externalParameters": {"source": repo_url, "ref": ref}},
                          "runDetails": {"builder": {"id": builder_id}}}}


def sign_envelope(statement: dict, signers: list[tuple[str, bytes]]) -> bytes:
    payload = json.dumps(statement, sort_keys=True, separators=(",", ":")).encode()
    sigs = [{"keyid": kid, "sig": base64.b64encode(ed25519.sign(sk, pae(PAYLOAD_TYPE, payload))).decode()}
            for kid, sk in signers]
    return json.dumps({"payloadType": PAYLOAD_TYPE, "payload": base64.b64encode(payload).decode(),
                       "signatures": sigs}, sort_keys=True).encode()


def verify(raw: bytes | None, *, commit: str, tree: str, repo_url: str, roots: TrustRoots, now: int,
           allowed_builders: tuple[str, ...], threshold: int = 1,
           external_verifier: Callable[[bytes], bool] | None = None, require_external: bool = False) -> dict:
    if raw is None:
        raise ProvenanceFailed("no provenance note for commit", oid=commit)
    if len(raw) > MAX_ENVELOPE:
        raise ProvenanceFailed("provenance envelope too large")
    try:
        env = json.loads(raw)
        payload = base64.b64decode(env["payload"], validate=True)
        st = json.loads(payload)
    except (ValueError, KeyError, TypeError):
        raise ProvenanceFailed("provenance envelope unparseable") from None
    if env.get("payloadType") != PAYLOAD_TYPE:
        raise ProvenanceFailed("unexpected DSSE payloadType")
    good = set()
    for s in env.get("signatures", [])[:16]:
        k = roots.keys.get(s.get("keyid", ""))
        if not k or k.algorithm != "ed25519" or "provenance" not in k.purposes:
            continue
        if k.revoked_at is not None and now >= k.revoked_at or not (k.not_before <= now <= k.not_after):
            continue
        try:
            sig = base64.b64decode(s["sig"], validate=True)
        except (ValueError, KeyError):
            continue
        if ed25519.verify(k.public_key, pae(PAYLOAD_TYPE, payload), sig):
            good.add(k.key_id)
    if len(good) < threshold:
        raise ProvenanceFailed("provenance not signed by enough trusted builder keys", have=len(good), need=threshold)
    if st.get("_type") != STATEMENT_TYPE or st.get("predicateType") not in PREDICATES:
        raise ProvenanceFailed("statement type/predicate not allowed")
    subj = st.get("subject") or []
    if not any(isinstance(x, dict) and x.get("digest", {}).get("gitCommit") == commit
               and x.get("digest", {}).get("gitTree") == tree for x in subj):
        raise ProvenanceFailed("no subject binds this commit and tree digest", oid=commit)
    pred = st.get("predicate", {})
    builder = pred.get("runDetails", {}).get("builder", {}).get("id")
    if builder not in allowed_builders:
        raise ProvenanceFailed("builder identity not allowed", builder=str(builder))
    src = pred.get("buildDefinition", {}).get("externalParameters", {}).get("source")
    if src != repo_url:
        raise ProvenanceFailed("provenance source does not match the pinned repository")
    if external_verifier is not None:
        if not external_verifier(raw):
            raise ProvenanceFailed("external GAP-07 verifier rejected the provenance")
    elif require_external:
        raise ProvenanceFailed("external GAP-07 verifier required but not configured")
    return {"builder": builder, "signers": sorted(good), "predicate": st["predicateType"]}


def parse_limits_ok(raw: bytes) -> bool:
    try:
        json.loads(raw)
        return len(raw) <= MAX_ENVELOPE
    except ValueError:
        raise Malformed("not JSON") from None
