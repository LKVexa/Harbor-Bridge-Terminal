# UC-2.7.0 Threat Model

## Assets and boundaries
The protected assets are sealed source/cargo bytes, TIFF/GIF state, 1-bit transport packets, operator control state, workflow evidence, credentials used by the local VWS terminal, and release metadata. The current enforcement boundary is the local host process plus filesystem permissions. A Python process boundary is **not** a hypervisor or tenant-isolation boundary.

## Actors
- **Local operator:** trusted to launch the ship and control its repository.
- **Cargo author:** potentially untrusted input producer; archives, JSON, paths and cargo bytes are validated before managed mutation.
- **Terminal client:** authenticated to the loopback VWS service; read-only by default, explicit control mode for allowed mutations.
- **Guest/workload:** not treated as hardware-isolated because no bootable unikernel guest backend exists in this release.
- **External peer:** not trusted; public ingress/egress and multi-host federation remain absent.

## Primary abuse cases and controls
1. Path traversal, links/reparse points, Windows device names and ZIP collisions: rejected by `safety.py`.
2. Malformed/duplicate-key JSON: rejected by `strictjson.py`.
3. Stale generation or state writes: generation/digest fences and managed transactions.
4. TIFF offset/size/overflow abuse: guarded TIFF admission and pixel-kernel bounds.
5. WebSocket command escape: allowlisted ship command policy, authenticated loopback session, read-only default.
6. Evidence forgery by status relabeling: master/source ledgers preserve OPEN/BLOCKED states and require reproducible proof before PASS.
7. Local audit tampering: hash-chained audit records detect modification, but there is **no external anchor**.
8. Resource exhaustion: bounded archives, payloads, queues and process supervision; OS-enforced global quotas remain incomplete.

## Residual risks
Native host-process cargo can share the host trust domain. No hypervisor guest, HSM-backed key authority, distributed consensus, public-network hardening, independent production signer, or multi-tenant isolation is claimed. These remain blocked master-series components.
