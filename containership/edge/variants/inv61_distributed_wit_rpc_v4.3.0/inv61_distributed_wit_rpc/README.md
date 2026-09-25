# INV-61 — Distributed WIT RPC

**Version:** 4.3.0 (see `CHANGELOG.md`) · **Group:** 01_Source_Inventory · **Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 controls in `CHECKLIST.json` (authoritative, ADR-0002), traced in `TRACEABILITY.json`
**Production status:** see `evidence/EXIT_GATE.json` — the exit gate is **NO_GO** until the owner/approval waivers in `WAIVERS.md` are closed.

Distributed WIT RPC carries typed WIT interface calls between components on different hosts. Each frame names the interface, version and function and carries a fingerprint of the caller's signature; the receiver checks that fingerprint against its own before decoding a byte, so two sides that drifted apart fail with a clear error instead of misreading each other's arguments. Since 4.3.0 this runs over a real, authenticated, bounded network transport.

## What 4.3.0 contains

| Area | Files |
|---|---|
| WIT parser (pinned subset) and canonical codec, `PK_WRPC_FRAME/2` | `wit_model.py`, `codec.py`, `wit/kv.wit`, `docs/WIT_SUBSET.md` |
| TCP / mutual-TLS transport, multiplexing client, deadlines, cancel, retry, drain | `transport.py` |
| Request pipeline (authn → replay → authz → fence → breaker → admission → dispatch) | `server.py` |
| Keys, envelope MAC, replay guard, capability policy, HMAC-chained audit | `security.py` |
| Version negotiation with downgrade protection | `negotiation.py`, `COMPAT_MATRIX.json` |
| Idempotency, retry/backoff, token buckets, admission, circuit breakers | `resilience.py` |
| Config schema, overlays, secret references, provenance, atomic activate/rollback | `config.py`, `deploy/config.example.json` |
| Health/readiness, Prometheus metrics, JSON logs, W3C trace context, telemetry policy | `observability.py`, `docs/TELEMETRY_POLICY.md` |
| Leases + fencing, durable checkpoint | `state.py`, `docs/STATE_INVENTORY.md` |
| Standalone node, post-install self check | `demo_node.py`, `selfcheck.py` |
| 4.2.0 in-process reference (deprecated, kept) | `rpc.py` |
| Optional `pk_core` gate integration (lazy) | `component.py`, `contract.py` |

Governance and evidence: `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/THREAT_MODEL.md`, `docs/OPERATIONS.md`, `docs/PERFORMANCE.md`, `docs/adr/`, `OWNERS.md`, `WAIVERS.md`, `CHECKLIST_EXECUTION_REPORT.md`, `evidence/`.

## Running it

```
python tools/run_tests.py                       # full suite -> evidence/test_results.json
python -O tools/run_tests.py                    # same under -O
python tools/runtime_matrix.py                  # every local CPython, normal and -O
python bench/bench.py && python tools/perf_gate.py
python tools/make_release.py && python tools/verify_release.py dist
./bootstrap.sh --wheel dist/<wheel> --config deploy/config.example.json
python tools/exit_gate.py                       # -> evidence/EXIT_GATE.json
python tools/explain.py <audit.jsonl> --key-file <audit.key> --event authz-deny
```

The `pk_core` gate path (`tests/test_component.py`, `python -m pk_core ...`) needs the `gate` extra, which is not available in this archive (W-002); its three tests are reported as skipped, never as passed.

## Boundaries

Owns: frame format, fingerprints, receiver compatibility checks, typed errors, deadlines, and the authenticated transport that carries them.
Does not own: interface definitions (INV-11), routing fabric (INV-60), capability providers (INV-65), control-frame sealing (INV-36), service discovery, load balancing, component logic.

Not claimed: interoperability with the Bytecode Alliance `wrpc` wire format, cross-architecture certification, production SLO measurements, signed releases. These are tracked, owned-pending, in `WAIVERS.md`.
