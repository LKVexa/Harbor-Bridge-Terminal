# Architecture — INV-39 5.1.0

```
caller ──token──▶ SandboxService.launch
                    │ authenticate · authorize(launch, tenant) · quarantine · offline check
                    │ profile policy (forbidden caps, namespaces, budget) · backend probe
                    │ Admission (node ceiling, tenant quota, breaker) · fenced lease
                    ▼ Lifecycle CREATED→APPLYING
             linux.launcher.launch(spec)
   host ──fork──▶ supervisor: PDEATHSIG · unshare(user)+id map · unshare(pid,mount,net,ipc,uts) · subreaper
                     └─fork─▶ workload (PID 1 of new pid ns):
                              private mounts · fresh /proc · tmpfs · rlimits · stdio · close fds
                              bounding drop · securebits lock · uid/gid · capset · NO_NEW_PRIVS · Landlock
                              report "R<program digest>" · install seccomp · block on gate
   host: read /proc/<pid> (NoNewPrivs, Seccomp, Cap*, ns inodes, fds, limits, net ifaces, mount propagation)
         verify == spec ──mismatch──▶ kill tree, E_NOT_APPLIED (nothing ran)
                         └─match──▶ VERIFYING→READY · sign PK_SANDBOX_APPLIED/2 · audit · RUNNING
                                    write "G" → workload execve(argv, sanitized env)
   wait: exit | timeout | cancel ─▶ SIGKILL pid-ns init (kernel kills the namespace) · reap
                    ▼ TERMINATING→CLEANED · reason record · metrics · logs · release admission
```

Seccomp program: arch check → KILL, x32 bit → KILL, JEQ per allowed nr → ALLOW, default ERRNO(EPERM) or KILL.
The gate protocol needs only `read`, `execve`, `exit_group` after the filter is live; profiles must include them.

Evidence: HMAC-SHA256 over the canonical record with node key; binds node, sandbox, tenant/workload, profile digest,
config digest, release digest, seccomp program digest, trace id, nonce, issue time. Verifier enforces trust map,
binding, ±30 s skew, 300 s age, nonce single use. Audit: append-only JSONL hash chain; verified on open.

Other backends: bubblewrap argv adapter (secondary Linux path), Seatbelt SBPL compiler (macOS, unexecuted).
