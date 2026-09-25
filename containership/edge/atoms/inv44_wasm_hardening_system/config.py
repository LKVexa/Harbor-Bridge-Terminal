"""Declarative configuration with provenance for INV-44 (missing component 11).

A ``ConfigStore`` is a directory:

    versions/000001.json ...   immutable, schema-valid PK_WASM_HARDENING/1 documents
    ACTIVE                     {"version": n, "digest": sha256, "activated_at": ts, "activated_by": subject}

* Every document must validate against PK_WASM_HARDENING/1 and name its
  author, version, creation time, reason and parent digest (C036).
* ``activate`` is compare-and-swap on the currently active version and swaps
  ACTIVE with ``os.replace`` (atomic on POSIX and NTFS) — a crash leaves either
  the old or the new pointer, never a partial one (C037, C057).
* ``rollback`` re-activates an earlier immutable version; history is never
  rewritten (C038).
* ``engine()`` refuses to build an engine from a document whose active
  feature set is incomplete *before* anything executes (C034, C035).
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

from .errors import HardeningError
from .runtime import REQUIRED_HARDENING, Engine
from .schema import load, validate


class ConfigInvalid(HardeningError):
    code = "WH-CONFIG-INVALID"


class ConfigConflict(HardeningError):
    code = "WH-CONFIG-CONFLICT"


def _canon(doc: dict) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()


def digest(doc: dict) -> str:
    return hashlib.sha256(_canon(doc)).hexdigest()


def check_document(doc: dict) -> None:
    errors = validate(doc, load("pk_wasm_hardening.v1.schema.json"))
    if errors:
        raise ConfigInvalid("configuration failed PK_WASM_HARDENING/1", errors=errors[:20])
    if set(doc["required_features"]) != REQUIRED_HARDENING:
        raise ConfigInvalid("required_features must equal the declared hardening set")
    missing = REQUIRED_HARDENING - set(doc["active_features"])
    if missing:
        raise ConfigInvalid("configuration activates a partial hardening set", missing=sorted(missing))


class ConfigStore:
    def __init__(self, root: str | os.PathLike, *, clock=time.time) -> None:
        self.root = Path(root)
        (self.root / "versions").mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self._lock = threading.Lock()

    def _vpath(self, n: int) -> Path:
        return self.root / "versions" / f"{n:06d}.json"

    def versions(self) -> list[int]:
        return sorted(int(p.stem) for p in (self.root / "versions").glob("*.json"))

    def active(self) -> dict | None:
        p = self.root / "ACTIVE"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def load_version(self, n: int) -> dict:
        doc = json.loads(self._vpath(n).read_text(encoding="utf-8"))
        return doc

    def propose(self, doc: dict) -> int:
        """Validate and store an immutable new version; does not activate it."""
        check_document(doc)
        with self._lock:
            n = doc["provenance"]["version"]
            existing = self.versions()
            if n in existing or (existing and n != existing[-1] + 1):
                raise ConfigConflict("version must be the next integer", have=existing[-1:] or [0], got=n)
            parent = doc["provenance"].get("parent_digest")
            if existing and parent != digest(self.load_version(existing[-1])):
                raise ConfigConflict("parent_digest does not match the latest version")
            tmp = self._vpath(n).with_suffix(".tmp")
            tmp.write_bytes(_canon(doc))
            os.replace(tmp, self._vpath(n))
            return n

    def activate(self, n: int, *, expected_active: int | None, activated_by: str) -> dict:
        with self._lock:
            cur = self.active()
            if (cur or {}).get("version") != expected_active:
                raise ConfigConflict("active version changed concurrently",
                                     expected=expected_active, actual=(cur or {}).get("version"))
            doc = self.load_version(n)
            check_document(doc)  # re-validate at activation time: stored bytes are not trusted
            pointer = {"version": n, "digest": digest(doc),
                       "activated_at": int(self._clock()), "activated_by": activated_by}
            tmp = self.root / "ACTIVE.tmp"
            with tmp.open("wb") as fh:
                fh.write(_canon(pointer)); fh.flush(); os.fsync(fh.fileno())
            os.replace(tmp, self.root / "ACTIVE")
            return pointer

    def rollback(self, to_version: int, *, activated_by: str) -> dict:
        cur = self.active()
        return self.activate(to_version, expected_active=(cur or {}).get("version"),
                             activated_by=activated_by)

    def engine(self) -> tuple[Engine, dict]:
        ptr = self.active()
        if ptr is None:
            raise ConfigInvalid("no active configuration")
        doc = self.load_version(ptr["version"])
        if digest(doc) != ptr["digest"]:
            raise ConfigInvalid("active configuration digest mismatch (tampered?)")
        check_document(doc)
        eng = Engine(doc["engine"], frozenset(doc["active_features"]),
                     memory_page_ceiling=doc["memory_page_ceiling"])
        eng.check()
        return eng, doc
