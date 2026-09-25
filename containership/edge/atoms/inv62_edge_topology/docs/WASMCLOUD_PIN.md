# wasmCloud pin (MC-021) — status: OPEN (external)

This archive contains **no wasmCloud host, provider, or WIT build**, and none was available in the
remediation environment, so no version can be *verified* here. `wasmcloud.pin.json` records the pin
*structure* that the release gate checks; its `verified` flag is `false` and the exit gate treats that
as blocking.

To close: choose the exact wasmCloud host and NATS versions, record their release digests and provenance
in `wasmcloud.pin.json`, run the integration suite inside that host, set `verified: true` with the evidence
path, and have the platform owner approve.
