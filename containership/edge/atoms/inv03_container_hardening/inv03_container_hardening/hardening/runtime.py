"""Sandbox runtime inventory, version pinning and fail-closed selection.

Checklist items served: 2 (discovery + approved-version matrix + minimum
security version), 4 (reject absent / unhealthy / unsupported / downgraded
runtime). Node reports come from a host agent (e.g. ``runsc --version`` +
containerd config); this module decides on them, it does not fabricate them.
"""
from __future__ import annotations

import re
import threading
from typing import Mapping

_RUNSC_VERSION = re.compile(r"release-(\d{8})\.(\d+)")


def parse_runsc_version(text: object) -> tuple[int, int] | None:
    """Parse ``runsc --version`` output ("runsc version release-20240807.0")."""
    if not isinstance(text, str):
        return None
    m = _RUNSC_VERSION.search(text)
    return (int(m.group(1)), int(m.group(2))) if m else None


class RuntimeInventory:
    def __init__(self, classes: Mapping[str, str], min_version: Mapping[str, tuple[int, int]],
                 max_report_age: int = 300):
        """``classes``: RuntimeClass name -> handler (e.g. {"gvisor": "runsc"})."""
        self._classes = dict(classes)
        self._min = dict(min_version)
        self._max_age = max_report_age
        self._nodes: dict[str, dict] = {}
        self._lock = threading.Lock()

    def handler_for(self, runtime_class: object) -> str | None:
        return self._classes.get(runtime_class) if isinstance(runtime_class, str) else None

    def report(self, node: str, handler: str, version_text: str, healthy: bool, at: int) -> None:
        with self._lock:
            prev = self._nodes.get(node, {}).get(handler)
            ver = parse_runsc_version(version_text)
            downgraded = bool(prev and prev.get("version") and ver and ver < prev["version"])
            self._nodes.setdefault(node, {})[handler] = {
                "version": ver, "healthy": healthy is True, "at": at,
                "downgraded": downgraded or bool(prev and prev.get("downgraded")),
            }

    def check(self, runtime_class: object, node: object, now: int | None = None) -> tuple[bool, str]:
        handler = self.handler_for(runtime_class)
        if handler is None:
            return False, f"runtime class {runtime_class!r} has no approved handler"
        if node is None:
            # Pre-scheduling admission: node unknown. The class is approved; the
            # node-side check is repeated at bind time by the adapter.
            return True, f"class {runtime_class} -> {handler} approved; node check deferred to bind"
        with self._lock:
            rep = self._nodes.get(node, {}).get(handler) if isinstance(node, str) else None
        if rep is None:
            return False, f"node {node!r} has not reported handler {handler}"
        if not rep["healthy"]:
            return False, f"handler {handler} unhealthy on {node}"
        if rep["downgraded"]:
            return False, f"handler {handler} was downgraded on {node}"
        if now is not None and now - rep["at"] > self._max_age:
            return False, f"runtime report from {node} is stale"
        floor = self._min.get(handler)
        if floor and (rep["version"] is None or rep["version"] < floor):
            return False, f"{handler} version {rep['version']} below minimum {floor}"
        return True, f"{handler} {rep['version']} healthy on {node}"

    def inventory(self) -> dict:
        with self._lock:
            return {n: {h: dict(r) for h, r in hs.items()} for n, hs in self._nodes.items()}
