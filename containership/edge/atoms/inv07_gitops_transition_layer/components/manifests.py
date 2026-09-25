"""Manifest/input parser hardening (component 24).

Desired state is read from the approved commit as ``*.json`` / ``*.yaml`` /
``*.yml`` files under the configured path.  Parsing is deliberately strict:

JSON
  duplicate keys refused (``object_pairs_hook``), NaN/Infinity refused, size
  and nesting depth bounded before and after decoding.

YAML (safe block subset -- no PyYAML dependency, no code paths to construct
objects)
  block mappings / sequences, plain, single- and double-quoted scalars,
  ``---`` multi-document, comments.  **Refused**: anchors ``&``, aliases
  ``*`` (billion-laughs), tags ``!``, merge keys ``<<``, flow collections,
  multi-line block scalars, tabs for indentation, duplicate keys, documents
  over the size/depth/node limits.  Scalars stay strings unless they are the
  YAML 1.2 core ints/floats/bools/null -- ``no``/``on``/``yes`` are strings
  (no Norway problem).

Resources must be objects with ``apiVersion``, ``kind`` and
``metadata.name``; identity is ``(apiVersion-group, kind, namespace, name)``
and duplicates across files are refused.  Helm/Kustomize rendering is an
external-renderer slot (``render_external``) that is BLOCKED until a pinned
renderer binary is supplied (see docs/COMPATIBILITY.md).
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

from .errors import LimitExceeded, Malformed

MAX_BYTES, MAX_DEPTH, MAX_NODES = 1 << 20, 32, 100_000
_INT = re.compile(r"^[-+]?(0|[1-9][0-9]*)$")
_FLOAT = re.compile(r"^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$")
_KEY = re.compile(r"^([A-Za-z0-9_./-][A-Za-z0-9_./ -]*|\"[^\"]*\"|'[^']*'):(\s|$)")


def _check_tree(v: Any, depth: int = 0, count: list | None = None, max_depth: int = MAX_DEPTH) -> None:
    count = count if count is not None else [0]
    count[0] += 1
    if count[0] > MAX_NODES:
        raise LimitExceeded("manifest has too many nodes")
    if depth > max_depth:
        raise LimitExceeded("manifest nesting too deep", depth=depth)
    if isinstance(v, dict):
        for x in v.values():
            _check_tree(x, depth + 1, count, max_depth)
    elif isinstance(v, list):
        for x in v:
            _check_tree(x, depth + 1, count, max_depth)
    elif isinstance(v, float) and not math.isfinite(v):
        raise Malformed("non-finite number")


def parse_json(data: bytes, *, max_bytes: int = MAX_BYTES, max_depth: int = MAX_DEPTH) -> Any:
    if len(data) > max_bytes:
        raise LimitExceeded("manifest exceeds size limit", size=len(data))
    # cheap pre-scan so a deeply nested document cannot exhaust the C stack
    depth = best = 0
    for ch in data:
        if ch in (0x5B, 0x7B):
            depth += 1
            best = max(best, depth)
            if best > max_depth:
                raise LimitExceeded("manifest nesting too deep")
        elif ch in (0x5D, 0x7D):
            depth -= 1

    def pairs(kv):
        d = {}
        for k, v in kv:
            if k in d:
                raise Malformed("duplicate key", key=k[:64])
            d[k] = v
        return d

    def bad_const(x):
        raise Malformed("non-finite number")

    try:
        v = json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=bad_const)
    except UnicodeDecodeError:
        raise Malformed("manifest is not UTF-8") from None
    except json.JSONDecodeError as exc:
        raise Malformed("invalid JSON", line=exc.lineno) from None
    _check_tree(v, max_depth=max_depth)
    return v


def _scalar(s: str, ln: int) -> Any:
    s = s.strip()
    if not s:
        return None
    if s[0] in "&*!":
        raise Malformed("YAML anchors, aliases and tags are refused", line=ln)
    if s[0] in "[{":
        if s in ("[]", "{}"):
            return [] if s == "[]" else {}
        raise Malformed("YAML flow collections are refused", line=ln)
    if s[0] in "|>":
        raise Malformed("YAML block scalars are refused", line=ln)
    if s[0] == '"':
        if not s.endswith('"') or len(s) < 2:
            raise Malformed("unterminated double-quoted scalar", line=ln)
        try:
            return json.loads(s)
        except ValueError:
            raise Malformed("bad escape in double-quoted scalar", line=ln) from None
    if s[0] == "'":
        if not s.endswith("'") or len(s) < 2:
            raise Malformed("unterminated single-quoted scalar", line=ln)
        return s[1:-1].replace("''", "'")
    if " #" in s:
        s = s.split(" #", 1)[0].rstrip()
    if s in ("null", "~", "Null", "NULL"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if _INT.match(s):
        return int(s)
    if _FLOAT.match(s):
        return float(s)
    if s in (".inf", ".nan", "-.inf", "+.inf", ".NaN", ".Inf"):
        raise Malformed("non-finite YAML number refused", line=ln)
    return s


def _key(raw: str, ln: int) -> str:
    raw = raw.strip()
    if raw == "<<":
        raise Malformed("YAML merge keys are refused", line=ln)
    if raw[:1] in "&*!?":
        raise Malformed("YAML anchors, aliases, tags and complex keys are refused", line=ln)
    k = _scalar(raw, ln) if raw[:1] in "\"'" else raw
    return str(k)


def parse_yaml(data: bytes, *, max_bytes: int = MAX_BYTES, max_depth: int = MAX_DEPTH) -> list[Any]:
    if len(data) > max_bytes:
        raise LimitExceeded("manifest exceeds size limit", size=len(data))
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Malformed("manifest is not UTF-8") from None
    docs, cur = [], []
    for ln_no, line in enumerate(text.split("\n"), 1):
        if line.rstrip() in ("---", "..."):
            docs.append(cur)
            cur = []
            continue
        if line.startswith("%"):
            raise Malformed("YAML directives are refused", line=ln_no)
        cur.append((ln_no, line))
    docs.append(cur)
    out = []
    for d in docs:
        lines = []
        for n, l in d:
            if "\t" in l[: len(l) - len(l.lstrip())]:
                raise Malformed("tab indentation refused", line=n)
            st = l.strip()
            if not st or st.startswith("#"):
                continue
            lines.append((n, len(l) - len(l.lstrip(" ")), l.strip()))
        if not lines:
            continue
        pos = [0]
        v = _block(lines, pos, lines[0][1], 0, max_depth)
        if pos[0] != len(lines):
            raise Malformed("unexpected indentation", line=lines[pos[0]][0])
        _check_tree(v, max_depth=max_depth)
        out.append(v)
    return out


def _block(lines, pos, indent, depth, max_depth):
    if depth > max_depth:
        raise LimitExceeded("manifest nesting too deep")
    n, ind, s = lines[pos[0]]
    if s.startswith("- ") or s == "-":
        seq = []
        while pos[0] < len(lines):
            n, ind, s = lines[pos[0]]
            if ind < indent:
                break
            if ind > indent or not (s.startswith("- ") or s == "-"):
                raise Malformed("bad sequence indentation", line=n)
            rest = s[1:].strip()
            pos[0] += 1
            if not rest:
                if pos[0] < len(lines) and lines[pos[0]][1] > indent:
                    seq.append(_block(lines, pos, lines[pos[0]][1], depth + 1, max_depth))
                else:
                    seq.append(None)
            elif _KEY.match(rest):
                # "- key: value" starts an inline mapping at indent+2
                sub_ind = ind + (len(s) - len(rest))
                lines.insert(pos[0], (n, sub_ind, rest))
                seq.append(_block(lines, pos, sub_ind, depth + 1, max_depth))
            else:
                seq.append(_scalar(rest, n))
        return seq
    mp: dict = {}
    while pos[0] < len(lines):
        n, ind, s = lines[pos[0]]
        if ind < indent:
            break
        if ind > indent:
            raise Malformed("bad mapping indentation", line=n)
        m = _KEY.match(s)
        if not m:
            raise Malformed("expected 'key: value'", line=n)
        k = _key(m.group(1), n)
        if k in mp:
            raise Malformed("duplicate key", key=k[:64], line=n)
        rest = s[m.end():].strip()
        pos[0] += 1
        if rest and not rest.startswith("#"):
            mp[k] = _scalar(rest, n)
        elif pos[0] < len(lines) and (lines[pos[0]][1] > indent or
                                      (lines[pos[0]][1] == indent and lines[pos[0]][2].startswith("-"))):
            mp[k] = _block(lines, pos, lines[pos[0]][1], depth + 1, max_depth)
        else:
            mp[k] = None
    return mp


def resource_id(r: dict) -> tuple[str, str, str, str]:
    group = r["apiVersion"].split("/")[0] if "/" in r["apiVersion"] else ""
    return (group, r["kind"], r.get("metadata", {}).get("namespace") or "", r["metadata"]["name"])


def validate_resource(r: Any, path: str) -> dict:
    if not isinstance(r, dict):
        raise Malformed("resource must be an object", path=path)
    for k in ("apiVersion", "kind"):
        if not isinstance(r.get(k), str) or not r[k]:
            raise Malformed(f"resource missing {k}", path=path)
    md = r.get("metadata")
    if not isinstance(md, dict) or not isinstance(md.get("name"), str) or not re.fullmatch(
            r"[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?", md["name"]):
        raise Malformed("resource metadata.name missing or not DNS-1123", path=path)
    ns = md.get("namespace")
    if ns is not None and not (isinstance(ns, str) and re.fullmatch(r"[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?", ns)):
        raise Malformed("metadata.namespace invalid", path=path)
    return r


def load_tree(files: list[tuple[str, bytes]], *, max_bytes: int = MAX_BYTES, max_depth: int = MAX_DEPTH,
              max_resources: int = 5000) -> dict[tuple, dict]:
    """Parse (path, bytes) pairs into a resource map keyed by identity."""
    out: dict[tuple, dict] = {}
    total = 0
    for path, data in sorted(files):
        total += len(data)
        if total > max_bytes * 16:
            raise LimitExceeded("total manifest bytes exceed limit")
        if path.endswith(".json"):
            docs = parse_json(data, max_bytes=max_bytes, max_depth=max_depth)
            docs = docs if isinstance(docs, list) else [docs]
        elif path.endswith((".yaml", ".yml")):
            docs = parse_yaml(data, max_bytes=max_bytes, max_depth=max_depth)
        else:
            continue
        for d in docs:
            if d is None:
                continue
            r = validate_resource(d, path)
            rid = resource_id(r)
            if rid in out:
                raise Malformed("duplicate resource identity across manifests", path=path, name=rid[3])
            out[rid] = r
            if len(out) > max_resources:
                raise LimitExceeded("too many resources", limit=max_resources)
    return out


def render_external(tool: str, *_args, **_kw):  # pragma: no cover - blocked slot
    """Helm/Kustomize rendering slot.  No pinned renderer ships with INV-07."""
    from .errors import TargetUnavailable
    raise TargetUnavailable("external renderer not bundled", tool=tool)
