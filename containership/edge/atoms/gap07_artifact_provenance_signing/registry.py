"""Artifact registry / OCI integration and streaming verification (v6).

* Immutable references only: ``parse_reference`` refuses tags for admission;
  ``resolve_tag`` returns a digest binding (tag->digest) that is recorded in
  evidence, and admission then operates solely on the digest.
* OCI image manifest / image index (OCI 1.1 media types, plus Docker v2
  schema2 read compatibility) are parsed strictly; descriptors are validated
  (digest algorithm + encoding, size bounds, no duplicates).  Every referenced
  blob is fetched digest-addressed and stream-hashed with size short-circuit.
* Referrers discovery uses the OCI 1.1 ``subject`` relation (not tag naming):
  attached signatures/attestations must name the exact manifest digest.
* Multi-platform indexes: the selected child is validated and the parent
  index digest is preserved in evidence.
* Wasm modules/components: digest boundary = the exact ``.wasm`` bytes;
  header (magic + version/layer) validated so a component cannot be admitted
  as a core module or vice versa.  microVM images / provider bundles are
  opaque digest-addressed blobs.
* ``VerifiedContentStore.open_verified`` re-hashes on handoff, so the bytes
  given to a runtime are provably those that were verified (TOCTOU guard).
"""
from __future__ import annotations

import hashlib
import hmac
import io
import os
import re
import threading
from dataclasses import dataclass
from typing import Any, BinaryIO, Iterable, Mapping

from .canonical import exact_fields, strict_loads
from .errors import fail

OCI_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
OCI_INDEX = "application/vnd.oci.image.index.v1+json"
DOCKER_MANIFEST = "application/vnd.docker.distribution.manifest.v2+json"
DOCKER_LIST = "application/vnd.docker.distribution.manifest.list.v2+json"
MANIFEST_TYPES = {OCI_MANIFEST, DOCKER_MANIFEST}
INDEX_TYPES = {OCI_INDEX, DOCKER_LIST}
MAX_MANIFEST = 4 * 1024 * 1024
MAX_DESCRIPTORS = 1000
MAX_BLOB = 16 * 1024 * 1024 * 1024
_DIGEST = re.compile(r"^(sha256:[0-9a-f]{64}|sha512:[0-9a-f]{128})$")
_REF = re.compile(r"^(?P<repo>[a-z0-9]+(?:[._/-][a-z0-9]+)*(?::[0-9]+)?(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*)(?::(?P<tag>[A-Za-z0-9_][A-Za-z0-9._-]{0,127}))?(?:@(?P<digest>[a-z0-9]+:[0-9a-f]+))?$")
WASM_MAGIC = b"\x00asm"
CHUNK = 1 << 20


def parse_reference(ref: str, *, require_digest: bool = True) -> tuple[str, str | None, str | None]:
    if not isinstance(ref, str) or len(ref) > 512:
        raise fail("REGISTRY_MALFORMED", "reference invalid")
    m = _REF.fullmatch(ref)
    if m is None:
        raise fail("REGISTRY_MALFORMED", "reference invalid")
    dg = m.group("digest")
    if dg is not None and _DIGEST.fullmatch(dg) is None:
        raise fail("REGISTRY_MALFORMED", "reference digest invalid")
    if require_digest and dg is None:
        raise fail("MUTABLE_REFERENCE", "admission requires an immutable @digest reference", reference=ref[:256])
    return m.group("repo"), m.group("tag"), dg


def stream_digest(reader: BinaryIO | Iterable[bytes], *, algorithm: str = "sha256", expected_size: int | None = None,
                  max_size: int = MAX_BLOB) -> tuple[str, int]:
    """Hash a stream without materialising it; abort early on size violations."""
    h = hashlib.new(algorithm)
    n = 0
    chunks = iter(lambda: reader.read(CHUNK), b"") if hasattr(reader, "read") else iter(reader)
    for chunk in chunks:
        n += len(chunk)
        if n > max_size or (expected_size is not None and n > expected_size):
            raise fail("INPUT_TOO_LARGE", "stream exceeds declared/maximum size", read=n, expected=expected_size)
        h.update(chunk)
    if expected_size is not None and n != expected_size:
        raise fail("REGISTRY_DIGEST_MISMATCH", "stream shorter than declared size (partial read?)", read=n, expected=expected_size)
    return f"{algorithm}:{h.hexdigest()}", n


def verify_stream(reader: BinaryIO | Iterable[bytes], expected_digest: str, *, expected_size: int | None = None, max_size: int = MAX_BLOB) -> int:
    if _DIGEST.fullmatch(expected_digest or "") is None:
        raise fail("REGISTRY_MALFORMED", "expected digest invalid")
    alg = expected_digest.split(":", 1)[0]
    got, n = stream_digest(reader, algorithm=alg, expected_size=expected_size, max_size=max_size)
    if not hmac.compare_digest(got, expected_digest):
        raise fail("REGISTRY_DIGEST_MISMATCH", "content digest mismatch", expected=expected_digest, actual=got)
    return n


def verify_file(path: str, expected_digest: str, *, max_size: int = MAX_BLOB) -> int:
    with open(path, "rb") as fh:
        return verify_stream(fh, expected_digest, expected_size=os.fstat(fh.fileno()).st_size, max_size=max_size)


def _descriptor(d: Any, allowed_types: set[str] | None = None) -> dict[str, Any]:
    d = exact_fields(d, {"mediaType", "digest", "size"}, {"annotations", "platform", "urls", "artifactType", "data"}, what="descriptor")
    if not isinstance(d["mediaType"], str) or len(d["mediaType"]) > 255:
        raise fail("REGISTRY_MALFORMED", "descriptor mediaType invalid")
    if allowed_types is not None and d["mediaType"] not in allowed_types:
        raise fail("REGISTRY_MEDIA_TYPE", "descriptor media type not supported", media_type=d["mediaType"])
    if not isinstance(d["digest"], str) or _DIGEST.fullmatch(d["digest"]) is None:
        raise fail("REGISTRY_MALFORMED", "descriptor digest invalid")
    if isinstance(d["size"], bool) or not isinstance(d["size"], int) or not 0 <= d["size"] <= MAX_BLOB:
        raise fail("REGISTRY_MALFORMED", "descriptor size invalid")
    if d.get("urls"):
        raise fail("REGISTRY_MALFORMED", "foreign/non-distributable layers (urls) are refused")
    return dict(d)


class ContentStore:
    """Digest-addressed blob store interface (in-memory reference implementation)."""

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}
        self._tags: dict[str, str] = {}
        self._lock = threading.Lock()
        self.fail_reads = False

    def put(self, data: bytes) -> str:
        dg = "sha256:" + hashlib.sha256(data).hexdigest()
        with self._lock:
            self._blobs[dg] = bytes(data)
        return dg

    def tag(self, repo_tag: str, digest: str) -> None:
        self._tags[repo_tag] = digest

    def resolve(self, repo_tag: str) -> str:
        try:
            return self._tags[repo_tag]
        except KeyError as exc:
            raise fail("REGISTRY_UNAVAILABLE", "tag not found") from exc

    def open(self, digest: str) -> BinaryIO:
        if self.fail_reads:
            raise fail("REGISTRY_UNAVAILABLE", "content store read failed")
        try:
            return io.BytesIO(self._blobs[digest])
        except KeyError as exc:
            raise fail("REGISTRY_UNAVAILABLE", "blob not found", digest=digest) from exc

    def all_manifests(self) -> Iterable[tuple[str, bytes]]:
        return list(self._blobs.items())


def resolve_tag(store: ContentStore, repo_tag: str) -> dict[str, Any]:
    """Tag -> immutable digest binding recorded in evidence; never authorises by itself."""
    _, tag, _ = parse_reference(repo_tag, require_digest=False)
    if tag is None:
        raise fail("REGISTRY_MALFORMED", "no tag to resolve")
    return {"reference": repo_tag, "digest": store.resolve(repo_tag)}


def _read_verified(store: ContentStore, desc: Mapping[str, Any], max_size: int) -> bytes:
    if desc["size"] > max_size:
        raise fail("INPUT_TOO_LARGE", "blob larger than policy allows", digest=desc["digest"], size=desc["size"])
    with store.open(desc["digest"]) as fh:
        data = fh.read(desc["size"] + 1)
    if len(data) != desc["size"]:
        raise fail("REGISTRY_DIGEST_MISMATCH", "blob size differs from descriptor (partial read or substitution)", digest=desc["digest"])
    verify_stream([data], desc["digest"], expected_size=desc["size"])
    return data


def parse_manifest(raw: bytes, media_type: str) -> dict[str, Any]:
    if len(raw) > MAX_MANIFEST:
        raise fail("INPUT_TOO_LARGE", "manifest too large")
    doc = strict_loads(raw, max_bytes=MAX_MANIFEST)
    if not isinstance(doc, Mapping) or doc.get("schemaVersion") != 2:
        raise fail("REGISTRY_MALFORMED", "manifest schemaVersion must be 2")
    if doc.get("mediaType", media_type) != media_type:
        raise fail("REGISTRY_MALFORMED", "manifest mediaType disagrees with descriptor")
    if media_type in MANIFEST_TYPES:
        m = exact_fields(doc, {"schemaVersion", "config", "layers"}, {"mediaType", "annotations", "subject", "artifactType"}, what="manifest")
        _descriptor(m["config"])
        if not isinstance(m["layers"], list) or len(m["layers"]) > MAX_DESCRIPTORS:
            raise fail("REGISTRY_MALFORMED", "layers invalid")
        layers = [_descriptor(x) for x in m["layers"]]
        if len({x["digest"] for x in layers}) != len(layers):
            raise fail("REGISTRY_MALFORMED", "duplicate layer descriptors")
        if "subject" in m:
            _descriptor(m["subject"], MANIFEST_TYPES | INDEX_TYPES)
        return dict(m)
    if media_type in INDEX_TYPES:
        m = exact_fields(doc, {"schemaVersion", "manifests"}, {"mediaType", "annotations", "subject", "artifactType"}, what="index")
        if not isinstance(m["manifests"], list) or not 0 < len(m["manifests"]) <= MAX_DESCRIPTORS:
            raise fail("REGISTRY_MALFORMED", "index manifests invalid")
        ms = [_descriptor(x, MANIFEST_TYPES | INDEX_TYPES) for x in m["manifests"]]
        plats = [canonical_platform(x.get("platform")) for x in ms if x.get("platform")]
        if len(set(plats)) != len(plats):
            raise fail("REGISTRY_MALFORMED", "ambiguous duplicate platform entries in index")
        return dict(m)
    raise fail("REGISTRY_MEDIA_TYPE", "unsupported manifest media type", media_type=media_type)


def canonical_platform(p: Mapping[str, Any] | None) -> str:
    if not p:
        return ""
    return f"{p.get('os', '')}/{p.get('architecture', '')}/{p.get('variant', '')}"


@dataclass
class OciVerification:
    digest: str
    media_type: str
    selected_digest: str
    parent_index: str | None
    platform: str
    blobs_verified: int

    def evidence(self) -> dict[str, Any]:
        return {"digest": self.digest, "media_type": self.media_type, "selected_digest": self.selected_digest,
                "parent_index": self.parent_index, "platform": self.platform, "blobs_verified": self.blobs_verified}


def verify_oci(store: ContentStore, digest: str, media_type: str, size: int, *, platform: str | None = None,
               max_blob: int = 2 * 1024 * 1024 * 1024, depth: int = 0) -> OciVerification:
    if depth > 2:
        raise fail("REGISTRY_MALFORMED", "nested index depth exceeded")
    desc = _descriptor({"mediaType": media_type, "digest": digest, "size": size}, MANIFEST_TYPES | INDEX_TYPES)
    raw = _read_verified(store, desc, MAX_MANIFEST)
    m = parse_manifest(raw, media_type)
    if media_type in INDEX_TYPES:
        cands = [d for d in m["manifests"] if platform is None or canonical_platform(d.get("platform")) == platform]
        if len(cands) != 1:
            raise fail("REGISTRY_MALFORMED", "platform selection is not unique", platform=platform, candidates=len(cands))
        child = _descriptor(cands[0])
        sub = verify_oci(store, child["digest"], child["mediaType"], child["size"], platform=platform, max_blob=max_blob, depth=depth + 1)
        return OciVerification(digest, media_type, sub.selected_digest, digest, canonical_platform(child.get("platform")), sub.blobs_verified + 1)
    n = 1
    for d in [m["config"], *m["layers"]]:
        dd = _descriptor(d)
        with store.open(dd["digest"]) as fh:
            verify_stream(fh, dd["digest"], expected_size=dd["size"], max_size=max_blob)
        n += 1
    return OciVerification(digest, media_type, digest, None, platform or "", n)


def discover_referrers(store: ContentStore, subject_digest: str, artifact_type: str | None = None) -> list[dict[str, Any]]:
    """OCI 1.1 referrers by ``subject`` relation (fallback scan of a local store)."""
    out = []
    for dg, raw in store.all_manifests():
        try:
            doc = strict_loads(raw, max_bytes=MAX_MANIFEST)
        except Exception:  # noqa: BLE001 - non-JSON blobs are not manifests
            continue
        if isinstance(doc, Mapping) and isinstance(doc.get("subject"), Mapping) and doc["subject"].get("digest") == subject_digest:
            if artifact_type is None or doc.get("artifactType") == artifact_type:
                out.append({"digest": dg, "artifactType": doc.get("artifactType"), "manifest": doc})
    return sorted(out, key=lambda r: r["digest"])


def check_wasm(data_head: bytes, kind: str) -> str:
    if len(data_head) < 8 or data_head[:4] != WASM_MAGIC:
        raise fail("REGISTRY_MEDIA_TYPE", "not a WebAssembly binary")
    version, layer = int.from_bytes(data_head[4:6], "little"), int.from_bytes(data_head[6:8], "little")
    if kind == "wasm-module" and (version, layer) != (1, 0):
        raise fail("REGISTRY_MEDIA_TYPE", "expected a core Wasm module (version 1, layer 0)")
    if kind == "wasm-component" and layer != 1:
        raise fail("REGISTRY_MEDIA_TYPE", "expected a Wasm component (layer 1)")
    return f"{kind}:v{version}:l{layer}"


class VerifiedContentStore:
    """Digest-addressed handoff: the runtime receives bytes re-hashed at handoff time."""

    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _path(self, digest: str) -> str:
        if _DIGEST.fullmatch(digest) is None:
            raise fail("REGISTRY_MALFORMED", "digest invalid")
        return os.path.join(self.root, digest.replace(":", "_"))

    def ingest(self, reader: BinaryIO | Iterable[bytes], digest: str, *, max_size: int = MAX_BLOB) -> str:
        path = self._path(digest)
        tmp = path + ".partial"
        h = hashlib.new(digest.split(":")[0])
        n = 0
        chunks = iter(lambda: reader.read(CHUNK), b"") if hasattr(reader, "read") else iter(reader)
        with open(tmp, "wb") as fh:
            for c in chunks:
                n += len(c)
                if n > max_size:
                    fh.close()
                    os.remove(tmp)
                    raise fail("INPUT_TOO_LARGE", "blob exceeds maximum size")
                h.update(c)
                fh.write(c)
            fh.flush()
            os.fsync(fh.fileno())
        if not hmac.compare_digest(f"{digest.split(':')[0]}:{h.hexdigest()}", digest):
            os.remove(tmp)
            raise fail("REGISTRY_DIGEST_MISMATCH", "ingested content digest mismatch")
        os.replace(tmp, path)
        return path

    def open_verified(self, digest: str) -> bytes:
        """Read and re-verify at the moment of handoff (TOCTOU guard)."""
        path = self._path(digest)
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError as exc:
            raise fail("REGISTRY_UNAVAILABLE", "verified content missing or unreadable at handoff", digest=digest) from exc
        got = f"{digest.split(':')[0]}:{hashlib.new(digest.split(':')[0], data).hexdigest()}"
        if not hmac.compare_digest(got, digest):
            raise fail("TOCTOU", "content changed between verification and handoff", digest=digest)
        return data
