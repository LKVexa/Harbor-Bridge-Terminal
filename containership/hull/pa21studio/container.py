"""Applications as containers.

The runtime arrives as a container: one named directory, a manifest, and a
`RELEASE_CONTENTS.sha256` that hashes every byte in it. That is what makes it
something a system can hold — copy it, verify it, install it, remove it, and
know at any moment whether what is on disk is what was shipped.

An application built with this studio is packaged the same way, in the same
format, with the same seal file name, so the same verification applies to both
halves of the system. A container is:

    <name>_<version>/
      CONTAINER.json              identity, requirements, digests
      RELEASE_CONTENTS.sha256     every file in the container, hashed
      README.md                   what it is and what it needs, generated
      src/main.lctlc              the source of record
      image/<name>.brimg          the compiled image
      image/<name>.provenance.json
      image/<name>.brir.json

Two things travel with it that a bare image cannot carry on its own: the
capability surface it will ask the VM for, and the fabric it needs the host to
stand up -- which devices, which adapter, what console input, what budget.
A container that needs the persistent block device says so before it is
installed, rather than trapping when it is run.

`RELEASE_CONTENTS.sha256` is deliberately the same filename and the same
`<digest>  <relative path>` line format the runtime container uses. One
verifier, both kinds.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil
import zipfile
from typing import Dict, List, Optional, Sequence, Tuple

SCHEMA = "PA21.STUDIO/CONTAINER/1"
FORMAT = "PA21C/1"
MANIFEST = "CONTAINER.json"
SEAL = "RELEASE_CONTENTS.sha256"
SUFFIX = ".pa21c"
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")

# the services a program can ask the fabric for, by the service call it makes
SERVICE_DEVICES = {
    "CONSOLE_WRITE": "console", "CONSOLE_READ": "console",
    "STORAGE_READ": "persistent block", "STORAGE_WRITE": "persistent block",
    "MONOTONIC": "monotonic state", "ENTROPY": "entropy", "TIMER": "clock",
    "MAILBOX_PUT": "mailbox", "MAILBOX_GET": "mailbox",
    "DEVICE_CALL": "extension device", "DEVICE_ENUM": "device discovery",
    "DIAG": "diagnostics", "SAVE": "persistence", "SHA256": "digest",
    "VERIFY": "signature verification", "TRUST": "trust state",
}


class ContainerError(RuntimeError):
    """A container the studio will not accept, with the reason attached."""

    def __init__(self, message: str, detail: Optional[Dict[str, object]] = None):
        super().__init__(message)
        self.detail = detail or {}


def utc_now() -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0).isoformat().replace("+00:00", "Z"))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ==========================================================================
# sealing
# ==========================================================================


def seal(root: str) -> Dict[str, object]:
    """Write RELEASE_CONTENTS.sha256 over every file except itself."""
    lines: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn == SEAL:
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, root).replace(os.sep, "/")
            lines.append(f"{sha256_file(fp)}  {rel}")
    lines.sort(key=lambda x: x.split("  ", 1)[1])
    path = os.path.join(root, SEAL)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return {"seal": path, "files": len(lines), "seal_sha256": sha256_file(path)}


def verify_seal(root: str) -> Dict[str, object]:
    """Re-derive every digest, and report anything the seal does not cover.

    Both directions matter. A file whose digest changed is a modified
    container; a file on disk that the seal never listed is an ADDED one, and
    a verifier that only walks the seal would not notice it.
    """
    path = os.path.join(root, SEAL)
    if not os.path.isfile(path):
        return {"sealed": False, "reason": f"no {SEAL} in this container",
                "checked": 0}
    listed, mismatched, missing = set(), [], []
    checked = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            try:
                digest, rel = line.split("  ", 1)
            except ValueError:
                continue
            listed.add(rel)
            full = os.path.join(root, rel.replace("/", os.sep))
            if not os.path.isfile(full):
                missing.append(rel)
                continue
            checked += 1
            if sha256_file(full) != digest:
                mismatched.append(rel)
    on_disk = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn == SEAL:
                continue
            on_disk.add(os.path.relpath(os.path.join(dirpath, fn), root)
                        .replace(os.sep, "/"))
    unlisted = sorted(on_disk - listed)
    ok = not mismatched and not missing and not unlisted
    return {"sealed": ok, "checked": checked, "listed": len(listed),
            "mismatched": mismatched[:10], "missing": missing[:10],
            "unlisted": unlisted[:10],
            "seal_sha256": sha256_file(path),
            "reason": "" if ok else
                      f"{len(mismatched)} modified, {len(missing)} absent, "
                      f"{len(unlisted)} present but unlisted"}


# ==========================================================================
# building one
# ==========================================================================


def _requested_services(source_text: str) -> List[str]:
    out = []
    for m in re.finditer(r"svc=([A-Z_]+)", source_text):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def service_calls(source_text: str) -> List[Dict[str, str]]:
    """Each service call, with the row it is on and the register it answers in.

    The service list alone says which devices a container touches. It does not
    say where a call's result went, and a byte count of zero in the register a
    row named is the difference between a transfer that did not happen and one
    that was never attempted.
    """
    calls: List[Dict[str, str]] = []
    for line in source_text.splitlines():
        if "│" not in line:
            continue
        col = [c.strip() for c in line.split("│")]
        if len(col) < 7 or col[2] != "SVC":
            continue
        m = re.search(r"svc=([A-Z_]+)", col[6])
        if m:
            calls.append({"id": col[0], "service": m.group(1), "out": col[3]})
    return calls


def _requested_caps(source_text: str) -> List[str]:
    m = re.search(r"br_request_caps=([A-Z|]+)", source_text)
    return m.group(1).split("|") if m else []


def scaffold(dest: str, name: str, version: str, source_text: str,
             app_meta: Dict[str, object], runtime: Dict[str, object],
             studio_version: str) -> Dict[str, object]:
    """Create a container for a new project, before anything is compiled.

    A project is a container from the moment it exists, not once it happens to
    be packaged. It starts in the SOURCE_ONLY state -- sealed, self-describing,
    listable, removable -- and gains its image when it is built.
    """
    if not NAME_RE.match(name):
        raise ContainerError(f"{name!r} is not a usable container name",
                             {"pattern": NAME_RE.pattern})
    if os.path.exists(dest) and os.listdir(dest):
        raise ContainerError(f"{dest} exists and is not empty", {"path": dest})
    os.makedirs(os.path.join(dest, "src"), exist_ok=True)
    os.makedirs(os.path.join(dest, "image"), exist_ok=True)
    src_path = os.path.join(dest, "src", "main.lctlc")
    with open(src_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(source_text)
    man = _manifest(name, version, source_text, app_meta, runtime,
                    studio_version, prov=None)
    _write(dest, man)
    s = seal(dest)
    return {"path": dest, "manifest": man, "seal": s, "source": src_path}


def record_build(dest: str, image: str, provenance: str,
                 brir: Optional[str]) -> Dict[str, object]:
    """Fold a compiled image into the container and re-seal it.

    The seal is rewritten here rather than left stale: a container whose seal
    describes the source but not the image it now carries is a container that
    verifies while lying.
    """
    man = read_manifest(dest)
    name = str(man["name"])
    os.makedirs(os.path.join(dest, "image"), exist_ok=True)

    def place(src: Optional[str], dst_name: str) -> None:
        # the compiler usually writes straight into the container, so the
        # common case here is that there is nothing to move
        if not src or not os.path.isfile(src):
            return
        dst = os.path.join(dest, "image", dst_name)
        if os.path.exists(dst) and os.path.samefile(src, dst):
            return
        shutil.copy2(src, dst)

    place(image, f"{name}.brimg")
    place(provenance, f"{name}.provenance.json")
    place(brir, f"{name}.brir.json")
    with open(provenance, encoding="utf-8") as fh:
        prov = json.load(fh)
    src_text = open(os.path.join(dest, "src", "main.lctlc"),
                    encoding="utf-8").read()
    updated = _manifest(name, str(man.get("version", "0.1.0")), src_text,
                        {"budget": man.get("budget", 4096),
                         "pa21": man.get("pa21", {}),
                         "expect": man.get("expect", {}),
                         "fabric": man.get("fabric", {})},
                        man.get("runtime", {}),
                        str(man.get("built_by", "")).replace(
                            "PA21 Language Studio ", ""),
                        prov=prov)
    updated["created_utc"] = man.get("created_utc", updated["created_utc"])
    updated["built_utc"] = utc_now()
    updated["state"] = "SEALED"
    _write(dest, updated)
    s = seal(dest)
    return {"path": dest, "manifest": updated, "seal": s}


def _write(dest: str, man: Dict[str, object]) -> None:
    with open(os.path.join(dest, MANIFEST), "w", encoding="utf-8",
              newline="\n") as fh:
        json.dump(man, fh, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(dest, "README.md"), "w", encoding="utf-8",
              newline="\n") as fh:
        fh.write(_readme(man))


def _manifest(name: str, version: str, src_text: str,
              app_meta: Dict[str, object], runtime: Dict[str, object],
              studio_version: str, prov: Optional[Dict[str, object]]
              ) -> Dict[str, object]:
    services = _requested_services(src_text)
    devices = sorted({SERVICE_DEVICES.get(s, s) for s in services})
    fab = dict(app_meta.get("fabric") or {})
    fab.setdefault("adapter", "memory")
    fab.setdefault("seed", 20260816)
    fab.setdefault("extension_devices",
                   "DEVICE_CALL" in services or "DEVICE_ENUM" in services)
    # whether this container's fabric carries over between runs, and any
    # message the host is expected to have waiting for it: both are part of
    # what the host must stand up, so both travel with the container
    fab.setdefault("state", "fresh")
    fab.setdefault("mailbox_in_hex", "")
    prov = prov or {}
    return {
        "schema": SCHEMA,
        "format": FORMAT,
        "name": name,
        "version": version,
        "state": "SEALED" if prov else "SOURCE_ONLY",
        "created_utc": utc_now(),
        "built_by": f"PA21 Language Studio {studio_version}",
        "entry": "src/main.lctlc",
        "image": f"image/{name}.brimg" if prov else None,
        "provenance": f"image/{name}.provenance.json" if prov else None,
        "language": prov.get("language_version"),
        "isa": prov.get("isa_version"),
        "compiler": prov.get("compiler_version"),
        "image_version": prov.get("image_version"),
        "instruction_count": prov.get("instruction_count"),
        "runtime": {
            "package": runtime.get("name") or runtime.get("package"),
            "requires": "a BOTTLE ROCKET runtime with a RAM-backed device "
                        "fabric (br_hal_memory or br_hal_deterministic)",
        },
        "capabilities": _requested_caps(src_text),
        "services": services,
        "service_calls": service_calls(src_text),
        "fabric": {
            "devices": devices,
            "adapter": fab["adapter"],
            "seed": fab["seed"],
            "extension_devices": bool(fab["extension_devices"]),
            "console_in_hex": fab.get("console_in_hex", ""),
            "mailbox_in_hex": fab.get("mailbox_in_hex", ""),
            "state": fab.get("state", "fresh"),
            "backend": "RAM",
            "note": "these are the services the source actually calls, read "
                    "out of it rather than declared by hand",
        },
        "budget": int(app_meta.get("budget", 4096)),
        "pa21": {"requires_operational":
                 [int(i) for i in (app_meta.get("pa21") or {})
                  .get("requires_operational", [])]},
        "expect": app_meta.get("expect") or {},
        "digests": {
            "source_sha256": prov.get("source_sha256")
            or hashlib.sha256(src_text.encode("utf-8")).hexdigest(),
            "image_sha256": prov.get("brim_sha256"),
            "brir_sha256": prov.get("brir_sha256"),
            "payload_sha256": prov.get("payload_sha256"),
        },
    }


def _readme(man: Dict[str, object]) -> str:
    fab = man["fabric"]
    req = man["pa21"]["requires_operational"]
    return f"""# {man['name']} {man['version']}

A COLUMNED LCTL container, format `{man['format']}`, built by
{man['built_by']}.

| | |
|---|---|
| language | {man['language']} |
| ISA | {man['isa']} |
| state | {man['state']} |
| instructions | {man['instruction_count'] if man['instruction_count'] is not None else 'not built yet'} |
| image | `{man['image'] or 'not built yet — run studio build'}` |
| capabilities | {', '.join(man['capabilities']) or 'none declared'} |

## What it asks the fabric for

{chr(10).join('- ' + d for d in fab['devices']) or '- nothing: it never calls a service'}

Adapter: `{fab['adapter']}` on a {fab['backend']} backend. Extension devices:
{'configured' if fab['extension_devices'] else 'none'}.

Every one of those devices is provided by the runtime container's memory
adapter, in the host process's own memory. Running this container needs no
filesystem and opens no socket.

## What it requires of the delivery

{('PA21 ledger items ' + ', '.join(str(i) for i in req) + ' must be OPERATIONAL.') if req else 'No PA21 ledger items are required.'}

## Running it

```
studio run {man['name']}
```

The seal in `{SEAL}` covers every file here. `studio containers --verify`
re-derives it.
"""


def pack(container_dir: str, out_file: Optional[str] = None) -> str:
    """Zip a sealed container directory into a single `.pa21c` file."""
    v = verify_seal(container_dir)
    if not v["sealed"]:
        raise ContainerError(f"refusing to pack an unsealed container: "
                             f"{v.get('reason')}", v)
    name = os.path.basename(container_dir.rstrip("/\\"))
    out = out_file or os.path.join(os.path.dirname(container_dir.rstrip("/\\")),
                                   name + SUFFIX)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(container_dir):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in sorted(filenames):
                fp = os.path.join(dirpath, fn)
                rel = os.path.relpath(fp, container_dir).replace(os.sep, "/")
                zf.write(fp, f"{name}/{rel}")
    return out


def unpack(archive: str, dest_parent: str) -> str:
    """Extract a `.pa21c` and return the container directory."""
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        tops = sorted({n.split("/")[0] for n in names if n.strip()})
        if len(tops) != 1:
            raise ContainerError(
                "a container archive must hold exactly one top-level "
                "directory; refused rather than guessing which one it is",
                {"top_level": tops[:8]})
        zf.extractall(dest_parent)
    return os.path.join(dest_parent, tops[0])


def read_manifest(container_dir: str) -> Dict[str, object]:
    p = os.path.join(container_dir, MANIFEST)
    if not os.path.isfile(p):
        raise ContainerError(f"no {MANIFEST} here; this is not a container",
                             {"path": container_dir})
    with open(p, encoding="utf-8") as fh:
        man = json.load(fh)
    if man.get("format") != FORMAT:
        raise ContainerError(f"unknown container format "
                             f"{man.get('format')!r}; this studio speaks "
                             f"{FORMAT}", {"path": container_dir})
    return man


def classify(container_dir: str) -> Dict[str, object]:
    """What state is this container in, and what does that mean for the author?

    A seal that does not match is not one condition, it is two, and confusing
    them is the fastest way to make an authoring tool feel hostile:

      SOURCE_ONLY  written, never built
      SEALED       the image on disk was built from the source on disk
      DRAFT        the source has been edited since the last build. This is
                   what an open editor looks like, not damage.
      BROKEN       the image, the manifest or the file list changed under the
                   seal. That is damage, and it is reported as such.

    The check is the same digest arithmetic either way. The difference is
    WHICH files moved, and telling the author that is the whole point.
    """
    try:
        man = read_manifest(container_dir)
    except ContainerError as e:
        return {"state": "NOT_A_CONTAINER", "reason": str(e), "ok": False}
    v = verify_seal(container_dir)
    src = os.path.join(container_dir, str(man.get("entry", "src/main.lctlc")))
    src_now = (hashlib.sha256(open(src, "rb").read()).hexdigest()
               if os.path.isfile(src) else None)
    src_built = (man.get("digests") or {}).get("source_sha256")
    if v["sealed"]:
        state = str(man.get("state", "SEALED"))
        return {"state": state, "sealed": True, "seal": v, "manifest": man,
                "ok": True,
                "reason": "the container matches its seal",
                "next": "studio build" if state == "SOURCE_ONLY"
                        else "studio run"}
    moved = set(v.get("mismatched", []) + v.get("missing", [])
                + v.get("unlisted", []))
    only_source = moved and all(p.startswith("src/") for p in moved)
    if only_source and man.get("state") == "SOURCE_ONLY":
        return {"state": "SOURCE_ONLY", "sealed": False, "seal": v,
                "manifest": man, "ok": True,
                "reason": "edited before the first build",
                "next": "studio build"}
    if only_source:
        return {"state": "DRAFT", "sealed": False, "seal": v, "manifest": man,
                "ok": True,
                "source_changed": src_now != src_built,
                "reason": "the source has been edited since this container was "
                          "built, so the image on disk is from the previous "
                          "version of it",
                "next": "studio build"}
    return {"state": "BROKEN", "sealed": False, "seal": v, "manifest": man,
            "ok": False,
            "reason": f"files outside src/ no longer match the seal: "
                      f"{', '.join(sorted(moved)[:4])}",
            "next": "studio build, or restore the files the seal describes"}


def inspect(container_dir: str) -> Dict[str, object]:
    """Everything checkable about a container, without running it."""
    try:
        man = read_manifest(container_dir)
    except ContainerError as e:
        return {"path": container_dir, "container": False, "reason": str(e)}
    v = verify_seal(container_dir)
    img = os.path.join(container_dir, str(man.get("image", "")))
    digests_ok = (os.path.isfile(img)
                  and sha256_file(img) == (man.get("digests") or {})
                  .get("image_sha256"))
    return {"path": container_dir, "container": True, "manifest": man,
            "name": man.get("name"), "version": man.get("version"),
            "seal": v, "sealed": v["sealed"],
            "image_matches_manifest": bool(digests_ok),
            "devices": (man.get("fabric") or {}).get("devices", []),
            "requires_operational":
                (man.get("pa21") or {}).get("requires_operational", []),
            "ok": bool(v["sealed"] and digests_ok)}
