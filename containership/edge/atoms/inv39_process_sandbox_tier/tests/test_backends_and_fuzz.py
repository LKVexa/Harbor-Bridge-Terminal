"""MC-030/031/032/033/038/088 — compiler correctness (cBPF emulator), backends, fuzzing."""
from __future__ import annotations

import os
import random
import struct
import unittest
from importlib import import_module

from _support import PKG_DIR, pkg

S = import_module(PKG_DIR.name + ".linux.seccomp")
T = import_module(PKG_DIR.name + ".linux.syscall_tables")
B = import_module(PKG_DIR.name + ".backends")
L = import_module(PKG_DIR.name + ".linux.launcher")
P = import_module(PKG_DIR.name + ".linux.primitives")
cfg = import_module(PKG_DIR.name + ".config")
sc = import_module(PKG_DIR.name + ".schema_check")
ctl = import_module(PKG_DIR.name + ".control")
errors = import_module(PKG_DIR.name + ".errors")


def run_bpf(prog: bytes, nr: int, arch: int) -> int:
    """Minimal classic-BPF interpreter for the opcodes the compiler emits."""
    ins = [struct.unpack("=HBBI", prog[i:i + 8]) for i in range(0, len(prog), 8)]
    data = struct.pack("=iI", nr, arch)
    pc, acc = 0, 0
    for _ in range(len(ins) + 1):
        code, jt, jf, k = ins[pc]
        if code == 0x20:
            acc = struct.unpack("=I", data[k:k + 4])[0]; pc += 1
        elif code == 0x15:
            pc += 1 + (jt if acc == k else jf)
        elif code == 0x35:
            pc += 1 + (jt if acc >= k else jf)
        elif code == 0x06:
            return k
        else:
            raise AssertionError(f"unexpected opcode {code:#x}")
    raise AssertionError("program did not terminate")


class CompilerTest(unittest.TestCase):
    def test_exhaustive_semantics_both_arches(self):
        for arch, (audit, table) in S.ARCHES.items():
            rnd = random.Random(arch)
            allowed = set(rnd.sample(sorted(table), 40)) | {"read", "execve", "exit_group"}
            f = S.compile_filter(allowed, arch=arch)
            ok = {table[n] for n in allowed}
            for nr in range(0, 600):
                with self.subTest(arch=arch, nr=nr):
                    want = S.SECCOMP_RET_ALLOW if nr in ok else S.SECCOMP_RET_ERRNO | S.EPERM
                    self.assertEqual(run_bpf(f.program, nr, audit), want)
            other = [a for a in S.ARCHES.values() if a[0] != audit][0][0]
            self.assertEqual(run_bpf(f.program, table["read"], other), S.SECCOMP_RET_KILL_PROCESS)
            if arch == "x86_64":
                self.assertEqual(run_bpf(f.program, 0x40000000 | 39, audit), S.SECCOMP_RET_KILL_PROCESS)

    def test_kill_action_and_determinism(self):
        a = S.compile_filter({"write", "read"}, arch="x86_64", deny_action="kill")
        b = S.compile_filter(["read", "write", "read"], arch="x86_64", deny_action="kill")
        self.assertEqual(a.digest, b.digest)
        self.assertEqual(run_bpf(a.program, 101, 0xC000003E), S.SECCOMP_RET_KILL_PROCESS)

    def test_refusals(self):
        for kw in ({"syscalls": set()}, {"syscalls": {"read", "not_a_syscall"}},
                   {"syscalls": {"read"}, "deny_action": "log"}, {"syscalls": {"read"}, "arch": "mips"}):
            with self.subTest(kw), self.assertRaises(errors.SandboxError):
                S.compile_filter(**kw)


class BackendAdapterTest(unittest.TestCase):
    def test_probe_never_raises_and_require_fails_closed(self):
        p = B.probe()
        self.assertIn("os", p)
        with self.assertRaises(errors.SandboxError) as c:
            B.require({"os": "Plan9"})
        self.assertEqual(c.exception.code, "E_BACKEND_UNSUPPORTED")
        with self.assertRaises(errors.SandboxError):
            B.require(dict(p, landlock_abi=0), need_landlock=True)

    def test_bwrap_argv(self):
        spec = L.LaunchSpec(argv=("/bin/true",), syscalls=frozenset({"read", "execve", "exit_group"}),
                            env={"A": "1"}, run_as=(1000, 1000))
        if not B.shutil.which("bwrap"):
            with self.assertRaises(errors.SandboxError):
                B.bwrap_argv(spec, 9)
            B.shutil.which = (lambda orig: (lambda n: "/usr/bin/bwrap" if n == "bwrap" else orig(n)))(B.shutil.which)
        a = B.bwrap_argv(spec, 9)
        for flag in ("--unshare-all", "--die-with-parent", "--clearenv", "--new-session"):
            self.assertIn(flag, a)
        self.assertEqual(a[a.index("--cap-drop") + 1], "ALL")
        self.assertEqual(a[a.index("--seccomp") + 1], "9")
        self.assertEqual(a[-2:], ["--", "/bin/true"])
        self.assertNotIn("--share-net", a)

    def test_seatbelt_profile(self):
        prof = B.seatbelt_profile(read_paths=["/opt/app"], write_paths=["/tmp/w"], allow_exec=["/opt/app/bin"])
        self.assertIn("(deny default)", prof)
        self.assertNotIn("network", prof)
        for evil in ('/x") (allow default) ("', "/a\\b", "/a\nb"):
            with self.assertRaises(errors.SandboxError):
                B.seatbelt_profile(read_paths=[evil])

    def test_env_sanitizer(self):
        env = P.sanitize_env({"LD_PRELOAD": "x", "LD_LIBRARY_PATH": "x", "PYTHONPATH": "x", "GLIBC_TUNABLES": "x",
                              "OK": "1", "NOTALLOWED": "1", "BAD\0": "1"},
                             frozenset({"LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH", "GLIBC_TUNABLES", "OK", "BAD\0"}))
        self.assertEqual(set(env), {"PATH", "LANG", "OK"})

    def test_launchspec_refusals(self):
        for kw in ({"argv": ()}, {"argv": ("true",)}, {"argv": ("/bin/true", "a\0b")}, {"timeout_s": 0}):
            base = {"argv": ("/bin/true",), "syscalls": frozenset({"read", "execve", "exit_group"})}
            base.update(kw)
            with self.subTest(kw), self.assertRaises(errors.SandboxError):
                L.LaunchSpec(**base).validate()


class FuzzTest(unittest.TestCase):
    """Seeded, bounded generative fuzzing: every input either parses or raises a *typed* error."""
    N = int(os.environ.get("INV39_FUZZ_ITERS", "3000"))

    def rand_value(self, r, depth=0):
        choices = [lambda: r.randint(-2**40, 2**40), lambda: r.random(), lambda: None, lambda: r.choice([True, False]),
                   lambda: "".join(chr(r.randint(0, 0x2FFF)) for _ in range(r.randint(0, 20))),
                   lambda: r.choice(["read", "CAP_SYS_ADMIN", "pid", "", " ", "a" * 200, "../x", "rEaD"])]
        if depth < 3:
            choices += [lambda: [self.rand_value(r, depth + 1) for _ in range(r.randint(0, 5))],
                        lambda: {self.rand_value(r, 3) if r.random() < .5 else r.choice(list(cfg.SCHEMA)):
                                 self.rand_value(r, depth + 1) for _ in range(r.randint(0, 5))}]
        return r.choice(choices)()

    def test_profile_parser(self):
        r = random.Random(1)
        for _ in range(self.N):
            try:
                p = pkg.SandboxProfile(self.rand_value(r), self.rand_value(r), self.rand_value(r) or [],
                                       self.rand_value(r) or pkg.REQUIRED_NAMESPACES)
                self.assertEqual(sc.validate(p.as_dict()), [])
            except pkg.ProfileInvalid:
                pass

    def test_config_loader(self):
        r = random.Random(2)
        import json
        for _ in range(self.N):
            v = self.rand_value(r)
            try:
                raw = json.dumps(v) if r.random() < .8 else bytes(r.randrange(256) for _ in range(r.randint(0, 40)))
            except (TypeError, ValueError):
                continue
            try:
                cfg.load(raw)
            except errors.SandboxError as e:
                self.assertEqual(e.code, "E_CONFIG_INVALID")

    def test_token_and_identifiers(self):
        r = random.Random(3)
        for _ in range(self.N):
            tok = "".join(r.choice("0123456789abcdef.{}\"") for _ in range(r.randint(0, 120)))
            with self.assertRaises(errors.SandboxError):
                ctl.authenticate({"a": b"k" * 32}, tok, "aud")

    def test_schema_validator_total(self):
        r = random.Random(4)
        for _ in range(self.N):
            v = self.rand_value(r)
            sid = r.choice(["PK_SANDBOX_PROFILE/1", "PK_SANDBOX_APPLIED/2", "PK_SANDBOX_ERROR/1", None])
            self.assertIsInstance(sc.validate(v, sid) if sid else sc.validate(v), list)

    def test_compiler_names(self):
        r = random.Random(5)
        names = sorted(T.X86_64)
        for _ in range(self.N // 10):
            s = set(r.sample(names, r.randint(1, 50))) | {"".join(r.choice("abc_") for _ in range(r.randint(1, 8)))}
            try:
                f = S.compile_filter(s, arch="x86_64")
                self.assertLessEqual(f.instructions, 8 + len(s))
            except errors.SandboxError as e:
                self.assertEqual(e.code, "E_PROFILE_INVALID")


if __name__ == "__main__":
    unittest.main()
