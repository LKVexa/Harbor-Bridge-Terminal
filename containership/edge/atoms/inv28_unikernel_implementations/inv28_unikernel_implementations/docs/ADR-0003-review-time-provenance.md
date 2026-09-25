# ADR-0003: Review time and provenance model (MC-096)

**Status:** PROPOSED (owner decision D-003) · **Date:** 2026-09-23

## Decision
- Each security review is a `ReviewRecord` with a reviewer, an RFC 3339 **UTC** `reviewed_at`, a result (`approved`, `conditional` or `rejected`), an evidence URI with the evidence SHA-256, and a per-toolchain `interval_days`.
- A review is stale when `now > reviewed_at + interval_days`, so the boundary instant still counts as fresh.
- `now` must be a timezone-aware UTC `datetime` from a trusted clock the host supplies. A naive or non-UTC clock gets `SEL_CLOCK_UNTRUSTED`.
- The v4.2.0 logical ticks survive only in the deprecated v1 API.

## Open
- Which reviewers are authorised, and how review evidence is stored and signed, is an upstream governance decision.
- Who supplies the trusted clock (NTP/PTP attestation) is also open.
