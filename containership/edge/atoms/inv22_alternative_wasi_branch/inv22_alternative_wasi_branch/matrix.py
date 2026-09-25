"""PK_BRANCH_MATRIX/1 typed envelope, baselines, completeness (MC-05, MC-06, MC-11, MC-62).

The in-code ``component.MATRIX`` remains the legacy view; this module is the
external contract.  Consumers need only the JSON Schema in ``schemas/`` plus
the canonicalisation rules in ``canonical.py``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping

from . import canonical
from .errors import Inv22Error

CONTRACT = "PK_BRANCH_MATRIX/1"
CLASSIFICATIONS = ("identical", "shimmable", "divergent")
INTERFACE_ID = re.compile(r"^[a-z][a-z0-9-]*:[a-z][a-z0-9-]*(/[a-z][a-z0-9-]*)?$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
MAX_ENTRIES = 4096

_ENTRY_KEYS = {"interface", "source_version", "target_version", "classification", "rationale",
               "shim_id", "proof_ref", "deprecation"}
_TOP_KEYS = {"contract", "revision", "source_baseline", "target_baseline", "generated_at",
             "producer", "entries", "integrity"}


def _schema(msg: str, **details) -> Inv22Error:
    return Inv22Error("INV22.VALIDATION.SCHEMA", msg, details)


def _text(obj: Mapping, key: str, maxlen: int = 512) -> str:
    v = obj.get(key)
    if not isinstance(v, str) or not v.strip() or len(v) > maxlen:
        raise _schema(f"{key} must be a non-empty string of at most {maxlen} chars", field=key)
    return v


def _baseline(obj: Any, key: str) -> dict:
    if not isinstance(obj, dict) or set(obj) != {"id", "digest"}:
        raise _schema(f"{key} must be {{id, digest}}", field=key)
    _text(obj, "id", 256)
    if not DIGEST.match(obj["digest"] if isinstance(obj["digest"], str) else ""):
        raise _schema(f"{key}.digest must be sha256:<hex64>", field=key)
    return obj


@dataclass(frozen=True)
class Entry:
    interface: str
    classification: str
    source_version: str
    target_version: str
    rationale: str
    shim_id: str | None = None
    proof_ref: str | None = None
    end_of_support: str | None = None


@dataclass(frozen=True)
class Matrix:
    revision: int
    source_baseline: dict
    target_baseline: dict
    entries: tuple[Entry, ...]
    digest: str

    def classification(self, interface: str) -> str:
        for e in self.entries:
            if e.interface == interface:
                return e.classification
        raise Inv22Error("INV22.CLASSIFY.UNCLASSIFIED", "interface is not classified", {"interface": interface})

    def as_legacy(self) -> dict[str, str]:
        return {e.interface: e.classification for e in self.entries}


def _entry(raw: Any, today: date | None) -> Entry:
    if not isinstance(raw, dict):
        raise _schema("entry must be an object")
    unknown = set(raw) - _ENTRY_KEYS
    if unknown:
        raise _schema("unknown entry field", field=sorted(unknown)[0])
    iface = _text(raw, "interface", 128)
    if not INTERFACE_ID.match(iface):
        raise _schema("interface id is not canonical", interface=iface)
    cls = raw.get("classification")
    if cls not in CLASSIFICATIONS:
        raise Inv22Error("INV22.CLASSIFY.INVALID", "unsupported classification", {"interface": iface, "value": cls})
    shim_id = raw.get("shim_id")
    if cls == "shimmable":
        if not isinstance(shim_id, str) or not shim_id:
            raise _schema("shimmable entries require shim_id", interface=iface)
        if not isinstance(raw.get("proof_ref"), str) or not raw["proof_ref"]:
            raise _schema("shimmable entries require proof_ref (MC-13)", interface=iface)
    elif shim_id is not None:
        raise _schema("shim_id only allowed for shimmable entries", interface=iface)
    eos = None
    if "deprecation" in raw:
        dep = raw["deprecation"]
        if not isinstance(dep, dict) or set(dep) - {"announced", "end_of_support", "migration"}:
            raise _schema("malformed deprecation", interface=iface)
        eos = _text(dep, "end_of_support", 10)
        try:
            eos_d = date.fromisoformat(eos)
        except ValueError:
            raise _schema("end_of_support must be YYYY-MM-DD", interface=iface) from None
        if today is not None and today > eos_d:
            raise Inv22Error("INV22.VERSION.UNSUPPORTED", "interface is past end of support",
                             {"interface": iface, "end_of_support": eos})
    return Entry(iface, cls, _text(raw, "source_version", 64), _text(raw, "target_version", 64),
                 _text(raw, "rationale", 2048), shim_id, raw.get("proof_ref"), eos)


def entries_digest(entries: list) -> str:
    return canonical.digest(sorted(entries, key=lambda e: e["interface"]))


def parse(doc: Any, *, today: date | None = None) -> Matrix:
    """Validate a PK_BRANCH_MATRIX/1 document; any doubt fails closed."""
    if isinstance(doc, (bytes, str)):
        doc = canonical.loads(doc)
    if not isinstance(doc, dict):
        raise _schema("matrix must be an object")
    canonical.require_supported(doc.get("contract", ""), "PK_BRANCH_MATRIX")
    missing = _TOP_KEYS - set(doc)
    if missing:
        raise _schema("missing field", field=sorted(missing)[0])
    if set(doc) - _TOP_KEYS:
        raise _schema("unknown field", field=sorted(set(doc) - _TOP_KEYS)[0])
    rev = doc["revision"]
    if not isinstance(rev, int) or isinstance(rev, bool) or rev < 1:
        raise _schema("revision must be a positive integer")
    src = _baseline(doc["source_baseline"], "source_baseline")
    dst = _baseline(doc["target_baseline"], "target_baseline")
    if not TIMESTAMP.match(doc["generated_at"] if isinstance(doc["generated_at"], str) else ""):
        raise _schema("generated_at must be RFC3339 UTC (YYYY-MM-DDTHH:MM:SSZ)")
    _text(doc, "producer", 256)
    raw_entries = doc["entries"]
    if not isinstance(raw_entries, list) or not raw_entries:
        raise _schema("entries must be a non-empty list")
    if len(raw_entries) > MAX_ENTRIES:
        raise Inv22Error("INV22.VALIDATION.LIMIT", "too many entries", {"max": MAX_ENTRIES})
    entries = [_entry(e, today) for e in raw_entries]
    seen = set()
    for e in entries:
        if e.interface in seen:
            raise _schema("duplicate interface id", interface=e.interface)
        seen.add(e.interface)
    integ = doc["integrity"]
    if not isinstance(integ, dict) or set(integ) != {"entries_digest"}:
        raise _schema("integrity must be {entries_digest}")
    expected = entries_digest(raw_entries)
    if integ["entries_digest"] != expected:
        raise Inv22Error("INV22.INTEGRITY.CORRUPT", "matrix entries digest mismatch")
    ordered = tuple(sorted(entries, key=lambda e: e.interface))
    return Matrix(rev, src, dst, ordered, canonical.digest(doc))


def build(entries: list[dict], *, revision: int, source_baseline: dict, target_baseline: dict,
          generated_at: str, producer: str) -> dict:
    """Produce a canonical, self-consistent matrix document (validated before return)."""
    entries = sorted(entries, key=lambda e: e["interface"])
    doc = {"contract": CONTRACT, "revision": revision, "source_baseline": source_baseline,
           "target_baseline": target_baseline, "generated_at": generated_at, "producer": producer,
           "entries": entries, "integrity": {"entries_digest": entries_digest(entries)}}
    parse(doc)
    return doc


# --- completeness (MC-11) -----------------------------------------------------

def completeness(matrix: Matrix, discovered: Iterable[str], excluded: Mapping[str, str] | None = None) -> dict:
    """Reconcile discovered interfaces with the matrix.  ``ok`` only when unclassified == 0."""
    excluded = dict(excluded or {})
    for iface, why in excluded.items():
        if not isinstance(why, str) or not why.strip():
            raise _schema("every exclusion needs a justification", interface=iface)
    classified = {e.interface for e in matrix.entries}
    disc = sorted(set(discovered))
    unclassified = [i for i in disc if i not in classified and i not in excluded]
    return {"discovered": len(disc),
            "classified": sum(1 for i in disc if i in classified),
            "excluded": sum(1 for i in disc if i in excluded and i not in classified),
            "unclassified": len(unclassified),
            "unclassified_ids": unclassified,
            "matrix_digest": matrix.digest,
            "ok": not unclassified}


# --- baselines (MC-05) --------------------------------------------------------

def check_baselines(manifest: Any) -> dict:
    """Validate the baselines manifest; report whether both branches are immutably pinned."""
    if not isinstance(manifest, dict) or manifest.get("schema") != "PK_BRANCH_BASELINES/1":
        raise _schema("baselines manifest must declare schema PK_BRANCH_BASELINES/1")
    problems: list[str] = []
    out = {"pinned": True, "problems": problems}
    for key in ("standards", "fork"):
        b = manifest.get(key)
        if not isinstance(b, dict):
            raise _schema("missing branch baseline", field=key)
        ref = b.get("commit")
        dig = b.get("digest")
        if not (isinstance(ref, str) and re.fullmatch(r"[0-9a-f]{40}", ref)):
            out["pinned"] = False
            problems.append(f"{key}: commit is not an immutable 40-hex SHA")
        if not (isinstance(dig, str) and DIGEST.match(dig)):
            out["pinned"] = False
            problems.append(f"{key}: content digest missing")
        if not isinstance(b.get("feature_profile"), list) or not b.get("feature_profile"):
            out["pinned"] = False
            problems.append(f"{key}: feature profile not enumerated")
    return out
