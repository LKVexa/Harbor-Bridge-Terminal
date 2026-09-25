"""Binding contract for INV-36 - Control transport."""
from __future__ import annotations

from .pkcore_adapter import require

Contract, Dependency, Slo = require("contract", "Contract", "Dependency", "Slo")  # dynamic estate types

ELEMENT_ID = "INV-36"
ELEMENT_NAME = "Control transport"


def build() -> Contract:
    """Return the production contract for INV-36."""
    return Contract(
        element=ELEMENT_ID,
        name=ELEMENT_NAME,
        responsibility=(
            "Own the small authoritative control-message channel: authenticated session context, "
            "per-frame authenticated encryption, strict sequencing, replay/reordering rejection and "
            "frame bounds end to end across opaque relays."
        ),
        owns=[
            "Session traffic-key derivation from authenticated establishment material",
            "Per-frame authenticated encryption",
            "Strict monotonic sequencing and replay/reordering rejection",
            "Frame size and sequence-space bounds",
            "End-to-end confidentiality and integrity across relays",
        ],
        not_owns=[
            "Attestation evidence production and KMS/HSM operation (consumed via adapters)",
            "Bulk payload movement",
            "NAT traversal and relay selection",
            "Control-message business semantics",
            "Scheduling",
        ],
        dependencies=[
            Dependency("GAP-06 Device identity/attestation", "upstream", "Authenticates peers and supplies session-establishment material"),
            Dependency("GAP-12 WAN resilience and NAT traversal", "downstream", "Relays bounded sealed frames it cannot open"),
            Dependency("PLN-03 Distributed runtime plane", "downstream", "Sends leases and placements over this channel"),
            Dependency("INV-37 Bulk data plane", "peer", "Carries large payloads referenced by control messages"),
        ],
        source_of_truth="The authenticated PK_CTRL_FRAME/2 accepted by the receiver; relay assertions about frame contents are untrusted.",
        assumptions=[
            "Session establishment authenticates both peer identities before a shared secret is handed to this component",
            "A fresh 16-byte-or-longer session_id is agreed for every establishment using the same shared secret",
            "Every peer, network path and store can fail independently",
            "Callers are untrusted until their identity is established",
            "Relays may observe, drop, duplicate, delay, reorder or modify ciphertext",
        ],
        boundaries={
            "tenant": "session keys and traffic must be partitioned per tenant",
            "environment": "limits and endpoints may differ per environment but the frame protocol does not",
            "site": "each site may run independent relays; no global singleton is assumed",
            "workload": "sessions are scoped to authenticated workload/node identities",
        },
        mandatory=[
            "Use PK_CTRL_FRAME/2 (AES-256-GCM-SIV) for every control frame",
            "Use a fresh session identifier for every authenticated establishment",
            "Authenticate each frame before it can advance receive state or reach message semantics",
            "Accept only the exact next sequence number; reject replayed or reordered frames",
            "Refuse plaintext above 64 KiB and wire frames above the protocol bound",
            "Never expose plaintext or traffic keys to an opaque relay",
            "Re-establish the session before the 64-bit sequence space is exhausted",
        ],
        optional=[
            "Bounded ciphertext history for local diagnostics",
            "Per-tenant tuning below the hard protocol frame ceiling",
            "Additional transport adapters beyond the shipped virtio-vsock adapter, provided they preserve end-to-end sealing",
        ],
        non_goals=[
            "Moving bulk data",
            "Choosing relays",
            "Operating the KMS/HSM that holds long-term keys (INV-36 consumes it through keys.KeyProvider)",
            "Producing attestation evidence (INV-36 verifies it through handshake.AttestationVerifier)",
            "Interpreting control messages",
        ],
        interfaces={
            "stream": "PK_CTRL_STREAM/1 - preamble plus bounded length-delimited records over virtio-vsock",
            "handshake": "PK_CTRL_HS/1 - signed-ephemeral X25519 mutual authentication exporting session material",
            "message": "PK_CTRL_MSG/1 - canonical typed control envelope (type, tenant, op_id, traceparent)",
            "session": "PK_CTRL_SESSION/2 - authenticated establishment material plus fresh session_id and ordered directional state",
            "frame": "PK_CTRL_FRAME/2 - versioned AES-256-GCM-SIV sealed frame with 64-bit sequence",
            "relay": "PK_CTRL_RELAY/1 - opaque bounded forwarding of sealed frames",
        },
        threats=[
            "Relay operator reading control traffic",
            "Replay of a stale revocation, placement or lease",
            "Out-of-order delivery changing authoritative control state",
            "Frame/header/ciphertext tampering in transit",
            "Reflection of a frame back to its sender",
            "Cross-session frame injection",
            "Oversized frames or unbounded diagnostic retention exhausting memory",
            "Concurrent senders racing and reusing a sequence number",
        ],
        failure_modes=[
            "Authentication failure",
            "Replay detected",
            "Out-of-order frame detected",
            "Malformed or unsupported frame version",
            "Frame too large",
            "Session key/session-id mismatch",
            "Sequence space exhausted",
            "Session closed",
        ],
        slos=[
            Slo("authenticity", "zero unauthenticated frames acted upon", "no budget"),
            Slo("relay blindness", "zero plaintext bytes visible to any relay", "no budget"),
            Slo("control latency", "p99 seal+open under 50us per small frame on a certified target", "1% may exceed"),
        ],
        signals={
            "frames_sealed": "counter by session",
            "frames_opened": "counter by session",
            "auth_failures": "counter by reason",
            "replays_rejected": "counter by session",
            "out_of_order_rejected": "counter by session",
            "malformed_frames": "counter by reason",
            "frame_bytes": "histogram",
        },
    )
