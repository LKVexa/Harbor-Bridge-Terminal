# Migration notes — GAP-02 4.1.0 → 4.2.0

4.2.0 is wire-compatible with `PK_NODE_CAPABILITIES/1`, but it deliberately tightens invalid-input handling.

- Empty reports now raise `ReportInvalid` at the consumer boundary.
- Probe and consumer timestamps must be non-negative integers; booleans and future probe timestamps are rejected.
- Node and capability labels must match the bounded safe-label format used by the package.
- Direct corruption/mutation of `CapabilityReport.results` is detected before serialization.
- Failed/ambiguous re-probes overwrite prior state with `unprobed` and retain bounded local diagnostics.
- `canonical_bytes()` is new and should be used for signatures instead of `repr(for_consumer(...))`; it intentionally excludes dynamic `age`.
- GPU adapter observations do not imply schedulable GPU compute capability. Until a vendor/runtime probe is installed, `gpu` is `unprobed`.
- NPU remains `unprobed` without a reliable platform/vendor probe.
- `ProbeSchedule` adds deterministic interval/hot-add due calculation; it does not itself run a daemon or publish reports.
- `pk_core` remains required for the suite integration contract, but the local discovery/report primitives now import without it. Check `PK_CORE_AVAILABLE` before invoking the integration layer in standalone tooling.
