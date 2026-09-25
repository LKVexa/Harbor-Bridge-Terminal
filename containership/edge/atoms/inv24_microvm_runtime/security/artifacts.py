"""Artifact integrity and approved-artifact policy (MC-001-I01, MC-018).

An artifact (Firecracker/jailer binary, guest kernel, rootfs) is usable only
if it is listed in the approved manifest with an immutable version and a
SHA-256 digest, is referenced by absolute path (no PATH discovery, no URLs,
no ``latest``), is a regular non-symlink file, and its bytes hash to the pin.
A manifest entry whose digest is ``null`` is *unpinned* and fails closed.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import stat
from dataclasses import dataclass

from ..errors import Inv24Error

_HEX64 = re.compile(r"[0-9a-f]{64}")
_FORBIDDEN_VERSIONS = {"latest", "stable", "main", "master", "*", ""}
CHUNK = 1 << 20


@dataclass(frozen=True, slots=True)
class ApprovedArtifact:
    name: str
    version: str
    sha256: str | None
    kind: str
    source: str

    @property
    def pinned(self) -> bool:
        return bool(self.sha256 and _HEX64.fullmatch(self.sha256))


def sha256_file(path: str | os.PathLike, *, max_bytes: int = 8 << 30) -> str:
    h = hashlib.sha256()
    seen = 0
    with open(path, "rb") as fh:
        while chunk := fh.read(CHUNK):
            seen += len(chunk)
            if seen > max_bytes:
                raise Inv24Error("RESOURCE_EXHAUSTED", f"{path} exceeds {max_bytes} bytes")
            h.update(chunk)
    return h.hexdigest()


class ArtifactManifest:
    def __init__(self, entries: dict[str, ApprovedArtifact], manifest_version: str) -> None:
        self.entries, self.manifest_version = entries, manifest_version

    @classmethod
    def load(cls, path: str | os.PathLike) -> "ArtifactManifest":
        try:
            data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise Inv24Error("ARTIFACT_NOT_APPROVED", f"cannot load artifact manifest: {exc}") from None
        if data.get("schema") != "PK_MICROVM_ARTIFACTS/1":
            raise Inv24Error("ARTIFACT_NOT_APPROVED", "manifest schema mismatch")
        entries = {}
        for raw in data.get("artifacts", []):
            version = str(raw.get("version", ""))
            if version.lower() in _FORBIDDEN_VERSIONS or version.startswith("v*"):
                raise Inv24Error("ARTIFACT_NOT_APPROVED", f"{raw.get('name')}: floating version {version!r}")
            src = str(raw.get("source", ""))
            if "latest" in src.lower():
                raise Inv24Error("ARTIFACT_NOT_APPROVED", f"{raw.get('name')}: floating source URL")
            art = ApprovedArtifact(str(raw["name"]), version, raw.get("sha256"), str(raw.get("kind", "binary")), src)
            entries[art.name] = art
        return cls(entries, str(data.get("manifest_version", "0")))

    def verify(self, name: str, path: str | os.PathLike) -> ApprovedArtifact:
        """Return the approved entry iff ``path`` holds exactly the pinned bytes."""
        art = self.entries.get(name)
        if art is None:
            raise Inv24Error("ARTIFACT_NOT_APPROVED", f"{name} is not in the approved manifest")
        if not art.pinned:
            raise Inv24Error("ARTIFACT_UNPINNED", f"{name} {art.version} has no approved SHA-256 pin")
        p = pathlib.Path(path)
        if not p.is_absolute():
            raise Inv24Error("ARTIFACT_NOT_APPROVED", f"{name}: path must be absolute (no PATH discovery)")
        try:
            st = os.lstat(p)
        except OSError:
            raise Inv24Error("ARTIFACT_NOT_APPROVED", f"{name}: {p} not found") from None
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            raise Inv24Error("ARTIFACT_NOT_APPROVED", f"{name}: {p} must be a regular file, not a symlink")
        if st.st_mode & stat.S_IWOTH:
            raise Inv24Error("ARTIFACT_NOT_APPROVED", f"{name}: {p} is world-writable")
        digest = sha256_file(p)
        if digest != art.sha256:
            raise Inv24Error("ARTIFACT_DIGEST_MISMATCH", f"{name}: digest {digest[:12]}.. != pin {art.sha256[:12]}..")
        return art
