# Least-privilege authority model (C042, C043, C024)

Actions: `produce` (put), `consume` (receive/ack/nack/extend/health), `redrive`, `read_dlq` (explain), `admin`.
A `Grant(principal, tenant, queue|*, actions)` is always scoped to exactly one tenant; `*` across tenants is
refused at construction. Nothing is allowed without a grant. `admin` does **not** imply data-plane access.

Administrative functions (`freeze`, `emergency_disable`, `drain`, `shutdown`) are in-process methods that
take an `actor` and are audited; they are deliberately not exposed on the wire in 5.1.0. Purge is available
only through the offline CLI, which must take the store's OS lock (so it cannot race a live broker).

The broker process needs: read/write on its store root, append on its audit file, read of its key source.
It needs no network listener of its own (the transport is supplied by the embedding service) and no root.
