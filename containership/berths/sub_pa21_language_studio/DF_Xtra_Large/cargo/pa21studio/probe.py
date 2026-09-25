"""What this machine can actually do, asked rather than assumed.

Every capability the studio depends on is probed by running the thing, not by
inferring it from the platform name. A machine either has a C compiler that
produces a working binary or it does not, and the only way to know is to
compile something. The probe is cheap, it is cached per process, and every
answer carries the reason behind it so a caller that gets `False` can see what
would change it.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence

_C_PROGRAM = "int main(void){return 0;}\n"
_CRYPTO_PROGRAM = "#include <openssl/evp.h>\nint main(void){return EVP_MD_size(EVP_sha256())>0?0:1;}\n"


@dataclass
class Finding:
    """One probed capability: what was asked, what came back, and what it means."""
    name: str
    available: bool
    detail: str = ""
    remedy: str = ""
    value: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _run(cmd: List[str], timeout: float = 60.0, cwd: Optional[str] = None
         ) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          cwd=cwd)


def find_compiler() -> Optional[str]:
    names = [os.environ.get("CC", ""), "cc", "gcc", "clang"]
    if os.name == "nt":
        # MSVC is the compiler most Windows machines actually have, and it is
        # only on PATH inside a Developer Command Prompt. MinGW's gcc is tried
        # first because the runtime and this host are written for a C11
        # compiler with POSIX-ish flags, and gcc there needs no translation.
        names = [os.environ.get("CC", ""), "gcc", "clang", "cc", "cl"]
    for name in names:
        if not name:
            continue
        p = shutil.which(name)
        if p:
            return p
    return None


def compiler_kind(cc: Optional[str]) -> str:
    """'msvc' or 'unix' -- they do not take the same command line."""
    if not cc:
        return "none"
    base = os.path.basename(cc).lower()
    return "msvc" if base in ("cl", "cl.exe") else "unix"


def compile_command(cc: str, sources: Sequence[str], out: str,
                    includes: Sequence[str] = (),
                    defines: Sequence[str] = (),
                    libs: Sequence[str] = ()) -> List[str]:
    """One build line, in the dialect the compiler in hand actually speaks.

    Everything the studio compiles goes through here, so adding a compiler is
    one place rather than three, and so the Windows path is not a guess made
    separately at each call site.
    """
    if compiler_kind(cc) == "msvc":
        cmd = [cc, "/nologo", "/std:c11", "/O2", "/W3"]
        cmd += [f"/I{i}" for i in includes]
        cmd += [f"/D{d}" for d in defines]
        cmd += list(sources)
        cmd += [f"/Fe:{out}"]
        if libs:
            cmd += ["/link"] + [f"{lib_msvc(l)}" for l in libs]
        return cmd
    cmd = [cc, "-std=c11", "-O2"]
    cmd += [f"-I{i}" for i in includes]
    cmd += [f"-D{d}" for d in defines]
    cmd += list(sources) + ["-o", out]
    cmd += [f"-l{l}" for l in libs]
    return cmd


def lib_msvc(name: str) -> str:
    """`crypto` is `libcrypto.lib` to the Microsoft linker."""
    return name if name.lower().endswith(".lib") else f"lib{name}.lib"


def probe_compiler() -> Finding:
    cc = find_compiler()
    if not cc:
        return Finding("c_compiler", False,
                       "no cc, gcc or clang on PATH",
                       "install a C toolchain (build-essential, Xcode command "
                       "line tools, or MSYS2/MinGW on Windows) to execute "
                       "images; compiling and verifying them does not need one")
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "probe.c")
        out = os.path.join(td, "probe.bin")
        with open(src, "w") as fh:
            fh.write(_C_PROGRAM)
        try:
            r = _run(compile_command(cc, [src], out))
        except (OSError, subprocess.SubprocessError) as e:
            return Finding("c_compiler", False, f"{cc} failed to run: {e}",
                           "check the toolchain installation")
        if r.returncode != 0 or not os.path.isfile(out):
            return Finding("c_compiler", False,
                           f"{cc} present but did not link a trivial program: "
                           f"{(r.stderr or '').strip()[:200]}",
                           "check the toolchain installation")
    return Finding("c_compiler", True, f"{cc} compiles and links", value=cc)


def probe_openssl(cc: Optional[str]) -> Finding:
    if not cc:
        return Finding("openssl_dev", False, "no compiler to test with",
                       "install a C toolchain first")
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "c.c")
        out = os.path.join(td, "c.bin")
        with open(src, "w") as fh:
            fh.write(_CRYPTO_PROGRAM)
        try:
            r = _run(compile_command(cc, [src], out, libs=["crypto"]))
        except (OSError, subprocess.SubprocessError) as e:
            return Finding("openssl_dev", False, f"probe failed: {e}", "")
        if r.returncode != 0:
            return Finding(
                "openssl_dev", False,
                "OpenSSL headers or libcrypto are not available to the compiler",
                "install libssl-dev / openssl-devel to build the package's own "
                "brctl, which signs images and authenticates persisted state. "
                "Running an image does not require it")
    return Finding("openssl_dev", True, "libcrypto links")


def probe_make() -> Finding:
    m = shutil.which(os.environ.get("MAKE", "") or "make")
    if not m:
        return Finding("make", False, "no make on PATH",
                       "install make to run the package's own qualification "
                       "targets; the studio builds its runner without it")
    return Finding("make", True, f"{m}", value=m)


def probe_python() -> Finding:
    ok = sys.version_info >= (3, 8)
    return Finding("python", ok,
                   f"{platform.python_implementation()} "
                   f"{platform.python_version()} at {sys.executable}",
                   "" if ok else "Python 3.8 or newer is required",
                   value=sys.executable)


def probe_all(refresh: bool = False) -> Dict[str, object]:
    """Every capability, with a summary a caller can branch on."""
    global _CACHE
    if _CACHE is not None and not refresh:
        return _CACHE
    t0 = time.perf_counter()
    py = probe_python()
    cc = probe_compiler()
    ssl = probe_openssl(cc.value or None if cc.available else None)
    mk = probe_make()
    findings = [py, cc, ssl, mk]
    out = {
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or platform.machine(),
            "cpu_count": os.cpu_count(),
            "python": platform.python_version(),
            "executable": sys.executable,
        },
        "findings": {f.name: f.to_dict() for f in findings},
        "can_compile_images": py.available,
        "can_execute_images": py.available and cc.available,
        "can_build_signing_cli": py.available and cc.available and ssl.available,
        "probe_seconds": round(time.perf_counter() - t0, 3),
        "note": "compiling and verifying an image is pure Python; executing one "
                "needs a C compiler; signing images and authenticating state "
                "additionally needs OpenSSL",
    }
    _CACHE = out
    return out


_CACHE: Optional[Dict[str, object]] = None


if __name__ == "__main__":                                   # pragma: no cover
    print(json.dumps(probe_all(), indent=2))
