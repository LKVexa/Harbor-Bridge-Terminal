# INV-36 - Control transport

**Version:** 5.1.0  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series  
**Checklist:** 100 controls in `CHECKLIST.json`; 752-item missing-component checklist tracked in `MC_CHECKLIST_STATUS.json`  
**Wire protocols:** `PK_CTRL_STREAM/1`, `PK_CTRL_HS/1`, `PK_CTRL_FRAME/2` / `PK_CTRL_SESSION/2`, `PK_CTRL_MSG/1`

INV-36 carries small authoritative control messages (placements, leases, revocations, drains) between host and guest agents over virtio-vsock. 5.1.0 adds everything above and around the 5.0.0 frame layer that a production control channel needs: the vsock adapter, stream framing, an authenticated forward-secret handshake, key custody/rotation hooks, a typed message envelope and IDL, authorization and tenant policy, configuration, health/backpressure, restart semantics, quarantine, observability, a tamper-evident audit log and a certification gate.

**Production status: not certifiable yet.** The repository-local gate passes everything it can check here except governance (no license, no named owners). The real `pk_core` estate gate, certified real-vsock VM rows, a production KMS/HSM adapter, a managed signing identity, and external review of the new handshake are still missing. See `docs/MC_CHECKLIST_STATUS.md` and `AUDIT_REPORT.md`.

## Layout

| Path | Contents |
|---|---|
| `transport.py` | PK_CTRL_FRAME/2 (AES-256-GCM-SIV, exact-next sequencing) - unchanged from 5.0.0 |
| `stream.py`, `vsock.py` | PK_CTRL_STREAM/1 framing; AF_VSOCK adapter; fake streams with fault injection |
| `handshake.py`, `keys.py` | PK_CTRL_HS/1; credentials, trust store, revocation, attestation hook; key custody, epochs, rotation |
| `messages.py`, `schema/`, `_wire.py` | PK_CTRL_MSG/1; IDL and generated constants; JSON schemas |
| `policy.py`, `quarantine.py` | authorization / tenant policy; quarantine and kill switch |
| `config.py`, `health.py`, `recovery.py` | configuration; health, retry, admission, breaker, failover; restart/recovery |
| `observability.py`, `audit_log.py` | metrics, logs, tracing, explain; hash-chained signed audit log |
| `endpoint.py` | `ControlEndpoint` - the full stack |
| `gate.py`, `audit.py`, `pkcore_adapter.py` | certification gate and evidence; single pk_core boundary |
| `tools/` | fuzz, bench, soak, release (SBOM/provenance/sign/verify), traceability, mc_status, docs_check, secret_scan, vsock_smoke, gen_wire |
| `docs/` | ADR, protocol, requirements, traceability, runbooks, governance, release, security-adjacent specs |
| `governance/`, `release/`, `compat/`, `perf/`, `requirements/`, `fixtures/` | owners/waivers/debt, exit gate + manifest, compatibility matrix, thresholds/baseline, requirements, golden fixtures |

## Install and test

```text
python -m pip install -r requirements.txt            # cryptography>=46.0.4,<47 (only runtime dependency)
cd ..                                                # run from the directory containing inv36_control_transport
python -m unittest discover -s inv36_control_transport/tests -t inv36_control_transport/tests
python -O -m unittest discover -s inv36_control_transport/tests -t inv36_control_transport/tests
python -m inv36_control_transport.audit              # local gate; writes evidence/<timestamp>/gate-evidence.json
python -m inv36_control_transport.audit --certify    # production mode: SKIP/ERROR block
```

## Minimal use

```python
from inv36_control_transport.messages import ControlMessage
from inv36_control_transport.testing import World, connect_pair   # test PKI - never for production

w = World()
host = w.endpoint("host:h1", "host_agent", "t1",
                  handlers={"LEASE_REVOKE": lambda principal, msg: None})
guest = w.endpoint("guest:g1", "guest_agent", "t1")
server_ch, client_ch = connect_pair(host, guest)          # PK_CTRL_STREAM/1 + PK_CTRL_HS/1 over an in-memory stream
client_ch.send(ControlMessage.of("LEASE_RENEW", "t1", b"lease-42"))
server_ch.serve_one()                                      # decrypt -> authorize -> admit -> dispatch
```

In production, build `ControlEndpoint` with a `KeyProvider`-backed identity key, credentials from the GAP-06 issuer, the estate trust store and revocation feed, a loaded `PolicyStore`, a `QuarantineRegistry`, an `AuditLog`, and connections from `vsock.vsock_connect` / `vsock.VsockListener`.

## Source material

`MASTER.md` (referenced by 4.1.0) is still missing and has not been reconstructed; see `docs/MASTER_MD_STATUS.md`. The governing checklist for this pass is kept verbatim in `docs/source/` with its SHA-256.
