"""A berth: one project's own blank four-node-plus-fabric scaffold, loaded.

    berths/<name>/
      BERTH.json            UC/BERTH/1 -- identity, kind, source digest, cargo per node, seals
      SORT_LEDGER.json/.md  UC/SORT_LEDGER/1 -- one record per script: features, node, rule, why
      CARGO.pal             the cargo manifest as a PA-LCTL bundle, one row per script (sealed;
                            witnessed on the engines in 84-row segments)
      CARGO_SEAL.json       seal + reference witness + segment count
      BERTH.pal             the berth declared in <= 84 rows (federation, domains, the four
                            nodes with their cargo digests, links, topology, claims)
      BERTH_SEAL.json       seal + reference witness -- the studio face's expected R2
      studio/main.lctlc     the hull's container: BERTH.pal's witness in R2 + the field rows (the tick
                            cell advanced, the witness mirrored into cell 8) -- runs on the studio's .tif fabric
      studio/pa21app.json   name, version, expect {status OK, trap 0, R2 = reference}
      DF_Small/ DF_Medium/ DF_Large/ DF_Xtra_Large/     the hollow node slots
        SLOT.json           UC/NODE_SLOT/1 -- engine binding (hold container + pinned digests), cargo summary
        node/NODE.pal       this berth's declaration of this node (verifies, seals)
        cargo/...           the scripts sorted to this node, byte-identical, original relative paths
        cargo/CARGO_MANIFEST.json
        fabric/GENESIS.fabric.tif  fabric/FABRIC.json   this container's own .tif fabric at tick 0 (sealed)
        _fabric/            this container's live fabric image (state; outside the seal; made by BUILD/RUN)
        README.md  BUILD VERIFY RUN (+ .cmd)   -> the ship's uc.py
      DF_Fabric/
        SLOT.json  fabric/BERTH_FABRIC.pal (+ seal)  fabric/NODES.json  fabric/GENESIS.fabric.tif  fabric/FABRIC.json
        _fabric/   README.md  BUILD VERIFY RUN
      _fabric/              the berth's tick log and the hull face's view (state; outside the seal)
      README.md
      SHA256SUMS.txt        every file of the berth (the _fabric/ state directories excepted)

Nothing in a berth is a VM: the engines live once, in the hold. A berth
*binds* them by digest, exactly as DF_Fabric binds its sibling nodes.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
from . import strictjson as json
import os
import shutil
import tempfile
import zipfile
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import (UC_RELEASE, DF_RELEASE_EXPECTED, NODE_IDS, NODE_CONTAINER, FABRIC_CONTAINER, SLOTS,
               BERTH_KINDS, SEGMENT_ROWS, BERTH_PAL_MAX_ROWS, ShipError, Refusal, face_container_name)
from . import sorter
from . import ucmanifest as M
from . import engines as E
from . import tif_fabric as TF
from . import hullmount as HM
from . import safety as SAFE

BERTH_NAME_RE = __import__("re").compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")

#: Portable storage. A script's identity is its original relative path (the ledger, CARGO.pal, the
#: manifests and every gate speak that path). Its bytes are normally stored under that same path in
#: its slot's cargo/ -- unless that path cannot exist on every host the ship must sail on: two source
#: paths that differ only by case (one file on a case-insensitive filesystem such as NTFS by default),
#: or a stored path so long that a Windows extraction (MAX_PATH 260) would fail. Such a script is
#: stored under an alias, `cargo/_alias/<sha256(path)[:16]><ext>`, and the ledger records `stored_as`
#: and why. Nothing else changes: same bytes, same identity, same sort.
#:
#: The budget is measured on the DELIVERED path -- the package folder the archive unpacks to, plus
#: `berths/<name>/<slot>/cargo/<path>` -- because that is what a host has to hold. Windows' MAX_PATH
#: is 260 characters for the whole absolute path, and Windows Explorer's own zip extractor does not
#: lift it even where the registry does (Python does): extracting `X.zip` into a folder Explorer
#: names after the archive can easily spend 90 characters before the first delivered byte. 140 leaves
#: room for that and more (a 119-character destination), which is why the budget is 140 and not 250.
PACKAGE_DIR = "Unikernel_Containership"   # the folder the delivered archive unpacks to
DELIVERED_PATH_BUDGET = 140       # <package>/berths/<name>/<slot>/cargo/<path>, in characters
STORED_PATH_BUDGET = DELIVERED_PATH_BUDGET - len(PACKAGE_DIR) - 1   # the same budget, ship-relative
ALIAS_DIR = "_alias"


def stored_alias(rel: str) -> str:
    ext = os.path.splitext(rel)[1]
    if len(ext) > 12 or not __import__("re").fullmatch(r"\.[A-Za-z0-9_.-]+", ext or ".x"):
        ext = ""
    return f"{ALIAS_DIR}/{hashlib.sha256(rel.encode('utf-8')).hexdigest()[:16]}{ext}"


def stored_path_of(rec: dict) -> str:
    """Where a ledger record's bytes live under its slot's cargo/ (the alias if it has one)."""
    return rec.get("stored_as") or rec["path"]


def cargo_disk_path(berth: str, path: str) -> Optional[str]:
    """The on-disk cargo file for an original relative path, through the berth's ledger."""
    lp = os.path.join(berth_dir(berth), "SORT_LEDGER.json")
    if not os.path.isfile(lp):
        return None
    led = json.load(open(lp, encoding="utf-8"))
    for r in led["records"]:
        if r["path"] == path:
            return SAFE.contained_path(berth_dir(berth), NODE_CONTAINER[r["node"]] + "/cargo/" + stored_path_of(r))
    return None
SOURCE_SKIP_DIRS = {"__pycache__", ".git", ".build", "_runs", "_engines", "_studio", "_scratch", ".DS_Store"}
SOURCE_SKIP_SUFFIX = (".pyc",)

DOMAIN_OF = {"N_SMALL": "D_BR", "N_MEDIUM": "D_BR", "N_LARGE": "D_BR", "N_XLARGE": "D_QVM"}
GROUP_OF = {"N_SMALL": "G_BR3", "N_MEDIUM": "G_ISA41", "N_LARGE": "G_BR11", "N_XLARGE": "G_QVM1"}
WORKER_OF = {"N_SMALL": "W_SMALL", "N_MEDIUM": "W_MEDIUM", "N_LARGE": "W_LARGE", "N_XLARGE": "W_XLARGE"}
DIALECT_OF = {"N_SMALL": "MSSL_ASM-1", "N_MEDIUM": "LCTLC_1.1", "N_LARGE": "LCTLC_1.2", "N_XLARGE": "LCTLC_1.0"}
LINKS = [("N_SMALL", "N_MEDIUM"), ("N_SMALL", "N_LARGE"), ("N_SMALL", "N_XLARGE"),
         ("N_MEDIUM", "N_LARGE"), ("N_MEDIUM", "N_XLARGE"), ("N_LARGE", "N_XLARGE")]

PAL_HEADER = ("#PA-LCTL/1.6\n#PROFILE pa.lctl.quantum.parallel.distributed\n#NETWORK deny\n#BACKEND none\n"
              "#COLUMNS ROW¦FACE¦LANE¦QSPACE¦OP¦OUT¦CTRL¦A¦B¦PARAM¦TYPE¦BASIS¦REGIME¦ASSUME¦ERROR¦RESOURCE¦CONF¦PROOF¦DOMAIN¦NODE¦LINK¦FAMILY\n")

LAUNCHER_SH = """#!/bin/sh
# {title} -- delegates to the ship (uc.py {cmd}). Offline; NETWORK=deny.
set -eu
HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PY="${{PYTHON:-python3}}"
exec "$PY" -B "$HERE/{up}/uc.py" {cmd} "$@"
"""
LAUNCHER_CMD = """@echo off
REM {title} -- delegates to the ship (uc.py {cmd}).
setlocal
set "HERE=%~dp0"
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%{up_win}\\uc.py" {cmd} %*
endlocal
"""


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def berths_dir() -> str:
    return os.path.join(E.ship_root(), "berths")


def berth_dir(name: str) -> str:
    SAFE.validate_name(name)
    return SAFE.contained_path(E.ship_root(), "berths/" + name)


def _write(path: str, text: str, mode: Optional[int] = None) -> None:
    SAFE.atomic_write(path, text, mode=mode)


def _write_json(path: str, obj: Any) -> None:
    _write(path, json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")


def _esc(s: str) -> str:
    """Escape for an ASSUME cell: the cell separator and the list separator."""
    return s.replace("%", "%25").replace("¦", "%A6").replace(";", "%3B").replace("\n", "%0A")


def _unesc(s: str) -> str:
    return s.replace("%0A", "\n").replace("%3B", ";").replace("%A6", "¦").replace("%25", "%")


# --------------------------------------------------------------------------
# ingest
# --------------------------------------------------------------------------

def ingest(source: str) -> Tuple[str, Dict[str, Any], Optional[str]]:
    """Return (root_dir, source_record, tempdir_to_cleanup)."""
    src = os.path.abspath(os.path.expanduser(source))
    if os.path.isfile(src) and zipfile.is_zipfile(src):
        td = tempfile.mkdtemp(prefix="uc-ingest-")
        try:
            with zipfile.ZipFile(src) as z:
                mapping, prefix = SAFE.stage_zip(z, td)
            rec = {"kind": "zip", "path": src, "sha256": M.sha256_file(src), "bytes": os.path.getsize(src),
                   "archive_root": ("one top-level directory " + prefix) if prefix else "files at archive root",
                   "_archive_files": mapping}
            return td, rec, td
        except BaseException:
            shutil.rmtree(td, ignore_errors=True)
            raise
    if os.path.isdir(src):
        scripts = list_scripts(src)  # validate/bound before hashing or reading large inputs
        h = hashlib.sha256()
        for rel in scripts:
            h.update(f"{M.sha256_file(SAFE.contained_path(src, rel))}  {rel}\n".encode("utf-8"))
        return src, {"kind": "directory", "path": src, "tree_sha256": h.hexdigest(), "files": len(scripts),
                     "digest_scope": "eligible cargo only; SOURCE_SKIP_DIRS/SOURCE_SKIP_SUFFIX excluded"}, None
    raise Refusal(f"no such project source: {src}", {"source": source})


def list_scripts(root: str) -> List[str]:
    SAFE.reject_link(root)
    out = []
    total = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SOURCE_SKIP_DIRS)
        for dn in dns:
            SAFE.reject_link(os.path.join(dp, dn))
        for fn in sorted(fns):
            if fn.endswith(SOURCE_SKIP_SUFFIX) or fn in SOURCE_SKIP_DIRS:
                continue
            p = os.path.join(dp, fn)
            SAFE.reject_link(p)
            if not os.path.isfile(p):
                raise Refusal("non-regular source file", {"path": p})
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            SAFE.relative_path(rel)
            size = os.path.getsize(p)
            total += size
            if size > SAFE.DEFAULT_LIMITS.member_bytes or total > SAFE.DEFAULT_LIMITS.total_bytes or len(out) >= SAFE.DEFAULT_LIMITS.entries:
                raise Refusal("source exceeds cargo size/count budget", {"path": rel})
            out.append(rel)
    return sorted(out)


# --------------------------------------------------------------------------
# bundles
# --------------------------------------------------------------------------

def _decl_rows(berth: str, per_node: Dict[str, dict], source_rec: dict) -> List[str]:
    rows = [
        f"R000¦FEDERATION¦-¦-¦DECLARE_FEDERATION¦DF0¦-¦-¦-¦-¦federation¦-¦EXACT¦-¦-¦trust=LOCAL_TRUSTED;network=deny;backend=none;ship={UC_RELEASE};berth={berth}¦1.0¦BILL_OF_LADING¦-¦-¦-¦-",
        "R001¦FEDERATION¦-¦-¦DECLARE_DOMAIN¦D_BR¦-¦-¦-¦-¦execution_domain¦-¦EXACT¦-¦-¦lineage=BOTTLE_ROCKET;trust=LOCAL_TRUSTED¦1.0¦-¦-¦-¦-¦-",
        "R002¦FEDERATION¦-¦-¦DECLARE_DOMAIN¦D_QVM¦-¦-¦-¦-¦execution_domain¦-¦EXACT¦-¦-¦lineage=QUORUM_VM;trust=LOCAL_TRUSTED¦1.0¦-¦-¦-¦-¦-",
    ]
    r = 3
    for nid in NODE_IDS:
        pn = per_node[nid]
        rows.append(f"R{r:03d}¦TOPOLOGY¦-¦-¦DECLARE_NODE¦{nid}¦-¦-¦-¦-¦node¦-¦EXACT¦-¦-¦device=classical_vm;engine={NODE_CONTAINER[nid]};worker={WORKER_OF[nid]};group={GROUP_OF[nid]};dialect={DIALECT_OF[nid]};qubits=0;cargo_files={pn['count']};cargo_bytes={pn['bytes']};cargo_tree={pn['tree_sha256'][:16]}¦1.0¦{NODE_CONTAINER[nid]}_SLOT¦{DOMAIN_OF[nid]}¦-¦-¦-")
        r += 1
    return rows


def cargo_pal(berth: str, ledger: List[dict], per_node: Dict[str, dict], source_rec: dict) -> str:
    rows = _decl_rows(berth, per_node, source_rec)
    rows.append("R007¦TOPOLOGY¦-¦-¦DECLARE_TOPOLOGY¦T0¦-¦-¦-¦-¦topology¦-¦EXACT¦-¦-¦nodes=4;domains=2;qcapacity=0¦1.0¦-¦-¦-¦-¦-")
    base = 10
    for i, rec in enumerate(ledger):
        rid = f"R{base + i:05d}"
        assume = (f"path={_esc(rec['path'])};sha256={rec['sha256'][:16]};bytes={rec['bytes']};kind={rec['kind']};"
                  f"rule={rec['rule']};band={rec['complexity_band']}"
                  + (f";stored={_esc(rec['stored_as'])}" if rec.get("stored_as") else ""))
        rows.append(f"{rid}¦LEDGER¦-¦-¦NOTE¦-¦-¦-¦-¦-¦proof_record¦-¦EXACT¦{assume}¦-¦cargo=1¦1.0¦SORT_LEDGER¦{DOMAIN_OF[rec['node']]}¦{rec['node']}¦-¦-")
    return PAL_HEADER + "\n".join(rows) + "\n"


def berth_pal(berth: str, kind: str, ledger: List[dict], per_node: Dict[str, dict], source_rec: dict,
              policy_sha: str, cargo_seal: str) -> str:
    rows = _decl_rows(berth, per_node, source_rec)
    r = 10
    for i, (a, b) in enumerate(LINKS):
        dom = "D_BR" if DOMAIN_OF[a] == DOMAIN_OF[b] == "D_BR" else "-"
        rows.append(f"R{r:03d}¦TOPOLOGY¦-¦-¦DECLARE_LINK¦C{i}¦-¦{a}¦{b}¦-¦classical_channel¦-¦EXACT¦-¦-¦transport=local_process;alpha_ticks=1;beta_bytes_per_tick=1000000¦1.0¦-¦{dom}¦-¦-¦-")
        r += 1
    rows.append("R020¦TOPOLOGY¦-¦-¦DECLARE_TOPOLOGY¦T0¦-¦-¦-¦-¦topology¦-¦EXACT¦-¦-¦nodes=4;domains=2;links=6;qcapacity=0¦1.0¦-¦-¦-¦-¦-")
    src_digest = source_rec.get("sha256") or source_rec.get("tree_sha256") or "-"
    rows.append(f"R030¦RESOURCE¦-¦-¦CLAIM¦-¦-¦-¦-¦-¦resource_report¦-¦EXACT¦kind={kind};source={_esc(os.path.basename(str(source_rec.get('path'))))}¦-¦cargo_files={len(ledger)};cargo_bytes={sum(x['bytes'] for x in ledger)};source_sha256={src_digest[:16]};policy_sha256={policy_sha[:16]};cargo_seal={cargo_seal[:16]}¦1.0¦SORT_LEDGER¦-¦-¦-¦-")
    r = 31
    for nid in NODE_IDS:
        pn = per_node[nid]
        rows.append(f"R{r:03d}¦EVIDENCE¦-¦-¦CLAIM¦-¦-¦-¦-¦-¦proof_record¦-¦EXACT¦-¦-¦cargo_files={pn['count']};cargo_bytes={pn['bytes']};cargo_tree={pn['tree_sha256'][:16]};rules={_esc('|'.join(f'{k}={v}' for k, v in sorted(pn['rules'].items())))}¦1.0¦{NODE_CONTAINER[nid]}_CARGO_MANIFEST¦{DOMAIN_OF[nid]}¦{nid}¦-¦CLASSICAL_REPLICA_PARALLEL")
        r += 1
    rows.append("R040¦MODEL¦-¦-¦NOTE¦-¦-¦-¦-¦-¦proof_record¦-¦EXACT¦unit_of_distribution=sealed_rows_not_images;engines_in_hold=4;berth_holds_no_vm=true¦-¦-¦1.0¦ARCHITECTURE¦-¦-¦-¦-")
    rows.append("R041¦MODEL¦-¦-¦NOTE¦-¦-¦-¦-¦-¦proof_record¦-¦IMPOSSIBLE¦cross_machine=BLOCKED;network=deny;physical_outputs=BLOCKED_EXTERNAL_AUTHORITY;qubits=0¦-¦-¦1.0¦ARCHITECTURE¦-¦-¦-¦-")
    rows.append("R050¦LEDGER¦-¦-¦EMIT_LEDGER¦-¦-¦-¦-¦-¦proof_record¦-¦EXACT¦-¦-¦ledger=SORT_LEDGER;bill_of_lading=BILL_OF_LADING;studio_face=main.lctlc¦1.0¦BERTH_JSON¦-¦-¦-¦-")
    return PAL_HEADER + "\n".join(rows) + "\n"


def slot_node_pal(berth: str, nid: str, pn: dict) -> str:
    rows = [
        f"R000¦FEDERATION¦-¦-¦DECLARE_FEDERATION¦DF0¦-¦-¦-¦-¦federation¦-¦EXACT¦-¦-¦trust=LOCAL_TRUSTED;network=deny;backend=none;ship={UC_RELEASE};berth={berth}¦1.0¦BILL_OF_LADING¦-¦-¦-¦-",
        f"R001¦FEDERATION¦-¦-¦DECLARE_DOMAIN¦{DOMAIN_OF[nid]}¦-¦-¦-¦-¦execution_domain¦-¦EXACT¦-¦-¦trust=LOCAL_TRUSTED¦1.0¦-¦-¦-¦-¦-",
        f"R002¦TOPOLOGY¦-¦-¦DECLARE_NODE¦{nid}¦-¦-¦-¦-¦node¦-¦EXACT¦-¦-¦device=classical_vm;engine={NODE_CONTAINER[nid]};worker={WORKER_OF[nid]};group={GROUP_OF[nid]};dialect={DIALECT_OF[nid]};qubits=0¦1.0¦SLOT_JSON¦{DOMAIN_OF[nid]}¦-¦-¦-",
        f"R003¦TOPOLOGY¦-¦-¦DECLARE_TOPOLOGY¦T_{nid[2:]}¦-¦-¦-¦-¦topology¦-¦EXACT¦-¦-¦nodes=1;domains=1;qcapacity=0¦1.0¦-¦-¦-¦-¦-",
        f"R010¦RESOURCE¦-¦-¦CLAIM¦-¦-¦-¦-¦-¦resource_report¦-¦EXACT¦-¦-¦cargo_files={pn['count']};cargo_bytes={pn['bytes']};cargo_tree={pn['tree_sha256'][:16]}¦1.0¦CARGO_MANIFEST¦{DOMAIN_OF[nid]}¦{nid}¦-¦-",
        f"R011¦RESOURCE¦-¦-¦CLAIM¦-¦-¦-¦-¦-¦resource_claim¦-¦EXACT¦-¦-¦cpu_slots=1;qpu_slots=0;ebit_budget=0¦1.0¦SLOT_JSON¦{DOMAIN_OF[nid]}¦{nid}¦-¦-",
        f"R020¦MODEL¦-¦-¦NOTE¦-¦-¦-¦-¦-¦proof_record¦-¦EXACT¦engine_bound_by_digest=true;slot_holds_no_vm=true;runnable_cargo=dialect_{DIALECT_OF[nid]}_and_pal¦-¦-¦1.0¦SLOT_JSON¦{DOMAIN_OF[nid]}¦{nid}¦-¦-",
        f"R030¦LEDGER¦-¦-¦EMIT_LEDGER¦-¦-¦-¦-¦-¦proof_record¦-¦EXACT¦-¦-¦ledger=CARGO_MANIFEST¦1.0¦SORT_LEDGER¦{DOMAIN_OF[nid]}¦{nid}¦-¦-",
    ]
    return PAL_HEADER + "\n".join(rows) + "\n"


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def _seal_bundle(text: str, name: str) -> Dict[str, Any]:
    b = E.bind()
    lang, W = b["lang"], b["witness"]
    prog, diags = lang.parse(text)
    if prog is None:
        raise ShipError(f"{name} did not parse", {"diagnostics": [d.as_dict() for d in diags]})
    v = lang.verify(prog)
    if not v.ok:
        raise ShipError(f"{name} did not verify", {"diagnostics": [d.as_dict() for d in v.diagnostics]})
    words = W.words_of(prog)
    return {"seal": prog.seal(), "rows": len(prog.rows), "reference_witness": W.reference_witness_words(words),
            "segments_of_84": (len(words) + SEGMENT_ROWS - 1) // SEGMENT_ROWS, "warnings": [d.as_dict() for d in v.diagnostics],
            "_words": words}


def _load_uncommitted(source: str, name: str, kind: str, dest: str, *, notes: Optional[str] = None,
                      on_event=None) -> Dict[str, Any]:
    """Break a project into scripts, sort each into a node, and give the
    project its own blank scaffold holding the sorted cargo."""
    if not BERTH_NAME_RE.match(name or ""):
        raise Refusal("a berth name must start with a letter and use letters, digits, dot, dash or underscore",
                      {"name": name})
    if kind not in BERTH_KINDS:
        raise Refusal(f"kind must be one of {BERTH_KINDS}", {"kind": kind})
    emit = on_event or (lambda ev: None)
    root, source_rec, td = ingest(source)
    archive_files = source_rec.pop("_archive_files", None)
    try:
        b = E.bind()
        W = b["witness"]
        scripts = (sorted(p for p in archive_files if not any(x in SOURCE_SKIP_DIRS for x in p.split("/"))
                          and not p.endswith(SOURCE_SKIP_SUFFIX)) if archive_files is not None else list_scripts(root))
        if not scripts:
            raise Refusal("the project holds no scripts to sort", {"source": source})
        emit({"phase": "sort", "scripts": len(scripts)})
        ledger: List[dict] = []
        per_node: Dict[str, dict] = {n: {"count": 0, "bytes": 0, "rules": {}, "kinds": {}, "_h": hashlib.sha256(), "files": []}
                                     for n in NODE_IDS}
        os.makedirs(dest)
        seen_lower: Dict[str, str] = {}
        stored_seen: set[str] = set()
        aliases: List[dict] = []
        for rel in scripts:
            source_path = archive_files[rel] if archive_files is not None else SAFE.contained_path(root, rel)
            with open(source_path, "rb") as fh:
                data = fh.read(SAFE.DEFAULT_LIMITS.member_bytes + 1)
            if len(data) > SAFE.DEFAULT_LIMITS.member_bytes:
                raise Refusal("source file grew beyond the cargo budget", {"path": rel})
            rec = sorter.sort_script(rel, data)
            # portable storage: alias a path that cannot exist on every host (see STORED_PATH_BUDGET)
            reasons = []
            for i in range(1, len(rel.split("/")) + 1):
                prefix = "/".join(rel.split("/")[:i])
                low = SAFE.portable_key(prefix)
                if low in seen_lower and seen_lower[low] != prefix:
                    reasons.append("case/Unicode-normalization collision in source path")
                seen_lower.setdefault(low, prefix)
            if SAFE.windows_unsafe(rel):
                reasons.append("Windows-reserved name or non-portable component")
            if SAFE.portable_key(rel) == "cargo_manifest.json" or SAFE.portable_key(rel.split("/")[0]) == ALIAS_DIR:
                reasons.append("reserved cargo metadata or alias namespace")
            delivered = f"{PACKAGE_DIR}/berths/{name}/{NODE_CONTAINER[rec['node']]}/cargo/{rel}"
            if len(delivered) > DELIVERED_PATH_BUDGET:
                reasons.append(f"the delivered path would be {len(delivered)} characters, over the "
                               f"{DELIVERED_PATH_BUDGET}-character budget (Windows MAX_PATH is 260 for the whole path, "
                               f"and Explorer's zip extractor does not lift it)")
            if reasons:
                rec["stored_as"] = stored_alias(rel)
                rec["stored_reason"] = "; ".join(reasons)
                aliases.append({"path": rel, "stored_as": rec["stored_as"], "why": rec["stored_reason"], "node": rec["node"]})
            stored = stored_path_of(rec)
            if len(f"{PACKAGE_DIR}/berths/{name}/{NODE_CONTAINER[rec['node']]}/cargo/{stored}") > DELIVERED_PATH_BUDGET:
                raise Refusal("even an aliased path exceeds the portable budget; use a shorter berth name", {"name": name, "path": rel})
            storage_key = SAFE.portable_key(NODE_CONTAINER[rec["node"]] + "/" + stored)
            if storage_key in stored_seen:
                raise Refusal("cargo alias/storage collision", {"path": rel})
            stored_seen.add(storage_key)
            ledger.append(rec)
            pn = per_node[rec["node"]]
            pn["count"] += 1
            pn["bytes"] += rec["bytes"]
            pn["rules"][rec["rule"]] = pn["rules"].get(rec["rule"], 0) + 1
            pn["kinds"][rec["kind"]] = pn["kinds"].get(rec["kind"], 0) + 1
            pn["_h"].update(f"{rec['sha256']}  {rel}\n".encode("utf-8"))
            frec = {"path": rel, "bytes": rec["bytes"], "sha256": rec["sha256"], "kind": rec["kind"], "rule": rec["rule"]}
            if rec.get("stored_as"):
                frec["stored_as"] = rec["stored_as"]
            pn["files"].append(frec)
            out = os.path.join(dest, NODE_CONTAINER[rec["node"]], "cargo", stored_path_of(rec))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, "wb") as fh:
                fh.write(data)
        for n in NODE_IDS:
            per_node[n]["tree_sha256"] = per_node[n].pop("_h").hexdigest()
        policy = sorter.policy_record()
        policy_sha = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()

        # -- bundles --------------------------------------------------------
        cpal = cargo_pal(name, ledger, per_node, source_rec)
        cseal = _seal_bundle(cpal, "CARGO.pal")
        bpal = berth_pal(name, kind, ledger, per_node, source_rec, policy_sha, cseal["seal"])
        bseal = _seal_bundle(bpal, "BERTH.pal")
        if bseal["rows"] > BERTH_PAL_MAX_ROWS:
            raise ShipError("BERTH.pal exceeds one lowering", {"rows": bseal["rows"]})
        _write(os.path.join(dest, "CARGO.pal"), cpal)
        _write(os.path.join(dest, "BERTH.pal"), bpal)
        _write_json(os.path.join(dest, "CARGO_SEAL.json"), {"schema": "UC/BUNDLE_SEAL/1", "bundle": "CARGO.pal",
                    **{k: v for k, v in cseal.items() if k != "_words"}, "note": "witnessed on the engines in 84-row segments (replica + pipeline)"})
        _write_json(os.path.join(dest, "BERTH_SEAL.json"), {"schema": "UC/BUNDLE_SEAL/1", "bundle": "BERTH.pal",
                    **{k: v for k, v in bseal.items() if k != "_words"}, "note": "one lowering on every engine; the studio face expects R2 == reference_witness"})

        # -- studio face: the witness as a field program on the studio's .tif fabric ---------
        unit_id = f"uc.berth.{name.replace('-', '_')}"
        face = face_container_name(name)
        lctlc = TF.hull_face_source(bseal["_words"], unit_id=unit_id)
        _write(os.path.join(dest, "studio", "main.lctlc"), lctlc)
        _write_json(os.path.join(dest, "studio", "pa21app.json"),
                    {"name": face, "version": "2.0.0", "entry": "src/main.lctlc", "budget": 4096,
                     "pa21": {"requires_operational": []},
                     "expect": {"status_name": "OK", "trap": 0, "registers": {"R2": bseal["reference_witness"]}}})
        _write_json(os.path.join(dest, "studio", "STUDIO_FACE.json"),
                    {"schema": "UC/STUDIO_FACE/1", "berth": name, "container_name": face,
                     "source": "studio/main.lctlc", "source_sha256": M.sha256_bytes(lctlc.encode("utf-8")),
                     "dialect": "LCTLC/1.2 (columned-lctl/4.3) -- the hull's runtime is the BOTTLE ROCKET 4.7.0 VM",
                     "lowering": "UC/FIELD_WITNESS_LOWERING/1 of BERTH.pal (unit " + unit_id + "): the DF row-sequence witness in R2, "
                                 "then STORAGE_READ object 0, tick cell (cell 0) += 1, witness into cell 8, STORAGE_WRITE object 0",
                     "expected_R2": bseal["reference_witness"], "berth_seal": bseal["seal"],
                     "fabric": {"image": f"_studio/state/{face}.fabric.tif", "kind": "PA21FABTIF/1",
                                "how": "studio fabric init creates it; every uc run / studio fabric tick reads it as the run's state, "
                                       "executes this program on the hull's VM against it, and appends the result as a new page"},
                     "how": "uc build registers this source as a studio container (studio new --from), builds it, captures its "
                            "expectation, checks R2 against BERTH_SEAL.reference_witness and creates the container's fabric image; "
                            "studio test then keeps it honest"})

        # -- slots ----------------------------------------------------------
        pins = E.hold_pins()
        for nid in NODE_IDS:
            slot = os.path.join(dest, NODE_CONTAINER[nid])
            os.makedirs(os.path.join(slot, "cargo"), exist_ok=True)
            pn = per_node[nid]
            _write_json(os.path.join(slot, "cargo", "CARGO_MANIFEST.json"),
                        {"schema": "UC/CARGO_MANIFEST/1", "berth": name, "node_id": nid, "files": pn["files"],
                         "count": pn["count"], "bytes": pn["bytes"], "tree_sha256": pn["tree_sha256"],
                         "rules": pn["rules"], "kinds": pn["kinds"]})
            npal = slot_node_pal(name, nid, pn)
            nseal = _seal_bundle(npal, f"{NODE_CONTAINER[nid]}/node/NODE.pal")
            _write(os.path.join(slot, "node", "NODE.pal"), npal)
            _write_json(os.path.join(slot, "node", "NODE_SEAL.json"), {"schema": "UC/BUNDLE_SEAL/1", "bundle": "node/NODE.pal",
                        **{k: v for k, v in nseal.items() if k != "_words"}})
            _write_json(os.path.join(slot, "SLOT.json"), {
                "schema": "UC/NODE_SLOT/1", "uc_release": UC_RELEASE, "berth": name, "slot": NODE_CONTAINER[nid], "node_id": nid,
                "engine": {"hold_container": f"hold/{NODE_CONTAINER[nid]}.zip",
                           "zip_sha256": (pins.get("zips") or {}).get(f"{NODE_CONTAINER[nid]}.zip"),
                           "extracted_at": f"_engines/{NODE_CONTAINER[nid]}", "bound_by": "digest (fabric/NODES.json of the hold's DF_Fabric)"},
                "cargo": {"count": pn["count"], "bytes": pn["bytes"], "tree_sha256": pn["tree_sha256"], "rules": pn["rules"], "kinds": pn["kinds"]},
                "holds_vm": False, "trust_domain": "LOCAL_TRUSTED", "qubits": 0,
                "runnable_cargo": f"scripts of kind {DIALECT_OF[nid]} (and .pal bundles) can be executed on this engine with RUN"})
            _write(os.path.join(slot, "README.md"),
                   f"# {name} / {NODE_CONTAINER[nid]} -- node slot {nid}\n\nHollow slot of berth `{name}` ({UC_RELEASE}). It holds no VM: the engine "
                   f"is `hold/{NODE_CONTAINER[nid]}.zip`, extracted and built once under `_engines/`. This slot holds the {pn['count']} script(s) "
                   f"({pn['bytes']} bytes) the sort policy placed on `{nid}` (rules {json.dumps(pn['rules'], sort_keys=True)}), under `cargo/` "
                   f"with their original relative paths, plus `cargo/CARGO_MANIFEST.json`, `node/NODE.pal` (this berth's declaration of the node, sealed), `SLOT.json`, "
                   f"and this container's own .tif fabric: `fabric/GENESIS.fabric.tif` + `fabric/FABRIC.json` (tick 0, sealed) and, once BUILD or RUN made it, "
                   f"the live image `_fabric/{NODE_CONTAINER[nid]}.fabric.tif` (state, outside the seal): tile 0 the state, tiles 1-2 the berth's declaration "
                   f"as row-word cells, tile 3 the seals. A tick (`../../../uc.py run {name}`) reads it, executes it on this engine, and appends a frame.\n\n"
                   f"```\n./RUN <cargo path>       run one runnable cargo script (dialect {DIALECT_OF[nid]}, or a .pal bundle) on the engine\n"
                   f"./VERIFY                 the berth battery (sort ledger re-derived, seals, witnesses on the engines, studio face)\n"
                   f"./BUILD                  the ship's BUILD (extract + build engines, install the hull)\n```\n")
            for base, cmd in (("BUILD", "build"), ("VERIFY", f"verify {name}"), ("RUN", f"slot-run {name} {NODE_CONTAINER[nid]}")):
                _write(os.path.join(slot, base), LAUNCHER_SH.format(title=f"{name}/{NODE_CONTAINER[nid]}/{base}", cmd=cmd, up="../../.."), 0o755)
                _write(os.path.join(slot, base + ".cmd"), LAUNCHER_CMD.format(title=f"{name}\\{NODE_CONTAINER[nid]}\\{base}.cmd", cmd=cmd, up_win="..\\..\\.."))
        fslot = os.path.join(dest, FABRIC_CONTAINER)
        os.makedirs(os.path.join(fslot, "fabric"), exist_ok=True)
        _write(os.path.join(fslot, "fabric", "BERTH_FABRIC.pal"), bpal)
        _write_json(os.path.join(fslot, "fabric", "BERTH_FABRIC_SEAL.json"), {"schema": "UC/BUNDLE_SEAL/1", "bundle": "fabric/BERTH_FABRIC.pal",
                    "identical_to": "../BERTH.pal", **{k: v for k, v in bseal.items() if k != "_words"}})
        _write_json(os.path.join(fslot, "fabric", "NODES.json"), {
            "schema": "UC/BERTH_NODES/1", "berth": name,
            "engines": [{"node_id": n, "hold_container": f"hold/{NODE_CONTAINER[n]}.zip",
                         "zip_sha256": (pins.get("zips") or {}).get(f"{NODE_CONTAINER[n]}.zip"),
                         "slot": NODE_CONTAINER[n], "cargo_files": per_node[n]["count"]} for n in NODE_IDS],
            "fabric_engine": {"hold_container": f"hold/{FABRIC_CONTAINER}.zip", "zip_sha256": (pins.get("zips") or {}).get(f"{FABRIC_CONTAINER}.zip")},
            "note": "the berth's fabric programs (replica, pipeline, bsp) run on the hold's engines through the hold's dfabric runtime"})
        _write_json(os.path.join(fslot, "SLOT.json"), {"schema": "UC/FABRIC_SLOT/1", "uc_release": UC_RELEASE, "berth": name, "slot": FABRIC_CONTAINER,
                    "bundles": {"BERTH.pal": bseal["seal"], "CARGO.pal": cseal["seal"]},
                    "programs": ["replica", "pipeline", "bsp"], "holds_vm": False})
        _write(os.path.join(fslot, "README.md"),
               f"# {name} / DF_Fabric -- fabric slot\n\nThe berth's fabric: `fabric/BERTH_FABRIC.pal` (identical to `../BERTH.pal`), the engine "
               f"registry `fabric/NODES.json`, this container's own .tif fabric (`fabric/GENESIS.fabric.tif` + `fabric/FABRIC.json`, sealed; "
               f"the live image `_fabric/DF_Fabric.fabric.tif` is state, outside the seal) and the three launchers. `./RUN` ticks the berth's fabric: "
               f"every container's picture is read, executed on its engine, and written back as a new frame; this container's picture records the "
               f"federation vote, the four accumulators and the sealed event log. `./RUN --sealed` executes the sealed bundles instead: BERTH.pal in one "
               f"lowering per engine (replica + BSP), CARGO.pal ({cseal['rows']} rows) in {cseal['segments_of_84']} segment(s) (replica per engine, and "
               f"a pipeline chained across engines).\n")
        for base, cmd in (("BUILD", "build"), ("VERIFY", f"verify {name}"), ("RUN", f"run {name}")):
            _write(os.path.join(fslot, base), LAUNCHER_SH.format(title=f"{name}/DF_Fabric/{base}", cmd=cmd, up="../../.."), 0o755)
            _write(os.path.join(fslot, base + ".cmd"), LAUNCHER_CMD.format(title=f"{name}\\DF_Fabric\\{base}.cmd", cmd=cmd, up_win="..\\..\\.."))

        # -- every container's own .tif fabric: the sealed genesis --------------------------
        zips = (pins.get("zips") or {})
        engine_shas = {slot: zips.get(f"{slot}.zip") for slot in SLOTS}
        fabric_rec = TF.make_genesis(dest, name, bseal["_words"], bseal["reference_witness"], bseal["seal"], cseal["seal"],
                                     {n: per_node[n]["tree_sha256"] for n in NODE_IDS}, engine_shas, policy_sha)

        # -- ledger, berth record, README, sums ------------------------------------
        _write_json(os.path.join(dest, "SORT_LEDGER.json"), {
            "schema": sorter.SCHEMA, "uc_release": UC_RELEASE, "berth": name, "kind": kind, "policy": policy,
            "policy_sha256": policy_sha, "source": source_rec, "scripts": len(ledger),
            "portable_storage": {"stored_path_budget": STORED_PATH_BUDGET, "delivered_path_budget": DELIVERED_PATH_BUDGET,
                                 "package_dir": PACKAGE_DIR, "alias_dir": ALIAS_DIR, "aliased": aliases,
                                 "rule": "a script's identity is its original path; its bytes are stored under an alias only when that path "
                                         "cannot exist on every host (case collision, or a stored path over the budget); the ledger, "
                                         "CARGO.pal (stored=) and the cargo manifest record the alias"},
            "per_node": {n: {k: v for k, v in per_node[n].items() if k != "files"} for n in NODE_IDS},
            "records": ledger})
        _write(os.path.join(dest, "SORT_LEDGER.md"), sort_ledger_md(name, kind, ledger, per_node, source_rec))
        # hull cargo: studio containers carried in the cargo (re-assemblable from the slots, mountable in the hull)
        try:
            hull_cargo = [{k: m.get(k) for k in ("name", "prefix", "version", "listed", "complete", "picture", "picture_node",
                                                   "pubkey", "pubkey_sha256", "entry", "image", "state", "devices", "built_by", "digests")}
                          | {"files": [{"path": f["path"], "slot": f.get("slot"), "rule": f.get("rule")} for f in m["files"]]}
                          for m in HM.detect(name, ledger={"records": ledger}, root=dest)]
        except Exception as exc:  # noqa: BLE001
            hull_cargo = [{"error": f"{type(exc).__name__}: {exc}"}]
        berth_rec = {
            "schema": "UC/BERTH/1", "uc_release": UC_RELEASE, "df_release": DF_RELEASE_EXPECTED, "berth": name, "kind": kind,
            "loaded_utc": utcnow(), "source": source_rec, "notes": notes,
            "scripts": len(ledger), "bytes": sum(x["bytes"] for x in ledger),
            "per_node": {n: {"count": per_node[n]["count"], "bytes": per_node[n]["bytes"], "tree_sha256": per_node[n]["tree_sha256"],
                             "rules": per_node[n]["rules"]} for n in NODE_IDS},
            "seals": {"CARGO.pal": cseal["seal"], "BERTH.pal": bseal["seal"]},
            "reference_witnesses": {"CARGO.pal": cseal["reference_witness"], "BERTH.pal": bseal["reference_witness"]},
            "cargo_segments_of_84": cseal["segments_of_84"],
            "studio_face": {"container_name": face, "expected_R2": bseal["reference_witness"],
                            "fabric_image": f"_studio/state/{face}.fabric.tif"},
            "fabric": {"available": fabric_rec.get("available"), "reason": fabric_rec.get("reason"),
                       "containers": fabric_rec.get("containers"), "hull_face": fabric_rec.get("hull_face"),
                       "genesis_dir": TF.GENESIS_DIR, "state_dir": TF.STATE_DIR,
                       "note": "each of the five containers has its own .tif fabric (sealed genesis under <slot>/fabric/, live image under "
                               "<slot>/_fabric/ outside the seal); the hull face has its own in the studio; a RUN ticks all six"},
            "policy_sha256": policy_sha, "slots": list(SLOTS),
            "hull_cargo": hull_cargo,
            "portable_storage": {"aliased": len(aliases), "stored_path_budget": STORED_PATH_BUDGET,
                                 "delivered_path_budget": DELIVERED_PATH_BUDGET},
            "layout": "hollow: slots hold cargo + declarations + their own .tif fabric; engines live once in the hold",
        }
        _write_json(os.path.join(dest, "BERTH.json"), berth_rec)
        _write(os.path.join(dest, "README.md"), berth_readme(berth_rec, per_node, cseal, bseal))
        # Do not embed the checksum of a file which also hashes this JSON (a self-reference).
        # The external bill of lading records the current checksum-file digest instead.
        M.write_sums(dest, name="SHA256SUMS.txt", extra=())
        return berth_rec
    finally:
        if td:
            shutil.rmtree(td, ignore_errors=True)


@SAFE.serialized
def load(source: str, name: str, kind: str = "subsystem", *, notes: Optional[str] = None,
         replace: bool = False, on_event=None) -> Dict[str, Any]:
    """Validate/build in staging, then swap; retain the previous berth as a backup.

    Ordinary exceptions restore the old berth. A process/host crash can leave a
    journal in _runs/transactions; doctor reports it. Registry + seals + hull are
    not a single crash-atomic transaction (see SECURITY.md).
    """
    import uuid
    SAFE.validate_name(name)
    if kind not in BERTH_KINDS:
        raise Refusal("invalid berth kind", {"kind": kind})
    dest = berth_dir(name)
    os.makedirs(berths_dir(), exist_ok=True)
    for existing in os.listdir(berths_dir()):
        if SAFE.portable_key(existing) == SAFE.portable_key(name) and existing != name:
            raise Refusal("berth name collides on a case-insensitive filesystem", {"existing": existing, "name": name})
    exists = os.path.exists(dest)
    if exists and (not replace or not os.path.isdir(dest)):
        raise Refusal("berth already exists; use --replace for a staged replacement", {"berth": name})
    txid = uuid.uuid4().hex
    txroot = SAFE.contained_path(E.ship_root(), "_runs/transactions/" + txid)
    candidate = os.path.join(txroot, "candidate")
    journal = os.path.join(txroot, "journal.json")
    backup = SAFE.contained_path(E.ship_root(), f"_runs/backups/load_{name}_{txid}") if exists else None
    state = {"schema": "UC/TRANSACTION/1", "operation": "load", "berth": name, "phase": "PREPARING",
             "candidate": candidate, "destination": dest, "backup": backup}
    SAFE.atomic_json(journal, state)
    moved_old = committed = completed = rollback_failed = False
    try:
        rec = _load_uncommitted(source, name, kind, candidate, notes=notes, on_event=on_event)
        check = M.check_sums(candidate)
        if not check["pass"]:
            raise ShipError("staged berth does not pass its own checksum gate", check)
        state["phase"] = "STAGED"
        SAFE.atomic_json(journal, state)
        if exists:
            os.makedirs(os.path.dirname(backup), exist_ok=True)
            os.replace(dest, backup)
            moved_old = True
            state["phase"] = "BACKED_UP"
            SAFE.atomic_json(journal, state)
        os.replace(candidate, dest)
        committed = True
        state["phase"] = "COMMITTED"
        SAFE.atomic_json(journal, state)
        if backup:
            rec["replacement_backup"] = backup
        completed = True
        return rec
    except BaseException:
        if moved_old and not committed:
            try:
                os.replace(backup, dest)
            except OSError:
                rollback_failed = True
                raise
        raise
    finally:
        # Keep evidence if the swap committed but final journaling failed, or rollback failed.
        if completed or (not committed and not rollback_failed):
            shutil.rmtree(txroot, ignore_errors=True)


@SAFE.serialized
def unload(name: str) -> Dict[str, Any]:
    import uuid
    d = berth_dir(name)
    if not os.path.isdir(d):
        raise Refusal(f"no berth {name!r}", {"berth": d})
    backup = SAFE.contained_path(E.ship_root(), f"_runs/backups/unload_{name}_{uuid.uuid4().hex}")
    os.makedirs(os.path.dirname(backup), exist_ok=True)
    os.replace(d, backup)
    return {"unloaded": name, "path": d, "backup": backup, "recoverable": True}


# --------------------------------------------------------------------------
# docs
# --------------------------------------------------------------------------

def sort_ledger_md(name: str, kind: str, ledger: List[dict], per_node: Dict[str, dict], source_rec: dict) -> str:
    lines = [f"# {name} -- sort ledger", "",
             f"Berth `{name}` ({kind}), {UC_RELEASE}. Source: `{os.path.basename(str(source_rec.get('path')))}` "
             f"({source_rec.get('kind')}, {source_rec.get('sha256') or source_rec.get('tree_sha256')}). "
             f"{len(ledger)} scripts sorted by policy {sorter.POLICY_VERSION} (rules S0-S9, first match wins; see `reports/SORT_POLICY.md`).", "",
             "| node | scripts | bytes | rules | kinds |", "|---|---:|---:|---|---|"]
    for n in NODE_IDS:
        pn = per_node[n]
        lines.append(f"| `{n}` ({NODE_CONTAINER[n]}) | {pn['count']} | {pn['bytes']} | {', '.join(f'{k}:{v}' for k, v in sorted(pn['rules'].items()))} | "
                     f"{', '.join(f'{k}:{v}' for k, v in sorted(pn['kinds'].items(), key=lambda kv: -kv[1])[:8])} |")
    lines += ["", "| script | node | rule | kind | bytes | lines | band | why |", "|---|---|---|---|---:|---:|---|---|"]
    for r in ledger[:400]:
        lines.append(f"| `{r['path']}` | `{r['node']}` | {r['rule']} | {r['kind']} | {r['bytes']} | {r['lines']} | {r['complexity_band']} | {r['explanation'].replace('|', '/')} |")
    if len(ledger) > 400:
        lines.append(f"| ... {len(ledger) - 400} more in SORT_LEDGER.json | | | | | | | |")
    al = [r for r in ledger if r.get("stored_as")]
    if al:
        lines += ["", f"**Portable storage.** {len(al)} script(s) are stored under an alias (`cargo/{ALIAS_DIR}/<sha256(path)[:16]><ext>`) because their "
                  f"original path cannot exist on every host (a path that differs only by case from another, or a delivered path over "
                  f"{DELIVERED_PATH_BUDGET} characters -- `{PACKAGE_DIR}/berths/{name}/<slot>/cargo/<path>` -- which a Windows extraction would refuse); "
                  f"their identity, bytes, node and rule are unchanged. First few:", ""]
        for r in al[:12]:
            lines.append(f"* `{r['path']}` -> `{r['stored_as']}` -- {r['stored_reason']}")
        if len(al) > 12:
            lines.append(f"* ... {len(al) - 12} more in SORT_LEDGER.json (`portable_storage.aliased`)")
    return "\n".join(lines) + "\n"


def hull_cargo_md(rec: dict) -> str:
    hc = [m for m in (rec.get("hull_cargo") or []) if m.get("name")]
    if not hc:
        return ""
    lines = ["**Hull cargo.** This berth's cargo is itself a sealed PA Language Studio container" + ("s" if len(hc) > 1 else "") + ":", ""]
    for m in hc:
        placed = ", ".join(f"`{f['path']}` -> {f['slot']}" for f in m["files"])
        lines.append(f"* `{m['name']}` (version {m.get('version')}, {m['listed']} sealed files, {'complete' if m.get('complete') else 'INCOMPLETE'}): {placed}"
                     + (f"; its picture `{m['picture']}` -> {m.get('picture_node')}" if m.get("picture") else "; no picture in the cargo")
                     + ". BUILD re-assembles it from the slots, re-verifies its seal and mounts it in the hull (`_studio/containers/" + m['name'] + "`) with its picture "
                       "(`_studio/state/" + m['name'] + ".fabric.tif`); `uc run` ticks it on its own picture and mirrors the picture into `_fabric/`.")
    lines.append("")
    return "\n".join(lines) + "\n"


def berth_readme(rec: dict, per_node: Dict[str, dict], cseal: dict, bseal: dict) -> str:
    name = rec["berth"]
    rows = "\n".join(f"| `{NODE_CONTAINER[n]}/` | `{n}` | {per_node[n]['count']} | {per_node[n]['bytes']} | `{per_node[n]['tree_sha256'][:16]}...` |" for n in NODE_IDS)
    return f"""# berth `{name}` -- {rec['kind']}

{UC_RELEASE}. This is the project's own blank four-node-plus-fabric scaffold, loaded: {rec['scripts']} scripts
({rec['bytes']} bytes) from `{os.path.basename(str(rec['source'].get('path')))}` were broken up script by script and sorted into the four
nodes by measured needs and complexity (`SORT_LEDGER.md`), then sealed as PA-LCTL bundles.

| slot | node | scripts | bytes | cargo tree |
|---|---|---:|---:|---|
{rows}
| `DF_Fabric/` | -- | -- | -- | the berth's fabric: BERTH_FABRIC.pal + engine registry |

* `CARGO.pal` -- the cargo manifest as a PA-LCTL bundle, {cseal['rows']} rows (one per script), seal `{cseal['seal'][:16]}...`,
  reference witness `{cseal['reference_witness']}`, executed on the engines in {cseal['segments_of_84']} segment(s) of 84 rows.
* `BERTH.pal` -- the berth declared in {bseal['rows']} rows, seal `{bseal['seal'][:16]}...`, reference witness `{bseal['reference_witness']}`
  -- one lowering on every engine, and the hull's container (`studio/main.lctlc`) expects exactly that number in R2.
* `SORT_LEDGER.json` -- every decision with its rule; VERIFY re-derives it from the cargo bytes.
* the slots hold no VM: engines live once in `hold/`, bound by digest (`DF_*/SLOT.json`).

{hull_cargo_md(rec)}Every container here has **its own .tif fabric** ({UC_RELEASE}): `DF_*/fabric/GENESIS.fabric.tif` (tick 0, sealed) and, once
BUILD or RUN made it, `DF_*/_fabric/DF_*.fabric.tif` -- the live picture (state, outside the seal): tile 0 the container's
state, tiles 1-2 this berth's declaration (BERTH.pal's row words as cells), tile 3 the seals; the fabric container's picture
holds the federation's vote and event log; the hull face's picture is the studio's own (`_studio/state/{rec['studio_face']['container_name']}.fabric.tif`).
A RUN is a tick: every picture is read, executed on its engine, and written back as a new frame.

```
../../uc.py run {name}                    one tick of the berth's fabric on the four engines + the hull (six pictures)
../../uc.py run {name} --sealed           the sealed bundles' programs: replica + pipeline + BSP over the four engines
../../uc.py fabric status|view|frames|live {name}
../../uc.py verify {name}                 the berth battery
DF_Small/RUN <cargo path>                 run one runnable script on its engine
```
"""
