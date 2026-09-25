# ADR-0003 — PK_DESCRIPTOR_TRANSPORT/1 (MC-015)

**Status:** Accepted, 4.3.0.

**Decision:** Any descriptor that crosses a process boundary travels over TLS 1.3 with mutual X.509 authentication against a pinned private CA. The channel can optionally pin the peer's DNS SAN. Frames are length-prefixed JSON of at most 4 KiB. The receiver always re-authenticates the descriptor with `from_wire`.

The stdlib `ssl` module is used, so there is no runtime dependency.

**Rejected alternatives:**

- **Custom AEAD envelope:** rejected because it means home-grown key exchange.
- **Relying on the service mesh:** rejected because it isn't verifiable from the component.

**Consequences:** Deployments must provide a CA and issue certificates (tracked as W-005). Plain sockets are refused.
