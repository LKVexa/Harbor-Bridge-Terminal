# ADR-0002 — Capability and egress enforcement boundary
- **Status:** Proposed · **Work items:** WI-INV20-05, WI-INV20-06

Egress is decided in three layers, all fail-closed and all in the host (never the guest):
1. **Capability** (`identity.CapabilityStore.resolve`): HMAC-bound to tenant, workload, environment,
   policy digest, expiry and epoch; revocable by id or globally (`revoke_all` = emergency disable).
2. **Authority allow-list** (`egress.DestinationPolicy`): host+port+scheme, canonicalised by the single
   `protocol.parse_authority` routine.
3. **Resolved destination**: every A/AAAA answer must be in an allowed address class (default
   `public` only); mixed answer sets are rejected; the transport receives `Destination.connect_ip`
   and must not re-resolve (TOCTOU closure). Redirects are re-authorised per hop, depth-capped, loop-detected.
Ambient proxy variables are ignored. TLS identity coherence is checked via
`egress.check_identity_coherence` at the adjacent transport (see contracts/TLS_ADJACENT_CONTRACT.md).
