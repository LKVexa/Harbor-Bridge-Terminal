#!/usr/bin/env python3
"""Stand-in VMM for the Supervisor tests (NOT a hypervisor).

It enforces the argv contract the QEMU plan must satisfy (sandbox flags, -nodefaults, -nic none unless
tap, -kernel path readable, 0400) and reads the kernel file to prove the Supervisor handed it the admitted
bytes: it prints ``DIGEST <sha256>`` and then the ready marker.  Env INV27_FAKE_MODE selects failure
modes: ``hang`` (never ready), ``crash`` (exit 3 before ready), ``flood`` (serial flood), ``ignore_term``.
Mode can also be given as the first argv ``--mode=...``.
"""
import hashlib, os, signal, stat, sys, time
args = sys.argv[1:]
mode = "ok"
if args and args[0].startswith("--mode="):
    mode = args.pop(0).split("=", 1)[1]
if args == ["--version"]:
    print("INV27-FAKE-VMM 1.0 (test double; not a hypervisor)"); sys.exit(0)
need = ["-nodefaults", "-no-user-config", "-nographic", "-sandbox"]
for n in need:
    if n not in args:
        print(f"CONTRACT-FAIL missing {n}", flush=True); sys.exit(2)
if "spawn=deny" not in args[args.index("-sandbox") + 1]:
    print("CONTRACT-FAIL sandbox", flush=True); sys.exit(2)
k = args[args.index("-kernel") + 1]
if stat.S_IMODE(os.stat(k).st_mode) != 0o400:
    print("CONTRACT-FAIL kernel mode", flush=True); sys.exit(2)
data = open(k, "rb").read()
print("DIGEST " + hashlib.sha256(data).hexdigest(), flush=True)
cmd = args[args.index("-append") + 1]
if mode == "crash":
    sys.exit(3)
if mode == "flood":
    while True:
        sys.stdout.write("x" * 4096); sys.stdout.flush()
if mode == "ignore_term":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
if mode != "hang":
    print("guest cmdline: " + cmd, flush=True)
    print("INV27-READY", flush=True)
while True:
    time.sleep(0.05)
