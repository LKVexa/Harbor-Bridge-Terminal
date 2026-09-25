"""Component 04 - durable per-node state store (and component 38 backup/restore
primitives).

One JSON document per node, written atomically (temp file + fsync + rename +
directory fsync) with a SHA-256 checksum and a monotonically increasing
generation. Every record carries the fencing token of the writer; a write with
an older token than the stored one is refused (split-brain protection).

On restore, a missing/corrupt record never yields a less restrictive state: the
caller gets ``None`` / ``STORE_CORRUPT`` and must start the node constrained.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
import threading
from dataclasses import asdict, dataclass

from .errors import ErrorCode, Gap10Error
from .keys import canonical

_SAFE = re.compile(r"[^A-Za-z0-9._-]")


@dataclass
class NodeRecord:
    node: str
    band: str
    last_trusted_observed_at: float | None
    last_trusted_seq: int | None
    policy_revision: str
    hysteresis_band: str
    fencing_token: int
    generation: int = 0
    controls: tuple = ()
    updated_at: float = 0.0


class FileStateStore:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)
        self._lock = threading.Lock()
        self.available = True

    def _path(self, node: str) -> str:
        digest = hashlib.sha256(node.encode()).hexdigest()[:12]
        return os.path.join(self.root, f"{_SAFE.sub('_', node)[:64]}.{digest}.json")

    def _check(self):
        if not self.available:
            raise Gap10Error(ErrorCode.STORE_UNAVAILABLE, "state store unavailable")

    def load(self, node: str) -> NodeRecord | None:
        self._check()
        path = self._path(node)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
            body = doc["record"]
            if hashlib.sha256(canonical(body)).hexdigest() != doc["sha256"]:
                raise ValueError("checksum")
            body["controls"] = tuple(body.get("controls", ()))
            rec = NodeRecord(**body)
            if rec.node != node:
                raise ValueError("node mismatch")
            return rec
        except Exception as exc:  # noqa: BLE001 - any decode failure is corruption
            raise Gap10Error(ErrorCode.STORE_CORRUPT, f"{node}: {exc}") from exc

    def save(self, rec: NodeRecord) -> NodeRecord:
        self._check()
        with self._lock:
            try:
                current = self.load(rec.node)
            except Gap10Error as e:
                if e.code != ErrorCode.STORE_CORRUPT:
                    raise
                current = None  # overwrite corrupt record only with a fenced write
            if current is not None:
                if rec.fencing_token < current.fencing_token:
                    raise Gap10Error(ErrorCode.FENCING_TOKEN_STALE,
                                     f"{rec.node}: token {rec.fencing_token} < stored {current.fencing_token}")
                rec.generation = current.generation + 1
            body = asdict(rec)
            body["controls"] = list(rec.controls)
            doc = {"schema": "PK_THERMAL_NODE_STATE/1", "record": body, "sha256": hashlib.sha256(canonical(body)).hexdigest()}
            path = self._path(rec.node)
            tmp = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
            try:
                dfd = os.open(self.root, os.O_RDONLY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
            except OSError:
                pass  # directory fsync unsupported on some platforms (Windows)
            return rec

    def delete(self, node: str) -> None:
        self._check()
        try:
            os.remove(self._path(node))
        except FileNotFoundError:
            pass

    def nodes(self) -> list[str]:
        out = []
        for name in sorted(os.listdir(self.root)):
            if name.endswith(".json"):
                try:
                    with open(os.path.join(self.root, name), encoding="utf-8") as fh:
                        out.append(json.load(fh)["record"]["node"])
                except Exception:  # noqa: BLE001
                    continue
        return out

    # -------------------------------------------------- 38 backup / restore
    def backup(self, archive_path: str) -> str:
        with tarfile.open(archive_path, "w:gz") as tar:
            for name in sorted(os.listdir(self.root)):
                if name.endswith(".json"):
                    tar.add(os.path.join(self.root, name), arcname=name)
        with open(archive_path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    @staticmethod
    def restore(archive_path: str, root: str, expected_sha256: str) -> "FileStateStore":
        with open(archive_path, "rb") as fh:
            if hashlib.sha256(fh.read()).hexdigest() != expected_sha256:
                raise Gap10Error(ErrorCode.STORE_CORRUPT, "backup digest mismatch")
        if os.path.exists(root):
            shutil.rmtree(root)
        os.makedirs(root)
        with tarfile.open(archive_path, "r:gz") as tar:
            for m in tar.getmembers():
                if not m.isfile() or "/" in m.name or "\\" in m.name or m.name.startswith(".."):
                    raise Gap10Error(ErrorCode.STORE_CORRUPT, f"unsafe member {m.name}")
                src = tar.extractfile(m)
                with open(os.path.join(root, m.name), "wb") as out:
                    out.write(src.read())
        return FileStateStore(root)
