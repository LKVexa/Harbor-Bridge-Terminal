"""The fabric, as a picture you can run.

A distributed fabric language's state is a spatial field, not a scalar. The
studio already persists a container's device fabric as a small binary blob
(`PA21FAB1`): the monotonic and clock counters, and eight storage slots, four
of which are the guest's own objects. This module makes that same fabric a
tiled image, losslessly and in both directions:

    fabric blob  <-->  PA21FABTIF/1  (a multi-page TIFF)

The four guest storage objects are laid out as tiles of one raster, in a grid,
so a cell's position in the fabric is its position in the picture -- shards are
tiles, the field is the image. The counters and the non-guest slots, which are
scalar, are carried as tags rather than pixels, because scalar state does not
want to be a picture. Every run appends the field as a new page, so the file is
an immutable frame history of the fabric evolving.

Because the map is a bijection, the language is reversible: the studio can
write the image from a run, and read the image back as the state of the next
run. When that loop runs continuously (`studio fabric live`), the image is in
constant flux and the program executes it in real time -- and an edit made to
the image from outside is read on the next tick, which is what a distributed
fabric demands.

Nothing here needs anything but Pillow, which the studio already relies on
for the window, so a container's fabric image works wherever the studio runs.
"""

from __future__ import annotations

import json
import struct
from typing import Dict, List, Optional, Tuple

MAGIC = b"PA21FAB1"                 # the binary fabric blob the C host writes
TIF_MAGIC = "PA21FABTIF/1"         # the image form of the same fabric
HEADER = 28                        # magic(8) + version(4) + monotonic(8) + clock(8)
SLOTS = 8                          # control0/1, object0..3, state0/1
GUEST_FIRST, GUEST_COUNT = 2, 4    # slots 2..5 are the guest storage objects
SHARD_BYTES = 512                  # BR_STORAGE_OBJECT_BYTES

# private TIFF tags for the scalar state; 700-range is free for local use
T_KIND, T_TICK, T_STATE = 65000, 65001, 65002


class FabricError(RuntimeError):
    """A fabric image the studio will not read, with the reason attached."""


# ---------------------------------------------------------------------------
# the binary fabric, parsed and rebuilt exactly
# ---------------------------------------------------------------------------


def parse_blob(blob: bytes) -> Dict[str, object]:
    """Split a PA21FAB1 blob into counters and eight slot payloads."""
    if len(blob) < HEADER or blob[:8] != MAGIC:
        raise FabricError("not a PA21FAB1 fabric blob")
    version = struct.unpack_from("<I", blob, 8)[0]
    monotonic = struct.unpack_from("<Q", blob, 12)[0]
    clock = struct.unpack_from("<Q", blob, 20)[0]
    off, slots = HEADER, []
    for _ in range(SLOTS):
        if off + 8 > len(blob):
            raise FabricError("fabric blob truncated in its slot table")
        ln = struct.unpack_from("<Q", blob, off)[0]
        off += 8
        if off + ln > len(blob):
            raise FabricError("fabric blob truncated in a slot payload")
        slots.append(blob[off:off + ln])
        off += ln
    return {"version": version, "monotonic": monotonic, "clock": clock,
            "slots": slots}


def build_blob(parts: Dict[str, object]) -> bytes:
    """Reassemble the exact PA21FAB1 blob from parsed parts."""
    out = bytearray()
    out += MAGIC
    out += struct.pack("<I", int(parts["version"]))
    out += struct.pack("<Q", int(parts["monotonic"]))
    out += struct.pack("<Q", int(parts["clock"]))
    slots = list(parts["slots"])                              # type: ignore
    if len(slots) != SLOTS:
        raise FabricError(f"a fabric has {SLOTS} slots, not {len(slots)}")
    for s in slots:
        out += struct.pack("<Q", len(s))
        out += bytes(s)
    return bytes(out)


# ---------------------------------------------------------------------------
# the spatial layout: guest shards -> tiles of one raster
# ---------------------------------------------------------------------------


FRAME = b"BRO1"                    # the VM frames a stored object: BRO1 header,
FRAME_HEADER = 16                  # 16-byte header, payload, then a 32-byte hash


def _unframe(slot: bytes) -> bytes:
    """The guest-visible payload inside a framed storage object.

    The VM wraps a stored object in a BRO1 frame with a content hash. That
    hash is integrity over the frame, not user data, and it is what makes
    painting raw pixels fail. The editable fabric is the payload; the frame is
    the VM's to maintain. So the image holds payloads, and the VM reframes
    them on read (any object whose length is not the full frame is reframed).
    """
    if len(slot) >= FRAME_HEADER and slot[:4] == FRAME:
        plen = struct.unpack_from("<H", slot, 12)[0]
        return slot[FRAME_HEADER:FRAME_HEADER + plen]
    return slot


def _grid(cols: int) -> Tuple[int, int]:
    rows = (GUEST_COUNT + cols - 1) // cols
    return rows, cols


def _tile_shape() -> Tuple[int, int]:
    """A shard is SHARD_BYTES bytes = SHARD_BYTES/4 RGBA pixels, as a tile."""
    px = SHARD_BYTES // 4                                     # 128 pixels
    w = 16
    h = px // w                                               # 8
    return w, h


def _field_image(slots: List[bytes], cols: int):
    from PIL import Image
    tw, th = _tile_shape()
    rows, _ = _grid(cols)
    W, H = cols * tw, rows * th
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for k in range(GUEST_COUNT):
        payload = slots[GUEST_FIRST + k]
        buf = bytes(payload) + bytes(SHARD_BYTES - len(payload))
        tile = Image.frombytes("RGBA", (tw, th), buf)
        r, c = k // cols, k % cols
        canvas.paste(tile, (c * tw, r * th))
    return canvas, (tw, th, rows, cols)


def _read_field(img, geom: Dict[str, int]) -> List[bytes]:
    tw, th = geom["tw"], geom["th"]
    cols = geom["cols"]
    out = []
    for k in range(GUEST_COUNT):
        r, c = k // cols, k % cols
        tile = img.crop((c * tw, r * th, c * tw + tw, r * th + th))
        out.append(tile.convert("RGBA").tobytes())
    return out


# ---------------------------------------------------------------------------
# blob <-> tif
# ---------------------------------------------------------------------------


def _sidecar(parts: Dict[str, object], geom: Tuple[int, int, int, int],
             tick: int) -> Dict[str, object]:
    tw, th, rows, cols = geom
    slots = list(parts["slots"])                              # type: ignore
    return {
        "kind": TIF_MAGIC,
        "version": int(parts["version"]),
        "monotonic": int(parts["monotonic"]),
        "clock": int(parts["clock"]),
        "tick": int(tick),
        "grid": {"rows": rows, "cols": cols, "tile_w": tw, "tile_h": th,
                 "shard_bytes": SHARD_BYTES},
        # the true payload length of each guest shard, so trailing pad is not
        # mistaken for fabric content on the way back
        "shard_len": [len(slots[GUEST_FIRST + k]) for k in range(GUEST_COUNT)],
        # the scalar, non-guest slots, exact, as hex -- they are not spatial
        "scalar_slots": {str(i): slots[i].hex()
                         for i in range(SLOTS)
                         if not (GUEST_FIRST <= i < GUEST_FIRST + GUEST_COUNT)},
    }


def _page_ifd(car: Dict[str, object]):
    from PIL.TiffImagePlugin import ImageFileDirectory_v2
    js = json.dumps(car, separators=(",", ":"))
    ifd = ImageFileDirectory_v2()
    ifd[T_KIND] = TIF_MAGIC
    ifd[T_TICK] = int(car.get("tick", 0))
    ifd[T_STATE] = js
    ifd[270] = js                     # ImageDescription, the standard mirror
    return ifd


def write_tif(blob: bytes, path: str, cols: int = 2, tick: int = 0,
              history: Optional[List] = None) -> Dict[str, object]:
    """Write the fabric blob as a PA21FABTIF/1 image, newest page first.

    `history` is a list of prior PIL frames (page 1..n), each carrying its own
    sidecar in `encoderinfo`, so the file keeps an immutable, self-describing
    record of every state the fabric has held.
    """
    parts = parse_blob(blob)
    # the image shows guest-visible payloads, not the VM's framed wrappers, so
    # a cell in the picture is a cell the program reads -- and paintable
    slots = list(parts["slots"])
    payloads = [_unframe(slots[GUEST_FIRST + k]) for k in range(GUEST_COUNT)]
    view_parts = dict(parts)
    view_slots = list(slots)
    for k in range(GUEST_COUNT):
        view_slots[GUEST_FIRST + k] = payloads[k]
    view_parts["slots"] = view_slots
    parts = view_parts
    field, (tw, th, rows, cols2) = _field_image(list(parts["slots"]), cols)
    car = _sidecar(parts, (tw, th, rows, cols2), tick)
    ifd = _page_ifd(car)
    hist = list(history or [])
    # each history page must carry its own tiffinfo, or Pillow writes page 0's
    # tags onto all of them and the frames all read back as the newest state
    for h in hist:
        if not getattr(h, "encoderinfo", None):
            h.encoderinfo = {"tiffinfo": _page_ifd(
                {"kind": TIF_MAGIC, "tick": 0, "grid": car["grid"]})}
    field.encoderinfo = {"tiffinfo": ifd}
    field.save(path, save_all=True, append_images=hist,
               tiffinfo=ifd, compression="tiff_deflate")
    return {"path": path, "tick": tick, "pages": 1 + len(hist),
            "grid": car["grid"], "bytes": _size(path)}


def _size(path: str) -> int:
    import os
    return os.path.getsize(path)


def read_tif(path: str) -> Dict[str, object]:
    """Read a PA21FABTIF/1 image back to the exact fabric blob it encodes."""
    from PIL import Image
    img = Image.open(path)
    car = _load_sidecar(img)
    geom = {"tw": car["grid"]["tile_w"], "th": car["grid"]["tile_h"],
            "rows": car["grid"]["rows"], "cols": car["grid"]["cols"]}
    shards = _read_field(img.convert("RGBA"), geom)
    shard_len = car["shard_len"]
    slots: List[bytes] = [b""] * SLOTS
    for i, hexs in car["scalar_slots"].items():
        slots[int(i)] = bytes.fromhex(hexs)
    for k in range(GUEST_COUNT):
        slots[GUEST_FIRST + k] = shards[k][:int(shard_len[k])]
    parts = {"version": car["version"], "monotonic": car["monotonic"],
             "clock": car["clock"], "slots": slots}
    blob = build_blob(parts)
    return {"blob": blob, "tick": int(car.get("tick", 0)),
            "pages": getattr(img, "n_frames", 1), "sidecar": car}


def _load_sidecar(img) -> Dict[str, object]:
    tag = None
    if hasattr(img, "tag_v2"):
        try:
            tag = img.tag_v2.get(T_STATE) or img.tag_v2.get(270)
        except Exception:                                     # noqa: BLE001
            tag = None
    if not tag:
        tag = (img.info or {}).get("description")
    if not tag:
        raise FabricError("this .tif carries no PA21FABTIF/1 sidecar; it was "
                          "not written as a fabric image")
    try:
        car = json.loads(tag)
    except ValueError as e:
        raise FabricError(f"the fabric sidecar is not JSON: {e}")
    if car.get("kind") != TIF_MAGIC:
        raise FabricError(f"this .tif is {car.get('kind')!r}, not "
                          f"{TIF_MAGIC}")
    return car


def frames(path: str) -> List[Dict[str, object]]:
    """The tick and scalars of every page, oldest run last -- the history."""
    from PIL import Image
    img = Image.open(path)
    out = []
    for i in range(getattr(img, "n_frames", 1)):
        img.seek(i)
        try:
            car = _load_sidecar(img)
        except FabricError:
            continue
        out.append({"page": i, "tick": car.get("tick"),
                    "monotonic": car.get("monotonic"),
                    "clock": car.get("clock")})
    return out


def load_frames(path: str) -> List:
    """The raw PIL pages, each re-carrying its sidecar, so a rewrite keeps the
    history intact rather than stamping every page with the newest state."""
    from PIL import Image
    img = Image.open(path)
    out = []
    for i in range(getattr(img, "n_frames", 1)):
        img.seek(i)
        frame = img.convert("RGBA").copy()
        try:
            car = _load_sidecar(img)
            frame.encoderinfo = {"tiffinfo": _page_ifd(car)}
        except FabricError:
            pass
        out.append(frame)
    return out


def render_view(path: str, out: str, scale: int = 16) -> Dict[str, object]:
    """An upscaled PNG of the current field, for looking at the fabric."""
    from PIL import Image
    img = Image.open(path).convert("RGBA")
    big = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    big.save(out)
    return {"view": out, "cells": (img.width, img.height),
            "pixels": (big.width, big.height)}


def validate_roundtrip(blob: bytes, path: str) -> Dict[str, object]:
    """Write then read, and confirm the fabric survived byte for byte."""
    import hashlib
    write_tif(blob, path)
    back = read_tif(path)["blob"]
    ok = back == blob
    return {"reversible": ok,
            "in_sha256": hashlib.sha256(blob).hexdigest(),
            "out_sha256": hashlib.sha256(back).hexdigest(),
            "bytes_in": len(blob), "bytes_out": len(back),
            "reason": "" if ok else "the fabric did not survive the round "
                                    "trip through the image"}
