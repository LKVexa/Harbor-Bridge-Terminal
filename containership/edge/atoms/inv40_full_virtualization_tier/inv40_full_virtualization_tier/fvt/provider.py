"""Hypervisor provider adapters (REPO-003, INV-40-C031, C021).

``Provider`` is the boundary the service drives.  Two implementations:

* ``QemuKvmProvider`` - launches ``qemu-system-*`` with KVM acceleration only
  (``-accel kvm``; TCG is never passed, so the tier cannot silently degrade to
  software emulation) and drives the guest over QMP on a private unix socket.
  Resident footprint is read from ``/proc/<pid>/status`` VmRSS, i.e. the real
  size, never the requested size.
* ``FakeProvider`` - deterministic in-memory provider for tests and fault
  injection; it is labelled ``production=False`` and the service refuses it
  when the active configuration's environment is ``prod``.

``HostProbe`` answers "is the hardware primitive usable" from the host:
``/dev/kvm`` openable read-write AND the CPU advertising vmx/svm.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass, field

from .errors import OpError


@dataclass
class ProbeResult:
    usable: bool
    reasons: list[str] = field(default_factory=list)
    cpu_flag: str | None = None


class HostProbe:
    def __init__(self, dev="/dev/kvm", cpuinfo="/proc/cpuinfo"):
        self.dev, self.cpuinfo = dev, cpuinfo

    def probe(self) -> ProbeResult:
        reasons, flag = [], None
        try:
            text = pathlib.Path(self.cpuinfo).read_text(errors="replace")
            flags = set()
            for line in text.splitlines():
                if line.startswith("flags"):
                    flags |= set(line.split(":", 1)[1].split())
            flag = "vmx" if "vmx" in flags else "svm" if "svm" in flags else None
            if flag is None:
                reasons.append("cpu does not advertise vmx/svm")
        except OSError as exc:
            reasons.append(f"cpuinfo unreadable: {exc.strerror}")
        if not os.path.exists(self.dev):
            reasons.append(f"{self.dev} absent")
        elif not os.access(self.dev, os.R_OK | os.W_OK):
            reasons.append(f"{self.dev} not read-write for this identity")
        return ProbeResult(not reasons, reasons, flag)


class Provider:
    name = "abstract"
    production = False

    def probe(self) -> ProbeResult: ...
    def launch(self, spec: dict) -> dict: ...
    def status(self, handle: dict) -> dict: ...
    def stop(self, handle: dict) -> None: ...
    def destroy(self, handle: dict) -> None: ...


class QmpClient:
    """Minimal QMP client: greeting, qmp_capabilities, execute(cmd)."""

    def __init__(self, path: str, timeout: float = 5.0):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect(path)
        self._buf = b""
        greet = self._read()
        if "QMP" not in greet:
            raise OpError("PK_FULL_VM_PROVIDER_FAILED", "peer is not QMP")
        self.execute("qmp_capabilities")

    def _read(self) -> dict:
        while b"\n" not in self._buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise OpError("PK_FULL_VM_PROVIDER_UNAVAILABLE", "QMP connection closed")
            self._buf += chunk
            if len(self._buf) > 1 << 20:
                raise OpError("PK_FULL_VM_PROVIDER_FAILED", "QMP message too large")
        line, self._buf = self._buf.split(b"\n", 1)
        return json.loads(line)

    def execute(self, cmd: str, **args) -> dict:
        msg = {"execute": cmd}
        if args:
            msg["arguments"] = args
        self.sock.sendall(json.dumps(msg).encode() + b"\n")
        while True:
            r = self._read()
            if "event" in r:
                continue
            if "error" in r:
                raise OpError("PK_FULL_VM_PROVIDER_FAILED", f"QMP {cmd}: {r['error'].get('desc')}")
            return r.get("return", {})

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def rss_mib(pid: int) -> int:
    try:
        for line in pathlib.Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


class QemuKvmProvider(Provider):
    name = "qemu-kvm"
    production = True

    def __init__(self, binary: str = "qemu-system-x86_64", probe: HostProbe | None = None,
                 workdir: str | None = None, boot_timeout_s: float = 60.0):
        self.binary, self._probe = binary, probe or HostProbe()
        self.workdir = workdir or tempfile.mkdtemp(prefix="inv40-")
        self.boot_timeout_s = boot_timeout_s

    def probe(self) -> ProbeResult:
        r = self._probe.probe()
        if shutil.which(self.binary) is None and not os.path.isfile(self.binary):
            r.usable = False
            r.reasons.append(f"{self.binary} not installed")
        return r

    def argv(self, spec: dict, qmp_path: str) -> list[str]:
        """Deterministic command line.  KVM only; the full baseline device model."""
        a = [self.binary, "-name", f"guest={spec['name']}", "-accel", "kvm", "-cpu", "host",
             "-machine", "q35", "-m", str(spec["memory_mib"]), "-smp", str(spec.get("vcpus", 1)),
             "-nodefaults", "-no-user-config", "-display", "none", "-vga", "std",
             "-sandbox", "on,obsolete=deny,elevateprivileges=deny,spawn=deny,resourcecontrol=deny",
             "-qmp", f"unix:{qmp_path},server=on,wait=off", "-S",
             "-device", "virtio-net-pci,netdev=n0", "-netdev", "user,id=n0,restrict=on",
             "-device", "virtio-balloon-pci", "-object", "rng-random,id=rng0,filename=/dev/urandom",
             "-device", "virtio-rng-pci,rng=rng0", "-device", "virtio-serial-pci",
             "-device", "qemu-xhci", "-device", "ahci,id=ahci0"]
        if spec.get("disk"):
            a += ["-drive", f"file={spec['disk']},if=virtio,format=raw,readonly=on"]
        if spec.get("tpm_socket"):
            a += ["-chardev", f"socket,id=tpmc,path={spec['tpm_socket']}",
                  "-tpmdev", "emulator,id=tpm0,chardev=tpmc", "-device", "tpm-tis,tpmdev=tpm0"]
        if "tcg" in " ".join(a):  # explicit (not assert): survives python -O
            raise OpError("PK_FULL_VM_PRIMITIVE_REQUIRED", "software emulation refused")
        return a

    def launch(self, spec: dict) -> dict:
        pr = self.probe()
        if not pr.usable:
            raise OpError("PK_FULL_VM_PRIMITIVE_REQUIRED", "; ".join(pr.reasons), reasons=pr.reasons)
        qmp = os.path.join(self.workdir, f"{spec['instance_id']}.qmp")
        t0 = time.monotonic()
        proc = subprocess.Popen(self.argv(spec, qmp), stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        deadline = t0 + self.boot_timeout_s
        while not os.path.exists(qmp):
            if proc.poll() is not None:
                raise OpError("PK_FULL_VM_GUEST_START_FAILED", "hypervisor exited during launch",
                              rc=proc.returncode, stderr=(proc.stderr.read() or b"")[-2000:].decode(errors="replace"))
            if time.monotonic() > deadline:
                proc.kill()
                raise OpError("PK_FULL_VM_TIMEOUT", "QMP socket did not appear")
            time.sleep(0.05)
        q = QmpClient(qmp)
        q.execute("cont")
        st = q.execute("query-status")
        elapsed = int((time.monotonic() - t0) * 1000)
        return {"pid": proc.pid, "qmp": qmp, "proc": proc, "client": q, "elapsed_ms": elapsed,
                "resident_mib": rss_mib(proc.pid), "running": st.get("running", False)}

    def status(self, h: dict) -> dict:
        st = h["client"].execute("query-status")
        return {"running": st.get("running", False), "resident_mib": rss_mib(h["pid"])}

    def stop(self, h: dict) -> None:
        try:
            h["client"].execute("system_powerdown")
        finally:
            self.destroy(h)

    def destroy(self, h: dict) -> None:
        try:
            h["client"].execute("quit")
        except Exception:  # noqa: BLE001
            pass
        h["client"].close()
        try:
            h["proc"].wait(timeout=10)
        except subprocess.TimeoutExpired:
            h["proc"].kill()


class FakeProvider(Provider):
    """Deterministic non-production provider with programmable faults."""

    name = "fake"
    production = False

    def __init__(self, *, usable=True, boot_ms=3000, resident_mib=900):
        self.usable, self.boot_ms, self.resident_mib = usable, boot_ms, resident_mib
        self.faults: list[str] = []   # queue: "unavailable" | "fail" | "hang" | "guest"
        self.live: dict[str, dict] = {}
        self.launches = 0
        self.delay_s = 0.0   # simulated hypervisor launch latency (bench/overload tests)

    def probe(self) -> ProbeResult:
        return ProbeResult(self.usable, [] if self.usable else ["fake: primitive disabled"], "vmx")

    def _fault(self):
        if self.faults:
            f = self.faults.pop(0)
            if f == "unavailable":
                raise OpError("PK_FULL_VM_PROVIDER_UNAVAILABLE", "injected: provider unavailable")
            if f == "fail":
                raise OpError("PK_FULL_VM_PROVIDER_FAILED", "injected: provider failure")
            if f == "hang":
                raise OpError("PK_FULL_VM_TIMEOUT", "injected: provider hang")
            if f == "guest":
                raise OpError("PK_FULL_VM_GUEST_START_FAILED", "injected: guest failed to start")

    def launch(self, spec: dict) -> dict:
        if not self.usable:
            raise OpError("PK_FULL_VM_PRIMITIVE_REQUIRED", "fake: primitive disabled")
        self._fault()
        if self.delay_s:
            time.sleep(self.delay_s)
        self.launches += 1
        h = {"id": spec["instance_id"], "elapsed_ms": self.boot_ms, "resident_mib": self.resident_mib, "running": True}
        self.live[spec["instance_id"]] = h
        return h

    def status(self, h):
        return {"running": h["id"] in self.live, "resident_mib": self.resident_mib}

    def stop(self, h):
        self._fault()
        self.live.pop(h["id"], None)

    def destroy(self, h):
        self.live.pop(h["id"], None)
