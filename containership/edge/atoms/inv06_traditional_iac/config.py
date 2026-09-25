"""Configuration parser/compiler, overlays and provenance (MC-016, MC-024, MC-025).

``parse_hcl_subset`` accepts a deliberately small, pinned HCL subset
(``IAC_LANG = "inv06-hcl-subset/1"``)::

    resource "type" "name" {
      key   = "string with ${other_type.other_name.attr} reference"
      count = 3
      on    = true
      tags  = ["a", "b"]
      meta  = { owner = "team" }
      depends_on = ["type.other"]
    }

Anything outside the subset (modules, providers, variables, expressions,
heredocs, functions) is refused with a line/column error rather than being
half-interpreted.  Full Terraform HCL remains the job of a pinned external
engine (see ``execution.py``).

``compile_config`` layers an immutable base artifact with ordered overlays
(``global < environment < site``), validates the result, builds the resource
graph and returns a digest-bound activation record.  ``ProvenanceLedger``
records who activated which revision, from which source, with which approval,
and links each activation to the one it can roll back to.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import time
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from .graph import ResourceGraph
from .state import IacError, _canonical_bytes, _normalise_resource_map

IAC_LANG = "inv06-hcl-subset/1"
MAX_SOURCE_BYTES = 4 * 1024 * 1024
OVERLAY_ORDER = ("global", "environment", "site")


class ConfigError(IacError):
    code = "PK_IAC_CONFIG_INVALID"


_TOKEN = re.compile(
    r"""(?P<ws>[ \t\r]+)|(?P<nl>\n)|(?P<comment>\#[^\n]*|//[^\n]*)|
        (?P<str>"(?:[^"\\\n]|\\.)*")|(?P<num>-?\d+(?:\.\d+)?)|
        (?P<ident>[A-Za-z_][\w-]*)|(?P<punct>[{}\[\]=,])""",
    re.X,
)


def _tokenise(src: str) -> list[tuple[str, str, int, int]]:
    toks, pos, line, col = [], 0, 1, 1
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        if not m:
            raise ConfigError("unexpected character", details={"line": line, "col": col, "char": src[pos]})
        kind, text = m.lastgroup, m.group()
        if kind == "nl":
            line, col = line + 1, 1
        else:
            if kind not in ("ws", "comment"):
                toks.append((kind, text, line, col))
            col += len(text)
        pos = m.end()
    return toks


class _Parser:
    def __init__(self, toks: list[tuple[str, str, int, int]]) -> None:
        self.t, self.i = toks, 0

    def peek(self) -> tuple[str, str, int, int] | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, kind: str | None = None, text: str | None = None) -> tuple[str, str, int, int]:
        tok = self.peek()
        if tok is None:
            raise ConfigError("unexpected end of input", details={"expected": text or kind})
        if (kind and tok[0] != kind) or (text and tok[1] != text):
            raise ConfigError("unexpected token", details={"line": tok[2], "col": tok[3], "got": tok[1], "expected": text or kind})
        self.i += 1
        return tok

    def value(self) -> Any:
        tok = self.peek()
        if tok is None:
            raise ConfigError("missing value")
        if tok[0] == "str":
            self.i += 1
            return json.loads(tok[1])
        if tok[0] == "num":
            self.i += 1
            return float(tok[1]) if "." in tok[1] else int(tok[1])
        if tok[0] == "ident" and tok[1] in ("true", "false", "null"):
            self.i += 1
            return {"true": True, "false": False, "null": None}[tok[1]]
        if tok[1] == "[":
            self.i += 1
            out = []
            while self.peek() and self.peek()[1] != "]":
                out.append(self.value())
                if self.peek() and self.peek()[1] == ",":
                    self.i += 1
            self.take(text="]")
            return out
        if tok[1] == "{":
            return self.body()
        raise ConfigError("unsupported expression (outside inv06-hcl-subset/1)", details={"line": tok[2], "col": tok[3], "got": tok[1]})

    def body(self) -> dict[str, Any]:
        self.take(text="{")
        out: dict[str, Any] = {}
        while self.peek() and self.peek()[1] != "}":
            key = self.take("ident")
            if key[1] in out:
                raise ConfigError("duplicate attribute", details={"line": key[2], "key": key[1]})
            self.take(text="=")
            out[key[1]] = self.value()
            if self.peek() and self.peek()[1] == ",":
                self.i += 1
        self.take(text="}")
        return out


def parse_hcl_subset(src: str) -> dict[str, Any]:
    if len(src.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise ConfigError("configuration source too large", details={"limit": MAX_SOURCE_BYTES})
    p = _Parser(_tokenise(src))
    resources: dict[str, Any] = {}
    while p.peek():
        kw = p.take("ident")
        if kw[1] != "resource":
            raise ConfigError("only 'resource' blocks are supported", details={"line": kw[2], "got": kw[1]})
        rtype = json.loads(p.take("str")[1])
        rname = json.loads(p.take("str")[1])
        for part in (rtype, rname):
            if not re.fullmatch(r"[A-Za-z_][\w-]*", part):
                raise ConfigError("invalid resource type/name", details={"value": part, "line": kw[2]})
        rid = f"{rtype}.{rname}"
        if rid in resources:
            raise ConfigError("duplicate resource", details={"resource": rid, "line": kw[2]})
        resources[rid] = p.body()
    return resources


def _deep_merge(base: Any, over: Any) -> Any:
    if isinstance(base, Mapping) and isinstance(over, Mapping):
        out = dict(base)
        for k, v in over.items():
            out[k] = _deep_merge(base[k], v) if k in base else deepcopy(v)
        return out
    return deepcopy(over)


def compile_config(base: Mapping[str, Any], overlays: Mapping[str, Mapping[str, Any]] | None = None, *, source_revision: str = "unknown") -> dict[str, Any]:
    """Return ``{"desired", "digest", "order", "layers", "lang"}`` or raise ``ConfigError``.

    Overlays may only *modify* resources declared in the base artifact; adding
    new resources through an overlay is refused so that the immutable artifact
    remains the single source of the resource set.  Setting a value to ``null``
    in an overlay is explicit and kept.
    """
    overlays = dict(overlays or {})
    unknown = sorted(set(overlays) - set(OVERLAY_ORDER))
    if unknown:
        raise ConfigError("unknown overlay layer", details={"unknown": unknown, "allowed": list(OVERLAY_ORDER)})
    desired = _normalise_resource_map(base, label="base")
    layers = []
    for name in OVERLAY_ORDER:
        if name not in overlays:
            continue
        ov = _normalise_resource_map(overlays[name], label=f"overlay.{name}")
        extra = sorted(set(ov) - set(desired))
        if extra:
            raise ConfigError("overlay introduces resources absent from base artifact", details={"layer": name, "resources": extra})
        for rid, v in ov.items():
            desired[rid] = _deep_merge(desired[rid], v)
        layers.append({"layer": name, "digest": hashlib.sha256(_canonical_bytes(ov)).hexdigest()})
    graph = ResourceGraph(desired)
    return {
        "lang": IAC_LANG,
        "source_revision": source_revision,
        "desired": desired,
        "order": graph.order,
        "layers": layers,
        "digest": hashlib.sha256(_canonical_bytes(desired)).hexdigest(),
    }


class ProvenanceLedger:
    """Append-only JSONL configuration-activation ledger with hash chaining."""

    REQUIRED = ("config_digest", "source_revision", "actor", "environment", "approval")

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text("utf-8").splitlines() if l.strip()]

    def record(self, **fields: Any) -> dict[str, Any]:
        missing = [k for k in self.REQUIRED if not fields.get(k)]
        if missing:
            raise ConfigError("provenance record incomplete", details={"missing": missing})
        prior = self.entries()
        prev_same_env = next((e for e in reversed(prior) if e["environment"] == fields["environment"]), None)
        entry = {
            "seq": len(prior) + 1,
            "activated_ns": time.time_ns(),
            **{k: fields[k] for k in self.REQUIRED},
            "version": fields.get("version"),
            "rollback_to": prev_same_env["config_digest"] if prev_same_env else None,
            "previous_digest": prior[-1]["digest"] if prior else "0" * 64,
        }
        entry["digest"] = hashlib.sha256(_canonical_bytes(entry)).hexdigest()
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return entry

    def verify(self) -> bool:
        prev = "0" * 64
        for e in self.entries():
            body = {k: v for k, v in e.items() if k != "digest"}
            if e["previous_digest"] != prev or hashlib.sha256(_canonical_bytes(body)).hexdigest() != e["digest"]:
                return False
            prev = e["digest"]
        return True
