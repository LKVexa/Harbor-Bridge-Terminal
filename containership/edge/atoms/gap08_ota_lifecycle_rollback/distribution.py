"""Bandwidth-aware content distribution (component 19).

* ``ChunkManifest`` splits an artifact into fixed-size chunks with per-chunk
  SHA-256 plus the whole-artifact digest bound by GAP-07 verification;
* ``fetch`` is **resumable**: chunks already on disk and valid are skipped,
  each fetched chunk is verified before it is written, and the final file is
  re-hashed against the verified digest before it becomes visible;
* sources are tried in preference order (site cache -> peer -> origin/CDN);
* a per-site ``TokenBucket`` enforces the constrained-edge bandwidth budget.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .admission import TokenBucket
from .errors import ArtifactMismatch, DependencyUnavailable, Overloaded

MANIFEST_SCHEMA = "PK_CHUNK_MANIFEST/1"
Source = Callable[[int], bytes]  # chunk index -> bytes (raises on failure)


@dataclass(frozen=True)
class ChunkManifest:
    digest: str
    size: int
    chunk_size: int
    chunks: tuple[str, ...]

    @classmethod
    def build(cls, data: bytes, chunk_size: int = 1 << 20) -> "ChunkManifest":
        chunks = tuple(hashlib.sha256(data[i:i + chunk_size]).hexdigest() for i in range(0, len(data), chunk_size))
        return cls("sha256:" + hashlib.sha256(data).hexdigest(), len(data), chunk_size, chunks)

    def to_dict(self) -> dict:
        return {"schema": MANIFEST_SCHEMA, "digest": self.digest, "size": self.size, "chunk_size": self.chunk_size,
                "chunks": list(self.chunks)}


def fetch(manifest: ChunkManifest, dest: Path, sources: Sequence[Source], *,
          budget: TokenBucket | None = None) -> dict:
    """Resumably fetch into ``dest``; returns stats.  Raises on budget or exhausted sources."""
    dest = Path(dest)
    part_dir = dest.with_name(dest.name + ".parts")
    part_dir.mkdir(parents=True, exist_ok=True)
    stats = {"reused": 0, "fetched": 0, "bytes": 0, "source_failures": 0}
    for i, expected in enumerate(manifest.chunks):
        p = part_dir / f"{i:06d}"
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == expected:
            stats["reused"] += 1
            continue
        last_exc: Exception | None = None
        for src in sources:
            try:
                data = src(i)
            except Exception as exc:  # source failure -> next source
                stats["source_failures"] += 1
                last_exc = exc
                continue
            if hashlib.sha256(data).hexdigest() != expected:
                stats["source_failures"] += 1
                last_exc = ArtifactMismatch(f"chunk {i} digest mismatch from source")
                continue
            if budget is not None:
                wait = budget.take(len(data))
                if wait:
                    raise Overloaded(f"site bandwidth budget exhausted at chunk {i}", retry_after_s=round(wait, 3))
            tmp = p.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, p)
            stats["fetched"] += 1
            stats["bytes"] += len(data)
            break
        else:
            raise DependencyUnavailable(f"no source could supply chunk {i}", cause=last_exc)
    h = hashlib.sha256()
    tmp = dest.with_suffix(".assembling")
    with open(tmp, "wb") as out:
        for i in range(len(manifest.chunks)):
            b = (part_dir / f"{i:06d}").read_bytes()
            h.update(b)
            out.write(b)
        out.flush()
        os.fsync(out.fileno())
    if "sha256:" + h.hexdigest() != manifest.digest:
        tmp.unlink()
        raise ArtifactMismatch("assembled artifact does not match verified digest")
    os.replace(tmp, dest)
    for q in part_dir.iterdir():
        q.unlink()
    part_dir.rmdir()
    return stats
