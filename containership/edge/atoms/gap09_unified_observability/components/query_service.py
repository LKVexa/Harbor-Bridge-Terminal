"""Query service beyond latest value (33).

Time-range reads over an append-only per-series point store with filtering,
aggregation, opaque signed pagination cursors and explicit consistency
semantics: every response states ``consistency: "read_committed_local"`` and
the ``watermark`` (highest ingest sequence visible), so a client can tell a
later page was read against the same or a newer snapshot.
"""
from __future__ import annotations

import base64
import bisect
import hashlib
import hmac
import json
import threading
from collections import defaultdict
from typing import Any

from .errors import Malformed, Unauthorized

MAX_PAGE = 1000
AGGS = ("none", "sum", "avg", "min", "max", "count", "last")


class RangeStore:
    def __init__(self, *, cursor_key: bytes, max_points_per_series: int = 100_000) -> None:
        self._pts: dict[tuple, list] = defaultdict(list)  # key -> [(at, seq, value, exemplar)]
        self._seq = 0
        self._lock = threading.Lock()
        self._key = cursor_key
        self._max = max_points_per_series

    def add(self, key: tuple, at: int, value: float, exemplar: str | None = None) -> None:
        with self._lock:
            self._seq += 1
            pts = self._pts[key]
            bisect.insort(pts, (at, self._seq, value, exemplar))
            if len(pts) > self._max:
                del pts[0]

    def _cursor(self, payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        mac = hmac.new(self._key, raw, hashlib.sha256).digest()[:16]
        return base64.urlsafe_b64encode(raw + mac).decode()

    def _uncursor(self, c: str) -> dict:
        try:
            blob = base64.urlsafe_b64decode(c.encode())
        except Exception as exc:
            raise Malformed("cursor malformed") from exc
        raw, mac = blob[:-16], blob[-16:]
        if not hmac.compare_digest(hmac.new(self._key, raw, hashlib.sha256).digest()[:16], mac):
            raise Malformed("cursor tampered")
        return json.loads(raw)

    def query(self, *, scope_tenants: frozenset, tenant: str, signal: str, start: int, end: int,
              filters: dict | None = None, agg: str = "none", step: int | None = None, limit: int = 100,
              cursor: str | None = None) -> dict:
        if tenant not in scope_tenants and "*" not in scope_tenants:
            raise Unauthorized("tenant not in authenticated scope")
        if not (0 <= start < end) or end - start > 400 * 86_400:
            raise Malformed("range invalid or too wide")
        if agg not in AGGS:
            raise Malformed("unknown aggregation")
        if not (1 <= limit <= MAX_PAGE):
            raise Malformed("limit out of bounds")
        filters = dict(filters or {})
        with self._lock:
            watermark = self._seq
            keys = sorted(k for k in self._pts if k[0] == tenant and k[4] == signal
                          and all(dict(zip(("tenant", "environment", "site", "workload"), k[:4])).get(f) == v
                                  for f, v in filters.items()))
            rows = []
            for k in keys:
                pts = self._pts[k]
                lo = bisect.bisect_left(pts, (start, -1, float("-inf"), None))
                for at, seq, val, ex in pts[lo:]:
                    if at >= end:
                        break
                    rows.append((k, at, seq, val, ex))
        if cursor:
            c = self._uncursor(cursor)
            if (c["t"], c["s"], c["a"], c["b"], c["g"]) != (tenant, signal, start, end, agg):
                raise Malformed("cursor belongs to a different query")
            watermark = c["w"]
            rows = [r for r in rows if r[2] <= watermark]
            offset = c["o"]
        else:
            offset = 0
        if agg != "none":
            if not step or step <= 0:
                raise Malformed("aggregation requires a positive step")
            buckets: dict = {}
            for k, at, seq, val, ex in rows:
                buckets.setdefault((at - at % step), []).append((at, val, ex))
            fn = {"sum": lambda xs: sum(v for _, v, _ in xs), "avg": lambda xs: sum(v for _, v, _ in xs) / len(xs),
                  "min": lambda xs: min(v for _, v, _ in xs), "max": lambda xs: max(v for _, v, _ in xs),
                  "count": len, "last": lambda xs: max(xs)[1]}[agg]
            items = [{"t": t, "value": fn(xs), "exemplar": next((e for _, _, e in xs if e), None)}
                     for t, xs in sorted(buckets.items())]
        else:
            items = [{"series": dict(zip(("tenant", "environment", "site", "workload", "signal"), k)), "t": at,
                      "value": val, "exemplar": ex} for k, at, seq, val, ex in rows]
        page = items[offset: offset + limit]
        nxt = None
        if offset + limit < len(items):
            nxt = self._cursor({"t": tenant, "s": signal, "a": start, "b": end, "g": agg, "w": watermark,
                                "o": offset + limit})
        return {"schema": "GAP09-RANGE/1", "consistency": "read_committed_local", "watermark": watermark,
                "items": page, "next_cursor": nxt}
