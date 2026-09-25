# Security model — INV-39 5.1.0

## Intended use
Trusted or constrained code where shared-kernel residual risk is accepted. Hostile / strongly multi-tenant untrusted code needs a stronger tier (PLN-04 enforces this; `integration.pln04_admit` repeats the check).

## Enforced on Linux (verified from the kernel before exec)
Default-deny seccomp-BPF (arch + x32 kill), NO_NEW_PRIVS, empty bounding/ambient/inheritable sets, locked securebits (NOROOT, NO_SETUID_FIXUP, NO_CAP_AMBIENT_RAISE), user/pid/mount/net/ipc/uts namespaces, private mount propagation, fresh /proc (hidepid=2), empty network namespace, fd closure, environment allow-list with loader/interpreter stripping, rlimits (core 0, nofile, nproc, fsize), optional Landlock, PDEATHSIG chain, timeout/cancel kill of the whole pid namespace.

Adversarial probes run inside the sandbox on every test run (`tools/escape_probes.c`): ptrace, inet socket, mount, unshare, setuid-regain, bpf, keyctl, perf_event_open, userfaultfd, inherited fds, LD_PRELOAD/PYTHONPATH, rlimit raise, /dev/mem, host /proc visibility, x32 ABI, network egress, Landlock read-outside — all BLOCKED on the build host.

## Known limits (see docs/EXCEPTIONS.json, TRACEABILITY.json)
* Seccomp rule contents are launcher-attested (program digest), not read back from the kernel.
* No cgroup v2 limits; rlimits only.
* /sys and /dev are host views in the native backend.
* Node trust root is an HMAC key; no hardware attestation.
* Shared-kernel bugs reachable via allowed syscalls and side channels remain residual — stated in every applied record.

## Reporting
Security contact and SLA: _UNASSIGNED_ (docs/OWNERSHIP.md).
