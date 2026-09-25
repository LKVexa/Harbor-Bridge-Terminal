"""Policy engine integration (component 23).

A deterministic, bounded, built-in evaluator for signed, versioned policy
bundles (``PK_GITOPS_POLICY/1``), plus an adapter slot for OPA/Rego or CEL.

Bundle
  ``{"schema", "version", "rules": [...], "waivers": [...]}`` signed as a DSSE
  envelope by a trust-root key with purpose ``policy``; an unsigned, badly
  signed or version-regressing bundle is refused and the previous bundle
  stays active.

Rule
  ``{"id", "effect": "deny", "match": {"kind": [...], "namespace": [...]},
  "when": [{"path": "spec.replicas", "op": "gt", "value": 50}], "reason"}``.
  Operators: ``eq ne gt ge lt le in not_in exists absent matches``
  (``matches`` = anchored regex, length-bounded).  Paths are dotted with
  numeric list indices; ``*`` fans out over a list.

Evaluation
  input = (commit, ref, signer, resources); output = sorted deny list with
  rule id + reason + resource.  Bounded by ``max_evals`` steps; exceeding it
  is ``PolicyUnavailable`` (fail closed).  Waivers ``{"rule", "resource",
  "approved_by", "expires"}`` suppress a matching deny until expiry and are
  reported as ``waived`` -- never silently.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re

from . import ed25519
from .errors import Malformed, PolicyDenied, PolicyUnavailable, Untrusted
from .provenance import pae

PAYLOAD_TYPE = "application/vnd.pk.gitops.policy+json"
OPS = ("eq", "ne", "gt", "ge", "lt", "le", "in", "not_in", "exists", "absent", "matches")
_MISSING = object()


def _get(obj, path: str):
    cur = [obj]
    for part in path.split("."):
        nxt = []
        for c in cur:
            if part == "*" and isinstance(c, list):
                nxt.extend(c)
            elif isinstance(c, dict) and part in c:
                nxt.append(c[part])
            elif isinstance(c, list) and part.isdigit() and int(part) < len(c):
                nxt.append(c[int(part)])
        cur = nxt
    return cur


def _test(vals: list, op: str, v) -> bool:
    if op == "exists":
        return bool(vals)
    if op == "absent":
        return not vals
    res = []
    for x in vals:
        try:
            if op == "eq": res.append(x == v)
            elif op == "ne": res.append(x != v)
            elif op == "gt": res.append(x > v)
            elif op == "ge": res.append(x >= v)
            elif op == "lt": res.append(x < v)
            elif op == "le": res.append(x <= v)
            elif op == "in": res.append(x in v)
            elif op == "not_in": res.append(x not in v)
            elif op == "matches": res.append(isinstance(x, str) and len(x) <= 4096 and re.fullmatch(v, x) is not None)
        except TypeError:
            res.append(False)
    return any(res)


def validate_bundle(doc: dict) -> dict:
    if doc.get("schema") != "PK_GITOPS_POLICY/1" or not isinstance(doc.get("version"), int):
        raise Malformed("policy bundle schema/version invalid")
    ids = set()
    for r in doc.get("rules", []):
        if r.get("effect") != "deny" or not r.get("id") or r["id"] in ids:
            raise Malformed("policy rule invalid or duplicate id")
        ids.add(r["id"])
        for w in r.get("when", []):
            if w.get("op") not in OPS or not isinstance(w.get("path"), str) or len(w["path"]) > 256:
                raise Malformed("policy condition invalid", rule=r["id"])
            if w["op"] == "matches":
                if len(str(w.get("value"))) > 256:
                    raise Malformed("regex too long", rule=r["id"])
                re.compile(w["value"])
    return doc


def sign_bundle(doc: dict, key_id: str, secret: bytes) -> bytes:
    payload = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    sig = ed25519.sign(secret, pae(PAYLOAD_TYPE, payload))
    return json.dumps({"payloadType": PAYLOAD_TYPE, "payload": base64.b64encode(payload).decode(),
                       "signatures": [{"keyid": key_id, "sig": base64.b64encode(sig).decode()}]}).encode()


class PolicyEngine:
    def __init__(self, roots, *, max_evals: int = 200_000, external=None) -> None:
        self.roots, self.max_evals, self.external = roots, max_evals, external
        self.bundle: dict | None = None
        self.digest: str = "none"

    def load(self, raw: bytes, *, now: int) -> dict:
        try:
            env = json.loads(raw)
            payload = base64.b64decode(env["payload"], validate=True)
        except (ValueError, KeyError, TypeError):
            raise Untrusted("policy bundle envelope unparseable") from None
        if env.get("payloadType") != PAYLOAD_TYPE:
            raise Untrusted("policy bundle payload type")
        ok = False
        for s in env.get("signatures", [])[:8]:
            k = self.roots.keys.get(s.get("keyid", ""))
            if k and "policy" in k.purposes and (k.revoked_at is None or now < k.revoked_at) and \
                    ed25519.verify(k.public_key, pae(PAYLOAD_TYPE, payload), base64.b64decode(s["sig"])):
                ok = True
        if not ok:
            raise Untrusted("policy bundle not signed by a trusted policy key")
        doc = validate_bundle(json.loads(payload))
        if self.bundle and doc["version"] <= self.bundle["version"]:
            raise Untrusted("policy bundle version regression", have=self.bundle["version"], got=doc["version"])
        self.bundle, self.digest = doc, hashlib.sha256(payload).hexdigest()
        return {"version": doc["version"], "digest": self.digest}

    def evaluate(self, resources: dict, *, context: dict, now: int) -> dict:
        if self.bundle is None:
            raise PolicyUnavailable("no policy bundle loaded (fail closed)")
        steps, denies, waived = 0, [], []
        for rid in sorted(resources):
            obj = resources[rid]
            for r in self.bundle["rules"]:
                m = r.get("match", {})
                if m.get("kind") and rid[1] not in m["kind"]:
                    continue
                if m.get("namespace") and rid[2] not in m["namespace"]:
                    continue
                hit = True
                for w in r.get("when", []):
                    steps += 1
                    if steps > self.max_evals:
                        raise PolicyUnavailable("policy evaluation exceeded its step budget")
                    if not _test(_get(obj, w["path"]), w["op"], w.get("value")):
                        hit = False
                        break
                if hit:
                    d = {"rule": r["id"], "reason": r.get("reason", r["id"]), "resource": "/".join(x or "_" for x in rid)}
                    w = next((w for w in self.bundle.get("waivers", []) if w.get("rule") == r["id"]
                              and w.get("resource") in (d["resource"], "*") and w.get("approved_by")
                              and now < w.get("expires", 0)), None)
                    (waived if w else denies).append({**d, **({"waiver_by": w["approved_by"]} if w else {})})
        if self.external is not None:
            ext = self.external({"context": context, "resources": [list(k) for k in sorted(resources)]})
            denies.extend(ext.get("deny", []))
        return {"allow": not denies, "deny": denies, "waived": waived, "bundle_version": self.bundle["version"],
                "bundle_digest": self.digest, "steps": steps}

    def enforce(self, resources: dict, *, context: dict, now: int) -> dict:
        res = self.evaluate(resources, context=context, now=now)
        if not res["allow"]:
            raise PolicyDenied("policy denied the desired state", denies=res["deny"][:10])
        return res
