"""MC01 / MC14 — OCI Image Specification model and multi-platform selection.

Stdlib-only parsing and validation of OCI image-spec v1.1 documents: descriptors,
image manifests, image indexes, image configs, platforms and annotations, plus the
Docker schema-2 media types that registries still serve.  Parsing is strict and fails
closed with :class:`OCIError` subclasses carrying a stable ``code``.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from .registry import IntegrityError, ValidationError

# --- media types -----------------------------------------------------------------
MT_DESCRIPTOR = "application/vnd.oci.descriptor.v1+json"
MT_MANIFEST = "application/vnd.oci.image.manifest.v1+json"
MT_INDEX = "application/vnd.oci.image.index.v1+json"
MT_CONFIG = "application/vnd.oci.image.config.v1+json"
MT_LAYER_TAR = "application/vnd.oci.image.layer.v1.tar"
MT_LAYER_GZIP = "application/vnd.oci.image.layer.v1.tar+gzip"
MT_LAYER_ZSTD = "application/vnd.oci.image.layer.v1.tar+zstd"
MT_LAYER_ND_TAR = "application/vnd.oci.image.layer.nondistributable.v1.tar"
MT_LAYER_ND_GZIP = "application/vnd.oci.image.layer.nondistributable.v1.tar+gzip"
MT_EMPTY = "application/vnd.oci.empty.v1+json"
MT_DOCKER_MANIFEST = "application/vnd.docker.distribution.manifest.v2+json"
MT_DOCKER_LIST = "application/vnd.docker.distribution.manifest.list.v2+json"
MT_DOCKER_CONFIG = "application/vnd.docker.container.image.v1+json"
MT_DOCKER_LAYER = "application/vnd.docker.image.rootfs.diff.tar.gzip"

MANIFEST_TYPES = frozenset({MT_MANIFEST, MT_DOCKER_MANIFEST})
INDEX_TYPES = frozenset({MT_INDEX, MT_DOCKER_LIST})
LAYER_TYPES = frozenset(
    {MT_LAYER_TAR, MT_LAYER_GZIP, MT_LAYER_ZSTD, MT_LAYER_ND_TAR, MT_LAYER_ND_GZIP, MT_DOCKER_LAYER}
)
EMPTY_JSON_DIGEST = "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"

_MEDIA_TYPE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}\Z")
# OCI digest grammar: algorithm ":" encoded; we accept registered sha256/sha512 only.
_DIGEST_RES = {
    "sha256": re.compile(r"sha256:[a-f0-9]{64}\Z"),
    "sha512": re.compile(r"sha512:[a-f0-9]{128}\Z"),
}
_ANNOTATION_KEY_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,254}\Z")
MAX_DOC_BYTES = 4 * 1024 * 1024
MAX_DESCRIPTORS = 1024
MAX_ANNOTATIONS = 256
MAX_JSON_DEPTH = 32


class OCIError(IntegrityError):
    code = "OCI_INVALID"


class UnsupportedMediaType(OCIError):
    code = "OCI_UNSUPPORTED_MEDIA_TYPE"


class NoMatchingPlatform(OCIError, LookupError):
    code = "OCI_NO_MATCHING_PLATFORM"


def validate_oci_digest(value: object, where: str = "digest") -> str:
    if not isinstance(value, str) or ":" not in value:
        raise OCIError(f"{where}: invalid digest {value!r}")
    algo = value.split(":", 1)[0]
    rx = _DIGEST_RES.get(algo)
    if rx is None:
        raise OCIError(f"{where}: unsupported digest algorithm {algo!r}")
    if not rx.fullmatch(value):
        raise OCIError(f"{where}: malformed digest {value!r}")
    return value


def _depth(obj: Any, limit: int = MAX_JSON_DEPTH, cur: int = 0) -> None:
    if cur > limit:
        raise OCIError("document nesting exceeds depth limit")
    if isinstance(obj, dict):
        for v in obj.values():
            _depth(v, limit, cur + 1)
    elif isinstance(obj, list):
        for v in obj:
            _depth(v, limit, cur + 1)


def load_json_document(raw: bytes, *, max_bytes: int = MAX_DOC_BYTES) -> dict:
    """Decode an untrusted OCI JSON document with size, encoding, duplicate-key and depth checks."""
    if not isinstance(raw, (bytes, bytearray, memoryview)):
        raise ValidationError("document must be bytes")
    raw = bytes(raw)
    if len(raw) > max_bytes:
        raise OCIError(f"document exceeds {max_bytes} bytes")

    def _no_dupes(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise OCIError(f"duplicate JSON key {k!r}")
            out[k] = v
        return out

    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupes)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise OCIError("document is not valid UTF-8 JSON") from exc
    if not isinstance(doc, dict):
        raise OCIError("document root must be an object")
    _depth(doc)
    return doc


def _annotations(value: object, where: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict) or len(value) > MAX_ANNOTATIONS:
        raise OCIError(f"{where}.annotations must be an object of <= {MAX_ANNOTATIONS} entries")
    for k, v in value.items():
        if not _ANNOTATION_KEY_RE.fullmatch(k) or not isinstance(v, str) or len(v) > 4096:
            raise OCIError(f"{where}.annotations[{k!r}] invalid")
    return dict(value)


@dataclass(frozen=True)
class Platform:
    os: str
    architecture: str
    variant: str | None = None
    os_version: str | None = None
    os_features: tuple[str, ...] = ()

    @classmethod
    def parse(cls, value: object, where: str = "platform") -> "Platform":
        if not isinstance(value, dict):
            raise OCIError(f"{where} must be an object")
        os_, arch = value.get("os"), value.get("architecture")
        if not isinstance(os_, str) or not os_ or not isinstance(arch, str) or not arch:
            raise OCIError(f"{where} requires os and architecture")
        variant = value.get("variant")
        if variant is not None and not isinstance(variant, str):
            raise OCIError(f"{where}.variant must be a string")
        feats = value.get("os.features", [])
        if not isinstance(feats, list) or not all(isinstance(f, str) for f in feats):
            raise OCIError(f"{where}.os.features must be a string array")
        osv = value.get("os.version")
        return cls(os_, normalize_arch(arch), variant, osv if isinstance(osv, str) else None, tuple(feats))

    @classmethod
    def from_string(cls, text: str) -> "Platform":
        parts = text.split("/")
        if len(parts) not in (2, 3) or not all(parts):
            raise ValidationError(f"platform must be os/arch[/variant]: {text!r}")
        return cls(parts[0], normalize_arch(parts[1]), parts[2] if len(parts) == 3 else None)

    def __str__(self) -> str:
        return "/".join(p for p in (self.os, self.architecture, self.variant) if p)


_ARCH_ALIASES = {"x86_64": "amd64", "x86-64": "amd64", "aarch64": "arm64", "armhf": "arm", "i386": "386"}


def normalize_arch(arch: str) -> str:
    return _ARCH_ALIASES.get(arch, arch)


@dataclass(frozen=True)
class Descriptor:
    media_type: str
    digest: str
    size: int
    urls: tuple[str, ...] = ()
    annotations: Mapping[str, str] = field(default_factory=dict)
    platform: Platform | None = None
    artifact_type: str | None = None
    data: bytes | None = None

    @classmethod
    def parse(cls, value: object, where: str = "descriptor") -> "Descriptor":
        import base64

        if not isinstance(value, dict):
            raise OCIError(f"{where} must be an object")
        mt = value.get("mediaType")
        if not isinstance(mt, str) or not _MEDIA_TYPE_RE.fullmatch(mt):
            raise OCIError(f"{where}.mediaType invalid: {mt!r}")
        dg = validate_oci_digest(value.get("digest"), f"{where}.digest")
        size = value.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0 or size > 2**53:
            raise OCIError(f"{where}.size invalid")
        urls = value.get("urls", [])
        if not isinstance(urls, list) or not all(isinstance(u, str) and u.startswith(("https://", "http://")) for u in urls):
            raise OCIError(f"{where}.urls invalid")
        plat = Platform.parse(value["platform"], f"{where}.platform") if "platform" in value else None
        data = None
        if "data" in value:
            try:
                data = base64.b64decode(value["data"], validate=True)
            except Exception as exc:  # binascii.Error / TypeError
                raise OCIError(f"{where}.data is not base64") from exc
            from .registry import digest as _sha

            if len(data) != size or (dg.startswith("sha256:") and _sha(data) != dg):
                raise OCIError(f"{where}.data does not match digest/size")
        at = value.get("artifactType")
        if at is not None and (not isinstance(at, str) or not _MEDIA_TYPE_RE.fullmatch(at)):
            raise OCIError(f"{where}.artifactType invalid")
        return cls(mt, dg, size, tuple(urls), _annotations(value.get("annotations"), where), plat, at, data)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"mediaType": self.media_type, "digest": self.digest, "size": self.size}
        if self.urls:
            d["urls"] = list(self.urls)
        if self.annotations:
            d["annotations"] = dict(self.annotations)
        if self.artifact_type:
            d["artifactType"] = self.artifact_type
        if self.platform:
            p = {"os": self.platform.os, "architecture": self.platform.architecture}
            if self.platform.variant:
                p["variant"] = self.platform.variant
            d["platform"] = p
        return d


def _descriptor_list(value: object, where: str) -> tuple[Descriptor, ...]:
    if not isinstance(value, list) or len(value) > MAX_DESCRIPTORS:
        raise OCIError(f"{where} must be an array of <= {MAX_DESCRIPTORS} descriptors")
    return tuple(Descriptor.parse(v, f"{where}[{i}]") for i, v in enumerate(value))


@dataclass(frozen=True)
class ImageManifest:
    media_type: str
    config: Descriptor
    layers: tuple[Descriptor, ...]
    subject: Descriptor | None = None
    artifact_type: str | None = None
    annotations: Mapping[str, str] = field(default_factory=dict)

    @property
    def is_artifact(self) -> bool:
        return self.artifact_type is not None or self.config.media_type not in (MT_CONFIG, MT_DOCKER_CONFIG)


@dataclass(frozen=True)
class ImageIndex:
    media_type: str
    manifests: tuple[Descriptor, ...]
    subject: Descriptor | None = None
    artifact_type: str | None = None
    annotations: Mapping[str, str] = field(default_factory=dict)


def parse_manifest(raw: bytes, *, expected_media_type: str | None = None) -> ImageManifest | ImageIndex:
    """Parse an OCI/Docker manifest or index.  ``expected_media_type`` is the transport
    ``Content-Type``; a mismatch with the document's own ``mediaType`` fails closed."""
    doc = load_json_document(raw)
    if doc.get("schemaVersion") != 2:
        raise OCIError("schemaVersion must be 2")
    mt = doc.get("mediaType")
    if mt is None:
        # OCI permits omission; infer strictly from shape.
        if "manifests" in doc and "layers" not in doc:
            mt = MT_INDEX
        elif "config" in doc and "manifests" not in doc:
            mt = MT_MANIFEST
        else:
            raise OCIError("cannot infer mediaType from ambiguous document")
    if expected_media_type and expected_media_type != mt:
        raise OCIError(f"content-type {expected_media_type!r} disagrees with mediaType {mt!r}")
    subject = Descriptor.parse(doc["subject"], "subject") if "subject" in doc else None
    at = doc.get("artifactType")
    ann = _annotations(doc.get("annotations"), "manifest")
    if mt in MANIFEST_TYPES:
        if "manifests" in doc:
            raise OCIError("image manifest must not contain manifests")
        config = Descriptor.parse(doc.get("config"), "config")
        layers = _descriptor_list(doc.get("layers"), "layers")
        if config.media_type == MT_EMPTY and at is None:
            raise OCIError("artifact manifest with empty config requires artifactType")
        return ImageManifest(mt, config, layers, subject, at, ann)
    if mt in INDEX_TYPES:
        if "layers" in doc or "config" in doc:
            raise OCIError("image index must not contain config/layers")
        return ImageIndex(mt, _descriptor_list(doc.get("manifests"), "manifests"), subject, at, ann)
    raise UnsupportedMediaType(f"unsupported manifest mediaType {mt!r}")


@dataclass(frozen=True)
class ImageConfig:
    platform: Platform
    diff_ids: tuple[str, ...]
    config: Mapping[str, Any]
    created: str | None

    @classmethod
    def parse(cls, raw: bytes) -> "ImageConfig":
        doc = load_json_document(raw)
        plat = Platform.parse({k: doc.get(k) for k in ("os", "architecture", "variant") if k in doc}
                              | ({"os.features": doc["os.features"]} if "os.features" in doc else {}), "config")
        rootfs = doc.get("rootfs")
        if not isinstance(rootfs, dict) or rootfs.get("type") != "layers":
            raise OCIError("config.rootfs.type must be 'layers'")
        diff_ids = rootfs.get("diff_ids")
        if not isinstance(diff_ids, list):
            raise OCIError("config.rootfs.diff_ids must be an array")
        ids = tuple(validate_oci_digest(d, f"diff_ids[{i}]") for i, d in enumerate(diff_ids))
        cfg = doc.get("config") or {}
        if not isinstance(cfg, dict):
            raise OCIError("config.config must be an object")
        return cls(plat, ids, cfg, doc.get("created") if isinstance(doc.get("created"), str) else None)


def verify_config_matches(manifest: ImageManifest, config: ImageConfig) -> None:
    """Cross-document invariant: one diff_id per layer (non-artifact images)."""
    if manifest.is_artifact:
        return
    if len(config.diff_ids) != len(manifest.layers):
        raise OCIError("config diff_ids count does not match manifest layers")


# --- MC14: platform selection ----------------------------------------------------
_VARIANT_ORDER = {"arm64": ["v8", None], "arm": ["v7", "v6", "v5", None], "amd64": [None, "v1", "v2", "v3"]}


def platform_candidates(target: Platform) -> list[tuple[str, str, str | None]]:
    """Ordered acceptable (os, arch, variant) tuples for a host platform.  Only
    *compatible* fallbacks are listed (e.g. arm/v7 host accepts v6, v5)."""
    order = _VARIANT_ORDER.get(target.architecture, [None])
    if target.variant is not None and target.variant in order:
        order = order[order.index(target.variant):]
        if None not in order:
            order = order + [None]
    return [(target.os, target.architecture, v) for v in dict.fromkeys([target.variant] + order)]


def select_platform(index: ImageIndex, target: Platform, *, require_features: tuple[str, ...] = ()) -> Descriptor:
    """Deterministically pick the best manifest for ``target``.

    Never falls back to a different os/architecture; ties are broken by list order,
    which the OCI spec defines as the publisher's preference.  Attestation entries
    (``vnd.docker.reference.type``) and entries without a platform are ignored.
    """
    candidates = platform_candidates(target)
    best: tuple[int, int, Descriptor] | None = None
    for pos, d in enumerate(index.manifests):
        if d.platform is None or "vnd.docker.reference.type" in d.annotations:
            continue
        if d.media_type not in MANIFEST_TYPES:
            continue
        if not set(require_features) <= set(d.platform.os_features):
            continue
        key = (d.platform.os, d.platform.architecture, d.platform.variant)
        if key not in candidates:
            continue
        rank = candidates.index(key)
        if best is None or (rank, pos) < (best[0], best[1]):
            best = (rank, pos, d)
    if best is None:
        raise NoMatchingPlatform(f"no manifest in index matches {target}")
    return best[2]
