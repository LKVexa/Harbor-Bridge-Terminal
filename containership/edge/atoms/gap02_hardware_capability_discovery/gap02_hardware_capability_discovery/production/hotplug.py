"""GAP02-MC-29 — Hot-plug watcher adapters.

Portable polling adapter: fingerprints sysfs/OS device listings per probe
family and notifies the executor when a fingerprint changes. (udev/netlink,
WMI and IOKit event adapters can replace ``PollingWatcher.poll`` without
changing the executor contract: ``notify_hotplug(probe_names)``.)
Debounced so a flapping device cannot trigger a probe storm.
"""
from __future__ import annotations

import hashlib
import threading
import time
from typing import Callable

from .evidence import Host

WATCH = {
    "accelerators": ("/sys/class/drm", "/sys/class/accel", "/sys/class/kfd/kfd/topology/nodes"),
    "storage": ("/sys/block",),
    "nic": ("/sys/class/net",),
    "tpm": ("/sys/class/tpm",),
    "numa": ("/sys/devices/system/node",),
    "cpu": ("/sys/devices/system/cpu",),
}


class PollingWatcher:
    def __init__(self, notify: Callable[[list[str]], None], host: Host | None = None,
                 debounce: float = 2.0, watch: dict | None = None):
        self.notify, self.host, self.debounce = notify, host or Host(), debounce
        self.watch = watch or WATCH
        self._fp = {k: self._fingerprint(v) for k, v in self.watch.items()}
        self._last_fire: dict[str, float] = {}
        self._stop = threading.Event()

    def _fingerprint(self, paths) -> str:
        h = hashlib.sha256()
        for p in paths:
            h.update(p.encode())
            for e in self.host.listdir(p):
                h.update(b"\0" + e.encode())
        return h.hexdigest()

    def poll(self, now: float | None = None) -> list[str]:
        now = time.monotonic() if now is None else now
        changed = []
        for k, paths in self.watch.items():
            fp = self._fingerprint(paths)
            if fp != self._fp[k] and now - self._last_fire.get(k, -1e9) >= self.debounce:
                self._fp[k] = fp
                self._last_fire[k] = now
                changed.append(k)
        if changed:
            self.notify(changed)
        return changed

    def run(self, interval: float = 1.0) -> None:
        while not self._stop.wait(interval):
            self.poll()

    def stop(self) -> None:
        self._stop.set()
