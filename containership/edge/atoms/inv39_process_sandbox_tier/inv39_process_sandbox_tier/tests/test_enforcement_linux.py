"""MC-030/031/034..047/051/055/086/090 — real OS enforcement, adversarial probes, pre-exec guarantee."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from _support import LINUX, PKG_DIR, pkg, probes_binary, require
from importlib import import_module

L = import_module(PKG_DIR.name + ".linux.launcher")
S = import_module(PKG_DIR.name + ".linux.seccomp")
profiles = import_module(PKG_DIR.name + ".profiles")
errors = import_module(PKG_DIR.name + ".errors")

PROBES = probes_binary()


def run(spec_kw, *args):
    p = profiles.load_profile("posix-minimal", extra_syscalls=spec_kw.pop("extra", ()))
    r, w = os.pipe()
    spec = L.LaunchSpec(argv=(PROBES, *args), syscalls=p.syscalls, stdio=(0, w, 2), **spec_kw)
    try:
        res = L.launch(spec)
    finally:
        os.close(w)
    out = b""
    while True:
        c = os.read(r, 65536)
        if not c:
            break
        out += c
    os.close(r)
    return res, dict(l.split("=", 1) for l in out.decode().split() if "=" in l)


@require(LINUX, "Linux seccomp/namespace enforcement not available on this host")
@require(PROBES is not None, "C compiler needed to build adversarial probes")
class EnforcementTest(unittest.TestCase):
    def test_all_escape_probes_blocked(self):
        leak = os.open("/etc/hostname", os.O_RDONLY)
        os.set_inheritable(leak, True)
        try:
            res, out = run({"env": {"LD_PRELOAD": "/evil.so", "PYTHONPATH": "/evil", "OK": "1"},
                            "env_allow": frozenset({"LD_PRELOAD", "PYTHONPATH", "OK"})}, "all")
        finally:
            os.close(leak)
        self.assertEqual(res.exit_code, 0)
        self.assertGreaterEqual(len(out), 14, out)
        self.assertEqual({k for k, v in out.items() if v != "BLOCKED"}, set(), out)
        self.assertEqual(res.evidence["defects"], [])

    def test_kernel_read_back_shows_controls(self):
        res, _ = run({}, "ptrace")
        rb = res.evidence["kernel_read_back"]
        self.assertTrue(rb["no_new_privs"])
        self.assertEqual(rb["seccomp_mode"], 2)
        self.assertEqual((rb["cap_eff"], rb["cap_prm"], rb["cap_inh"], rb["cap_amb"], rb["cap_bnd"]), (0, 0, 0, 0, 0))
        self.assertEqual(rb["namespaces_new"], ["ipc", "mount", "net", "pid", "user", "uts"])
        self.assertEqual(rb["net_interfaces"], ["lo"])
        self.assertEqual(rb["shared_mount_propagation"], 0)
        self.assertEqual(rb["rlimits"]["core"], 0)

    def test_x32_abi_is_killed(self):
        res, out = run({}, "x32")
        self.assertNotEqual(out.get("x32_abi_getpid"), "ESCAPED")
        self.assertEqual(res.exit_code, 128 + signal.SIGSYS)

    def test_network_namespace_blocks_egress_even_with_socket_allowed(self):
        res, out = run({"extra": {"socket", "connect"}}, "connect")
        self.assertEqual(out["net_egress"], "BLOCKED")

    @require(import_module(PKG_DIR.name + ".linux.landlock").abi_version() > 0, "Landlock unavailable")
    def test_landlock_confines_reads(self):
        res, out = run({"landlock_ro": ("/lib", "/lib64", "/usr", os.path.dirname(PROBES))}, "landlock", "/etc/hostname")
        self.assertEqual(out["landlock_read_outside"], "BLOCKED")

    def test_pre_exec_refusal_means_nothing_runs(self):
        marker = tempfile.mktemp()
        p = profiles.load_profile("posix-minimal")
        spec = L.LaunchSpec(argv=("/bin/sh", "-c", f"echo ran > {marker}"), syscalls=p.syscalls,
                            namespaces=frozenset({"user", "pid", "ipc", "uts", "net"}))  # no mount ns
        def refuse(pid, ev):
            raise errors.SandboxError("E_NOT_APPLIED", "simulated verification failure")
        with self.assertRaises(errors.SandboxError):
            L.launch(spec, on_ready=refuse)
        time.sleep(0.2)
        self.assertFalse(os.path.exists(marker))

    def test_missing_handoff_syscall_refused(self):
        with self.assertRaises(errors.SandboxError) as c:
            L.launch(L.LaunchSpec(argv=("/bin/true",), syscalls=frozenset({"read", "exit_group"})))
        self.assertEqual(c.exception.code, "E_PROFILE_INVALID")

    def test_timeout_kills_whole_tree(self):
        p = profiles.load_profile("posix-minimal")
        spec = L.LaunchSpec(argv=("/bin/sh", "-c", "sh -c 'while :; do :; done' & while :; do :; done"),
                            syscalls=p.syscalls, timeout_s=0.5)
        seen = {}

        def ready(pid, ev):
            seen["pid"], seen["ns"] = pid, os.readlink(f"/proc/{pid}/ns/pid")
        res = L.launch(spec, on_ready=ready)
        self.assertTrue(res.timed_out)
        members = ["?"]
        for _ in range(100):  # no process may remain in the sandbox's pid namespace
            members = []
            for d in os.listdir("/proc"):
                if d.isdigit():
                    try:
                        if os.readlink(f"/proc/{d}/ns/pid") == seen["ns"]:
                            members.append(d)
                    except OSError:
                        pass
            if not members:
                break
            time.sleep(0.02)
        self.assertEqual(members, [])

    def test_host_crash_kills_sandbox(self):
        code = (
            "import sys,os;sys.path.insert(0,%r);"
            "from %s.linux.launcher import LaunchSpec,launch;from %s.profiles import load_profile;"
            "p=load_profile('posix-minimal');"
            "launch(LaunchSpec(argv=('/bin/sh','-c','exec sleep 300 2>/dev/null || while :; do :; done'),syscalls=p.syscalls,timeout_s=300),"
            "on_ready=lambda pid,ev:(print(pid,flush=True)))"
        ) % (str(PKG_DIR.parent), PKG_DIR.name, PKG_DIR.name)
        host = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
        pid = int(host.stdout.readline())
        time.sleep(0.2)
        host.kill()
        host.wait()
        for _ in range(100):
            if not os.path.exists(f"/proc/{pid}"):
                break
            time.sleep(0.02)
        self.assertFalse(os.path.exists(f"/proc/{pid}"), "sandbox outlived its host (PDEATHSIG failed)")

    def test_run_as_unprivileged_identity(self):
        res, out = run({}, "whoami")
        self.assertEqual(out.get("uid"), "0")
        res, out = run({"run_as": (1000, 1000)}, "whoami")
        self.assertEqual((out.get("uid"), out.get("gid")), ("1000", "1000"))
        self.assertEqual(res.evidence["defects"], [])

    def test_cancellation_kills_tree(self):
        import threading
        ev = threading.Event()
        p = profiles.load_profile("posix-minimal")
        spec = L.LaunchSpec(argv=("/bin/sh", "-c", "while :; do :; done"), syscalls=p.syscalls, cancel=ev)
        threading.Timer(0.3, ev.set).start()
        with self.assertRaises(errors.SandboxError) as c:
            L.launch(spec)
        self.assertEqual(c.exception.code, "E_CANCELLED")

    def test_deny_action_kill(self):
        res, _ = run({"deny_action": "kill"}, "ptrace")
        self.assertEqual(res.exit_code, 128 + signal.SIGSYS)


if __name__ == "__main__":
    unittest.main()
