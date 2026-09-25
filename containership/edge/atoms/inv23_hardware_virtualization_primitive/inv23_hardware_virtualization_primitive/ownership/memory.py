"""In-memory provider: deterministic unit tests and single-process embedding only."""

from __future__ import annotations

import copy
import threading
from contextlib import contextmanager

from .base import ClaimProvider


class MemoryClaimProvider(ClaimProvider):
    name = "memory"

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self._mutex = threading.RLock()
        self._records: dict = {}
        self._gens: dict = {}
        self.quarantined: list = []

    @contextmanager
    def _critical(self, resource):
        with self._mutex:
            yield

    def _load(self, resource):
        r = self._records.get(resource)
        return copy.deepcopy(r) if r is not None else None

    def _store(self, resource, rec):
        self._records[resource] = copy.deepcopy(rec)

    def _load_generation(self, resource):
        return self._gens.get(resource, 0)

    def _store_generation(self, resource, gen):
        self._gens[resource] = max(gen, self._gens.get(resource, 0))

    def _quarantine(self, resource):
        if resource in self._records:
            self.quarantined.append(self._records.pop(resource))
