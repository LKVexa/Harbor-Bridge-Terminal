"""The studio itself: install, uninstall, and everything an application needs
to be built, verified and executed.

Two rules shape this file.

The first is that an install is only finished when it has been demonstrated.
`install()` does not end by copying files and declaring success; it ends by
compiling a canonical application from source, executing it on the runtime it
just built, and comparing the result with the answer that application declares.
If that fails, the install reports FAILED and says which step did it -- with
the runtime left in place so the failure can be looked at.

The second is that uninstall may only remove what install recorded. Every path
the installer creates is written into the manifest as it is created, and
`uninstall()` walks that list rather than deleting by pattern. A studio that
deletes by pattern eventually deletes something a user put there.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from typing import Callable, Dict, List, Optional, Sequence

from . import abi as abi_mod
from . import container as containers
from . import describe as describe_mod
from . import fabric_tif as fabric_tif
from . import fault as fault_mod
from . import ledger as pa21_ledger
from . import lctlc
from . import probe as probe_mod
from . import repair as repair_mod

VERSION = "2.0.0"
# where the selftest flips a byte to prove a signature is actually checked:
# inside the code section, past the 80-byte image header
BR_TAMPER_OFFSET = 100
SCHEMA = "PA21.STUDIO/INSTALL/1"
APP_SCHEMA = "PA21.STUDIO/APP/1"
MANIFEST_NAME = "studio.json"
APP_MANIFEST = "pa21app.json"

Event = Callable[[Dict[str, object]], None]


def utc_now() -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0).isoformat().replace("+00:00", "Z"))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def default_root() -> str:
    env = os.environ.get("PA21_STUDIO_HOME")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "PA21LanguageStudio")
    return os.path.join(os.path.expanduser("~"), ".pa21-studio")


class StudioError(RuntimeError):
    """Something the studio refuses to do, with the reason attached."""

    def __init__(self, message: str, detail: Dict[str, object] = None):
        super().__init__(message)
        self.detail = detail or {}


class Studio:
    """The scriptable surface. Everything the CLI and the window do is here.

        from pa21studio import Studio
        s = Studio()
        s.install(vm_source="Large.zip", pa21_root=r"C:\\...\\PA21.2")
        s.run_app("myapp")            # -> {"status_name": "OK", "registers": {...}}
        s.uninstall()

    Every method returns a plain dict, so a caller can json.dumps it, assert on
    it, or ignore it. Nothing prints unless a caller asks for events.
    """

    def __init__(self, root: Optional[str] = None):
        self.root = os.path.abspath(os.path.expanduser(root or default_root()))
        self.manifest_path = os.path.join(self.root, MANIFEST_NAME)

    # ------------------------------------------------------------------
    # manifest
    # ------------------------------------------------------------------
    @property
    def installed(self) -> bool:
        return os.path.isfile(self.manifest_path)

    def manifest(self) -> Dict[str, object]:
        if not self.installed:
            raise StudioError("no studio is installed at this root",
                              {"root": self.root})
        with open(self.manifest_path, encoding="utf-8") as fh:
            return json.load(fh)

    def _save_manifest(self, man: Dict[str, object]) -> None:
        os.makedirs(self.root, exist_ok=True)
        tmp = self.manifest_path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(man, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, self.manifest_path)

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------
    def status(self, deep: bool = False) -> Dict[str, object]:
        """What is installed, what works, and what does not -- with reasons."""
        pr = probe_mod.probe_all()
        out: Dict[str, object] = {
            "schema": "PA21.STUDIO/STATUS/1",
            "studio_version": VERSION,
            "root": self.root,
            "installed": self.installed,
            "checked_utc": utc_now(),
            "host": pr["host"],
            "capabilities": {
                "compile_images": pr["can_compile_images"],
                "execute_images": pr["can_execute_images"],
                "build_signing_cli": pr["can_build_signing_cli"],
            },
            "findings": pr["findings"],
        }
        if not self.installed:
            out["summary"] = "not installed"
            return out
        man = self.manifest()
        out["installed_utc"] = man.get("installed_utc")
        out["runtime"] = {k: man.get("runtime", {}).get(k)
                          for k in ("name", "path", "source", "source_sha256",
                                    "files", "bytes")}
        out["binaries"] = man.get("binaries", {})
        out["pa21"] = man.get("pa21", {})
        out["apps"] = self.list_apps()["apps"]
        out["execution_mode"] = man.get("execution_mode")
        out["signing"] = self.signing_key()
        out["fabric_backend"] = (man.get("binaries", {}).get("brrun") or {}
                                 ).get("backend", "none: no runner built")
        out["fabric_devices"] = (man.get("binaries", {}).get("brrun") or {}
                                 ).get("devices", [])
        runner = (man.get("binaries", {}).get("brrun") or {}).get("path")
        out["runner_present"] = bool(runner and os.path.isfile(runner))
        if deep and out["runner_present"]:
            out["selftest"] = self.selftest()
        parts = ["installed"]
        if out["runner_present"]:
            parts.append("runtime executable")
        else:
            parts.append("no runner built")
        if man.get("pa21", {}).get("found"):
            parts.append(f"PA21 {man['pa21'].get('round', 'delivery')} bound")
        out["summary"] = ", ".join(parts)
        return out

    # ------------------------------------------------------------------
    # install
    # ------------------------------------------------------------------
    def plan_install(self, vm_source: str, pa21_root: Optional[str] = None,
                     build: bool = True) -> Dict[str, object]:
        """Exactly what an install would do, computed without doing any of it.

        The window shows this before the button is pressed. An installer that
        cannot say in advance what it will write is asking for trust it has
        not earned.
        """
        pr = probe_mod.probe_all()
        src = os.path.abspath(os.path.expanduser(vm_source))
        kind = ("archive" if os.path.isfile(src) else
                "directory" if os.path.isdir(src) else "missing")
        size = os.path.getsize(src) if kind == "archive" else None
        writes = [
            os.path.join(self.root, MANIFEST_NAME),
            os.path.join(self.root, "runtime", "<package>"),
            os.path.join(self.root, "containers"),
            os.path.join(self.root, "logs"),
        ]
        if build and pr["can_execute_images"]:
            writes.insert(2, os.path.join(self.root, "bin", "brrun"))
        pa21 = pa21_ledger.survey(os.path.abspath(os.path.expanduser(pa21_root))) \
            if pa21_root else {"found": False, "reason": "no PA21 root given"}
        return {
            "schema": "PA21.STUDIO/PLAN/1",
            "root": self.root,
            "source": {"path": src, "kind": kind, "bytes": size},
            "will_write": writes,
            "will_build_runner": bool(build and pr["can_execute_images"]),
            "will_bind_pa21": bool(pa21.get("found")),
            "pa21": pa21,
            "already_installed": self.installed,
            "capabilities": {
                "compile_images": pr["can_compile_images"],
                "execute_images": pr["can_execute_images"],
            },
            "notes": [
                "the runtime is COPIED into the studio root; the source "
                "archive is not modified",
                "nothing outside the studio root is written",
                "an install ends by compiling and executing a canonical "
                "application; it is not reported as complete until that runs",
            ],
        }

    def install(self, vm_source: str, pa21_root: Optional[str] = None,
                build: bool = True, force: bool = False,
                on_event: Optional[Event] = None) -> Dict[str, object]:
        emit = _emitter(on_event)
        t0 = time.perf_counter()
        if self.installed and not force:
            raise StudioError(
                "a studio is already installed at this root; uninstall first, "
                "or pass force to replace it",
                {"root": self.root,
                 "installed_utc": self.manifest().get("installed_utc")})
        src = os.path.abspath(os.path.expanduser(vm_source))
        if not os.path.exists(src):
            raise StudioError(f"no VM package at {src}", {"source": src})
        pr = probe_mod.probe_all(refresh=True)
        owned: List[str] = []
        steps: List[Dict[str, object]] = []

        def step(name: str, ok: bool, detail: str = "", **extra):
            rec = {"step": name, "ok": bool(ok), "detail": detail}
            rec.update(extra)
            steps.append(rec)
            emit({"phase": name, "ok": bool(ok), "message": detail,
                  "progress": min(0.95, 0.08 * len(steps))})
            return rec

        emit({"phase": "start", "message": "preparing", "progress": 0.02})
        os.makedirs(self.root, exist_ok=True)
        owned.append(self.root)
        for sub in ("runtime", "bin", "containers", "apps", "logs"):
            p = os.path.join(self.root, sub)
            os.makedirs(p, exist_ok=True)
            owned.append(p)
        step("prepare", True, f"studio root ready at {self.root}")

        # ---- 1. copy the runtime -------------------------------------
        rt_parent = os.path.join(self.root, "runtime")
        if os.path.isfile(src):
            source_sha = sha256_file(src)
            with tempfile.TemporaryDirectory() as td:
                with zipfile.ZipFile(src) as zf:
                    names = zf.namelist()
                    top = sorted({n.split("/")[0] for n in names if n.strip()})
                    if len(top) != 1:
                        raise StudioError(
                            "the archive does not contain exactly one top-level "
                            "package directory; refused rather than guessing "
                            "which one is the runtime",
                            {"top_level": top[:8]})
                    zf.extractall(td)
                extracted = os.path.join(td, top[0])
                runtime_name = top[0]
                dest = os.path.join(rt_parent, runtime_name)
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                shutil.copytree(extracted, dest)
        else:
            runtime_name = os.path.basename(src.rstrip("/\\"))
            dest = os.path.join(rt_parent, runtime_name)
            if os.path.isdir(dest):
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            source_sha = ""
        owned.append(dest)
        files = sum(len(f) for _r, _d, f in os.walk(dest))
        nbytes = sum(os.path.getsize(os.path.join(r, f))
                     for r, _d, fs in os.walk(dest) for f in fs)
        step("copy_runtime", True,
             f"{files} files, {nbytes / 1024:.0f} KiB copied to {dest}",
             files=files, bytes=nbytes)

        if not os.path.isfile(os.path.join(dest, "src", "brvm.c")):
            raise StudioError(
                "the copied package has no src/brvm.c; it is not a BOTTLE "
                "ROCKET runtime and the studio will not pretend it is",
                {"runtime": dest})

        # ---- 2. verify the copy against the package's own manifest ----
        contents = os.path.join(dest, "RELEASE_CONTENTS.sha256")
        if os.path.isfile(contents):
            checked = bad = 0
            for line in open(contents, encoding="utf-8"):
                line = line.strip()
                if not line or " " not in line:
                    continue
                digest, rel = line.split(None, 1)
                rel = rel.strip().lstrip("*")
                full = os.path.join(dest, rel)
                if not os.path.isfile(full):
                    continue
                checked += 1
                if sha256_file(full) != digest:
                    bad += 1
            step("verify_copy", bad == 0,
                 f"{checked} files re-hashed against RELEASE_CONTENTS.sha256, "
                 f"{bad} mismatched", checked=checked, mismatched=bad)
            if bad:
                raise StudioError(
                    f"{bad} file(s) in the copied runtime do not match the "
                    f"package's own manifest", {"runtime": dest})
        else:
            step("verify_copy", True,
                 "the package ships no RELEASE_CONTENTS.sha256; the copy was "
                 "hashed but had nothing to be compared against")

        # ---- 3. build the studio's runner ----------------------------
        binaries: Dict[str, Dict[str, object]] = {}
        exec_mode = "UNAVAILABLE_NO_C_TOOLCHAIN"
        if build and pr["can_execute_images"]:
            cc = pr["findings"]["c_compiler"]["value"]
            host_src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "hosts", "brrun.c")
            out_bin = os.path.join(self.root, "bin",
                                   "brrun.exe" if os.name == "nt" else "brrun")
            # the memory adapter is not optional decoration: it IS the
            # backend the device and I/O service architecture runs on. A VM
            # built without it has no console, no persistent block, no
            # monotonic state, no entropy and no clock, and traps BR_TRAP_HOST
            # at the first service call.
            adapter_src = os.path.join(dest, "adapters", "br_memory_adapter.c")
            if not os.path.isfile(adapter_src):
                raise StudioError(
                    "the copied runtime has no adapters/br_memory_adapter.c, "
                    "so its device fabric has no RAM backend to run on",
                    {"runtime": dest})
            incs = [os.path.join(dest, "src"), os.path.join(dest, "adapters")]
            srcs = [os.path.join(dest, "src", "brvm.c"), adapter_src, host_src]
            base = probe_mod.compile_command(
                cc, srcs, out_bin, includes=incs, defines=["BR_DEVELOPMENT=1"])
            # With OpenSSL present the runner is built with a signature
            # verifier, which is what lets a SIGNED image run on the RAM
            # fabric: the memory adapter answers "unsupported" for signature
            # checks, so without this the choice would be signed images or
            # the RAM backend, and the studio would have to give one up.
            signing = bool(pr.get("can_build_signing_cli"))
            cmd = probe_mod.compile_command(
                cc, srcs, out_bin, includes=incs,
                defines=["BR_DEVELOPMENT=1", "BR_STUDIO_SIGNING=1"],
                libs=["crypto"]) if signing else base
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if r.returncode != 0 and signing:
                # the honest fallback: build the runner it can build, and say
                # in the manifest that signed images will not run here
                signing = False
                cmd = base
                r = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=900)
            if r.returncode != 0 or not os.path.isfile(out_bin):
                step("build_runner", False,
                     (r.stderr or "").strip()[-400:] or "the compiler failed")
                raise StudioError(
                    "the runtime copy did not compile on this machine",
                    {"compiler": cc, "stderr": (r.stderr or "")[-2000:]})
            owned.append(out_bin)
            binaries["brrun"] = {"path": out_bin, "sha256": sha256_file(out_bin),
                                 "built_with": cc,
                                 "verifies_signatures": signing,
                                 "defines": ["BR_DEVELOPMENT=1"] +
                                            (["BR_STUDIO_SIGNING=1"]
                                             if signing else []),
                                 "sources": ["src/brvm.c",
                                             "adapters/br_memory_adapter.c",
                                             "pa21studio/hosts/brrun.c"],
                                 "backend": "RAM (br_hal_memory / "
                                            "br_hal_deterministic)",
                                 "devices": ["console", "persistent block",
                                             "monotonic state", "entropy",
                                             "clock", "mailbox",
                                             "diagnostics"]}
            exec_mode = "DEVELOPMENT_RAW"     # revised below once signing is
            #                                   known: an installation that
            #                                   verifies signatures should not
            #                                   describe itself as the raw
            #                                   development path
            step("build_runner", True,
                 f"brrun built with {cc}, on the memory adapter: the device "
                 f"fabric is backed by RAM"
                 + (", and it verifies Ed25519 image signatures"
                    if signing else
                    "; no OpenSSL here, so signed images cannot be verified"))
            # ---- 3b. the signing CLI, and this installation's key -------
            # An image the studio signs is signed by the runtime's own brctl,
            # with the runtime's own key format, so nothing about the trust
            # chain is the studio's invention. The key is generated here and
            # never leaves this root.
            if signing:
                ctl_src = os.path.join(dest, "host", "brctl.c")
                ctl_bin = os.path.join(self.root, "bin",
                                       "brctl.exe" if os.name == "nt"
                                       else "brctl")
                # brctl is POSIX C: it includes unistd.h and calls chmod, so
                # it does not build under MSVC. On Windows that means signing
                # needs a MinGW toolchain, and the studio says so rather than
                # failing the install.
                ctl_cmd = probe_mod.compile_command(
                    cc, [os.path.join(dest, "src", "brvm.c"),
                         os.path.join(dest, "adapters", "br_file_adapter.c"),
                         ctl_src],
                    ctl_bin, includes=incs, defines=["BR_DEVELOPMENT=1"],
                    libs=["crypto"])
                cr = subprocess.run(ctl_cmd, capture_output=True, text=True,
                                    timeout=900) \
                    if (os.path.isfile(ctl_src)
                        and probe_mod.compiler_kind(cc) != "msvc") else None
                if cr is not None and cr.returncode == 0 \
                        and os.path.isfile(ctl_bin):
                    owned.append(ctl_bin)
                    keys_dir = os.path.join(self.root, "keys")
                    os.makedirs(keys_dir, exist_ok=True)
                    owned.append(keys_dir)
                    priv = os.path.join(keys_dir, "studio.key")
                    pub = os.path.join(keys_dir, "studio.pub")
                    kr = subprocess.run([ctl_bin, "keygen", priv, pub],
                                        capture_output=True, text=True,
                                        timeout=120)
                    if kr.returncode == 0 and os.path.isfile(pub):
                        try:
                            os.chmod(priv, 0o600)
                        except OSError:
                            pass
                        owned.extend([priv, pub])
                        binaries["brctl"] = {
                            "path": ctl_bin, "sha256": sha256_file(ctl_bin),
                            "built_with": cc,
                            "public_key": pub, "private_key": priv,
                            "key_sha256": sha256_file(pub),
                            "note": "Ed25519, generated at install; the "
                                    "private key stays in this studio root "
                                    "and is never packed into a container"}
                        step("signing", True,
                             f"brctl built and an Ed25519 key generated: "
                             f"images built here are signed and verified "
                             f"before they run")
                    else:
                        step("signing", True,
                             "brctl built but no key could be generated; "
                             "images will run unsigned")
                else:
                    signing = False
                    binaries["brrun"]["signs_images"] = False
                    step("signing", True,
                         "the runtime's brctl did not build here"
                         + (" (it is POSIX C and this is MSVC; a MinGW "
                            "toolchain would build it)"
                            if probe_mod.compiler_kind(cc) == "msvc" else "")
                         + "; images will run unsigned, and the runner will "
                           "say so")
            else:
                step("signing", True,
                     "no OpenSSL on this host: images are neither signed nor "
                     "signature-checked, and every result says "
                     "DEVELOPMENT_RAW")

            if signing and "brctl" in binaries:
                exec_mode = "SIGNED_VERIFIED"
            st = self._run_binary([out_bin, "selftest"])
            step("vm_selftest", st.get("selftest") == "PASS",
                 f"core selftest {st.get('selftest', 'no result')}", result=st)
            if st.get("selftest") != "PASS":
                raise StudioError("the VM core selftest did not pass",
                                  {"result": st})
        else:
            reason = ("build was not requested" if not build else
                      pr["findings"]["c_compiler"]["detail"])
            step("build_runner", True,
                 f"no runner built: {reason}. Images can still be compiled and "
                 f"verified; executing them cannot be done on this machine")

        # ---- 4. bind the PA21 delivery -------------------------------
        pa21 = {"found": False, "reason": "no PA21 root given"}
        if pa21_root:
            pa21 = pa21_ledger.survey(os.path.abspath(
                os.path.expanduser(pa21_root)))
            step("bind_pa21", bool(pa21.get("found")),
                 (f"{pa21.get('package_count', 0)} package(s), ledger "
                  f"{pa21.get('round', 'unknown')}, "
                  f"{pa21.get('operational', 0)}/{pa21.get('items', 0)} "
                  f"operational") if pa21.get("found")
                 else str(pa21.get("reason")))
        else:
            step("bind_pa21", True, "no PA21 delivery bound; applications that "
                                    "declare ledger requirements will refuse "
                                    "to run until one is")

        # ---- 5. write the manifest before proving it -----------------
        man: Dict[str, object] = {
            "schema": SCHEMA,
            "studio_version": VERSION,
            "installed_utc": utc_now(),
            "root": self.root,
            "runtime": {"name": runtime_name, "path": dest, "source": src,
                        "source_sha256": source_sha, "files": files,
                        "bytes": nbytes},
            "binaries": binaries,
            "execution_mode": exec_mode,
            "execution_mode_note":
                "raw image loading is the runtime's development path. The "
                "package's production CLI refuses raw and merely signed "
                "images unless a BRTM/1 trust chain has been provisioned, and "
                "the package exposes no provisioning path, so the studio "
                "executes in the same development mode the package's own "
                "tests use -- and says so in every result.",
            "pa21": pa21,
            "probe": pr,
            "owned_paths": sorted(set(owned)),
            "host": pr["host"],
        }
        self._save_manifest(man)
        owned.append(self.manifest_path)
        man["owned_paths"] = sorted(set(owned))
        self._save_manifest(man)
        step("write_manifest", True, f"{self.manifest_path}")

        # ---- 6. prove it by running something -------------------------
        proof = self.selftest(deep=True)
        step("prove", bool(proof.get("ok")),
             proof.get("summary", ""), proof=proof)
        man["install_proof"] = proof
        man["steps"] = steps
        man["install_seconds"] = round(time.perf_counter() - t0, 3)
        self._save_manifest(man)
        ok = all(s["ok"] for s in steps)
        emit({"phase": "done", "ok": ok, "progress": 1.0,
              "message": "installed" if ok else "installed with failures"})
        return {"schema": "PA21.STUDIO/INSTALL_RESULT/1", "ok": ok,
                "root": self.root, "runtime": dest,
                "execution_mode": exec_mode,
                "seconds": man["install_seconds"], "steps": steps,
                "proof": proof, "manifest": self.manifest_path,
                "pa21": pa21}

    # ------------------------------------------------------------------
    # uninstall
    # ------------------------------------------------------------------
    def plan_uninstall(self, purge: bool = False) -> Dict[str, object]:
        if not self.installed:
            return {"schema": "PA21.STUDIO/PLAN/1", "installed": False,
                    "will_remove": [], "root": self.root,
                    "note": "nothing is installed at this root"}
        man = self.manifest()
        owned = [p for p in man.get("owned_paths", []) if os.path.exists(p)]
        apps = self.list_apps()["apps"]
        kept = [] if purge else [a["path"] for a in apps
                                 if not a["path"].startswith(self.root)]
        return {"schema": "PA21.STUDIO/PLAN/1", "installed": True,
                "root": self.root,
                "will_remove": owned,
                "will_keep": kept,
                "purge": purge,
                "bytes": _tree_bytes(owned),
                "note": "only paths this installation recorded as its own are "
                        "removed; anything else under the root is reported as "
                        "residue and left alone"}

    def uninstall(self, purge: bool = False,
                  on_event: Optional[Event] = None) -> Dict[str, object]:
        emit = _emitter(on_event)
        if not self.installed:
            return {"schema": "PA21.STUDIO/UNINSTALL_RESULT/1", "ok": True,
                    "removed": [], "residue": [], "root": self.root,
                    "note": "nothing was installed at this root"}
        man = self.manifest()
        owned = list(man.get("owned_paths", []))
        # deepest first, so directories empty before they are removed
        owned.sort(key=lambda p: (-p.count(os.sep), p))
        removed, failed = [], []
        total = max(1, len(owned))
        for i, p in enumerate(owned):
            emit({"phase": "remove", "message": p,
                  "progress": 0.05 + 0.85 * (i / total)})
            if p == self.root:
                continue
            try:
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p, ignore_errors=False)
                elif os.path.exists(p):
                    os.remove(p)
                removed.append(p)
            except OSError as e:
                failed.append({"path": p, "error": str(e)})
        residue: List[str] = []
        if os.path.isdir(self.root):
            for r, _d, fs in os.walk(self.root):
                for f in fs:
                    residue.append(os.path.join(r, f))
        if purge and os.path.isdir(self.root):
            try:
                shutil.rmtree(self.root)
                removed.append(self.root)
                residue = []
            except OSError as e:
                failed.append({"path": self.root, "error": str(e)})
        elif os.path.isdir(self.root) and not residue:
            try:
                os.rmdir(self.root)
                removed.append(self.root)
            except OSError:
                pass
        ok = not failed
        emit({"phase": "done", "ok": ok, "progress": 1.0,
              "message": "removed" if ok else "removed with errors"})
        return {"schema": "PA21.STUDIO/UNINSTALL_RESULT/1", "ok": ok,
                "root": self.root, "removed": removed, "failed": failed,
                "residue": residue[:50], "residue_count": len(residue),
                "purge": purge,
                "note": "residue is anything still under the root that this "
                        "installation did not create; it was left alone"}

    # ------------------------------------------------------------------
    # applications
    # ------------------------------------------------------------------
    def _runtime(self) -> str:
        man = self.manifest()
        rt = man.get("runtime", {}).get("path")
        if not rt or not os.path.isdir(rt):
            raise StudioError("the installed runtime is missing",
                              {"expected": rt})
        return rt

    def _runner(self) -> str:
        man = self.manifest()
        b = (man.get("binaries", {}).get("brrun") or {}).get("path")
        if not b or not os.path.isfile(b):
            raise StudioError(
                "this installation has no runner, so images cannot be "
                "executed here. Compiling and verifying them still works.",
                {"capabilities": self.status()["capabilities"]})
        return b

    def containers_dir(self) -> str:
        """Where every project this studio creates lives, one container each."""
        return os.path.join(self.root, "containers")

    def apps_dir(self) -> str:
        """The pre-container layout, still resolved so older roots keep working."""
        return os.path.join(self.root, "apps")

    def new_app(self, name: str, path: Optional[str] = None,
                template: str = "hello",
                requires_operational: Sequence[int] = (),
                version: str = "0.1.0",
                source: Optional[str] = None,
                state: str = "fresh",
                mailbox_in: Optional[bytes] = None) -> Dict[str, object]:
        """Create a project. A project is a container, from the first moment.

        It lands in the studio's own container registry beside the runtime
        container, sealed and self-describing, so the language system holds
        one kind of thing: containers. Nothing has to be "packaged" later --
        packaging is just zipping what is already there.
        """
        if not containers.NAME_RE.match(name or ""):
            raise StudioError("a project name must start with a letter and "
                              "use letters, digits, dot, dash or underscore",
                              {"name": name})
        base = os.path.abspath(os.path.expanduser(path)) if path else \
            os.path.join(self.containers_dir(), name)
        if os.path.exists(base) and os.listdir(base):
            raise StudioError(f"{base} exists and is not empty", {"path": base})
        t = lctlc.TEMPLATES.get(template)
        if t is None and source is None:
            raise StudioError(f"{template!r} is not a template",
                              {"templates": sorted(lctlc.TEMPLATES)})
        text = None
        if source is not None:
            # code that already exists -- from a repository, an editor, or a
            # generator writing to a pipe -- becomes a container in one step,
            # rather than being pasted into a scaffold afterwards
            if source == "-":
                text = sys.stdin.read()
            else:
                sp = os.path.abspath(os.path.expanduser(source))
                if not os.path.isfile(sp):
                    raise StudioError(f"no source file at {sp}",
                                      {"source": source})
                with open(sp, encoding="utf-8") as fh:
                    text = fh.read()
            if not text.strip():
                raise StudioError("the source is empty; refused rather than "
                                  "sealing a container around nothing")
        runtime = {}
        try:
            runtime = self.manifest().get("runtime", {})
        except StudioError:
            pass
        meta = {"budget": 4096,
                "pa21": {"requires_operational": [int(i) for i in
                                                  requires_operational]},
                "expect": (t or {}).get("expect", {}) if text is None else {},
                "fabric": {"state": state,
                           "mailbox_in_hex": (mailbox_in or b"").hex()}}
        try:
            made = containers.scaffold(
                base, name, version,
                text if text is not None
                else lctlc.render(template, name.replace("-", "_")[:31]),
                meta, runtime, VERSION)
        except containers.ContainerError as e:
            raise StudioError(str(e), e.detail)
        # the container is the studio's to remove, so the manifest says so
        self._own(base)
        self._write_registry()
        return {"schema": "PA21.STUDIO/NEW_RESULT/1", "ok": True,
                "path": base, "container": base,
                "entry": made["source"],
                "manifest": os.path.join(base, containers.MANIFEST),
                "template": None if text is not None else template,
                "from_source": source, "version": version,
                "state": made["manifest"]["state"],
                "sealed_files": made["seal"]["files"],
                "expect": t["expect"],
                "next": f"studio build {name}"}

    # ------------------------------------------------------------------
    def _own(self, path: str) -> None:
        """Record a path as this installation's, so uninstall may remove it."""
        if not self.installed:
            return
        man = self.manifest()
        owned = set(man.get("owned_paths", []))
        if path not in owned:
            owned.add(path)
            man["owned_paths"] = sorted(owned)
            self._save_manifest(man)

    def _disown(self, path: str) -> None:
        if not self.installed:
            return
        man = self.manifest()
        man["owned_paths"] = sorted(p for p in man.get("owned_paths", [])
                                    if p != path)
        self._save_manifest(man)

    def _write_registry(self) -> Dict[str, object]:
        """Rebuild containers/REGISTRY.json from what is actually on disk.

        The registry is derived, never appended to: an index that is written
        alongside changes eventually describes containers that are no longer
        there.
        """
        d = self.containers_dir()
        if not os.path.isdir(d):
            return {"containers": [], "count": 0}
        entries = []
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if not os.path.isdir(p):
                continue
            try:
                man = containers.read_manifest(p)
            except containers.ContainerError:
                continue
            entries.append({"name": man.get("name", name), "dir": name,
                            "version": man.get("version"),
                            "state": man.get("state"),
                            "devices": (man.get("fabric") or {}).get("devices", []),
                            "requires_operational":
                                (man.get("pa21") or {}).get(
                                    "requires_operational", [])})
        reg = {"schema": "PA21.STUDIO/REGISTRY/1", "rebuilt_utc": utc_now(),
               "format": containers.FORMAT, "root": d,
               "containers": entries, "count": len(entries)}
        with open(os.path.join(d, "REGISTRY.json"), "w", encoding="utf-8",
                  newline="\n") as fh:
            json.dump(reg, fh, indent=2, sort_keys=True)
            fh.write("\n")
        return reg

    def resolve_app(self, ref: str) -> str:
        """A container by name, or by path. Containers first, legacy apps after."""
        cand = [os.path.abspath(os.path.expanduser(ref)),
                os.path.join(self.containers_dir(), ref),
                os.path.join(self.apps_dir(), ref)]
        for p in cand:
            if os.path.isfile(os.path.join(p, containers.MANIFEST)) or \
                    os.path.isfile(os.path.join(p, APP_MANIFEST)):
                return p
        raise StudioError(f"no container or application named {ref!r}",
                          {"looked_in": cand,
                           "known": [c["name"] for c in
                                     self.list_containers()["containers"]]})

    def app_manifest(self, app: str) -> Dict[str, object]:
        """The container manifest, or a legacy application manifest."""
        cm = os.path.join(app, containers.MANIFEST)
        if os.path.isfile(cm):
            with open(cm, encoding="utf-8") as fh:
                return json.load(fh)
        with open(os.path.join(app, APP_MANIFEST), encoding="utf-8") as fh:
            return json.load(fh)

    def list_apps(self) -> Dict[str, object]:
        """Containers first; the legacy apps/ layout is folded in after."""
        out = [{"name": c["name"], "path": c["path"],
                "template": None, "built": c["built"],
                "container": True, "state": c["state"],
                "requires_operational": c["requires_operational"]}
               for c in self.list_containers()["containers"]]
        d = self.apps_dir()
        if os.path.isdir(d):
            for name in sorted(os.listdir(d)):
                p = os.path.join(d, name)
                if os.path.isfile(os.path.join(p, APP_MANIFEST)):
                    try:
                        m = self.app_manifest(p)
                    except (OSError, ValueError):
                        continue
                    img = os.path.join(p, "build", f"{m.get('name', name)}.brimg")
                    out.append({"name": m.get("name", name), "path": p,
                                "template": m.get("template"),
                                "container": False,
                                "built": os.path.isfile(img),
                                "requires_operational":
                                    m.get("pa21", {}).get(
                                        "requires_operational", [])})
        return {"schema": "PA21.STUDIO/APPS/1", "apps": out, "count": len(out),
                "apps_dir": d}

    def trust_dir(self) -> str:
        return os.path.join(self.root, "keys", "trusted")

    def trusted_keys(self) -> Dict[str, str]:
        """Every public key this studio will accept a signature from."""
        out: Dict[str, str] = {}
        own = self.signing_key()
        if own.get("available") and os.path.isfile(str(own["public_key"])):
            out[sha256_file(str(own["public_key"]))] = str(own["public_key"])
        d = self.trust_dir()
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                p = os.path.join(d, fn)
                if os.path.isfile(p):
                    out[sha256_file(p)] = p
        return out

    def trust(self, ref: str) -> Dict[str, object]:
        """Accept signatures made with this key from now on.

        `ref` is a public key file, or a container that carries one. Trusting
        a key is a decision the studio will not make on someone's behalf: a
        signed container from elsewhere runs on the raw development path until
        this is called, and every result says so.
        """
        p = os.path.abspath(os.path.expanduser(ref))
        if os.path.isdir(p) or not os.path.isfile(p):
            app = self.resolve_app(ref)
            man = self.app_manifest(app)
            name = man.get("name", os.path.basename(app))
            p = os.path.join(app, "image", f"{name}.pubkey")
            if not os.path.isfile(p):
                raise StudioError("that container carries no public key, so "
                                  "there is nothing to trust",
                                  {"container": app})
        if os.path.getsize(p) != 32:
            raise StudioError("a public key is 32 raw bytes", {"path": p,
                                                               "bytes":
                                                               os.path.getsize(p)})
        digest = sha256_file(p)
        os.makedirs(self.trust_dir(), exist_ok=True)
        self._own(self.trust_dir())
        dest = os.path.join(self.trust_dir(), f"{digest[:16]}.pub")
        shutil.copy2(p, dest)
        self._own(dest)
        return {"schema": "PA21.STUDIO/TRUST/1", "ok": True, "key": dest,
                "key_sha256": digest, "source": p,
                "trusted": len(self.trusted_keys()),
                "note": "containers signed with this key will now be verified "
                        "before they run, instead of falling back to the raw "
                        "development path"}

    def signing_key(self) -> Dict[str, object]:
        """This installation's signing key, if it has one."""
        if not self.installed:
            return {"available": False, "reason": "nothing is installed"}
        b = (self.manifest().get("binaries") or {}).get("brctl") or {}
        pub, priv = b.get("public_key"), b.get("private_key")
        ok = bool(pub and priv and os.path.isfile(pub) and os.path.isfile(priv))
        runner = (self.manifest().get("binaries") or {}).get("brrun") or {}
        return {"available": ok, "brctl": b.get("path"),
                "public_key": pub, "private_key": priv,
                "runner_verifies": bool(runner.get("verifies_signatures")),
                "reason": "" if ok else
                          "this installation has no signing key: either the "
                          "host has no OpenSSL, or brctl did not build here"}

    def _sign_image(self, image: str, out: str) -> Dict[str, object]:
        """Sign a built image with the runtime's own signing tool."""
        k = self.signing_key()
        if not k["available"]:
            return {"signed": False, "path": None, "reason": k["reason"]}
        r = subprocess.run([str(k["brctl"]), "sign-image", image, out,
                            str(k["private_key"])],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0 or not os.path.isfile(out):
            return {"signed": False, "path": None,
                    "reason": (r.stderr or r.stdout or "brctl refused").strip()
                              [-300:]}
        return {"signed": True, "path": out, "sha256": sha256_file(out),
                "bytes": os.path.getsize(out),
                "public_key": k["public_key"],
                "algorithm": "Ed25519, by the runtime's own brctl"}

    def build_app(self, ref: str) -> Dict[str, object]:
        """Compile the container's source, fold in the image, and re-seal it."""
        app = self.resolve_app(ref)
        man = self.app_manifest(app)
        rt = self._runtime()
        src = os.path.join(app, man.get("entry", "src/main.lctlc"))
        if not os.path.isfile(src):
            raise StudioError(f"the entry source {src} does not exist",
                              {"container": app})
        name = man.get("name", os.path.basename(app))
        is_container = os.path.isfile(os.path.join(app, containers.MANIFEST))
        out_dir = os.path.join(app, "image" if is_container else "build")
        os.makedirs(out_dir, exist_ok=True)
        image = os.path.join(out_dir, f"{name}.brimg")
        manifest = os.path.join(out_dir, f"{name}.provenance.json")
        brir = os.path.join(out_dir, f"{name}.brir.json")
        t0 = time.perf_counter()
        chk = lctlc.check(rt, src, executable=True)
        comp = lctlc.compile_image(rt, src, image, factory=True,
                                   manifest=manifest, brir=brir)
        prov = lctlc.provenance(rt, src, image, manifest)
        ver = lctlc.brim_verify(rt, image, manifest)
        # If this installation has a key, the image is signed with the
        # runtime's own brctl, into a second file beside the raw one. Both are
        # sealed into the container: the raw image is what the provenance
        # manifest describes, and the signed image is what a run verifies.
        signed = self._sign_image(image, os.path.join(out_dir,
                                                      f"{name}.signed.brimg"))
        if signed.get("signed"):
            # the public key travels inside the container, so another studio
            # can see WHICH key signed it -- and decide whether it trusts that
            # key, which is a different question from whether the bytes are
            # intact
            shutil.copy2(str(signed["public_key"]),
                         os.path.join(out_dir, f"{name}.pubkey"))
            signed["key_sha256"] = sha256_file(
                os.path.join(out_dir, f"{name}.pubkey"))
        sealed = None
        if is_container:
            try:
                rec = containers.record_build(app, image, manifest, brir)
            except containers.ContainerError as e:
                raise StudioError(str(e), e.detail)
            sealed = rec["seal"]
            self._write_registry()
        return {"schema": "PA21.STUDIO/BUILD_RESULT/1", "ok": True,
                "app": app, "container": app if is_container else None,
                "name": name, "source": src, "image": image,
                "provenance": manifest, "brir": brir,
                "image_bytes": os.path.getsize(image),
                "image_sha256": sha256_file(image),
                "source_sha256": (chk.get("json") or {}).get("sha256"),
                "check": chk.get("json"),
                "compiled": comp.get("json"),
                "provenance_check": prov.get("stdout", "")[:400],
                "image_verified": True,
                "verify_output": ver.get("json") or ver.get("stdout", "")[:400],
                "signed_image": signed.get("path"),
                "signature": signed,
                "sealed": bool(sealed),
                "seal": sealed,
                "state": "SEALED" if sealed else "BUILT",
                "seconds": round(time.perf_counter() - t0, 3)}

    def _image_path(self, app: str, name: str) -> str:
        for sub in ("image", "build"):
            p = os.path.join(app, sub, f"{name}.brimg")
            if os.path.isfile(p):
                return p
        return os.path.join(app, "image" if os.path.isfile(
            os.path.join(app, containers.MANIFEST)) else "build",
            f"{name}.brimg")

    # ------------------------------------------------------------------
    # containers
    # ------------------------------------------------------------------
    def list_containers(self, verify: bool = False) -> Dict[str, object]:
        """Every container in this studio, read from disk each time."""
        d = self.containers_dir()
        out = []
        if os.path.isdir(d):
            for nm in sorted(os.listdir(d)):
                p = os.path.join(d, nm)
                if not os.path.isdir(p):
                    continue
                try:
                    man = containers.read_manifest(p)
                except containers.ContainerError:
                    continue
                row = {"name": man.get("name", nm), "path": p,
                       "version": man.get("version"),
                       "state": man.get("state"),
                       "devices": (man.get("fabric") or {}).get("devices", []),
                       "adapter": (man.get("fabric") or {}).get("adapter"),
                       "requires_operational":
                           (man.get("pa21") or {}).get(
                               "requires_operational", []),
                       "built": man.get("state") == "SEALED"}
                if verify:
                    cl = containers.classify(p)
                    row["state"] = cl["state"]
                    row["sealed"] = bool(cl.get("sealed"))
                    row["seal_reason"] = cl.get("reason", "")
                    row["next"] = cl.get("next")
                    row["healthy"] = bool(cl.get("ok"))
                    row["gate"] = self.gate(p) if self.installed else None
                out.append(row)
        return {"schema": "PA21.STUDIO/CONTAINERS/1", "containers": out,
                "count": len(out), "containers_dir": d,
                "format": containers.FORMAT}

    # ------------------------------------------------------------------
    # the writing surface: for whatever is producing the source
    # ------------------------------------------------------------------
    def describe(self) -> Dict[str, object]:
        """The contract: language rules, tables, states, and the writing loop.

        Read out of the installed runtime where possible, so it is the
        runtime's own answer rather than this studio's recollection of it.
        """
        rt = None
        try:
            rt = self._runtime()
        except StudioError:
            pass
        d = describe_mod.describe(
            runtime=rt, studio_version=VERSION,
            container_format=containers.FORMAT,
            templates=lctlc.template_list())
        d["installed"] = self.installed
        d["root"] = self.root
        if self.installed:
            man = self.manifest()
            d["runtime_package"] = man.get("runtime", {}).get("name")
            d["execution_mode"] = man.get("execution_mode")
            d["pa21"] = {k: man.get("pa21", {}).get(k)
                         for k in ("found", "round", "operational", "items")}
        return d

    def doctor(self) -> Dict[str, object]:
        """What this host can do, what it cannot, and what is merely untested.

        The studio ships Windows entry points and a Windows build path. Saying
        so is not the same as having run them, and a tool that implies a
        platform works because a .cmd file exists is misleading its user. So
        this reports three separate things: what is present, what has been
        exercised here just now, and what remains untested on this host.
        """
        pr = probe_mod.probe_all(refresh=True)
        cc = pr["findings"]["c_compiler"]["value"]
        kind = probe_mod.compiler_kind(cc)
        exercised: List[Dict[str, object]] = []

        def ex(name: str, ok: bool, detail: str):
            exercised.append({"check": name, "ok": bool(ok), "detail": detail})

        # paths with spaces and non-ASCII are where a Windows path breaks, so
        # they are exercised rather than assumed
        tmp = tempfile.mkdtemp(prefix="pa21doctor-")
        try:
            odd = os.path.join(tmp, "a folder with spaces", "ünïcode")
            os.makedirs(odd, exist_ok=True)
            f = os.path.join(odd, "seal me.txt")
            with open(f, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("x\n")
            sealed = containers.seal(odd)
            v = containers.verify_seal(odd)
            ex("paths_with_spaces_and_non_ascii", bool(v["sealed"]),
               f"sealed and re-verified {sealed['files']} file(s) under "
               f"{odd!r}")
            with open(os.path.join(odd, containers.SEAL), encoding="utf-8") as fh:
                line = fh.read().strip().split("\n")[0]
            ex("seal_uses_forward_slashes", "\\" not in line.split("  ", 1)[-1],
               "a seal written on one platform is readable on the other")
        except OSError as e:
            ex("paths_with_spaces_and_non_ascii", False, str(e))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        ex("default_root_for_this_platform", True, default_root())
        if self.installed:
            man = self.manifest()
            runner = (man.get("binaries", {}).get("brrun") or {}).get("path")
            ex("runner_present_and_executable",
               bool(runner and os.path.isfile(runner)),
               str(runner))
            if runner and os.path.isfile(runner):
                st = self._run_binary([runner, "selftest"])
                ex("vm_core_selftest_here", st.get("selftest") == "PASS",
                   json.dumps(st))
        untested: List[str] = []
        if os.name != "nt":
            untested.append(
                "the Windows entry points (studio.cmd, INSTALL.cmd) and the "
                "%LOCALAPPDATA% root: written, and not executed on this host, "
                "which is " + platform.system())
            untested.append(
                "the MSVC build line: constructed by probe.compile_command "
                "and unit-checked here, but no cl.exe has compiled the runner "
                "on this host")
        else:
            if kind == "msvc":
                untested.append(
                    "signing on MSVC: brctl is POSIX C and does not build "
                    "with cl.exe; install a MinGW toolchain for signed images")
        if not pr["can_execute_images"]:
            untested.append("executing images: no C toolchain on this host")
        if not pr.get("can_build_signing_cli"):
            untested.append("signing images: no OpenSSL development files")
        return {"schema": "PA21.STUDIO/DOCTOR/1",
                "platform": {"system": platform.system(),
                             "release": platform.release(),
                             "python": platform.python_version(),
                             "os_name": os.name,
                             "compiler": cc, "compiler_kind": kind,
                             "shell_entry": "studio.cmd" if os.name == "nt"
                                            else "studio.sh"},
                "exercised": exercised,
                "untested_here": untested,
                "ok": all(e["ok"] for e in exercised),
                "summary": f"{sum(1 for e in exercised if e['ok'])}/"
                           f"{len(exercised)} platform checks passed"
                           + (f", {len(untested)} thing(s) untested on this "
                              f"host" if untested else ""),
                "note": "an untested item is not a broken one; it is one this "
                        "host cannot demonstrate, and the studio would rather "
                        "say that than imply otherwise"}

    def abi_evidence(self, only: Optional[str] = None) -> Dict[str, object]:
        """Demonstrate the ABI the description states, service by service.

        The ledger's rule is that nothing is operational because a file says
        so. The studio's description of the language is a file, so it gets the
        same treatment: every claim is a program, run here, on this runtime.
        """
        if not self.installed:
            raise StudioError("no studio is installed at this root",
                              {"root": self.root})
        return abi_mod.evidence(self, only)

    def compile_probe(self, source: str) -> Optional[str]:
        """Ask the runtime's compiler about a source, and return its refusal.

        Nothing is built and nothing is written outside a temporary file: this
        is the question `try` and `fix` both need answered, and neither should
        have to create a container to ask it.
        """
        rt = self._runtime()
        tmp = tempfile.mkdtemp(prefix="pa21probe-")
        try:
            p = os.path.join(tmp, "main.lctlc")
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(source)
            try:
                lctlc.check(rt, p)
                return None
            except lctlc.ToolchainError as e:
                return str(e).strip()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def fix_source(self, source: str) -> Dict[str, object]:
        """Apply the corrections that have one legal form, and report them.

        The studio already names the rule a refusal breaks and what to do
        about it. Where "what to do about it" admits exactly one edit, doing
        it and reporting it is better than describing it and waiting. Where it
        does not -- a missing immediate, an unknown branch target -- this
        stops and says which decision it will not make for you.
        """
        out = repair_mod.repair(source, self.compile_probe)
        out["changed"] = out["source"] != source
        return out

    def try_source(self, source: str, keep: Optional[str] = None,
                   requires_operational: Sequence[int] = (),
                   adapter: str = "deterministic",
                   budget: Optional[int] = None,
                   console_in: Optional[bytes] = None,
                   run: bool = True,
                   fix: bool = False,
                   mailbox_in: Optional[bytes] = None,
                   state: str = "fresh") -> Dict[str, object]:
        """One call: source in, verdict out.

        A candidate program is built in a scratch container that is removed
        again, so an agent iterating fifty times does not leave fifty
        containers behind. The verdict carries the compiler's own refusal when
        it does not compile, and the rule that refusal maps to -- which is the
        only part of this an author can act on.

        `keep=NAME` promotes the candidate into the registry as a container
        under that name instead of discarding it.
        """
        if not source or not source.strip():
            raise StudioError("nothing to compile", {"source": ""})
        repairs: Optional[Dict[str, object]] = None
        if fix:
            # the corrections are applied before the container is scaffolded,
            # so what gets sealed is the source that compiles -- not the one
            # that did not, with a note attached
            repairs = self.fix_source(source)
            if repairs.get("changed"):
                source = str(repairs["source"])
        scratch = os.path.join(self.root, ".scratch")
        os.makedirs(scratch, exist_ok=True)
        self._own(scratch)
        tmpname = "candidate_" + hashlib.sha256(
            (source + str(time.time())).encode("utf-8")).hexdigest()[:10]
        cdir = os.path.join(scratch, tmpname)
        out: Dict[str, object] = {"schema": "PA21.STUDIO/TRY_RESULT/1",
                                  "compiled": False, "ran": False,
                                  "kept": None, "adapter": adapter}
        if repairs is not None:
            out["repairs"] = repairs.get("repairs")
            out["repaired"] = bool(repairs.get("changed"))
            out["source"] = source if repairs.get("changed") else None
            if not repairs.get("compiled"):
                out["repair_declined"] = repairs.get("declined")
                out["repair_reason"] = repairs.get("reason")
        try:
            made = containers.scaffold(
                cdir, tmpname, "0.0.0", source,
                {"budget": budget or 4096,
                 "pa21": {"requires_operational":
                          [int(i) for i in requires_operational]},
                 "expect": {}, "fabric": {"adapter": adapter}},
                (self.manifest().get("runtime", {}) if self.installed else {}),
                VERSION)
            out["container_manifest"] = made["manifest"]
            try:
                b = self.build_app(cdir)
                out["compiled"] = True
                out["image_bytes"] = b["image_bytes"]
                out["image_sha256"] = b["image_sha256"]
                out["instructions"] = (b.get("compiled") or {}).get(
                    "instruction_count")
                out["capabilities"] = made["manifest"].get("capabilities")
                out["services"] = made["manifest"].get("services")
                out["devices"] = (made["manifest"].get("fabric") or {}).get(
                    "devices")
            except (StudioError, lctlc.ToolchainError) as e:
                msg = str(e)
                out["error"] = msg
                out["hint"] = describe_mod.explain(msg)
                return out
            if run:
                try:
                    r = self.run_app(cdir, adapter=adapter,
                                     console_in=console_in,
                                     mailbox_in=mailbox_in, state=state,
                                     check_expectations=False)
                    out.update({"ran": bool(r.get("ran")),
                                "status_name": r.get("status_name"),
                                "machine_status": r.get("machine_status"),
                                "trap": r.get("trap"),
                                "registers": r.get("registers"),
                                "memory_head_hex": r.get("memory_head_hex"),
                                "fabric": r.get("fabric"),
                                "seconds": r.get("seconds")})
                    if r.get("ran"):
                        out["fault"] = r.get("fault")
                        out["effects"] = describe_mod.effects(
                            list(out.get("services") or []),
                            r.get("fabric") or {}, r.get("registers"),
                            r.get("memory_head_hex"),
                            console_in=bool(console_in),
                            service_calls=containers.service_calls(source))
                        out["memory_head_hex"] = r.get("memory_head_hex")
                    if not r.get("ran"):
                        out["error"] = r.get("reason")
                        out["gate"] = r.get("gate")
                except StudioError as e:
                    out["error"] = str(e)
                    out["hint"] = describe_mod.explain(str(e))
            if keep:
                dest = os.path.join(self.containers_dir(), keep)
                if os.path.exists(dest):
                    raise StudioError(f"a container named {keep!r} already "
                                      f"exists", {"path": dest})
                os.makedirs(self.containers_dir(), exist_ok=True)
                shutil.move(cdir, dest)
                cdir = None
                # the promoted container is renamed inside its own manifest
                cman = containers.read_manifest(dest)
                cman["name"] = keep
                cman["version"] = "0.1.0"
                with open(os.path.join(dest, containers.MANIFEST), "w",
                          encoding="utf-8", newline="\n") as fh:
                    json.dump(cman, fh, indent=2, sort_keys=True)
                    fh.write("\n")
                for ext in (".brimg", ".signed.brimg", ".provenance.json",
                            ".brir.json"):
                    old = os.path.join(dest, "image", tmpname + ext)
                    if os.path.isfile(old):
                        os.replace(old, os.path.join(dest, "image", keep + ext))
                cman["image"] = f"image/{keep}.brimg"
                cman["provenance"] = f"image/{keep}.provenance.json"
                with open(os.path.join(dest, containers.MANIFEST), "w",
                          encoding="utf-8", newline="\n") as fh:
                    json.dump(cman, fh, indent=2, sort_keys=True)
                    fh.write("\n")
                containers.seal(dest)
                self._own(dest)
                self._write_registry()
                out["kept"] = dest
        except containers.ContainerError as e:
            raise StudioError(str(e), e.detail)
        finally:
            if cdir and os.path.isdir(cdir):
                shutil.rmtree(cdir, ignore_errors=True)
        out["ok"] = bool(out["compiled"] and (not run or out.get("trap") == 0))
        return out

    def _fix_container_source(self, app: str) -> Dict[str, object]:
        """Repair a container's source in place, and report what changed."""
        path = os.path.join(app, "src", "main.lctlc")
        if not os.path.isfile(path):
            return {"repairs": [], "changed": False}
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        out = self.fix_source(text)
        if out.get("changed"):
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(str(out["source"]))
            out["written"] = path
        return out

    def watch(self, ref: str, on_event: Optional[Event] = None,
              interval: float = 0.6, once: bool = False,
              run: bool = True, iterations: int = 0,
              fix: bool = False) -> Dict[str, object]:
        """Build and run a container whenever its source changes on disk.

        This is the authoring loop for an editor that is not this program:
        keep the file open in whatever you write in, save, and the studio
        builds it, runs it, and reports -- including the compiler's refusal
        when the source does not compile, which is the message you actually
        need while writing.

        It watches `src/` only. Nothing else in a container should change
        while you are authoring, and if it does, the seal is the right place
        to hear about it.

        With `fix=True`, a refusal whose correction has only one legal form is
        applied to the file on disk before the round is called a failure, and
        the edit is reported. Your editor will show the corrected line the
        next time it looks at the file. Anything needing a decision is still
        handed back to you.
        """
        emit = _emitter(on_event)
        app = self.resolve_app(ref)
        src_dir = os.path.join(app, "src")
        name = self.app_manifest(app).get("name", os.path.basename(app))

        def stamp() -> Dict[str, float]:
            out = {}
            for r, _d, fs in os.walk(src_dir):
                for f in fs:
                    fp = os.path.join(r, f)
                    try:
                        out[fp] = os.path.getmtime(fp)
                    except OSError:
                        pass
            return out

        last = None
        rounds = 0
        history: List[Dict[str, object]] = []
        emit({"phase": "watching", "message": f"{src_dir} — save to rebuild",
              "container": name})
        try:
            while True:
                now = stamp()
                if now != last:
                    last = now
                    rounds += 1
                    entry: Dict[str, object] = {"round": rounds,
                                                "at": utc_now()}
                    if fix:
                        rep = self._fix_container_source(app)
                        if rep.get("repairs"):
                            entry["repairs"] = rep["repairs"]
                            for r in rep["repairs"]:
                                emit({"phase": "fixed", "ok": True,
                                      "message": f"{r['refusal']} -> "
                                                 f"{r['change']}"})
                            last = stamp()      # our own write is not an edit
                    try:
                        b = self.build_app(app)
                        entry["built"] = True
                        entry["image_sha256"] = b["image_sha256"]
                        emit({"phase": "built",
                              "message": f"{b['image_bytes']} bytes, "
                                         f"sealed",
                              "ok": True})
                        if run:
                            r = self.run_app(app)
                            entry["run"] = {k: r.get(k) for k in
                                            ("ran", "ok", "status_name",
                                             "trap", "registers", "fabric",
                                             "reason")}
                            emit({"phase": "ran" if r.get("ran") else "refused",
                                  "ok": bool(r.get("ok")),
                                  "message": (f"{r.get('status_name')} "
                                              f"trap={r.get('trap')} "
                                              + " ".join(
                                                  f"{k}={v}" for k, v in
                                                  (r.get("registers") or {})
                                                  .items() if v))
                                  if r.get("ran") else str(r.get("reason"))})
                    except (StudioError, lctlc.ToolchainError) as e:
                        entry["built"] = False
                        entry["error"] = str(e)
                        # a compiler refusal is the point of the loop, not a
                        # crash in it: report it and keep watching
                        emit({"phase": "refused", "ok": False,
                              "message": str(e).splitlines()[0][:200]})
                    history.append(entry)
                    if once or (iterations and rounds >= iterations):
                        break
                elif once and rounds:
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            emit({"phase": "stopped", "message": "watching ended"})
        return {"schema": "PA21.STUDIO/WATCH_RESULT/1", "container": app,
                "name": name, "rounds": rounds, "history": history}

    def pack_container(self, ref: str, out_file: Optional[str] = None
                       ) -> Dict[str, object]:
        """Zip a container into one `.pa21c` file, sealed as it stands."""
        app = self.resolve_app(ref)
        if not os.path.isfile(os.path.join(app, containers.MANIFEST)):
            raise StudioError("that is a legacy application directory, not a "
                              "container; create it again with `studio new` "
                              "to get one", {"path": app})
        man = containers.read_manifest(app)
        default = os.path.join(os.path.dirname(app.rstrip("/\\")),
                               f"{man['name']}_{man['version']}"
                               f"{containers.SUFFIX}")
        try:
            path = containers.pack(app, out_file or default)
        except containers.ContainerError as e:
            raise StudioError(str(e), e.detail)
        return {"schema": "PA21.STUDIO/PACK_RESULT/1", "ok": True,
                "container": app, "archive": path,
                "bytes": os.path.getsize(path),
                "sha256": sha256_file(path),
                "name": man["name"], "version": man["version"],
                "state": man.get("state")}

    def import_container(self, source: str, force: bool = False
                         ) -> Dict[str, object]:
        """Bring a container built elsewhere into this studio, verified first."""
        src = os.path.abspath(os.path.expanduser(source))
        if not os.path.exists(src):
            raise StudioError(f"nothing at {src}", {"source": src})
        tmp = None
        try:
            if os.path.isfile(src):
                tmp = tempfile.mkdtemp(prefix="pa21c-import-")
                cdir = containers.unpack(src, tmp)
            else:
                cdir = src
            insp = containers.inspect(cdir)
            if not insp.get("container"):
                raise StudioError(f"{src} is not a container: "
                                  f"{insp.get('reason')}", insp)
            if not insp["sealed"]:
                raise StudioError(
                    f"refusing to import a container whose seal does not "
                    f"match its contents: {insp['seal'].get('reason')}", insp)
            man = insp["manifest"]
            dest = os.path.join(self.containers_dir(), str(man["name"]))
            if os.path.exists(dest) and not force:
                raise StudioError(f"a container named {man['name']!r} is "
                                  f"already installed here", {"path": dest})
            if os.path.exists(dest):
                shutil.rmtree(dest)
            os.makedirs(self.containers_dir(), exist_ok=True)
            shutil.copytree(cdir, dest)
            after = containers.verify_seal(dest)
            if not after["sealed"]:
                shutil.rmtree(dest, ignore_errors=True)
                raise StudioError("the container did not survive the copy "
                                  "intact; nothing was installed", after)
            self._own(dest)
            self._write_registry()
            return {"schema": "PA21.STUDIO/IMPORT_RESULT/1", "ok": True,
                    "name": man["name"], "version": man.get("version"),
                    "path": dest, "state": man.get("state"),
                    "seal": after, "gate": self.gate(dest),
                    "devices": (man.get("fabric") or {}).get("devices", [])}
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)

    def remove_container(self, ref: str) -> Dict[str, object]:
        """Remove one container, and only that one."""
        app = self.resolve_app(ref)
        if not app.startswith(self.containers_dir()):
            raise StudioError("that container is not inside this studio's "
                              "registry, so the studio will not delete it",
                              {"path": app})
        man = self.app_manifest(app)
        shutil.rmtree(app)
        self._disown(app)
        self._write_registry()
        return {"schema": "PA21.STUDIO/REMOVE_RESULT/1", "ok": True,
                "removed": app, "name": man.get("name"),
                "remaining": self.list_containers()["count"]}

    def gate(self, ref: str) -> Dict[str, object]:
        """Does the bound PA21 delivery satisfy this application's ledger
        requirements? Fails closed."""
        app = self.resolve_app(ref)
        man = self.app_manifest(app)
        req = [int(i) for i in man.get("pa21", {}).get(
            "requires_operational", [])]
        if not req:
            return {"required": [], "satisfied": True,
                    "reason": "this application declares no ledger "
                              "requirements"}
        sman = self.manifest()
        pa21 = sman.get("pa21", {})
        if not pa21.get("found"):
            return {"required": req, "satisfied": False,
                    "reason": "this application requires ledger items, and no "
                              "PA21 delivery is bound to this installation"}
        lp = pa21.get("ledger_path")
        if not lp or not os.path.isfile(lp):
            return {"required": req, "satisfied": False,
                    "reason": f"the bound ledger {lp} is no longer readable"}
        led = pa21_ledger.Ledger(lp)
        res = led.require(req)
        res["reason"] = ("every required item is OPERATIONAL"
                         if res["satisfied"] else
                         "the delivery does not carry every required item as "
                         "OPERATIONAL")
        return res

    def state_dir(self) -> str:
        return os.path.join(self.root, "state")

    def state_path(self, name: str) -> str:
        return os.path.join(self.state_dir(), f"{name}.state")

    # ------------------------------------------------------------------
    # the fabric as a picture you can run -- the reversible TIFF fabric
    # ------------------------------------------------------------------
    def fabric_path(self, name: str) -> str:
        return os.path.join(self.state_dir(), f"{name}.fabric.tif")

    def _empty_blob(self) -> bytes:
        return fabric_tif.build_blob(
            {"version": 1, "monotonic": 0, "clock": 0, "slots": [b""] * 8})

    def fabric_init(self, ref: str, cols: int = 2,
                    from_state: bool = True) -> Dict[str, object]:
        """Create a container's fabric image, before any tick has run.

        The fabric starts from whatever binary state the container already has
        (so an existing run's fabric becomes visible), or empty. A project is a
        container; its fabric is one picture beside it in the registry.
        """
        app = self.resolve_app(ref)
        name = self.app_manifest(app).get("name", os.path.basename(app))
        os.makedirs(self.state_dir(), exist_ok=True)
        self._own(self.state_dir())
        blob = self._empty_blob()
        sp = self.state_path(name)
        if from_state and os.path.isfile(sp):
            blob = open(sp, "rb").read()
        tif = self.fabric_path(name)
        info = fabric_tif.write_tif(blob, tif, cols=cols, tick=0)
        self._own(tif)
        return {"schema": "PA21.STUDIO/FABRIC_INIT/1", "ok": True,
                "container": name, "fabric": tif, "tick": 0,
                "grid": info["grid"], "bytes": info["bytes"],
                "note": "the fabric is now an image; a tick reads it, runs the "
                        "container against it, and writes it back"}

    def fabric_tick(self, ref: str, adapter: str = "deterministic",
                    mailbox_in: Optional[bytes] = None,
                    view: bool = True) -> Dict[str, object]:
        """One step of the reversible loop: image in, run, image out.

        Read the fabric image into the binary fabric, execute the container
        against exactly that state, and write the mutated fabric back as a new
        page. The read is the reverse of the write, so an edit made to the
        image from outside is picked up here -- the picture is the live state.
        """
        app = self.resolve_app(ref)
        name = self.app_manifest(app).get("name", os.path.basename(app))
        tif = self.fabric_path(name)
        if not os.path.isfile(tif):
            self.fabric_init(ref)
        prev = fabric_tif.read_tif(tif)
        # materialise the image as the binary fabric the VM's host consumes,
        # then run against precisely that -- reversibility in one line
        run_state = os.path.join(self.state_dir(), f"{name}.fabric.state")
        with open(run_state, "wb") as fh:
            fh.write(prev["blob"])
        r = self.run_app(ref, adapter=adapter, state="keep",
                         state_file=run_state, mailbox_in=mailbox_in,
                         check_expectations=False)
        if not r.get("ran"):
            return {"schema": "PA21.STUDIO/FABRIC_TICK/1", "ok": False,
                    "container": name, "ran": False,
                    "reason": r.get("reason"), "fault": r.get("fault")}
        new_blob = open(run_state, "rb").read()
        history = fabric_tif.load_frames(tif)
        tick = int(prev.get("tick", 0)) + 1
        info = fabric_tif.write_tif(new_blob, tif, tick=tick, history=history)
        self._own(tif)
        out = {"schema": "PA21.STUDIO/FABRIC_TICK/1", "ok": bool(r.get("ok")),
               "container": name, "ran": True, "tick": tick,
               "fabric": tif, "pages": info["pages"],
               "registers": r.get("registers"),
               "status_name": r.get("status_name"), "trap": r.get("trap"),
               "fabric_changed": new_blob != prev["blob"],
               "monotonic": (r.get("fabric") or {}).get("monotonic")}
        if view:
            v = self.fabric_view(ref)
            out["view"] = v.get("view")
        return out

    def fabric_live(self, ref: str, ticks: int = 0, interval: float = 0.5,
                    adapter: str = "deterministic",
                    on_event: Optional[Event] = None,
                    stop_when_still: bool = False) -> Dict[str, object]:
        """Run the fabric in constant flux: read, execute, write, repeat.

        This is the reversible language as a distributed fabric demands it --
        the image is the state, the state is executed, the result is the image,
        and the next tick reads whatever the image now says, including any
        change made to it from outside while the loop runs. It stops after
        `ticks` steps, or when the fabric stops changing if asked, or when
        interrupted.
        """
        emit = _emitter(on_event)
        app = self.resolve_app(ref)
        name = self.app_manifest(app).get("name", os.path.basename(app))
        tif = self.fabric_path(name)
        if not os.path.isfile(tif):
            self.fabric_init(ref)
        emit({"phase": "live", "message": f"{tif} — the fabric is running",
              "container": name})
        history: List[Dict[str, object]] = []
        seen_mtime = os.path.getmtime(tif) if os.path.isfile(tif) else 0
        n = 0
        try:
            while True:
                n += 1
                # an edit made to the image between ticks is part of the state
                now = os.path.getmtime(tif) if os.path.isfile(tif) else 0
                external = (now != seen_mtime)
                t = self.fabric_tick(ref, adapter=adapter, view=True)
                seen_mtime = os.path.getmtime(tif) if os.path.isfile(tif) else 0
                rec = {"tick": t.get("tick"), "changed": t.get("fabric_changed"),
                       "external_edit_seen": external,
                       "monotonic": t.get("monotonic"),
                       "status": t.get("status_name")}
                history.append(rec)
                emit({"phase": "tick", "ok": bool(t.get("ok")),
                      "message": (f"tick {t.get('tick')}: "
                                  f"{'changed' if t.get('fabric_changed') else 'still'}"
                                  + (", picked up an outside edit" if external
                                     else "")
                                  + f", monotonic {t.get('monotonic')}")})
                if not t.get("ran"):
                    break
                if stop_when_still and not t.get("fabric_changed") \
                        and not external:
                    emit({"phase": "converged",
                          "message": "the fabric stopped changing"})
                    break
                if ticks and n >= ticks:
                    break
                if interval:
                    time.sleep(interval)
        except KeyboardInterrupt:
            emit({"phase": "stopped", "message": "interrupted"})
        return {"schema": "PA21.STUDIO/FABRIC_LIVE/1", "ok": True,
                "container": name, "fabric": tif, "ticks": len(history),
                "history": history,
                "note": "each tick read the image, executed it, and wrote it "
                        "back; an outside edit to the image is read on the "
                        "next tick"}

    def fabric_view(self, ref: str, out: Optional[str] = None,
                    scale: int = 16) -> Dict[str, object]:
        """Render the fabric's current field as a viewable PNG."""
        app = self.resolve_app(ref)
        name = self.app_manifest(app).get("name", os.path.basename(app))
        tif = self.fabric_path(name)
        if not os.path.isfile(tif):
            raise StudioError("this container has no fabric image yet; "
                              "studio fabric init " + name + " makes one",
                              {"container": name})
        out = out or os.path.join(self.state_dir(), f"{name}.fabric.png")
        info = fabric_tif.render_view(tif, out, scale=scale)
        self._own(out)
        return {"schema": "PA21.STUDIO/FABRIC_VIEW/1", "ok": True,
                "container": name, "fabric": tif, **info}

    def fabric_frames(self, ref: str) -> Dict[str, object]:
        """The immutable frame history the fabric image has accumulated."""
        app = self.resolve_app(ref)
        name = self.app_manifest(app).get("name", os.path.basename(app))
        tif = self.fabric_path(name)
        if not os.path.isfile(tif):
            raise StudioError("this container has no fabric image yet",
                              {"container": name})
        fr = fabric_tif.frames(tif)
        return {"schema": "PA21.STUDIO/FABRIC_FRAMES/1", "ok": True,
                "container": name, "fabric": tif, "pages": len(fr),
                "frames": fr}

    def reset_state(self, ref: str) -> Dict[str, object]:
        """Throw away a container's carried fabric state."""
        app = self.resolve_app(ref)
        name = self.app_manifest(app).get("name", os.path.basename(app))
        p = self.state_path(name)
        existed = os.path.isfile(p)
        if existed:
            os.remove(p)
        return {"schema": "PA21.STUDIO/STATE_RESET/1", "ok": True,
                "container": name, "path": p, "existed": existed,
                "note": "the next run starts from an empty fabric"}

    def run_app(self, ref: str, budget: Optional[int] = None,
                check_expectations: bool = True,
                skip_gate: bool = False, adapter: Optional[str] = None,
                seed: Optional[int] = None, console_in: Optional[bytes] = None,
                devices: Optional[bool] = None,
                build_if_stale: bool = False,
                state: Optional[str] = None,
                mailbox_in: Optional[bytes] = None,
                signed: Optional[bool] = None,
                trace: Optional[int] = None,
                state_file: Optional[str] = None) -> Dict[str, object]:
        """Execute the application on the RAM-backed device fabric.

        `adapter` selects the backend kind: "memory" seeds entropy and the
        clock per run, "deterministic" uses the replay substitutes so two runs
        of one image produce identical bytes. Either way the fabric is in this
        process's memory -- no file is opened and no socket exists.
        """
        app = self.resolve_app(ref)
        man = self.app_manifest(app)
        name = man.get("name", os.path.basename(app))
        image = self._image_path(app, name)
        if not os.path.isfile(image):
            build = self.build_app(app)
            image = build["image"]
        is_container = os.path.isfile(os.path.join(app, containers.MANIFEST))
        cstate = containers.classify(app) if is_container else None
        if cstate is not None and cstate["state"] in ("DRAFT", "SOURCE_ONLY"):
            if build_if_stale:
                self.build_app(app)
                image = self._image_path(app, name)
                cstate = containers.classify(app)
            else:
                return {"schema": "PA21.STUDIO/RUN_RESULT/1", "ok": False,
                        "ran": False, "app": app, "name": name,
                        "state": cstate["state"], "seal": cstate["seal"],
                        "reason": cstate["reason"],
                        "note": "this is what an open editor looks like, not "
                                "damage. Build it and the studio will run the "
                                "image that came from the source you have "
                                "now.",
                        "next": cstate["next"],
                        "hint": f"studio run {name} --build"}
        if cstate is not None and cstate["state"] == "BROKEN":
            return {"schema": "PA21.STUDIO/RUN_RESULT/1", "ok": False,
                    "ran": False, "app": app, "name": name,
                    "state": "BROKEN", "seal": cstate["seal"],
                    "reason": cstate["reason"],
                    "note": "files outside src/ changed under the seal, so the "
                            "image is no longer the one this container "
                            "describes",
                    "next": cstate["next"]}
        seal_state = cstate["seal"] if cstate else None
        gate = {"satisfied": True, "reason": "gate skipped"} if skip_gate \
            else self.gate(app)
        if not gate.get("satisfied"):
            return {"schema": "PA21.STUDIO/RUN_RESULT/1", "ok": False,
                    "ran": False, "app": app, "name": name,
                    "gate": gate,
                    "reason": str(gate.get("reason")),
                    "note": "the application declares PA21 ledger items it "
                            "needs; the studio does not run it against a "
                            "delivery that does not carry them"}
        runner = self._runner()
        b = int(budget or man.get("budget", 4096))
        fab = man.get("fabric") or {}
        kind = adapter or fab.get("adapter") or "memory"
        sd = seed if seed is not None else fab.get("seed", 20260816)
        cin = console_in
        if cin is None and fab.get("console_in_hex"):
            cin = bytes.fromhex(str(fab["console_in_hex"]))
        use_devices = fab.get("extension_devices", False) if devices is None \
            else devices
        # A signed image, verified by the VM through the HAL before the first
        # instruction runs, whenever this installation can do it. The raw
        # image is still there and `signed=False` still runs it, because the
        # difference between the two is the thing worth being able to show.
        k = self.signing_key()
        signed_image = os.path.join(os.path.dirname(image),
                                    os.path.basename(image)[:-6]
                                    + ".signed.brimg")
        # Which key can verify THIS container: the one it was signed with, if
        # this studio trusts it. A container built elsewhere is signed with a
        # key this studio has never seen, and the honest answer is to run it
        # on the raw path and say why -- not to pretend the signature checked
        # out, and not to refuse a container that is otherwise sound.
        own_key = os.path.join(os.path.dirname(image),
                               os.path.basename(image)[:-6] + ".pubkey")
        trust_reason = ""
        verify_key = None
        if os.path.isfile(signed_image):
            trusted = self.trusted_keys()
            if os.path.isfile(own_key):
                d = sha256_file(own_key)
                verify_key = trusted.get(d)
                if not verify_key:
                    trust_reason = ("this container was signed with a key "
                                    "this studio does not trust; run "
                                    f"`studio trust {name}` to accept it")
            elif k["available"]:
                verify_key = str(k["public_key"])
            else:
                trust_reason = k["reason"]
        use_signed = bool(verify_key and k["runner_verifies"]) \
            if signed is None else bool(signed)
        if use_signed and not verify_key:
            verify_key = str(k["public_key"]) if k["available"] else None
        if signed and not (k["available"] and k["runner_verifies"]):
            raise StudioError("this installation cannot verify signatures",
                              {"reason": k["reason"]})
        if signed and not os.path.isfile(signed_image):
            raise StudioError("this container holds no signed image; build it "
                              "again on an installation that has a key",
                              {"expected": signed_image})
        cmd = [runner, "run", signed_image if use_signed else image,
               "--budget", str(b),
               "--adapter", str(kind), "--seed", str(int(sd))]
        if use_signed and verify_key:
            cmd += ["--verify-key", str(verify_key), "--require-signature"]
        if trace:
            cmd += ["--trace", str(int(trace))]
        if cin:
            cmd += ["--console-in", cin.hex()]
        if use_devices:
            cmd.append("--devices")
        # The fabric is in RAM, so it starts empty unless this run is told to
        # carry the previous one's state. That is a decision, never a default:
        # a run that silently depends on an earlier one is not reproducible,
        # and a persistent block device that forgets is not persistent. A
        # container that needs the state says so in its own manifest.
        want_state = state if state is not None else fab.get("state", "fresh")
        if str(want_state) not in ("fresh", "keep"):
            raise StudioError("state must be 'fresh' or 'keep'",
                              {"state": want_state})
        sp = None
        if str(want_state) == "keep":
            os.makedirs(self.state_dir(), exist_ok=True)
            self._own(self.state_dir())
            # a caller can point the run at a specific fabric file -- the live
            # TIFF loop uses this to run against the image it just read
            sp = state_file or self.state_path(name)
            cmd += ["--state", sp]
        mb = mailbox_in
        if mb is None and fab.get("mailbox_in_hex"):
            mb = bytes.fromhex(str(fab["mailbox_in_hex"]))
        if mb:
            cmd += ["--mailbox-in", mb.hex()]
        t0 = time.perf_counter()
        res = self._run_binary(cmd)
        secs = round(time.perf_counter() - t0, 4)
        out = {"schema": "PA21.STUDIO/RUN_RESULT/1", "ran": True,
               "app": app, "name": name, "image": image,
               "budget": b, "seconds": secs, "gate": gate,
               "execution_mode": res.get("execution_mode"),
               "signature": dict(res.get("signature") or {},
                                 key_used=verify_key,
                                 not_verified_because=trust_reason),
               "image_run": signed_image if use_signed else image,
               "backend": res.get("backend"),
               "adapter": res.get("adapter"),
               "seed": res.get("seed"),
               "status": res.get("status"),
               "status_name": res.get("status_name"),
               "machine_status": res.get("machine_status"),
               "trap": res.get("trap"),
               "registers": res.get("registers", {}),
               "memory_head_hex": res.get("memory_head_hex"),
               "fabric": res.get("fabric", {}),
               "fabric_state": dict(res.get("state") or {},
                                    mode=str(want_state), path=sp),
               "seal": seal_state,
               "state": (cstate or {}).get("state"),
               "raw": res}
        # what the run visibly did, service by service -- the same reading a
        # candidate gets from `try`, so a container behaves no differently
        # from the scratch it was promoted out of
        # a trap code alone names the kind of failure; the row that did it is
        # in the VM's trap frame and the compiler's own instruction map, and
        # joining them is the difference between a diagnosis and a number
        out["fault"] = fault_mod.explain(
            out, image, os.path.join(app, man.get("entry", "src/main.lctlc")),
            self._runtime())
        out["effects"] = describe_mod.effects(
            list(man.get("services") or []), res.get("fabric") or {},
            res.get("registers"), res.get("memory_head_hex"),
            console_in=bool(cin),
            service_calls=list(man.get("service_calls") or []))
        expect = man.get("expect") or {}
        if check_expectations and expect:
            checks = []
            for key in ("status_name", "trap", "status"):
                if key in expect:
                    checks.append({"field": key, "expected": expect[key],
                                   "actual": out.get(key),
                                   "ok": out.get(key) == expect[key]})
            for reg, val in (expect.get("registers") or {}).items():
                actual = (out.get("registers") or {}).get(reg)
                checks.append({"field": f"registers.{reg}", "expected": val,
                               "actual": actual, "ok": actual == val})
            # an application may also assert on what the fabric holds
            # afterwards: what reached the console, what the block device
            # kept, where the monotonic counter stands
            for key, val in (expect.get("fabric") or {}).items():
                actual = (out.get("fabric") or {}).get(key)
                checks.append({"field": f"fabric.{key}", "expected": val,
                               "actual": actual, "ok": actual == val})
            out["expectation_checks"] = checks
            out["expectations_met"] = all(c["ok"] for c in checks)
            # meeting a declared expectation IS success, even when what the
            # container declares is a trap: a container that demonstrates a
            # DIV_ZERO is right when it traps and wrong when it does not, and
            # an `ok` that also insisted on trap==0 could never say so
            out["ok"] = bool(out["expectations_met"])
        else:
            out["ok"] = res.get("trap") == 0 and res.get("loaded", True)
        return out

    def capture_expectations(self, ref: str, registers: Sequence[str] = (),
                             fabric_keys: Sequence[str] = (),
                             write: bool = True,
                             state: str = "fresh") -> Dict[str, object]:
        """Record what this container does now as what it is expected to do.

        An `expect` block is the difference between a container that ran and a
        container that is still right. Writing one by hand is work nobody does
        twice, so the studio can take the current run as the declaration --
        which is only honest if the run is reproducible, so the capture is
        made on the deterministic adapter and says so.

        What is captured is deliberately narrow: the status, the trap, every
        register that holds something, and the fabric facts that carry meaning
        (what reached the console, what each storage object holds, what the
        host received). Timings and seeds are not expectations.
        """
        app = self.resolve_app(ref)
        man = self.app_manifest(app)
        # captured on the deterministic adapter and, by default, from a fresh
        # fabric: an expectation taken from a run that carried the previous
        # run's state describes that moment rather than the container, and
        # would fail the next time by design
        r = self.run_app(app, check_expectations=False,
                         adapter="deterministic", state=state)
        if not r.get("ran"):
            raise StudioError("the container did not run, so there is nothing "
                              "to capture", {"reason": r.get("reason"),
                                             "state": r.get("state")})
        regs = {k: v for k, v in (r.get("registers") or {}).items()
                if (k in registers) or (not registers and v)}
        fab = r.get("fabric") or {}
        keys = list(fabric_keys) or [k for k in ("console_out_text",
                                                 "console_out_bytes",
                                                 "mailbox_received_bytes",
                                                 "monotonic")
                                     if fab.get(k)]
        expect: Dict[str, object] = {
            "status_name": r.get("status_name"),
            "trap": r.get("trap"),
            "registers": regs,
            "fabric": {k: fab.get(k) for k in keys},
            "captured_utc": utc_now(),
            "captured_on": {"adapter": "deterministic",
                            "seed": r.get("seed"),
                            "state": str(state),
                            "image_sha256": (man.get("digests") or {}).get(
                                "image_sha256")},
            "note": "captured from a run, not written by hand; re-capture "
                    "deliberately when the behaviour is meant to change. It "
                    "is checked on the same terms it was captured on",
        }
        if not write:
            return {"schema": "PA21.STUDIO/EXPECT/1", "ok": True,
                    "container": man.get("name"), "expect": expect,
                    "written": False}
        man["expect"] = expect
        with open(os.path.join(app, containers.MANIFEST), "w",
                  encoding="utf-8", newline="\n") as fh:
            json.dump(man, fh, indent=2, sort_keys=True)
            fh.write("\n")
        containers.seal(app)
        self._write_registry()
        return {"schema": "PA21.STUDIO/EXPECT/1", "ok": True,
                "container": man.get("name"), "expect": expect,
                "written": True, "path": os.path.join(app, containers.MANIFEST),
                "registers": len(regs), "fabric_keys": keys}

    def test_all(self, only: Sequence[str] = ()) -> Dict[str, object]:
        """Run every container against its own declared expectations.

        A registry of containers that each say what they do is a regression
        suite, and this is the whole of it: no test runner, no framework, and
        nothing a container has to opt into beyond declaring an answer.
        """
        rows: List[Dict[str, object]] = []
        for c in self.list_containers()["containers"]:
            if only and c["name"] not in only:
                continue
            row: Dict[str, object] = {"container": c["name"],
                                      "version": c.get("version"),
                                      "state": c.get("state")}
            man = self.app_manifest(c["path"])
            if not (man.get("expect") or {}):
                row.update({"verdict": "NO_EXPECTATION",
                            "detail": "this container does not declare what "
                                      "it should do; studio expect "
                                      f"{c['name']} would record it"})
                rows.append(row)
                continue
            # on the terms the expectation was captured on, whatever the
            # container does when a person runs it by hand
            on = (man["expect"].get("captured_on") or {})
            try:
                r = self.run_app(c["path"], check_expectations=True,
                                 adapter=on.get("adapter") or "deterministic",
                                 state=on.get("state") or "fresh")
            except (StudioError, lctlc.ToolchainError) as e:
                row.update({"verdict": "REFUSED", "detail": str(e)})
                rows.append(row)
                continue
            if not r.get("ran"):
                row.update({"verdict": "REFUSED",
                            "detail": str(r.get("reason"))})
                rows.append(row)
                continue
            checks = r.get("expectation_checks") or []
            bad = [c2 for c2 in checks if not c2["ok"]]
            row.update({"verdict": "PASS" if r.get("ok") else "FAIL",
                        "checks": len(checks), "failed": bad[:6],
                        "detail": "" if r.get("ok") else
                                  "; ".join(f"{b['field']}: expected "
                                            f"{b['expected']!r}, got "
                                            f"{b['actual']!r}" for b in bad[:3])})
            rows.append(row)
        counts: Dict[str, int] = {}
        for r0 in rows:
            counts[str(r0["verdict"])] = counts.get(str(r0["verdict"]), 0) + 1
        return {"schema": "PA21.STUDIO/TEST_RESULT/1", "results": rows,
                "counts": counts, "total": len(rows),
                "ok": not counts.get("FAIL") and not counts.get("REFUSED"),
                "summary": ", ".join(f"{v} {k.lower().replace('_', ' ')}"
                                     for k, v in sorted(counts.items()))
                           or "no containers"}

    def verify_app(self, ref: str) -> Dict[str, object]:
        """Everything checkable about a built application, in one answer."""
        app = self.resolve_app(ref)
        man = self.app_manifest(app)
        rt = self._runtime()
        name = man.get("name", os.path.basename(app))
        image = self._image_path(app, name)
        prov = os.path.join(os.path.dirname(image), f"{name}.provenance.json")
        src = os.path.join(app, man.get("entry", "src/main.lctlc"))
        checks: List[Dict[str, object]] = []

        def add(name_: str, ok: bool, detail: str = ""):
            checks.append({"check": name_, "ok": bool(ok), "detail": detail})

        add("source_present", os.path.isfile(src), src)
        add("image_present", os.path.isfile(image), image)
        add("provenance_present", os.path.isfile(prov), prov)
        if os.path.isfile(src) and os.path.isfile(image) and os.path.isfile(prov):
            try:
                lctlc.provenance(rt, src, image, prov)
                add("provenance_binds_source_to_image", True,
                    "the manifest's source hash, BRIR hash and image hash all "
                    "agree with the files on disk")
            except lctlc.ToolchainError as e:
                add("provenance_binds_source_to_image", False, str(e)[:300])
            try:
                lctlc.brim_verify(rt, image, prov)
                add("image_structure", True, "BRIM header and payload verified")
            except lctlc.ToolchainError as e:
                add("image_structure", False, str(e)[:300])
        if os.path.isfile(os.path.join(app, containers.MANIFEST)):
            sv = containers.verify_seal(app)
            add("container_seal", sv["sealed"],
                f"{sv.get('checked', 0)} file(s) re-hashed"
                + (f"; {sv.get('reason')}" if not sv["sealed"] else ""))
            insp = containers.inspect(app)
            add("image_matches_container_manifest",
                insp.get("image_matches_manifest", False),
                "the digest in CONTAINER.json is the image on disk")
        # the signature, checked independently of the run: brctl is the
        # runtime's own tool and knows nothing about this studio
        signed_image = image[:-6] + ".signed.brimg"
        k = self.signing_key()
        if os.path.isfile(signed_image) and k["available"]:
            r = subprocess.run([str(k["brctl"]), "verify-image", signed_image,
                                str(k["public_key"])],
                               capture_output=True, text=True, timeout=300)
            add("image_signature", r.returncode == 0,
                "the runtime's own brctl verified this image against the "
                "studio's public key"
                if r.returncode == 0 else
                (r.stderr or r.stdout or "brctl refused it").strip()[:200])
        elif k["available"]:
            add("image_signature", True,
                "this container holds no signed image; it was built before "
                "this installation had a key, and runs on the raw path")
        gate = self.gate(app)
        add("pa21_gate", bool(gate.get("satisfied")), str(gate.get("reason")))
        return {"schema": "PA21.STUDIO/VERIFY_RESULT/1",
                "app": app, "name": name, "checks": checks,
                "ok": all(c["ok"] for c in checks),
                "gate": gate}

    # ------------------------------------------------------------------
    # proof
    # ------------------------------------------------------------------
    def selftest(self, deep: bool = True) -> Dict[str, object]:
        """Compile a canonical application from source and run it.

        This is what makes an install a claim about behaviour rather than
        about file copying. It builds in a temporary directory and removes it,
        so a selftest leaves nothing behind.
        """
        results: List[Dict[str, object]] = []

        def add(name: str, ok: bool, detail: str = "", **extra):
            r = {"check": name, "ok": bool(ok), "detail": detail}
            r.update(extra)
            results.append(r)

        try:
            rt = self._runtime()
        except StudioError as e:
            return {"ok": False, "checks": [], "summary": str(e)}
        add("runtime_present", True, rt)
        try:
            runner = self._runner()
        except StudioError as e:
            add("runner_present", False, str(e))
            return {"ok": False, "checks": results,
                    "summary": "compiled-only installation: no runner on this "
                               "machine",
                    "can_execute": False}
        st = self._run_binary([runner, "selftest"])
        add("vm_core_selftest", st.get("selftest") == "PASS", json.dumps(st))
        tmp = tempfile.mkdtemp(prefix="pa21studio-selftest-")
        try:
            for tname, tmpl in lctlc.TEMPLATES.items():
                if not deep and tname != "hello":
                    continue
                src = os.path.join(tmp, f"{tname}.lctlc")
                img = os.path.join(tmp, f"{tname}.brimg")
                pv = os.path.join(tmp, f"{tname}.provenance.json")
                with open(src, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(lctlc.render(tname, tname))
                try:
                    lctlc.check(rt, src)
                    lctlc.compile_image(rt, src, img, factory=True, manifest=pv)
                    lctlc.provenance(rt, src, img, pv)
                    lctlc.brim_verify(rt, img, pv)
                except lctlc.ToolchainError as e:
                    add(f"template:{tname}", False, str(e)[:300])
                    continue
                # when this installation can sign, the selftest proves the
                # path a user actually gets: signed image, verified by the VM
                # through the HAL, before any instruction runs
                k = self.signing_key()
                run_img, extra = img, []
                if k["available"] and k["runner_verifies"]:
                    signed_img = img[:-6] + ".signed.brimg"
                    sg = self._sign_image(img, signed_img)
                    if sg.get("signed"):
                        run_img = signed_img
                        extra = ["--verify-key", str(k["public_key"]),
                                 "--require-signature"]
                res = self._run_binary([runner, "run", run_img,
                                        "--budget", "4096",
                                        "--adapter", "deterministic"] + extra)
                want = tmpl["expect"]
                ok = (res.get("status_name") == want.get("status_name")
                      and res.get("trap") == want.get("trap")
                      and all(res.get("registers", {}).get(k) == v
                              for k, v in want.get("registers", {}).items())
                      and all(res.get("fabric", {}).get(k) == v
                              for k, v in want.get("fabric", {}).items()))
                add(f"template:{tname}", ok,
                    f"expected {want}, got status {res.get('status_name')} "
                    f"trap {res.get('trap')} registers {res.get('registers')} "
                    f"[{res.get('execution_mode')}]",
                    result=res, expected=want)
            # a signature that cannot be broken is not being checked: the
            # selftest tampers with one and requires the VM to refuse it
            kk = self.signing_key()
            if kk["available"] and kk["runner_verifies"]:
                bad = os.path.join(tmp, "tampered.signed.brimg")
                src = os.path.join(tmp, "hello.signed.brimg")
                if os.path.isfile(src):
                    with open(src, "rb") as fh:
                        blob = bytearray(fh.read())
                    blob[BR_TAMPER_OFFSET] ^= 0xFF
                    with open(bad, "wb") as fh:
                        fh.write(bytes(blob))
                    rb = self._run_binary([runner, "run", bad, "--verify-key",
                                           str(kk["public_key"]),
                                           "--require-signature"])
                    add("tampered_signature_refused",
                        rb.get("loaded") is False
                        and rb.get("execution_mode") == "SIGNATURE_REFUSED",
                        f"a flipped byte in a signed image is refused before "
                        f"execution: {rb.get('execution_mode')} trap "
                        f"{rb.get('trap')}", result=rb)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        ok = all(r["ok"] for r in results)
        passed = sum(1 for r in results if r["ok"])
        return {"ok": ok, "checks": results, "can_execute": True,
                "backend": "RAM (memory adapter)",
                "summary": f"{passed}/{len(results)} checks passed",
                "note": "each template was compiled from source and executed "
                        "on the RAM-backed device fabric; the expected result "
                        "is the one the template declares, and the fabric "
                        "template asserts on what actually reached the "
                        "console"}

    # ------------------------------------------------------------------
    def _run_binary(self, cmd: Sequence[str], timeout: float = 300.0
                    ) -> Dict[str, object]:
        r = subprocess.run(list(cmd), capture_output=True, text=True,
                           timeout=timeout)
        out = (r.stdout or "").strip()
        try:
            data = json.loads(out) if out.startswith("{") else {}
        except ValueError:
            data = {}
        if not data:
            data = {"error": (r.stderr or out or "no output").strip()[:400],
                    "returncode": r.returncode}
        data.setdefault("returncode", r.returncode)
        return data


def _emitter(on_event: Optional[Event]) -> Event:
    def emit(ev: Dict[str, object]) -> None:
        if on_event:
            try:
                on_event(ev)
            except Exception:                                # noqa: BLE001
                pass
    return emit


def _tree_bytes(paths: Sequence[str]) -> int:
    total = 0
    for p in paths:
        if os.path.isfile(p):
            total += os.path.getsize(p)
        elif os.path.isdir(p):
            for r, _d, fs in os.walk(p):
                for f in fs:
                    try:
                        total += os.path.getsize(os.path.join(r, f))
                    except OSError:
                        pass
    return total
