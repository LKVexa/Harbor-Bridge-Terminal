# INV-35 Boundary Inventory (C021)

Every boundary the component touches, with direction, trust level, interface,
authentication, failure behaviour and the test that exercises it.

| ID | Boundary | Direction | Trust | Interface / schema | AuthN / AuthZ | On failure | Tests |
|---|---|---|---|---|---|---|---|
| B1 | Guest descriptor ring | guest → INV-35 | **hostile** | `PK_VIRTQUEUE_SUBMIT/1` request (`schemas/submit/descriptor_chain.request.schema.json`) | none (data) — validated | E100–E107, audited, no mutation | `tests/fuzz`, `fixtures/*`, `test_io_model.py` |
| B2 | Guest notification | INV-35 → guest | n/a | `PK_VIRTQUEUE_COMPLETE/1` result | — | pending ⇒ always notify | `tests/concurrency` (lost-wakeup assertion) |
| B3 | VMM / vhost worker | process → Datapath | authenticated | submit/complete | capability action `submit`/`complete`, tenant+queue scoped | E300–E306 | `tests/security` T01–T09 |
| B4 | Controller (orchestration) | process → ControlPlane | authenticated, epoch-fenced | register/transition/claim | `register_memory`/`lifecycle`/`quarantine` | E303/E307 | T01, T17 |
| B5 | Operator configuration | file/API → ConfigStore | validated | `INV35_CONFIG/1` | `configure` capability + provenance digest | E500/E501/E504, active unchanged | `test_units.ConfigTest` |
| B6 | Hypervisor / VMM device model (INV-25) | upstream | trusted-for-membership only | queue list | via controller capability | queue absent ⇒ E403 | `tests/integration` |
| B7 | MicroVM runtime (INV-24) | upstream | trusted-for-regions | memory regions at registration | via controller capability | invalid region ⇒ TypeError/ValueError at registration | `tests/integration` |
| B8 | Data plane / backend (PLN-06) | downstream | trusted consumer | validated chains, completions | in-process | breaker opens E202 | `tests/faults` |
| B9 | Key service (KMS/HSM) | dependency | required | `KeyRing.sign/verify` | — | fail closed E306, not ready | T09 |
| B10 | Trusted time | dependency | required | `Authority.time_trusted` | — | fail closed E306 | T09 |
| B11 | Telemetry sinks | INV-35 → collectors | untrusted sink | Prometheus text, JSON lines | pull; redacted, cardinality-capped | drop, never block datapath | T13/T14 |
| B12 | Audit sink | INV-35 → SIEM | tamper-evident | hash-chained HMAC entries | key ring | chain break ⇒ E505 | T15 |
| B13 | Release pipeline | CI → host | digest-verified | `release/manifest/MANIFEST.json`, SBOM, provenance | evidence seal (HMAC; Sigstore planned TD-002) | promotion refused | `verify.py` gate |
| B14 | Transient-execution defence (INV-43) | peer, optional | — | none required | — | no safety change | `test_transient_execution_peer_optional` |
| B15 | `pk_core` certification framework | external | pinned (pending) | `component.py`/`contract.py` | — | `VERIFY=PARTIAL` | `test_component.py` (skips ⇒ gate non-green) |
