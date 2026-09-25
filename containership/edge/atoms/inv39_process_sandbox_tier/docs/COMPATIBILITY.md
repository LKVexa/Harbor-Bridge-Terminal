# Compatibility, versioning and deprecation (MC-007 / MC-012 / MC-017 / MC-096)

## Supported matrix
| Dimension | Supported (claimed) | Tested in this pass | Status |
|---|---|---|---|
| CPU arch | x86_64, aarch64 | x86_64 only (aarch64 compiler semantics checked by emulator) | PARTIAL |
| Linux kernel | ≥ 5.13 (Landlock optional), seccomp filter, unprivileged user ns | 6.18.44 | PARTIAL |
| Python | 3.10–3.13 | 3.11.15 | PARTIAL |
| bubblewrap | ≥ 0.6 | not installed on test host | NOT TESTED |
| macOS / Seatbelt | 13+ | none | BLOCKED |
| Schemas | PK_SANDBOX_PROFILE/1, PK_SANDBOX_APPLIED/1+/2, PK_SANDBOX_ERROR/1, PK_SANDBOX_STATUS/1 | all | OK |

## Version policy
* Schema ids are `FAMILY/N`. Additive, optional fields do not bump N; anything else does.
* A node supports N and N-1 of every family (`control.SUPPORTED`); `negotiate()` picks the highest common version, else `E_VERSION_UNSUPPORTED`.
* `PK_SANDBOX_APPLIED/1` (caller-supplied read-back, `os_enforcement_proven=false`) is **deprecated** as of 5.1.0 and removed no earlier than 7.0.0 or 2027-03-31, whichever is later; consumers must accept /2.
* Backends: the native launcher is the default; switching `backend` is a configuration change subject to the tighten-only overlay rules and canary rollout.
* Mixed-version peers: a /1-only consumer receives /1 records from `Sandbox.start()` only; kernel-verified launches always emit /2 and are refused to a /1-only peer (never downgraded silently).
