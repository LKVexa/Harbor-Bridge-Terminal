"""Configuration provenance/version/author/activation model (M10).

Every link config revision is an immutable ``ConfigRevision`` (monotonic version,
author principal, reason, created/activated timestamps, content digest, parent
version).  Activation is atomic per batch: ``activate_batch`` validates all
revisions first and commits all-or-nothing.  ``rollback`` activates a NEW
revision whose content equals an earlier one (history is never rewritten).
Staged rollout: revisions may be ``staged`` and promoted.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import asdict, dataclass

from ..errors.mapping import ProviderFault


@dataclass(frozen=True)
class ConfigRevision:
    link_key: tuple
    version: int
    parent: int | None
    author: str
    reason: str
    created_at: float
    digest: str
    config: dict
    state: str = "staged"  # staged | active | superseded
    activated_at: float | None = None


def digest(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ConfigHistory:
    def __init__(self):
        self._revs: dict[tuple, list[ConfigRevision]] = {}
        self._lock = threading.RLock()

    def propose(self, link_key: tuple, config: dict, *, author: str, reason: str) -> ConfigRevision:
        if not author or not reason:
            raise ProviderFault("PK_PROVIDER_INVALID_LINK", "config revision needs author and reason")
        with self._lock:
            revs = self._revs.setdefault(link_key, [])
            active = self.active(link_key)
            rev = ConfigRevision(link_key, len(revs) + 1, active.version if active else None, author[:256],
                                 reason[:512], time.time(), digest(config), json.loads(json.dumps(config)))
            revs.append(rev)
            return rev

    def active(self, link_key: tuple) -> ConfigRevision | None:
        with self._lock:
            for r in reversed(self._revs.get(link_key, [])):
                if r.state == "active":
                    return r
            return None

    def activate_batch(self, items: list[tuple[tuple, int]], validator=None) -> list[ConfigRevision]:
        """Atomically activate (link_key, version) pairs; any failure activates nothing."""
        with self._lock:
            chosen = []
            for key, ver in items:
                revs = self._revs.get(key, [])
                if not 1 <= ver <= len(revs) or revs[ver - 1].state != "staged":
                    raise ProviderFault("PK_PROVIDER_INVALID_LINK", f"revision {ver} of {key} not staged")
                if validator:
                    validator(key, revs[ver - 1].config)
                chosen.append((key, ver))
            now = time.time()
            out = []
            for key, ver in chosen:
                revs = self._revs[key]
                for i, r in enumerate(revs):
                    if r.state == "active":
                        revs[i] = ConfigRevision(**{**asdict(r), "state": "superseded"})
                revs[ver - 1] = ConfigRevision(**{**asdict(revs[ver - 1]), "state": "active", "activated_at": now})
                out.append(revs[ver - 1])
            return out

    def rollback(self, link_key: tuple, to_version: int, *, author: str, reason: str) -> ConfigRevision:
        with self._lock:
            revs = self._revs.get(link_key, [])
            if not 1 <= to_version <= len(revs):
                raise ProviderFault("PK_PROVIDER_INVALID_LINK", "unknown rollback target")
            rev = self.propose(link_key, revs[to_version - 1].config, author=author, reason=f"rollback to v{to_version}: {reason}")
            return self.activate_batch([(link_key, rev.version)])[0]

    def history(self, link_key: tuple) -> list[dict]:
        with self._lock:
            return [{k: v for k, v in asdict(r).items() if k != "config"} for r in self._revs.get(link_key, [])]
