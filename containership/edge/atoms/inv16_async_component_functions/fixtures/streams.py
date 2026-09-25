"""SURROGATE INV-17 stream: bounded buffer, backpressure, cancellation, ownership by call id."""
from __future__ import annotations

import threading
from collections import deque

SURROGATE = True
INV17_FIXTURE_VERSION = "surrogate-1"


class Backpressure(RuntimeError):
    pass


class StreamClosed(RuntimeError):
    pass


class Stream:
    def __init__(self, owner_call: int, capacity: int = 16):
        self.owner_call = owner_call
        self.capacity = capacity
        self.buf: deque = deque()
        self.state = "open"   # open | done | cancelled | trapped
        self.lock = threading.Lock()

    def write(self, item) -> None:
        with self.lock:
            if self.state != "open":
                raise StreamClosed(self.state)
            if len(self.buf) >= self.capacity:
                raise Backpressure(f"stream for call {self.owner_call} full")
            self.buf.append(item)

    def read(self):
        with self.lock:
            if self.buf:
                return self.buf.popleft()
            if self.state == "open":
                return None
            raise StreamClosed(self.state)

    def close(self, state: str = "done") -> None:
        with self.lock:
            if self.state == "open":
                self.state = state
                if state != "done":
                    self.buf.clear()   # release buffers deterministically


class StreamRegistry:
    """Streams are owned by exactly one call; its terminal transition closes them."""

    def __init__(self):
        self.by_call: dict[int, list[Stream]] = {}

    def open(self, fns, call_id: int, capacity: int = 16) -> Stream:
        s = Stream(call_id, capacity)
        first = call_id not in self.by_call
        self.by_call.setdefault(call_id, []).append(s)
        if first:
            tomb = fns.add_terminal_listener(call_id, self._on_terminal)
            if tomb is not None:
                self._on_terminal(call_id, tomb.outcome, None, tomb.reason)
        return s

    def _on_terminal(self, call_id, outcome, _v, _r):
        # Completion may precede stream exhaustion: completed calls leave streams
        # readable until drained (post-return lifetime owned by the reader);
        # cancelled/trapped calls release buffers immediately.
        for s in self.by_call.get(call_id, []):
            if outcome.value != "completed":
                s.close(outcome.value)
        if outcome.value != "completed":
            self.by_call.pop(call_id, None)

    def open_buffers(self) -> int:
        return sum(len(s.buf) for ss in self.by_call.values() for s in ss)
