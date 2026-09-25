"""Node preflight checks for bootstrap (C040). ``--profile production`` makes warnings blocking."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile


def checks(profile: str, workdir: str | None, dirs: list[str]) -> list[dict]:
    out = []

    def add(name, ok, detail="", blocking=True):
        out.append({"check": name, "ok": bool(ok), "detail": detail, "blocking": blocking})
    add("os.linux", platform.system() == "Linux", platform.platform())
    add("python>=3.10", sys.version_info >= (3, 10), platform.python_version())
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        k = AESGCM(AESGCM.generate_key(256))
        ok = k.decrypt(b"\0" * 12, k.encrypt(b"\0" * 12, b"x", b""), b"") == b"x"
        import cryptography
        add("cryptography.aesgcm_selftest", ok, cryptography.__version__)
    except Exception as exc:
        add("cryptography.aesgcm_selftest", False, type(exc).__name__)
    add("kvm.device", os.path.exists("/dev/kvm"), "/dev/kvm", blocking=profile == "production")
    for b in ("firecracker", "cloud-hypervisor"):
        add(f"vmm.binary.{b}", shutil.which(b) is not None, shutil.which(b) or "not on PATH", blocking=False)
    if workdir:
        fs = ""
        try:
            with open("/proc/mounts") as fh:
                best = ""
                for line in fh:
                    dev, mnt, typ = line.split()[:3]
                    if workdir.startswith(mnt) and len(mnt) > len(best):
                        best, fs = mnt, typ
        except OSError:
            pass
        add("workdir.tmpfs", fs == "tmpfs", f"{workdir} on {fs or 'unknown'}", blocking=profile == "production")
        try:
            mode = os.stat(workdir).st_mode & 0o777
            add("workdir.mode0700", mode == 0o700, oct(mode))
        except OSError as exc:
            add("workdir.mode0700", False, type(exc).__name__)
    for d in dirs:
        try:
            st = os.stat(d)
            add(f"dir.private:{d}", (st.st_mode & 0o077) == 0 and os.access(d, os.W_OK), oct(st.st_mode & 0o777))
        except OSError as exc:
            add(f"dir.private:{d}", False, type(exc).__name__)
    try:
        r = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], capture_output=True,
                           text=True, timeout=3)
        add("time.synchronized", r.stdout.strip() == "yes", r.stdout.strip() or "unknown",
            blocking=profile == "production")
    except (OSError, subprocess.SubprocessError):
        add("time.synchronized", False, "timedatectl unavailable", blocking=profile == "production")
    try:
        import resource
        soft, _ = resource.getrlimit(resource.RLIMIT_CORE)
        add("coredumps.disabled", soft == 0, f"RLIMIT_CORE={soft}", blocking=profile == "production")
    except Exception:
        pass
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="reference", choices=["reference", "production"])
    ap.add_argument("--workdir")
    ap.add_argument("--dir", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = checks(a.profile, a.workdir, a.dir)
    blockers = [c["check"] for c in res if c["blocking"] and not c["ok"]]
    doc = {"schema": "PK_SNAPSHOT_PREFLIGHT/1", "profile": a.profile, "checks": res, "blockers": blockers,
           "result": "PASS" if not blockers else "FAIL"}
    txt = json.dumps(doc, indent=1)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(txt + "\n")
    print(txt if a.json else f"preflight {doc['result']} blockers={blockers}")
    return 0 if not blockers else 2


if __name__ == "__main__":
    sys.exit(main())
