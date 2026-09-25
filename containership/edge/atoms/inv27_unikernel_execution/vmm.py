"""VMM boot/execution adapters (MC-007, MC-009; C046).

``Backend.plan(spec)`` is pure: it turns an admitted image + ``IsolationPlan`` into an exact argv
(and, for Firecracker, a config document).  ``Supervisor`` executes a plan:

* argv only, never a shell; environment scrubbed to PATH/LANG; new session so the whole process
  group can be killed; stdin closed.
* the image is materialised from the admitted ``ImageBlob`` into a private 0400 file and re-hashed
  immediately before exec (TOCTOU), then deleted on every exit path.
* readiness = the manifest's ``ready_marker`` on the guest serial console within the boot deadline;
  otherwise ``UK_VMM_TIMEOUT`` and the process group is killed.
* ``stop`` is idempotent: SIGTERM, grace period, SIGKILL, reap, cleanup.

Hardening flags (QEMU): ``-nodefaults -no-user-config -nographic -sandbox on,obsolete=deny,
elevateprivileges=deny,spawn=deny,resourcecontrol=deny`` - QEMU's own seccomp filter, so the VMM
process itself cannot fork/exec even if the guest escapes into it.  Network ``none`` emits
``-nic none``; nothing is attached that is not in the plan.

Environment note: this pass could not install QEMU or Firecracker (package mirror returned 403),
so the Supervisor is exercised end-to-end against ``tests/fake_vmm.py`` - a stand-in process that
checks the exact argv contract and the image digest.  A boot of a real image under a real VMM is
blocked on W-VMM.
"""
from __future__ import annotations

import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field

from .errors import UkError
from .image.blob import ImageBlob
from .isolation import IsolationPlan

QEMU_SANDBOX = "on,obsolete=deny,elevateprivileges=deny,spawn=deny,resourcecontrol=deny"
APPROVED_VERSIONS = {"qemu": re.compile(r"QEMU emulator version (8|9|10)\.\d+"),
                     "firecracker": re.compile(r"Firecracker v1\.(\d+)")}


@dataclass(frozen=True)
class LaunchSpec:
    instance_id: str
    blob: ImageBlob
    architecture: str
    memory_mib: int
    vcpus: int
    cmdline: str
    ready_marker: str
    isolation: IsolationPlan
    boot_deadline_s: float = 10.0


class Backend:
    name = "abstract"

    def __init__(self, binary: str | None = None, *, accel: str = "tcg") -> None:
        self.binary = binary
        self.accel = accel

    def probe(self) -> str:
        """Return the backend version string or raise UK_VMM_UNSUPPORTED (fail closed)."""
        exe = self.binary and shutil.which(self.binary)
        if not exe:
            raise UkError("UK_VMM_UNSUPPORTED", f"{self.name} binary {self.binary!r} not found")
        try:
            out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10,
                                 env={"PATH": os.environ.get("PATH", "")}).stdout
        except (OSError, subprocess.TimeoutExpired) as e:
            raise UkError("UK_VMM_UNSUPPORTED", f"{self.name} version probe failed: {e}") from None
        rx = APPROVED_VERSIONS.get(self.name)
        if rx is None or not rx.search(out):
            raise UkError("UK_VMM_UNSUPPORTED", f"{self.name} version not approved: {out.strip()[:80]!r}")
        return out.strip().splitlines()[0]

    def plan(self, spec: LaunchSpec, image_path: str) -> dict:  # pragma: no cover - abstract
        raise NotImplementedError


class QemuBackend(Backend):
    name = "qemu"

    def __init__(self, binary: str | None = None, *, accel: str = "tcg") -> None:
        super().__init__(binary, accel=accel)

    def plan(self, spec: LaunchSpec, image_path: str) -> dict:
        if spec.architecture != "x86_64":
            raise UkError("UK_VMM_UNSUPPORTED", "QemuBackend plans x86_64 microvm guests only")
        if self.accel not in ("tcg", "kvm"):
            raise UkError("UK_CONFIG_INVALID", "accel must be tcg or kvm")
        iso = spec.isolation
        argv = [self.binary or "qemu-system-x86_64", "-machine", f"microvm,accel={self.accel}",
                "-nodefaults", "-no-user-config", "-nographic", "-sandbox", QEMU_SANDBOX,
                "-m", str(spec.memory_mib), "-smp", str(spec.vcpus),
                "-kernel", image_path, "-append", spec.cmdline, "-serial", "stdio", "-no-reboot"]
        if iso.network == "none":
            argv += ["-nic", "none"]
        else:
            argv += ["-netdev", f"tap,id=n0,ifname={iso.bridge}-{spec.instance_id[:6]},script=no,downscript=no",
                     "-device", "virtio-net-device,netdev=n0"]
        if "virtio-rng" in iso.devices:
            argv += ["-device", "virtio-rng-device"]
        for i, (dig, _ro) in enumerate(iso.storage):
            argv += ["-drive", f"id=d{i},if=none,readonly=on,format=raw,file=/var/lib/inv27/volumes/{dig[7:]}",
                     "-device", f"virtio-blk-device,drive=d{i}"]
        return {"backend": self.name, "argv": argv, "config": None}


class FirecrackerBackend(Backend):
    name = "firecracker"

    def plan(self, spec: LaunchSpec, image_path: str) -> dict:
        iso = spec.isolation
        cfg = {"boot-source": {"kernel_image_path": image_path, "boot_args": spec.cmdline},
               "machine-config": {"vcpu_count": spec.vcpus, "mem_size_mib": spec.memory_mib, "smt": False},
               "drives": [{"drive_id": f"d{i}", "path_on_host": f"/var/lib/inv27/volumes/{dig[7:]}",
                           "is_root_device": False, "is_read_only": True} for i, (dig, _) in enumerate(iso.storage)],
               "network-interfaces": ([] if iso.network == "none" else
                                      [{"iface_id": "n0", "host_dev_name": f"{iso.bridge}-{spec.instance_id[:6]}"}])}
        argv = [self.binary or "firecracker", "--no-api", "--config-file", "<config>", "--level", "Warning"]
        return {"backend": self.name, "argv": argv, "config": cfg}


class ScriptBackend(Backend):
    """Runs an arbitrary *argv prefix* with the QEMU-shaped contract.  Used for the fake VMM in tests
    and for operator-supplied wrappers (e.g. jailer).  Probe is the wrapper's ``--version``."""
    name = "script"

    def __init__(self, prefix: list[str]) -> None:
        super().__init__(prefix[0])
        self.prefix = list(prefix)

    def probe(self) -> str:
        out = subprocess.run(self.prefix + ["--version"], capture_output=True, text=True, timeout=10).stdout
        if "INV27-FAKE-VMM" not in out:
            raise UkError("UK_VMM_UNSUPPORTED", "script backend did not identify itself")
        return out.strip()

    def plan(self, spec: LaunchSpec, image_path: str) -> dict:
        q = QemuBackend("qemu-system-x86_64").plan(spec, image_path)
        return {"backend": self.name, "argv": self.prefix + q["argv"][1:], "config": None,
                "expect_sha256": spec.blob.sha256}


@dataclass
class Running:
    instance_id: str
    proc: subprocess.Popen
    image_path: str
    config_path: str | None
    serial: list = field(default_factory=list)
    stopped: bool = False


class Supervisor:
    def __init__(self, backend: Backend, *, workdir: str | None = None, grace_s: float = 2.0,
                 max_serial_bytes: int = 256 * 1024) -> None:
        self.backend = backend
        self.workdir = workdir
        self.grace_s = grace_s
        self.max_serial = max_serial_bytes
        self.launches = 0          # side-effect counter used by the zero-side-effect tests
        self._lock = threading.Lock()

    def launch(self, spec: LaunchSpec) -> tuple[Running, dict]:
        self.backend.probe()
        image_path = spec.blob.materialize(self.workdir)
        cfg_path = None
        try:
            plan = self.backend.plan(spec, image_path)
            argv = list(plan["argv"])
            if plan.get("config") is not None:
                fd, cfg_path = tempfile.mkstemp(prefix="inv27-fc-", suffix=".json", dir=self.workdir)
                with os.fdopen(fd, "w") as fh:
                    json.dump(plan["config"], fh)
                argv[argv.index("<config>")] = cfg_path
            with self._lock:
                self.launches += 1
            proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C"},
                                    start_new_session=True)
        except BaseException as e:
            _cleanup(image_path, cfg_path)
            if isinstance(e, OSError):
                raise UkError("UK_VMM_LAUNCH_FAILED", str(e)) from None
            raise
        run = Running(spec.instance_id, proc, image_path, cfg_path)
        try:
            self._await_ready(run, spec)
        except BaseException:
            self.stop(run)
            raise
        return run, plan

    def _await_ready(self, run: Running, spec: LaunchSpec) -> None:
        sel = selectors.DefaultSelector()
        sel.register(run.proc.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + spec.boot_deadline_s
        buf, size = b"", 0
        marker = spec.ready_marker.encode()
        try:
            while True:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise UkError("UK_VMM_TIMEOUT", f"ready marker not seen within {spec.boot_deadline_s}s")
                if not sel.select(timeout=min(left, 0.2)):
                    if run.proc.poll() is not None:
                        raise UkError("UK_VMM_LAUNCH_FAILED", f"VMM exited {run.proc.returncode} before ready",
                                      serial=buf.decode(errors="replace")[-400:])
                    continue
                chunk = os.read(run.proc.stdout.fileno(), 4096)
                if not chunk:
                    run.proc.wait(timeout=1)
                    raise UkError("UK_VMM_LAUNCH_FAILED", f"VMM exited {run.proc.returncode} before ready",
                                  serial=buf.decode(errors="replace")[-400:])
                size += len(chunk)
                if size > self.max_serial:
                    raise UkError("UK_LIMIT_EXCEEDED", "serial output budget exhausted before ready")
                buf += chunk
                if marker in buf:
                    run.serial.append(buf.decode(errors="replace"))
                    return
        finally:
            sel.close()

    def stop(self, run: Running) -> int | None:
        if run.stopped:
            return run.proc.returncode
        try:
            if run.proc.poll() is None:
                try:
                    os.killpg(run.proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    run.proc.wait(timeout=self.grace_s)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(run.proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    run.proc.wait(timeout=5)
        finally:
            if run.proc.stdout:
                run.proc.stdout.close()
            _cleanup(run.image_path, run.config_path)
            run.stopped = True
        return run.proc.returncode


def _cleanup(*paths) -> None:
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.chmod(p, 0o600)
                os.unlink(p)
            except OSError:
                pass
