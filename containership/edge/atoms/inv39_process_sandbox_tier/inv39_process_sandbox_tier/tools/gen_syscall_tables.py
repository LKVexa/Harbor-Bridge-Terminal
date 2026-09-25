"""Regenerate linux/syscall_tables.py from the build host's Linux UAPI headers."""
import pathlib, re, sys
X = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/usr/include/x86_64-linux-gnu/asm/unistd_64.h")
G = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "/usr/include/asm-generic/unistd.h")
x = {m[1]: int(m[2]) for m in re.finditer(r"#define __NR_(\w+)\s+(\d+)\s*$", X.read_text(), re.M)}
g = {}
for m in re.finditer(r"#define __NR(?:3264)?_(\w+)\s+(\d+)", G.read_text()):
    if m[1] not in ("syscalls", "arch_specific_syscall") and int(m[2]) < 600:
        g.setdefault(m[1], int(m[2]))
out = pathlib.Path(__file__).resolve().parents[1] / "linux" / "syscall_tables.py"
body = '"""Syscall-name tables generated from Linux UAPI headers.\n\nRegenerate with tools/gen_syscall_tables.py; names absent from a table are refused (fail closed).\n"""\n'
body += "X86_64 = {\n" + "".join(f"    {k!r}: {v},\n" for k, v in sorted(x.items(), key=lambda i: i[1])) + "}\n"
body += "AARCH64 = {\n" + "".join(f"    {k!r}: {v},\n" for k, v in sorted(g.items(), key=lambda i: i[1])) + "}\n"
out.write_text(body)
print(len(x), len(g))
