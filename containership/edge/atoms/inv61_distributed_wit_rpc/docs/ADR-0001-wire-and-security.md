# ADR-0001 — Wire format, handshake and record protection for INV-61 (M22)

* **Status:** PROPOSED — needs an accountable owner and an approver (both UNASSIGNED)
* **Date:** 2026-09-22
* **Deciders:** _owner to name_

## Context
v4.2.0 had an in-process dispatcher only. INV-61's contract excludes transport encryption
(owned by INV-36 for control-class frames) and service discovery, but a cross-host RPC needs
some transport, peer identity and replay safety to be usable at all.

## Decision
1. **Wire:** length-prefixed messages over TCP; `PK_WRPC_FRAME/2` binary envelope with
   canonical LEB128/IEEE value encoding (`wrpc/codec.py`).
2. **Identity:** pre-shared keys per peer with key ids, expiry, rotation, revocation; mutual
   HMAC transcript authentication (`wrpc/security.py`).
3. **Records:** AES-256-GCM, direction-bound 96-bit nonce from a 64-bit sequence; replay and
   reorder rejected.
4. **Boundary:** INV-61 provides this as a *default adapter*. INV-36 remains the owner of
   control-class sealing; a deployment that already has mTLS MAY substitute it — the
   receiver pipeline after "record authentication" is unchanged.

## Alternatives considered
* **mTLS via `ssl`** — stronger ecosystem, but needs a PKI this archive does not have; kept
  as the preferred production substitution (open item in THREAT_MODEL.md T-12).
* **Noise protocol** — good fit, needs a third-party library with no pinning path here.
* **No transport (status quo)** — leaves every M03/M06/M08/M09 item open.

## Consequences
* One third-party dependency (`cryptography`).
* PSK distribution is an operational burden; compromise of a PSK exposes that peer's sessions
  (no forward secrecy — see THREAT_MODEL.md T-11).
* Exact-field envelope makes additive evolution a new wire major; negotiation carries it.

## Escalation
Security defect → owner → security reviewer; protocol change → owner + INV-11/INV-36/INV-60
owners. All currently UNASSIGNED.
