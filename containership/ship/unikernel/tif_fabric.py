"""The .tif fabric: every container in the ship gets its own picture you can run.

PA Language Studio 2.0.0 (the hull) persists a container's device fabric as a
tiled, multi-page TIFF (`PA21FABTIF/1`, `pa21studio.fabric_tif`): the four guest
storage objects are tiles of one raster, scalars ride as tags, every run
appends a page, and the map fabric <-> image is a bijection -- so the image can
be read back as the state of the next run, including an edit made to it from
outside. UC-2.0.0 gives that to every container of every berth:

    berths/<b>/DF_Small/       fabric/GENESIS.fabric.tif  fabric/FABRIC.json   (sealed genesis)
                               _fabric/DF_Small.fabric.tif  (.png .json)        (live state, outside the seal)
    berths/<b>/DF_Medium/      (same)         berths/<b>/DF_Large/  berths/<b>/DF_Xtra_Large/
    berths/<b>/DF_Fabric/      (same: the federation's picture)
    _studio/state/berth_<b>.fabric.tif                                          (the hull face's own, kept by the studio;
                                                                                 mirrored into berths/<b>/_fabric/face.fabric.tif)

What a tick executes (`uc run <berth>` / `uc fabric tick`):

* the four **node containers**: tile 0 is the container's STATE (tick, the chained
  accumulator, the reference, rows, flags, the engine), tiles 1-2 hold the berth's
  DECLARATION -- BERTH.pal's row words, one word per cell -- and tile 3 the
  provenance (seals). A tick reads the picture, hands the words and the
  accumulator it found there to the container's engine (the DF adapter lowers
  and runs them natively), and writes the new state back as a new page. Because
  the words come from the picture, painting a declaration cell changes what the
  engine executes; the container reports whether its declaration is still the
  sealed one, and the federation reports whether the four still agree;
* the **fabric container** (DF_Fabric): the federation program over the four --
  four witness tasks on the hold's TaskRuntime, a federation barrier, ALLGATHER
  and ALLREDUCE over the four accumulators (the vote), a sealed event log with a
  replay self-check -- and its picture records the vote, the four accumulators
  and the log hash;
* the **hull face** (`berth_<b>` in the studio): the studio's own reversible loop
  (`studio fabric tick`): the VM executes the berth's field program against the
  state read from its .tif -- the witness of BERTH.pal in R2 (must equal the
  reference), the tick cell advanced, the witness mirrored into cell 8 -- and the
  studio writes the state back as a new page.

Genesis is deterministic and sealed with the berth; the live images are state
and live outside the seal (exactly as the studio keeps a container's fabric
outside its container), so BUILD/VERIFY leave a sealed ship byte-identical
and RUN never has to re-seal anything. Nothing here needs more than Pillow,
which the hull already requires; without it, everything .tif is SKIPPED with
that reason and the ship still sails.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import importlib
from . import strictjson as json
import os
import shutil
import struct
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import UC_RELEASE, NODE_IDS, NODE_CONTAINER, FABRIC_CONTAINER, SLOTS, ShipError, Refusal
from . import engines as E
from . import safety as SAFE
from . import ucmanifest as M

FABRIC_SCHEMA = "UC/FABRIC/1"          # fabric/FABRIC.json (sealed with the berth)
TICK_SCHEMA = "UC/FABRIC_TICK/1"       # one tick of a berth (RUN)
STATUS_SCHEMA = "UC/FABRIC_STATUS/1"
IDENTITY_KIND = "UC/FABRIC_IDENTITY/1"
GENESIS_DIR = "fabric"                 # sealed genesis + record, per container
STATE_DIR = "_fabric"                  # live images, per container (and per berth), outside the seal
GENESIS_TIF = "GENESIS.fabric.tif"
FABRIC_JSON = "FABRIC.json"

TILE_STATE, TILE_WORDS_A, TILE_WORDS_B, TILE_PROV = 0, 1, 2, 3   # guest objects 0..3
TILE_NODES, TILE_LOG = 1, 2                                     # the fabric container's tiles 1 and 2
PAYLOAD_MAX = 464                      # BR_STORAGE_OBJECT_BYTES - the VM's 48-byte frame
WORDS_PER_TILE = PAYLOAD_MAX // 8      # 58 row words per tile
MAX_DECL_WORDS = 2 * WORDS_PER_TILE    # 116 >= BERTH.pal's 84-row bound
STATE_WORDS = 8                        # 64 bytes: the same window the studio's field template reads

# state flags (tile 0 word 5)
F_AGREE, F_INTACT, F_HALTED, F_UNANIMOUS, F_ALL_INTACT, F_REPLAY_OK, F_FACE_OK, F_TICKED = 1, 2, 4, 8, 16, 32, 64, 128

#: the DF witness constants (dfabric.witness, carried unchanged in the hold): the same arithmetic the four
#: engines and the DF lowerings use, so a hull-face witness equals the fabric's reference witness. Gate B4
#: checks the field lowering's witness rows are identical to the DF lowering's, row for row.
FNV_OFFSET = 1469598103934665603
FNV_PRIME = 0x100000001B3
MASK64 = (1 << 64) - 1

_CODEC: Dict[str, Any] = {}


# --------------------------------------------------------------------------
# the codec: the hull's own module, imported from hull/
# --------------------------------------------------------------------------

def available() -> Tuple[bool, str]:
    """Is the .tif fabric usable on this host? (the hull's codec + Pillow)"""
    try:
        codec()
        return True, ""
    except ShipError as exc:
        return False, str(exc)


def codec():
    if _CODEC.get("mod") is not None:
        return _CODEC["mod"]
    try:
        importlib.import_module("PIL.Image")
    except Exception as exc:  # noqa: BLE001
        raise ShipError("Pillow (PIL) is not installed; the .tif fabric needs it (see REQUIREMENTS.txt)",
                        {"import_error": f"{type(exc).__name__}: {exc}"})
    hull = E.hull_dir()
    if hull not in sys.path:
        sys.path.insert(0, hull)
    try:
        mod = importlib.import_module("pa21studio.fabric_tif")
    except Exception as exc:  # noqa: BLE001
        raise ShipError("the hull carries no pa21studio.fabric_tif; the hull must be PA Language Studio 2.0.0 or later",
                        {"import_error": f"{type(exc).__name__}: {exc}", "hull": hull})
    _CODEC["mod"] = mod
    return mod


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# --------------------------------------------------------------------------
# encoding: state, words, provenance  <->  the eight fabric slots
# --------------------------------------------------------------------------

def pack_state(tick: int, acc: int, ref: int, rows: int, index: int, flags: int, engine_lo: int, last: int) -> bytes:
    return struct.pack("<8Q", *(int(x) & MASK64 for x in (tick, acc, ref, rows, index, flags, engine_lo, last)))


def unpack_state(b: bytes) -> Dict[str, int]:
    b = bytes(b) + bytes(max(0, 8 * STATE_WORDS - len(b)))
    tick, acc, ref, rows, index, flags, engine_lo, last = struct.unpack_from("<8Q", b, 0)
    return {"tick": tick, "acc": acc, "ref": ref, "rows": rows, "index": index, "flags": flags,
            "engine_lo64": engine_lo, "last": last}


def pack_words(words: Sequence[int]) -> Tuple[bytes, bytes]:
    if len(words) > MAX_DECL_WORDS:
        raise ShipError("the declaration does not fit two tiles", {"words": len(words), "max": MAX_DECL_WORDS})
    a = words[:WORDS_PER_TILE]
    b = words[WORDS_PER_TILE:]
    return (struct.pack(f"<{len(a)}Q", *(w & MASK64 for w in a)) if a else b"",
            struct.pack(f"<{len(b)}Q", *(w & MASK64 for w in b)) if b else b"")


def unpack_words(a: bytes, b: bytes, count: int) -> List[int]:
    raw = bytes(a)[: 8 * min(count, WORDS_PER_TILE)] + bytes(b)[: 8 * max(0, count - WORDS_PER_TILE)]
    n = len(raw) // 8
    return list(struct.unpack(f"<{n}Q", raw[: 8 * n])) if n else []


def _hexbytes(h: Optional[str], n: int = 32) -> bytes:
    try:
        b = bytes.fromhex(h or "")
    except ValueError:
        b = b""
    return (b + bytes(n))[:n]


def identity(berth: str, container: str, node_id: Optional[str], engine_sha: Optional[str]) -> bytes:
    return json.dumps({"kind": IDENTITY_KIND, "uc": UC_RELEASE, "berth": berth, "container": container,
                       "node": node_id or "-", "engine_sha256": engine_sha or "-"},
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def parse_identity(b: bytes) -> Dict[str, Any]:
    try:
        d = json.loads(bytes(b).decode("utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def build_blob(tick: int, rows_total: int, slots: List[bytes]) -> bytes:
    if len(slots) != 8:
        raise ShipError("a fabric has eight slots", {"slots": len(slots)})
    for i, s in enumerate(slots):
        if 2 <= i < 6 and len(s) > PAYLOAD_MAX:
            raise ShipError("a guest tile payload exceeds the VM's frame", {"slot": i, "bytes": len(s), "max": PAYLOAD_MAX})
    return codec().build_blob({"version": 1, "monotonic": int(tick), "clock": int(rows_total), "slots": [bytes(s) for s in slots]})


def decode_blob(blob: bytes) -> Dict[str, Any]:
    p = codec().parse_blob(blob)
    sl = list(p["slots"])
    st = unpack_state(sl[2])
    return {"version": p["version"], "tick": p["monotonic"], "rows_total": p["clock"], "slots": sl,
            "identity": parse_identity(sl[0]), "receipt_hex": bytes(sl[1]).hex(), "state": st,
            "words": unpack_words(sl[3], sl[4], st["rows"]) if st["rows"] <= MAX_DECL_WORDS else [],
            "prov_hex": bytes(sl[5]).hex()}


def sha256_of(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# paths
# --------------------------------------------------------------------------

def _berth_dir(berth: str) -> str:
    from .berth import berth_dir
    return berth_dir(berth)


def genesis_dir(berth: str, slot: str) -> str:
    return os.path.join(_berth_dir(berth), slot, GENESIS_DIR)


def genesis_path(berth: str, slot: str) -> str:
    return os.path.join(genesis_dir(berth, slot), GENESIS_TIF)


def live_dir(berth: str, slot: str, base: Optional[str] = None) -> str:
    return os.path.join(base or _berth_dir(berth), slot, STATE_DIR)


def live_path(berth: str, slot: str, base: Optional[str] = None) -> str:
    return os.path.join(live_dir(berth, slot, base), f"{slot}.fabric.tif")


def berth_state_dir(berth: str, base: Optional[str] = None) -> str:
    return os.path.join(base or _berth_dir(berth), STATE_DIR)


#: Mirrors carry running state with the ship, so their names are part of the delivered tree and must
#: fit the same budget as cargo (berth.DELIVERED_PATH_BUDGET): a berth name and a container name can
#: each be sixty characters, and `<package>/berths/<b>/_fabric/<container>.fabric.tif` would then be
#: past what a Windows extraction can hold. The hull face's mirror is therefore simply `face` (the
#: container it belongs to is named in BERTH.json), and a hull-cargo mirror keeps the container's own
#: name unless that would not fit, in which case it is `mnt_<sha256(name)[:8]>` and the mount registry
#: (`_studio/uc_mounts.json`, `uc mounts <berth>`) says which container it is.
FACE_MIRROR = "face"


def mirror_name(berth: str, container: Optional[str] = None, ext: str = ".fabric.tif") -> str:
    """The file name of a picture mirrored into `berths/<b>/_fabric/` (face, or a hull-cargo container)."""
    from .berth import PACKAGE_DIR, DELIVERED_PATH_BUDGET
    if container is None:
        return FACE_MIRROR + ext
    name = container + ext
    if len(f"{PACKAGE_DIR}/berths/{berth}/{STATE_DIR}/{name}") > DELIVERED_PATH_BUDGET:
        name = "mnt_" + hashlib.sha256(container.encode("utf-8")).hexdigest()[:8] + ext
    return name


def mirror_path(berth: str, container: Optional[str] = None, base: Optional[str] = None,
                ext: str = ".fabric.tif", legacy_ok: bool = True) -> str:
    """Where that mirror lives. Reading falls back to the name a pre-UC-2.1.3 ship wrote."""
    d = berth_state_dir(berth, base)
    p = os.path.join(d, mirror_name(berth, container, ext))
    if legacy_ok and not os.path.isfile(p):
        legacy = os.path.join(d, f"{container or face_name(berth)}{ext}")
        if os.path.isfile(legacy):
            return legacy
    return p


def face_name(berth: str) -> str:
    from . import face_container_name
    return face_container_name(berth)


# --------------------------------------------------------------------------
# the hull face: BERTH.pal's witness as a field program on the studio's fabric
# --------------------------------------------------------------------------

def hull_face_source(words: Sequence[int], unit_id: str, acc_in: int = FNV_OFFSET) -> str:
    """LCTLC/1.2 (BR/1.1) unit for the hull's runtime: the row-sequence witness of
    `words` in R2 (identical arithmetic to the DF lowering: FNV-1a 64 over the row
    words), then the field: read the container's storage object 0 (64-byte window),
    advance the tick cell (cell 0), mirror the witness into cell 8, write it back.
    `studio fabric tick` executes exactly this against the .tif's state."""
    try:  # prefer the hold's own constants when the hold is bound
        W = E.bind(require=False).get("witness")
        offset, prime = (W.FNV_OFFSET, W.FNV_PRIME) if W else (FNV_OFFSET, FNV_PRIME)
    except Exception:  # noqa: BLE001
        offset, prime = FNV_OFFSET, FNV_PRIME
    if acc_in == FNV_OFFSET:
        acc_in = offset
    if 3 * len(words) + 4 + 11 > 256:
        raise ShipError("the declaration does not fit one BR/1.1 lowering with the field rows", {"words": len(words), "max_words": (256 - 15) // 3})
    SEP, INS = "│", "›"
    uid = unit_id.replace("_", "-")
    out = ["LCTLC/1.2",
           f"@unit id={uid} version=4.3.0 language=columned-lctl/4.3 isa=BR/1.1 br_image_version=10 br_request_caps=CONTROL|ARITH|MEMORY|STATE",
           "@defaults mode=WRAP width=WIDE",
           SEP.join(("ID", "LANE", "OP", "OUT", "CTRL", "IN", "ARG", "META"))]
    n = [0]

    def row(op: str, out_reg: str, cap: str, ins: Sequence[str] = (), arg: str = "_", meta: str = "_") -> None:
        n[0] += 1
        out.append(SEP.join((f"W{n[0]:05d}", "exec", op, out_reg, f"C0:{cap}", INS.join(ins) if ins else "_", arg, meta)))

    row("MOVI", "R0", "CONTROL", (), f"imm={acc_in & MASK64}")
    row("MOVI", "R1", "CONTROL", (), f"imm={prime}")
    for w in words:
        row("MUL", "R0", "ARITH", ("R0", "R1"))
        row("MOVI", "R3", "CONTROL", (), f"imm={w & MASK64}")
        row("XOR", "R0", "ARITH", ("R0", "R3"))
    row("MOV", "R2", "CONTROL", ("R0",), "_", "note=the-witness")
    row("MOVI", "R4", "CONTROL", (), "imm=0", "note=window-offset")
    row("MOVI", "R5", "CONTROL", (), "imm=64", "note=window-length")
    row("SVC", "R6", "STATE", ("R4", "R5"), "offset=0;svc=STORAGE_READ", "note=read-shard-0")
    row("LOAD", "R7", "MEMORY", (), "imm=0", "note=the-tick-cell")
    row("MOVI", "R8", "CONTROL", (), "imm=1")
    row("ADD", "R7", "ARITH", ("R7", "R8"), "_", "note=advance-the-tick")
    row("STORE", "_", "MEMORY", ("R7",), "imm=0", "note=tick-back-to-cell-0")
    row("STORE", "_", "MEMORY", ("R2",), "imm=8", "note=witness-into-cell-8")
    row("SVC", "R9", "STATE", ("R4", "R5"), "offset=0;svc=STORAGE_WRITE", "note=shard-0-back")
    row("HALT", "_", "CONTROL")
    out.append("@end")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# genesis (written by `uc load`, sealed with the berth)
# --------------------------------------------------------------------------

def make_genesis(dest: str, berth: str, words: Sequence[int], ref: int, berth_seal: str, cargo_seal: str,
                 per_node_tree: Dict[str, str], engine_shas: Dict[str, Optional[str]], policy_sha: str) -> Dict[str, Any]:
    """Write every container's genesis image and record under <slot>/fabric/.
    Returns the record for BERTH.json (or an `available: False` record without Pillow)."""
    ok, why = available()
    rec: Dict[str, Any] = {"schema": FABRIC_SCHEMA, "available": ok, "containers": {}, "layout": {
        "codec": "PA21FABTIF/1 (hull: pa21studio.fabric_tif)", "tiles": "4 guest objects as 16x8 RGBA tiles, 2x2 grid",
        "node_container": {"tile0": "STATE [tick, acc, ref, rows, node_index, flags, engine_lo64, last_acc_out] (8 x u64 LE)",
                           "tile1": f"DECLARATION words 0..{WORDS_PER_TILE - 1} (BERTH.pal row words, 8 bytes each)",
                           "tile2": f"DECLARATION words {WORDS_PER_TILE}..{MAX_DECL_WORDS - 1}",
                           "tile3": "PROVENANCE: BERTH.pal seal (32) + CARGO.pal seal (32) + this node's cargo tree sha256 (32)",
                           "control0": "identity JSON", "control1": "sha256 of the last tick record (zeros at genesis)",
                           "monotonic": "tick", "clock": "rows witnessed, cumulative"},
        "fabric_container": {"tile0": "STATE [tick, fed_acc, ref, rows, participants, flags, votes_bitmask, face_tick]",
                             "tile1": "NODES: the four accumulators (N_SMALL, N_MEDIUM, N_LARGE, N_XLARGE) + their flags",
                             "tile2": "LOG: event-log sha256 (32) + events (u64) + collectives_ok (u64)",
                             "tile3": "PROVENANCE: BERTH.pal seal + CARGO.pal seal + policy sha256",
                             "control1": "the event-log hash of the last tick"},
        "hull_face": "_studio/state/berth_<b>.fabric.tif -- the studio's own fabric image of the berth's container (studio fabric init/tick)",
        "flags": {"AGREE": F_AGREE, "INTACT": F_INTACT, "HALTED": F_HALTED, "UNANIMOUS": F_UNANIMOUS, "ALL_INTACT": F_ALL_INTACT,
                  "REPLAY_OK": F_REPLAY_OK, "FACE_OK": F_FACE_OK, "TICKED": F_TICKED},
        "state_dir": STATE_DIR, "genesis_dir": GENESIS_DIR}}
    if not ok:
        rec["reason"] = why
        return rec
    ftif = codec()
    wa, wb = pack_words(list(words))
    for i, nid in enumerate(NODE_IDS):
        slot = NODE_CONTAINER[nid]
        esha = engine_shas.get(slot)
        elo = int(esha[:16], 16) if esha else 0
        st = pack_state(0, FNV_OFFSET, ref, len(words), i, F_AGREE | F_INTACT, elo, 0)
        prov = _hexbytes(berth_seal) + _hexbytes(cargo_seal) + _hexbytes(per_node_tree.get(nid))
        blob = build_blob(0, 0, [identity(berth, slot, nid, esha), bytes(32), st, wa, wb, prov, b"", b""])
        d = os.path.join(dest, slot, GENESIS_DIR)
        os.makedirs(d, exist_ok=True)
        info = ftif.write_tif(blob, os.path.join(d, GENESIS_TIF), cols=2, tick=0)
        rt = ftif.validate_roundtrip(blob, os.path.join(d, ".rt.tif"))
        os.remove(os.path.join(d, ".rt.tif"))
        crec = {"schema": FABRIC_SCHEMA, "uc_release": UC_RELEASE, "berth": berth, "container": slot, "node_id": nid,
                "genesis": {"file": f"{GENESIS_DIR}/{GENESIS_TIF}", "tick": 0, "blob_sha256": hashlib.sha256(blob).hexdigest(),
                            "grid": info["grid"], "bytes": info["bytes"], "reversible": rt["reversible"]},
                "state0": unpack_state(st), "declaration_words": len(words), "reference_witness": ref,
                "engine_sha256": esha, "live": f"{STATE_DIR}/{slot}.fabric.tif",
                "executes": "the declaration words read from tiles 1-2, on this engine, from the accumulator read from tile 0 (uc run / uc fabric tick)"}
        with open(os.path.join(d, FABRIC_JSON), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(crec, indent=2, sort_keys=True) + "\n")
        rec["containers"][slot] = {"genesis_blob_sha256": crec["genesis"]["blob_sha256"], "reversible": rt["reversible"], "node_id": nid}
    # the fabric container: the federation's picture
    fsha = engine_shas.get(FABRIC_CONTAINER)
    st = pack_state(0, FNV_OFFSET, ref, len(words), len(NODE_IDS), F_UNANIMOUS | F_ALL_INTACT, int(fsha[:16], 16) if fsha else 0, 0)
    nodes_tile = struct.pack("<8Q", *([FNV_OFFSET] * 4 + [F_AGREE | F_INTACT] * 4))
    log_tile = bytes(32) + struct.pack("<2Q", 0, 0)
    prov = _hexbytes(berth_seal) + _hexbytes(cargo_seal) + _hexbytes(policy_sha)
    blob = build_blob(0, 0, [identity(berth, FABRIC_CONTAINER, None, fsha), bytes(32), st, nodes_tile, log_tile, prov, b"", b""])
    d = os.path.join(dest, FABRIC_CONTAINER, GENESIS_DIR)
    os.makedirs(d, exist_ok=True)
    info = ftif.write_tif(blob, os.path.join(d, GENESIS_TIF), cols=2, tick=0)
    rt = ftif.validate_roundtrip(blob, os.path.join(d, ".rt.tif"))
    os.remove(os.path.join(d, ".rt.tif"))
    crec = {"schema": FABRIC_SCHEMA, "uc_release": UC_RELEASE, "berth": berth, "container": FABRIC_CONTAINER, "node_id": None,
            "genesis": {"file": f"{GENESIS_DIR}/{GENESIS_TIF}", "tick": 0, "blob_sha256": hashlib.sha256(blob).hexdigest(),
                        "grid": info["grid"], "bytes": info["bytes"], "reversible": rt["reversible"]},
            "state0": unpack_state(st), "declaration_words": len(words), "reference_witness": ref,
            "engine_sha256": fsha, "live": f"{STATE_DIR}/{FABRIC_CONTAINER}.fabric.tif",
            "executes": "the federation program over the four node containers (TaskRuntime tasks, federation barrier, ALLGATHER/ALLREDUCE vote, sealed event log)"}
    with open(os.path.join(d, FABRIC_JSON), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(crec, indent=2, sort_keys=True) + "\n")
    rec["containers"][FABRIC_CONTAINER] = {"genesis_blob_sha256": crec["genesis"]["blob_sha256"], "reversible": rt["reversible"], "node_id": None}
    rec["hull_face"] = {"container": face_name(berth), "image": f"_studio/state/{face_name(berth)}.fabric.tif",
                        "mirror": f"{STATE_DIR}/{mirror_name(berth)}",
                        "program": "studio/main.lctlc (witness in R2 + field rows: tick cell +1, witness into cell 8)",
                        "created_by": "uc build / uc studio-register (studio fabric init), ticked by studio fabric tick"}
    return rec


# --------------------------------------------------------------------------
# live images
# --------------------------------------------------------------------------

def _studio_face(berth: str):
    """(studio, container name) if the hull is installed and the face registered, else (None, reason)."""
    try:
        s = E.studio()
    except Exception as exc:  # noqa: BLE001
        return None, f"hull not importable: {type(exc).__name__}: {exc}"
    if not s.installed:
        return None, "hull not installed at _studio/ (run BUILD)"
    cname = face_name(berth)
    names = {c.get("name") for c in (s.list_containers().get("containers") or [])}
    if cname not in names:
        return None, f"no studio container {cname} (run BUILD or `uc studio-register {berth}`)"
    return s, cname


def init_live(berth: str, force: bool = False, base: Optional[str] = None, face: bool = True) -> Dict[str, Any]:
    """Materialise the live images from the sealed genesis (kept if present unless force),
    and the hull face's own image in the studio (studio fabric init)."""
    codec()
    d = _berth_dir(berth)
    if not os.path.isdir(d):
        raise Refusal(f"no berth {berth!r}", {"berth": d})
    out: Dict[str, Any] = {"berth": berth, "containers": {}, "state_dir": STATE_DIR}
    for slot in SLOTS:
        g = genesis_path(berth, slot)
        if not os.path.isfile(g):
            out["containers"][slot] = {"created": False, "reason": "no sealed genesis (the berth was loaded without the .tif fabric)"}
            continue
        lp = live_path(berth, slot, base)
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        if os.path.isfile(lp) and not force:
            out["containers"][slot] = {"created": False, "kept": True, "path": lp}
            continue
        shutil.copyfile(g, lp)
        out["containers"][slot] = {"created": True, "path": lp, "from": g}
    os.makedirs(berth_state_dir(berth, base), exist_ok=True)
    if face:
        s, cname = _studio_face(berth)
        if s is None:
            out["hull_face"] = {"created": False, "reason": cname}
        else:
            tif = s.fabric_path(cname)
            mirror = mirror_path(berth, None, base)
            if os.path.isfile(tif) and not force:
                out["hull_face"] = {"created": False, "kept": True, "path": tif}
            elif os.path.isfile(mirror) and not force:
                # the running state travelled with the ship: restore it into the studio
                os.makedirs(os.path.dirname(tif), exist_ok=True)
                shutil.copyfile(mirror, tif)
                out["hull_face"] = {"created": False, "restored_from_mirror": mirror, "path": tif}
            else:
                if os.path.isfile(tif):
                    os.remove(tif)
                sp = s.state_path(cname)
                if os.path.isfile(sp) and force:
                    os.remove(sp)
                r = s.fabric_init(cname, from_state=False)
                out["hull_face"] = {"created": True, "path": r.get("fabric"), "grid": r.get("grid")}
                if force and os.path.isfile(mirror):
                    os.remove(mirror)
    return out


def mirror_face(berth: str, base: Optional[str] = None) -> Optional[str]:
    """Copy the hull face's picture from the studio's state dir into the berth's state dir."""
    s, cname = _studio_face(berth)
    if s is None:
        return None
    tif = s.fabric_path(cname)
    if not os.path.isfile(tif):
        return None
    d = berth_state_dir(berth, base)
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, mirror_name(berth))
    shutil.copyfile(tif, dst)
    return dst


MAX_TIF_BYTES = 8 * 1024 * 1024
MAX_TIF_PAGES = 512


def _validate_tif(path: str, *, appending: bool = False) -> None:
    """Preflight binary structure independently of the codec, then sidecars."""
    hull = E.hull_dir()
    if hull not in sys.path:
        sys.path.insert(0, hull)
    try:
        guard = importlib.import_module('pa21studio.fabric_guard')
    except ImportError as exc:
        raise Refusal('bounded TIFF admission module is unavailable') from exc
    try:
        SAFE.reject_link(path)
        raw = guard.read_bytes(path, limit=MAX_TIF_BYTES)
        bound = MAX_TIF_PAGES - (1 if appending else 0)
        report = guard.inspect_tiff(raw, max_pages=bound)
        if any(page['width'] != 32 or page['height'] != 16 for page in report['pages']):
            raise Refusal('unsupported ship TIFF geometry; expected 32 by 16 pixels')
        codec().inspect(path, max_pages=bound)
    except (guard.FabricError, OSError) as exc:
        raise Refusal(str(exc), {'path': path}) from exc


def _read(path: str) -> Dict[str, Any]:
    _validate_tif(path)
    ftif = codec()
    r = ftif.read_tif(path)
    d = decode_blob(r["blob"])
    d.update({"path": path, "pages": r["pages"], "tif_tick": r["tick"], "blob": r["blob"], "file_sha256": r["file_sha256"]})
    return d


def _preflight_next(path: str, row_increment: int = 0):
    """Refuse full history/counter exhaustion before any native work begins."""
    _validate_tif(path, appending=True)
    state = _read(path)
    if state['state']['tick'] >= MASK64 or state['rows_total'] > MASK64 - row_increment:
        raise Refusal('fabric counter capacity exhausted before native execution', {'path':path})
    return state


def _write_next(path: str, blob: bytes, tick: int, *, expected_sha256=None) -> Dict[str, Any]:
    ftif = codec()
    if os.path.isfile(path):
        _validate_tif(path, appending=True)
        current = ftif.G.read_bytes(path)
        digest = hashlib.sha256(current).hexdigest()
        if expected_sha256 is not None and expected_sha256 != digest:
            raise Refusal("stale fabric digest; no image was committed")
        expected_sha256 = digest
    hist = ftif.load_frames(path) if os.path.isfile(path) else []
    try:
        return ftif.write_tif(blob, path, cols=2, tick=tick, history=hist,
                              expected_sha256=expected_sha256)
    except ftif.FabricError as exc:
        raise Refusal(str(exc), {"path": path}) from exc
    finally:
        for frame in hist:
            frame.close()


def paint(path: str, tile: int, word: int, value: int, tick_keep: bool = True,
          *, expected_sha256=None) -> Dict[str, Any]:
    """Checked u64 cell patch, preserving history and the native 464-byte capacity.

    Cooperative callers hold the ship lock. expected_sha256 identifies the TIFF
    file, not its logical blob. A new page is committed only after validation.
    """
    if type(tile) is not int or not 0 <= tile < 4 or type(word) is not int or not 0 <= word < WORDS_PER_TILE:
        raise Refusal('paint requires tile 0..3 and word 0..57')
    if type(value) is not int or not 0 <= value < 2 ** 64:
        raise Refusal('paint value must be an unsigned 64-bit integer')
    _validate_tif(path, appending=True)
    ftif = codec()
    from pa21studio import pixel_kernel
    try:
        r = ftif.read_tif(path)
        if expected_sha256 is not None and r['file_sha256'] != expected_sha256:
            raise Refusal("stale fabric digest; no cell was changed")
        result = pixel_kernel.apply(r['blob'], [{'tile':tile, 'word':word, 'op':'set', 'value':value}])
        tick = r['tick'] if tick_keep else r['tick'] + 1
        written = _write_next(path, result.pop('blob'), tick, expected_sha256=r['file_sha256'])
        return {"path": path, "tile": tile, "word": word, "value": value,
                **result, "file_sha256":written['sha256'], "pages":written['pages']}
    except ftif.FabricError as exc:
        raise Refusal(str(exc), {"path":path}) from exc


# --------------------------------------------------------------------------
# the tick
# --------------------------------------------------------------------------

def _sealed_words(berth: str) -> Tuple[List[int], Dict[str, Any]]:
    b = E.bind()
    lang, W = b["lang"], b["witness"]
    d = _berth_dir(berth)
    prog, diags = lang.parse(open(os.path.join(d, "BERTH.pal"), encoding="utf-8").read())
    if prog is None:
        raise ShipError("BERTH.pal did not parse", {"diagnostics": [x.as_dict() for x in diags]})
    seal = json.load(open(os.path.join(d, "BERTH_SEAL.json"), encoding="utf-8"))
    words = W.words_of(prog)
    if not lang.verify(prog).ok or prog.seal() != seal.get("seal") or W.reference_witness_words(words) != seal.get("reference_witness"):
        raise Refusal("BERTH.pal seal/reference mismatch")
    return words, seal


@SAFE.serialized
def tick(berth: str, *, profile: str = "single_process_deterministic", base: Optional[str] = None,
         face: bool = True, view: bool = True, log_dir: Optional[str] = None, mounts: bool = True) -> Dict[str, Any]:
    """One tick of the berth's fabric: every container's picture in, executed, picture out."""
    ftif = codec()
    b = E.bind()
    W, FR, nodes_mod = b["witness"], b["fabric_runtime"], b["nodes"]
    F = FR.F
    roots = b["roots"]
    if not roots:
        raise ShipError("no engine is bound (run BUILD)", {})
    d = _berth_dir(berth)
    if not os.path.isdir(d):
        raise Refusal(f"no berth {berth!r}", {"berth": d})
    from . import ucmanifest as M
    integrity = M.check_sums(d)
    if not integrity["pass"]:
        raise Refusal("berth checksum verification failed before fabric execution", integrity)
    sealed_words, bseal = _sealed_words(berth)
    t_start = time.perf_counter()
    # make sure the live images exist (from genesis) -- never re-init an existing one
    init_live(berth, force=False, base=base, face=False)
    # Preflight all five live container images before scheduling a native task.
    # A full federation history must not be discovered only after node execution.
    for slot in SLOTS:
        image = live_path(berth, slot, base)
        if os.path.isfile(image):
            _preflight_next(image, len(sealed_words) * (len(NODE_IDS) if slot == FABRIC_CONTAINER else 1))
    if face:
        face_studio, face_container = _studio_face(berth)
        if face_studio is not None:
            face_image = face_studio.fabric_path(face_container)
            if os.path.isfile(face_image):
                _validate_tif(face_image, appending=True)
                if ftif.read_tif(face_image)['tick'] >= MASK64:
                    raise Refusal('hull face tick capacity exhausted before native execution')
    from . import host as H
    requested = profile
    profile, host_note = H.profile_for(profile)          # e.g. no `fork` on this host: multi_thread_deterministic, and say so
    rec: Dict[str, Any] = {"schema": TICK_SCHEMA, "uc_release": UC_RELEASE, "berth": berth, "utc": utcnow(),
                           "profile": profile, "profile_requested": requested, "host_note": host_note,
                           "declaration_rows": len(sealed_words), "reference_witness": bseal["reference_witness"],
                           "containers": {}, "state_base": base or d}
    # -- 1. read the four node pictures --------------------------------------
    inputs: Dict[str, Dict[str, Any]] = {}
    for nid in NODE_IDS:
        slot = NODE_CONTAINER[nid]
        lp = live_path(berth, slot, base)
        if not os.path.isfile(lp):
            rec["containers"][slot] = {"ticked": False, "reason": "no live image (no genesis)"}
            continue
        _validate_tif(lp, appending=True)
        img = _read(lp)
        st = img["state"]
        words = img["words"]
        inputs[nid] = {"slot": slot, "path": lp, "img": img, "state": st, "words": words,
                       "intact": words == sealed_words, "engine_bound": nid in roots}
    # -- 2. the federation program over the bound node containers ------------------
    run = FR.FabricRun({n: roots[n] for n in NODE_IDS if n in roots and n in inputs}, profile=profile, name=f"uc.tick.{berth}")
    tasks = []
    task_nodes = []
    for nid in run.node_ids:
        inp = inputs[nid]
        t = run.runtime.spawn(FR.witness_task, nid, roots[nid], list(inp["words"]), int(inp["state"]["acc"]),
                              f"uc.tick.{berth}.{nid}.t{int(inp['state']['tick']) + 1}",
                              task_id=f"uc.tick.{nid}", owner=run._worker(nid), cost_estimate=float(len(inp["words"])),
                              stage="tick", resource_claim={"cpu_slots": 1, "qpu_slots": 0},
                              provenance={"family": "CLASSICAL_REPLICA_PARALLEL", "proof_ref": "witness", "state_from": "tif"})
        tasks.append(t)
        task_nodes.append(nid)
    run.runtime.barrier("federation", participants=run.federation.worker_ids())
    results = run.runtime.await_all(tasks)
    by_node = {r["node_id"]: r for r in results}
    # the vote: ALLGATHER + ALLREDUCE over the four accumulators
    workers = [run._worker(n) for n in run.node_ids]
    vals = [int(by_node[n]["native_witness"]) for n in run.node_ids]
    coll = F.Collectives(len(workers), log=run.log, clock=run.clock)
    ch_g = F.select_algorithm("ALLGATHER", len(workers), 8)
    ch_r = F.select_algorithm("ALLREDUCE", len(workers), 8)
    rg = coll.run("ALLGATHER", vals, algorithm=ch_g.algorithm)
    rmax = coll.run("ALLREDUCE", vals, algorithm=ch_r.algorithm, reduce_op="max")
    rmin = coll.run("ALLREDUCE", vals, algorithm=ch_r.algorithm, reduce_op="min")
    gathered_ok = all(v == vals for v in rg.values)
    unanimous = len(set(vals)) == 1 and rmax.values[0] == rmin.values[0] == vals[0] and gathered_ok
    all_intact = all(inputs[n]["intact"] for n in run.node_ids)
    votes_mask = 0
    for i, nid in enumerate(NODE_IDS):
        if nid in by_node and by_node[nid]["differential_agreement"] and inputs[nid]["intact"]:
            votes_mask |= 1 << i
    run.log.append("-", "UC_TICK_VERDICT", inputs={"rows": len(sealed_words), "participants": len(run.node_ids)},
                   outputs={"unanimous": unanimous, "all_intact": all_intact, "votes": votes_mask,
                            "acc": vals[0] if unanimous and vals else 0})
    fin = run.finish()
    ev_hash = fin["event_log"]["hash"]
    replay_ok = fin["event_log"]["replay_self_check"]["token"] == "PASS" or bool(fin["event_log"]["replay_self_check"].get("ok"))
    # -- 3. write the node pictures ---------------------------------------------
    for nid in run.node_ids:
        inp = inputs[nid]
        r = by_node[nid]
        st = inp["state"]
        flags = (F_AGREE if r["differential_agreement"] else 0) | (F_INTACT if inp["intact"] else 0) | (F_HALTED if r["halted"] else 0) | F_TICKED
        new_tick = int(st["tick"]) + 1
        crec = {"container": inp["slot"], "node_id": nid, "tick": new_tick, "acc_in": int(st["acc"]), "acc_out": int(r["native_witness"]),
                "reference_for_words_read": int(r["reference_witness"]), "differential_agreement": bool(r["differential_agreement"]),
                "declaration_intact": inp["intact"], "words_read": len(inp["words"]), "instructions": r["instructions"],
                "image_sha256": r["image_sha256"], "source_sha256": r["source_sha256"], "halted": r["halted"],
                "engine": os.path.basename(roots[nid])}
        receipt = bytes.fromhex(sha256_of(crec))
        sl = list(inp["img"]["slots"])
        sl[1] = receipt
        sl[2] = pack_state(new_tick, int(r["native_witness"]), st["ref"], st["rows"], st["index"], flags, st["engine_lo64"], int(r["native_witness"]))
        blob = build_blob(new_tick, int(inp["img"]["rows_total"]) + len(inp["words"]), sl)
        info = _write_next(inp["path"], blob, new_tick, expected_sha256=inp["img"]["file_sha256"])
        crec.update({"ticked": True, "pages": info["pages"], "path": inp["path"], "fabric_changed": blob != inp["img"]["blob"]})
        if view:
            png = inp["path"][:-4] + ".png"
            ftif.render_view(inp["path"], png)
            crec["view"] = png
        with open(inp["path"][:-4] + ".json", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"schema": TICK_SCHEMA, **crec}, indent=2, sort_keys=True) + "\n")
        rec["containers"][inp["slot"]] = crec
    for nid in NODE_IDS:
        if nid in inputs and nid not in run.node_ids:
            lim = H.limits().get("no_c_toolchain")
            rec["containers"][inputs[nid]["slot"]] = {"ticked": False, "engine_bound": False,
                                                      "reason": (f"engine {nid} is not built on this host: {lim}" if lim and nid != "N_XLARGE"
                                                                 else f"engine {nid} not bound (run BUILD)")}
    # -- 4. the fabric container's picture --------------------------------------
    flp = live_path(berth, FABRIC_CONTAINER, base)
    if os.path.isfile(flp):
        fimg = _read(flp)
        fst = fimg["state"]
        new_tick = int(fst["tick"]) + 1
        fed_acc = vals[0] if unanimous and vals else 0
        # the hull face is ticked below; its result lands in the federation flags/tick after
        rec["_fed"] = {"path": flp, "img": fimg, "new_tick": new_tick, "fed_acc": fed_acc}
    frec = {"container": FABRIC_CONTAINER, "unanimous": unanimous, "all_intact": all_intact, "votes_bitmask": votes_mask,
            "participants": len(run.node_ids), "accumulators": {n: int(by_node[n]["native_witness"]) for n in run.node_ids},
            "collectives": {"allgather": ch_g.algorithm, "allreduce": ch_r.algorithm, "consistent": gathered_ok,
                            "min_equals_max": rmax.values[0] == rmin.values[0] if vals else None},
            "event_log": {"hash": ev_hash, "events": fin["event_log"]["events"], "replay": fin["event_log"]["replay_self_check"]},
            "profile": profile}
    # -- 5. the hull face: the studio's own reversible loop -------------------------
    face_rec: Dict[str, Any] = {"container": face_name(berth), "ticked": False}
    face_ok = False
    face_tick = 0
    if face:
        s, cname = _studio_face(berth)
        can_run, why = (H.hull_execution() if s is not None else (False, None))
        if s is None:
            face_rec["reason"] = cname
        elif not can_run:
            # a compile-only hull (no C toolchain): the face's picture is kept as it is, and this tick says so
            face_rec.update({"reason": why, "host_limited": True, "path": s.fabric_path(cname)})
        else:
            try:
                t = s.fabric_tick(cname, view=view)
                r2 = (t.get("registers") or {}).get("R2")
                face_ok = bool(t.get("ran")) and bool(t.get("ok")) and r2 == bseal["reference_witness"]
                face_tick = int(t.get("tick") or 0)
                face_rec.update({"ticked": bool(t.get("ran")), "tick": face_tick, "ok": face_ok, "R2": r2,
                                 "R2_equals_reference": r2 == bseal["reference_witness"], "tick_cell": (t.get("registers") or {}).get("R7"),
                                 "status_name": t.get("status_name"), "trap": t.get("trap"), "fabric_changed": t.get("fabric_changed"),
                                 "pages": t.get("pages"), "path": t.get("fabric"), "view": t.get("view"), "reason": t.get("reason")})
                if view and t.get("view") and os.path.isfile(t["view"]):
                    shutil.copyfile(t["view"], os.path.join(berth_state_dir(berth, base), mirror_name(berth, None, ".fabric.png")))
                face_rec["mirror"] = mirror_face(berth, base)
            except Exception as exc:  # noqa: BLE001
                face_rec.update({"error": f"{type(exc).__name__}: {exc}"})
    rec["hull_face"] = face_rec
    # hull cargo: the studio containers this berth carries, mounted in the hull, ticked on their own pictures
    if face and mounts:
        try:
            from . import hullmount as HM
            rec["hull_mounts"] = HM.tick_mounts(berth, view=view)
        except Exception as exc:  # noqa: BLE001
            rec["hull_mounts"] = {"error": f"{type(exc).__name__}: {exc}"}
    else:
        rec["hull_mounts"] = {}
    # -- 6. write the fabric container's picture --------------------------------------
    if "_fed" in rec:
        fed = rec.pop("_fed")
        fimg, new_tick, fed_acc = fed["img"], fed["new_tick"], fed["fed_acc"]
        fst = fimg["state"]
        flags = ((F_UNANIMOUS if unanimous else 0) | (F_ALL_INTACT if all_intact else 0) | (F_REPLAY_OK if replay_ok else 0)
                 | (F_FACE_OK if face_ok else 0) | F_TICKED)
        accs = [int(by_node[n]["native_witness"]) if n in by_node else 0 for n in NODE_IDS]
        nflags = [((F_AGREE if by_node[n]["differential_agreement"] else 0) | (F_INTACT if inputs[n]["intact"] else 0)) if n in by_node else 0 for n in NODE_IDS]
        sl = list(fimg["slots"])
        sl[1] = bytes.fromhex(ev_hash)[:32].ljust(32, b"\0")
        sl[2] = pack_state(new_tick, fed_acc, fst["ref"], fst["rows"], len(run.node_ids), flags, votes_mask, face_tick)
        sl[3] = struct.pack("<8Q", *(accs + nflags))
        sl[4] = bytes.fromhex(ev_hash)[:32].ljust(32, b"\0") + struct.pack("<2Q", int(fin["event_log"]["events"]), 1 if gathered_ok else 0)
        blob = build_blob(new_tick, int(fimg["rows_total"]) + len(sealed_words) * len(run.node_ids), sl)
        info = _write_next(fed["path"], blob, new_tick, expected_sha256=fimg["file_sha256"])
        frec.update({"ticked": True, "tick": new_tick, "pages": info["pages"], "path": fed["path"], "fabric_changed": blob != fimg["blob"],
                     "fed_acc": fed_acc, "replay_ok": replay_ok, "face_ok": face_ok})
        if view:
            png = fed["path"][:-4] + ".png"
            ftif.render_view(fed["path"], png)
            frec["view"] = png
        with open(fed["path"][:-4] + ".json", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"schema": TICK_SCHEMA, **frec}, indent=2, sort_keys=True, default=str) + "\n")
    else:
        frec.update({"ticked": False, "reason": "no live image (no genesis)"})
    rec["containers"][FABRIC_CONTAINER] = frec
    ticked = [k for k, v in rec["containers"].items() if v.get("ticked")]
    mounts = rec.get("hull_mounts") or {}
    m_ticked = sum(1 for v in mounts.values() if isinstance(v, dict) and v.get("ticked"))
    rec["summary"] = {"containers_ticked": len(ticked) + (1 if face_rec.get("ticked") else 0),
                      "of": len(SLOTS) + (1 if face else 0),
                      "hull_mounts_ticked": m_ticked, "hull_mounts": len([k for k in mounts if k != "error"]),
                      "unanimous": unanimous, "all_intact": all_intact,
                      "hull_face_ok": face_ok if face else None, "event_log_hash": ev_hash, "replay_ok": replay_ok,
                      "wall_s": round(time.perf_counter() - t_start, 3)}
    # TICK_OK: every picture ticked (the hull face ticked, or not tickable here for a stated reason), the engines unanimous
    # and every declaration intact; TICK_DISAGREEMENT: every picture ticked but the engines disagree or a declaration was
    # not intact (with a single engine bound nobody can out-vote it, so the intact check is what reports a painted
    # declaration); TICK_INCOMPLETE otherwise
    complete = len(ticked) == len(SLOTS) and (face_ok or not face)
    native_ok = all(bool(by_node[n].get("differential_agreement")) and bool(by_node[n].get("halted")) for n in run.node_ids)
    mount_results = [v for k, v in mounts.items() if k != "error" and isinstance(v, dict)]
    mounts_ok = "error" not in mounts and all(v.get("ticked") and v.get("ok") for v in mount_results)
    rec["summary"].update({"native_ok": native_ok, "mounts_ok": mounts_ok})
    rec["verdict"] = ("TICK_OK" if complete and unanimous and all_intact and native_ok and replay_ok and mounts_ok
                      else "TICK_DISAGREEMENT" if complete and (not unanimous or not all_intact or not native_ok or not replay_ok)
                      else "TICK_INCOMPLETE")
    # the berth-level log
    os.makedirs(berth_state_dir(berth, base), exist_ok=True)
    with open(os.path.join(berth_state_dir(berth, base), "TICKS.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({k: v for k, v in rec.items() if k != "containers"} | {"containers": {k: {kk: vv for kk, vv in v.items() if kk in ("tick", "acc_out", "differential_agreement", "declaration_intact", "unanimous", "ticked", "R2_equals_reference")} for k, v in rec["containers"].items()}},
                            sort_keys=True, default=str) + "\n")
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, f"tick_{rec['utc'].replace(':', '').replace('.', '')}.json"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, indent=1, sort_keys=True, default=str) + "\n")
    return rec


# --------------------------------------------------------------------------
# looking at the fabric
# --------------------------------------------------------------------------

def status(berth: str, base: Optional[str] = None) -> Dict[str, Any]:
    ok, why = available()
    out: Dict[str, Any] = {"schema": STATUS_SCHEMA, "berth": berth, "available": ok, "containers": {}}
    if not ok:
        out["reason"] = why
        return out
    ftif = codec()
    for slot in SLOTS:
        g = genesis_path(berth, slot)
        lp = live_path(berth, slot, base)
        c: Dict[str, Any] = {"genesis": os.path.isfile(g), "live": os.path.isfile(lp), "path": lp}
        if os.path.isfile(lp):
            img = _read(lp)
            st = img["state"]
            c.update({"tick": st["tick"], "pages": img["pages"], "acc": st["acc"], "flags": st["flags"],
                      "identity": img["identity"], "frames": ftif.frames(lp)[:8]})
            if slot == FABRIC_CONTAINER:
                c.update({"unanimous": bool(st["flags"] & F_UNANIMOUS), "all_intact": bool(st["flags"] & F_ALL_INTACT),
                          "replay_ok": bool(st["flags"] & F_REPLAY_OK), "hull_face_ok": bool(st["flags"] & F_FACE_OK),
                          "votes_bitmask": st["engine_lo64"], "participants": st["index"]})
            else:
                c.update({"declaration_intact": bool(st["flags"] & F_INTACT), "agree": bool(st["flags"] & F_AGREE)})
        out["containers"][slot] = c
    s, cname = _studio_face(berth)
    if s is None:
        out["hull_face"] = {"available": False, "reason": cname}
    else:
        tif = s.fabric_path(cname)
        f: Dict[str, Any] = {"container": cname, "path": tif, "live": os.path.isfile(tif)}
        if os.path.isfile(tif):
            try:
                fr = s.fabric_frames(cname)
                r = ftif.read_tif(tif)
                parts = ftif.parse_blob(r["blob"])
                sh0 = bytes(parts["slots"][2])
                f.update({"tick": r["tick"], "pages": fr["pages"], "tick_cell": struct.unpack_from("<Q", sh0 + bytes(16), 0)[0],
                          "witness_cell": struct.unpack_from("<Q", sh0 + bytes(16), 8)[0]})
            except Exception as exc:  # noqa: BLE001
                f["error"] = f"{type(exc).__name__}: {exc}"
        out["hull_face"] = f
    return out


def views(berth: str, base: Optional[str] = None, scale: int = 16) -> Dict[str, Any]:
    ftif = codec()
    out: Dict[str, Any] = {"berth": berth, "views": {}}
    for slot in SLOTS:
        lp = live_path(berth, slot, base)
        if os.path.isfile(lp):
            png = lp[:-4] + ".png"
            out["views"][slot] = ftif.render_view(lp, png, scale=scale)
    s, cname = _studio_face(berth)
    if s is not None and os.path.isfile(s.fabric_path(cname)):
        v = s.fabric_view(cname, scale=scale)
        out["views"][cname] = v
        try:
            shutil.copyfile(v["view"], os.path.join(berth_state_dir(berth, base), mirror_name(berth, None, ".fabric.png")))
        except Exception:  # noqa: BLE001
            pass
    return out


def frames(berth: str, base: Optional[str] = None) -> Dict[str, Any]:
    ftif = codec()
    out: Dict[str, Any] = {"berth": berth, "containers": {}}
    for slot in SLOTS:
        lp = live_path(berth, slot, base)
        if os.path.isfile(lp):
            out["containers"][slot] = ftif.frames(lp)
    s, cname = _studio_face(berth)
    if s is not None and os.path.isfile(s.fabric_path(cname)):
        out["containers"][cname] = s.fabric_frames(cname).get("frames")
    return out


# --------------------------------------------------------------------------
# what VERIFY checks (non-mutating structural checks over the live images)
# --------------------------------------------------------------------------

def check_images(berth: str, base: Optional[str] = None, scratch: Optional[str] = None) -> Dict[str, Any]:
    """For every container: the genesis exists, is PA21FABTIF/1 and reversible; the live image
    exists, is reversible, its oldest page decodes to the genesis blob, its page count is
    tick + 1, and its declaration tiles are reported against the sealed words."""
    ftif = codec()
    sealed_words, bseal = _sealed_words(berth)
    scratch = scratch or os.path.join(E.runs_dir(), "_tifcheck")
    os.makedirs(scratch, exist_ok=True)
    out: Dict[str, Any] = {"containers": {}, "declaration_rows": len(sealed_words)}
    allok = True
    for slot in SLOTS:
        c: Dict[str, Any] = {}
        g = genesis_path(berth, slot)
        gj = os.path.join(genesis_dir(berth, slot), FABRIC_JSON)
        c["genesis_present"] = os.path.isfile(g) and os.path.isfile(gj)
        if not c["genesis_present"]:
            c["ok"] = False
            allok = False
            out["containers"][slot] = c
            continue
        grec = json.load(open(gj, encoding="utf-8"))
        gimg = _read(g)
        c["genesis_kind_ok"] = gimg["identity"].get("kind") == IDENTITY_KIND and gimg["identity"].get("container") == slot
        c["genesis_blob_sha256_matches_record"] = hashlib.sha256(gimg["blob"]).hexdigest() == grec["genesis"]["blob_sha256"]
        rt = ftif.validate_roundtrip(gimg["blob"], os.path.join(scratch, f"{berth}.{slot}.g.tif"))
        c["genesis_reversible"] = rt["reversible"]
        c["genesis_words_equal_sealed"] = (gimg["words"] == sealed_words) if slot != FABRIC_CONTAINER else None
        c["genesis_reference_matches_seal"] = gimg["state"]["ref"] == bseal["reference_witness"]
        lp = live_path(berth, slot, base)
        c["live_present"] = os.path.isfile(lp)
        if c["live_present"]:
            limg = _read(lp)
            rt2 = ftif.validate_roundtrip(limg["blob"], os.path.join(scratch, f"{berth}.{slot}.l.tif"))
            c["live_reversible"] = rt2["reversible"]
            c["live_tick"] = limg["state"]["tick"]
            c["live_pages"] = limg["pages"]
            c["pages_equal_tick_plus_one"] = limg["pages"] == limg["state"]["tick"] + 1
            # the oldest page is the genesis
            fr = ftif.load_frames(lp)
            oldest = fr[-1] if fr else None
            same_genesis = None
            if oldest is not None:
                tmp = os.path.join(scratch, f"{berth}.{slot}.oldest.tif")
                oldest.save(tmp, tiffinfo=oldest.encoderinfo.get("tiffinfo") if getattr(oldest, "encoderinfo", None) else None, compression="tiff_deflate")
                try:
                    ob = ftif.read_tif(tmp)["blob"]
                    same_genesis = (ob == gimg["blob"])
                except Exception:  # noqa: BLE001
                    same_genesis = False
            c["oldest_page_is_genesis"] = same_genesis
            c["declaration_intact"] = (limg["words"] == sealed_words) if slot != FABRIC_CONTAINER else bool(limg["state"]["flags"] & F_ALL_INTACT) if limg["state"]["tick"] else True
            c["identity_ok"] = limg["identity"].get("container") == slot and limg["identity"].get("berth") == berth
            c["ok"] = all(c.get(k) for k in ("genesis_kind_ok", "genesis_blob_sha256_matches_record", "genesis_reversible", "genesis_reference_matches_seal",
                                              "live_reversible", "pages_equal_tick_plus_one", "identity_ok")) and (c["oldest_page_is_genesis"] is not False) \
                and (c["genesis_words_equal_sealed"] is not False)
        else:
            c["ok"] = False
        allok = allok and c["ok"]
        out["containers"][slot] = c
    s, cname = _studio_face(berth)
    f: Dict[str, Any] = {"container": cname if s is not None else face_name(berth)}
    if s is None:
        f.update({"present": False, "reason": cname})
    else:
        tif = s.fabric_path(cname)
        f["present"] = os.path.isfile(tif)
        if f["present"]:
            r = ftif.read_tif(tif)
            rt3 = ftif.validate_roundtrip(r["blob"], os.path.join(scratch, f"{berth}.face.tif"))
            parts = ftif.parse_blob(r["blob"])
            sh0 = bytes(parts["slots"][2]) + bytes(16)
            f.update({"reversible": rt3["reversible"], "tick": r["tick"], "pages": r["pages"],
                      "tick_cell": struct.unpack_from("<Q", sh0, 0)[0], "witness_cell": struct.unpack_from("<Q", sh0, 8)[0],
                      "witness_cell_equals_reference": struct.unpack_from("<Q", sh0, 8)[0] == bseal["reference_witness"] if r["tick"] else None,
                      "tick_cell_equals_tick": struct.unpack_from("<Q", sh0, 0)[0] == r["tick"]})
            f["ok"] = f["reversible"] and (f["witness_cell_equals_reference"] is not False) and f["tick_cell_equals_tick"]
        else:
            f["ok"] = False
    out["hull_face"] = f
    out["ok"] = allok and bool(f.get("ok"))
    return out
