# Operations

## Credentials and first launch

`TERMINAL.cmd` creates `_runs/vws/principals.json` only after the service binds. It stores a digest and capability metadata, never a reusable plaintext token. Preserve the first displayed token privately. Losing it requires stopping the service and explicitly running `TERMINAL.cmd --new-token`; rotation invalidates prior sessions through the normal revalidation policy. No token or test credential is included in the delivered archive.

Default mode is inspection only. `--control` enables allowlisted mutations for principals with both `ship.read` and `ship.control`. The generated operator record contains those capabilities, but they do not enable mutations unless the launch flag is also present. Capability changes are read from the file on change. Do not edit credentials in a folder shared with untrusted users.

Only the installed Node/Python runtimes are used. The web gateway does not bootstrap npm, Electron, Python packages, administrator rights, services, shortcuts or registry settings. Existing engine BUILD operations are separate and retain their existing behavior. The automatic browser process itself may write its own normal browser profile; no claim is made that the entire operating system has no AppData writes.

## Startup diagnostics

`TERMINAL.cmd --check --no-browser` verifies launcher options, Python discovery, ship location and gateway configuration without creating a token or starting a listener. It does not prove the port is free or native engines can run. `python -B uc.py doctor` inspects the broader containership. Use `--port 10001` to select a different local port. Keep the folder short (`D:\UC240`) to leave space for nested engine archive extraction.

Native Windows launchers are ASCII/CRLF, quote their paths, disable delayed expansion and retain error windows. Native Windows process execution, ACL behavior, conformance and path-length behavior still require a Windows run. Legacy hold archives can contain longer/internal case-sensitive paths; no claim is made that Explorer extraction of each nested archive works. Let the existing Python BUILD path apply its own host preflight.

## Busy, cancellation, and recovery

A second web request is rejected immediately when the broker is busy. A local BUILD/VERIFY/RUN may independently own UC's ship lock; in that case the bridge returns UC's explicit busy refusal. Inspection does not bypass a mutation's lock. Run qualification suites without another local ship operation in progress.

Ctrl+C in the terminal sends a virtual signal and cancels its gateway-owned Python job. Closing the browser or shutting down the gateway also cancels that session's work. Neither a transport disconnect nor cancellation proves the native operation had no side effects. On an interrupted mutation:

```text
ship recover list
ship lifecycle vm_small
```

Then, in the local operator console, inspect the returned transaction:

```bat
python -B uc.py recover inspect TRANSACTION_ID
python -B uc.py recover rollback TRANSACTION_ID
```

Do not invoke rollback until the record is understood and all old native processes have stopped. Only unresolved transactions can be rolled back by this API. The web bridge deliberately does not expose recovery writes. Read the lifecycle again before any retry. There is no automatic retry/resume of native commands after reconnect; a reconnect creates a new volatile terminal session.

## Reproduce validation

```bat
python -B uc.py self-test
VERIFY_VWS.cmd
CHECK_VWS.cmd
python -B uc.py vws-workflow check
```

Explicitly opted-in workload tests mutate the local candidate, so use a disposable copy, build first, and do not run other ship commands concurrently:

```bat
set UC_EXECUTION_TESTS=1
cd vws
node --test tests/ship/execution.test.js
```

The separate browser experiment uses Playwright only when already available; it does not install a browser. The current environment's Chromium policy blocked navigating to loopback, so browser end-to-end qualification is not passed. Protocol tests use the actual gateway and an independent Node WebSocket client.

## Rollback and migration

The release is a new folder, not an in-place updater. Keep the user's original UC230 folder and uploaded archive. Stop UC240, inspect/cancel its outstanding jobs, then launch the previous installation from its own unchanged folder. Do not copy `_runs`, `_studio`, `_engines`, managed transactions or live TIFF state across versions blindly. There is no automated live-state migration or reverse migration in this release.
