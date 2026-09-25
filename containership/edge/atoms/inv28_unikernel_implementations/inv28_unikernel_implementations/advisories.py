"""Upstream CVE/advisory ingestion (MC-037) - the contract's optional "automated upstream CVE tracking".

INV-28 does not scrape the internet.  An operator-side collector produces a signed
``PK_ADVISORY_FEED/1`` document (purpose ``advisory``) listing advisories against *exact* toolchain
versions.  :class:`AdvisoryStore` verifies and ingests it; selection eliminates a candidate that
has an open advisory at or above the environment's ``advisory_block_severity``
(``TC_ADVISORY_OPEN``, waivable only by an approved, expiring waiver).

Staleness: a feed older than ``max_age`` makes the store ``stale``; production selection then
refuses with ``SEL_DEPENDENCY_UNAVAILABLE`` - "no news" from a dead feed is not "no advisories".
"""
from __future__ import annotations

import datetime as dt
import threading
from dataclasses import dataclass

from .errors import Reason, ValidationError
from .model import parse_utc, sha256_hex, text
from .policy import SEVERITIES
from .trust import KeyRing

SCHEMA = "PK_ADVISORY_FEED/1"
MAX_ADVISORIES = 50_000


@dataclass(frozen=True)
class Advisory:
    id: str
    toolchain: str
    affected_versions: frozenset
    severity: str
    published: str
    fixed_in: str = ""
    withdrawn: bool = False


class AdvisoryStore:
    def __init__(self, ring: KeyRing, *, max_age: dt.timedelta = dt.timedelta(days=2)):
        self._ring = ring
        self._max_age = max_age
        self._adv: dict[str, Advisory] = {}
        self._by_name: dict[str, tuple] = {}
        self._generated_at: dt.datetime | None = None
        self._lock = threading.RLock()

    def ingest(self, feed: dict) -> int:
        if not isinstance(feed, dict) or feed.get("schema") != SCHEMA:
            raise ValidationError(f"feed schema must be {SCHEMA}", code=Reason.DEPENDENCY_UNAVAILABLE)
        body = {k: v for k, v in feed.items() if k != "signature"}
        if not self._ring.verify("advisory", body, feed.get("signature")):
            raise ValidationError("advisory feed signature invalid", code=Reason.DEPENDENCY_UNAVAILABLE)
        gen = parse_utc(feed.get("generated_at"), "generated_at")
        items = feed.get("advisories")
        if not isinstance(items, list) or len(items) > MAX_ADVISORIES:
            raise ValidationError("advisories must be a bounded list")
        parsed = {}
        for a in items:
            sev = str(a.get("severity", "")).lower()
            if sev not in SEVERITIES:
                raise ValidationError(f"advisory {a.get('id')}: unknown severity")
            vers = a.get("affected_versions")
            if not isinstance(vers, list) or not vers or any(not isinstance(v, str) or any(c in v for c in "*<>^~") for v in vers):
                raise ValidationError(f"advisory {a.get('id')}: affected_versions must be exact versions")
            adv = Advisory(text(a.get("id"), "id"), text(a.get("toolchain"), "toolchain").casefold(),
                           frozenset(vers), sev, text(a.get("published"), "published"),
                           str(a.get("fixed_in", "")), bool(a.get("withdrawn", False)))
            parsed[adv.id] = adv
        with self._lock:
            if self._generated_at and gen < self._generated_at:
                raise ValidationError("advisory feed is older than the one already ingested (rollback refused)",
                                      code=Reason.DEPENDENCY_UNAVAILABLE)
            self._adv.update(parsed)
            by_name: dict = {}
            for a in self._adv.values():
                by_name.setdefault(a.toolchain, []).append(a)
            self._by_name = {k: tuple(v) for k, v in by_name.items()}
            self._generated_at = gen
        return len(parsed)

    def stale(self, now: dt.datetime) -> bool:
        return self._generated_at is None or now - self._generated_at > self._max_age

    def open_for(self, name: str, version: str, min_severity: str) -> list[Advisory]:
        floor = SEVERITIES.index(min_severity)
        by_name = self._by_name          # copy-on-write reference; lock-free read (see certification.lookup)
        return sorted((a for a in by_name.get(name.casefold(), ())
                       if not a.withdrawn and version in a.affected_versions
                       and SEVERITIES.index(a.severity) >= floor), key=lambda a: a.id)

    @property
    def digest(self) -> str:
        with self._lock:
            return sha256_hex([sorted(self._adv), self._generated_at.isoformat() if self._generated_at else None])


def sign_feed(ring: KeyRing, advisories: list, generated_at: str) -> dict:
    body = {"schema": SCHEMA, "generated_at": generated_at, "advisories": advisories}
    return {**body, "signature": ring.sign("advisory", body)}
