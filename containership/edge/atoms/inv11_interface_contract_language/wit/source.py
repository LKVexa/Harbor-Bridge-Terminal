"""Bounded source loader (INV11-MC-01 items 003/006/007)."""
from __future__ import annotations

import bisect
import hashlib
import os
from dataclasses import dataclass, field

from .diagnostics import DiagnosticBag, Span
from .limits import DEFAULT_LIMITS, Limits


@dataclass(frozen=True)
class SourceFile:
    name: str  # canonical identity: posix relative path or "<memory:label>"
    text: str  # UTF-8 decoded, line endings normalized to \n, BOM removed
    digest: str  # sha256 of the normalized text bytes
    line_starts: tuple[int, ...] = field(default=(), repr=False)

    @staticmethod
    def build(name: str, text: str) -> SourceFile:
        starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                starts.append(i + 1)
        return SourceFile(name, text, hashlib.sha256(text.encode("utf-8")).hexdigest(), tuple(starts))

    def position(self, offset: int) -> tuple[int, int]:
        line = bisect.bisect_right(self.line_starts, offset) - 1
        return line + 1, offset - self.line_starts[line] + 1

    def span(self, start: int, end: int) -> Span:
        line, col = self.position(start)
        eline, ecol = self.position(max(start, end))
        return Span(self.name, start, end, line, col, eline, ecol)


def decode(name: str, data: bytes, diags: DiagnosticBag, limits: Limits = DEFAULT_LIMITS) -> SourceFile | None:
    limits.check("source_bytes", len(data))
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
        diags.add("E-SRC-BOM", "byte-order mark removed", Span(name, 0, 0, 1, 1))
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        prefix = data[: exc.start].decode("utf-8")
        line = prefix.count("\n") + 1
        col = len(prefix) - (prefix.rfind("\n") + 1) + 1
        diags.add("E-SRC-UTF8", f"invalid UTF-8 at byte {exc.start}: {exc.reason}",
                  Span(name, exc.start, exc.end, line, col))
        return None
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return SourceFile.build(name, text)


def from_memory(label: str, data: bytes | str, diags: DiagnosticBag, limits: Limits = DEFAULT_LIMITS) -> SourceFile | None:
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return decode(f"<memory:{label}>", raw, diags, limits)


def load_path(path: str, diags: DiagnosticBag, limits: Limits = DEFAULT_LIMITS,
              root: str | None = None) -> list[SourceFile]:
    """Load one .wit file or every .wit file of a directory (deterministic order).

    Directory traversal does not follow symlinks and is sorted by canonical
    posix relative path, so load order is independent of filesystem order.
    A `deps/` sub-directory is loaded as dependency packages by the resolver.
    """
    path = os.path.abspath(path)
    base = os.path.abspath(root) if root else (path if os.path.isdir(path) else os.path.dirname(path))
    files: list[str] = []
    if os.path.isdir(path):
        for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
            dirnames[:] = sorted(d for d in dirnames if d != "deps")
            files.extend(os.path.join(dirpath, f) for f in filenames if f.endswith(".wit"))
    else:
        files.append(path)
    limits.check("files", len(files))
    out: list[SourceFile] = []
    total = 0
    for f in sorted(files, key=lambda p: os.path.relpath(p, base).replace(os.sep, "/")):
        rel = os.path.relpath(f, base).replace(os.sep, "/")
        try:
            size = os.path.getsize(f)
            limits.check("source_bytes", size)
            with open(f, "rb") as fh:
                data = fh.read(limits.max_source_bytes + 1)
        except OSError as exc:
            diags.add("E-SRC-IO", f"{rel}: {exc.strerror}")
            continue
        total += len(data)
        limits.check("source_bytes", total)
        sf = decode(rel, data, diags, limits)
        if sf is not None:
            out.append(sf)
    return out
