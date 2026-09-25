# Release review — candidate 1.1.0-vws.1

## Gate decision

| Gate | Result |
|---|---|
| Local/loopback use by the owner (WEB profile, `static-file` identity, fabric allowlist) | **GO** — evidence: 106/106 tests incl. real browser and real DF fabric |
| Private network / single-operator self-hosting behind a TLS reverse proxy | **CONDITIONAL** — run the suite on the target host, measure RSS, keep `VWS_MAX_SESSIONS` at 4, grant `fabric` sparingly |
| Public internet service / multi-tenant | **NO-GO** — blocked on: identity provider (D-005), container build + hosted rehearsal (I046, I047, I050), independent security review, deployed-profile load data (I053) |
| Desktop (Electron) release | **NO-GO until launched once** — code changed but never executed under Electron (I041, I043–I045, I055) |
| PowerShell gateway parity | not part of this candidate (D-001) |

## Integration packs (60)

See `ledger/release.json` for the machine-readable list and `e/I0xx/RESULT.json` for each record. Every record is `SELF_REVIEWED`; none is independent.

## Source checklist tasks (6300)

`ledger/dispositions.jsonl` holds one line per preserved task ID with its unchanged requirement hash. Statuses are assigned conservatively: PASS only where a named test or document section demonstrably satisfies that exact requirement; NOT_APPLICABLE only with the decision that makes it so; BLOCKED with the missing environment; otherwise OPEN or IN_PROGRESS. Totals are in `ledger/release.json`. No requirement text or ID was altered.

## Supply chain

Hosted build: **no third-party runtime dependencies** (Node standard library; Python standard library inside the operator's DF containers). Desktop build: `electron ^31`, `electron-builder ^24.13.3`, caret ranges, **no lockfile**, not installed here — pin and lock before any desktop release. CI workflow authored, never run. `tools/verify.js` checks `release/manifest.json` (SHA-256 of every shipped file). Base image digest must be pinned before building `deploy/Dockerfile`.

## Licensing

The supplied `LICENSE` ("All rights reserved", © 2026 David Paul Russell) is preserved unchanged and governs the whole candidate, including the new files written for the copyright holder in this run. The two schema files in `protocol/` and the vectors in `tests/vectors/` are copied byte-identical from the owner's VWS200 package. The DF containers are **not** included in the candidate; they keep their own licence files.

## Release notes

Added: `hermit.vws.v1` gateway (RFC 6455, admission, tickets, flow control, heartbeat, supervisor, drain), headless per-session worker with framed bridge, web client, DF fabric remote policy with capacity lease, optional workspace snapshots, transport abstraction, accessibility layer, local launcher, tests. Fixed (from the series audit): F01–F14, F16, F17 as described in `docs/BASELINE.md`; F15 and F18 are labelling/licensing facts and are reported truthfully. Newly found and fixed: unbounded CSI counts, lost multi-line paste, unbounded `seq`, unbounded escape accumulation in the line editor, `vfs.move` into itself.

Known limitations: a single command that writes more than the worker output buffer (4 MiB) in one synchronous call — e.g. `seq 1 1000000` — is cut with an explicit gap marker even for a fast client; one cell per code point (no wide/combining handling); no alternate screen or mouse reporting; `$?` expands at parse time; stream resume not offered; web status bar has no cwd; REMOTE-DESKTOP profile not wired.
