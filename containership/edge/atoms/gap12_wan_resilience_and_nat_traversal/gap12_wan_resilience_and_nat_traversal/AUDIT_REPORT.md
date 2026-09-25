# GAP-12 v4.3.0 — checklist application report

**Date:** 2026-09-22 · **Input:** `gap12_wan_resilience_and_nat_traversal_v4.2.0_Audited_Hardened.zip` (sha256 `f6fa0f3c…7f70`) · **Checklist:** GAP-12 WAN Resilience & NAT Traversal Professional Engineering Checklist v4.2.0 (116 components, 2,420 sub-checks) · **Output version:** 4.3.0
The v4.2.0 audit is kept at `docs/AUDIT_REPORT_v4.2.0.md`.

## Verdict

| Measure | Result |
|---|---|
| Sub-checks evaluated | 2,420 / 2,420 (every item gets exactly one state) |
| PASS / NOT-EVIDENCED / FAIL / WAIVED | **615 / 1,805 / 0 / 0** |
| Component exit gates passed | **0 / 116** (P0 0/80 · P1 0/34 · P2 0/2) |
| Global definition of done | 2 of 7 PASS (G-DOD-03 bounded retries/resources, G-DOD-06 explainable decisions) |
| Production gate | **NO-GO** |
| Tests | 140 PASS · 0 FAIL · 3 SKIP (the `pk_core` conformance tests — `pk_core` is not in this package) |
| Kernel NAT lab | 11 / 11 scenarios, real netfilter NAT, pcaps kept |
| Benchmarks | 17 / 17 inside proposed budgets at representative and worst-supported load, no fd/thread leaks |
| Build | two builds byte-identical; SBOM + provenance bound to the artifact digest; provenance **unsigned** |

**Why no exit gate can pass here.** Every component carries items only people can close: a named engineering owner,
security reviewer, operational owner and escalation path (`-10`), and machine-readable acceptance evidence that
includes security-review findings and approved waivers (`-21`). No owner was assigned, no security review happened
and no waiver approver exists — this build does not invent any of them. On top of that the environment cannot
provide: IPv6 (the kernel has none), NAT64/464XLAT, tc/netem impairment, independent STUN/TURN implementations
(package indexes are blocked), a signing identity, or a vulnerability scanner.

The falsifier for this verdict is in `tests/test_i_release.py::EvaluatorFalsifierTest`: a fabricated PASS for an
owners item, a SKIP and a forged waiver are all refused, while a *synthetic, clearly labelled* approver that signs
waivers for one component's open items does open that component's gate — so the gate is a gate, not a wall.

## How each item was decided

`evidence/evaluate.py` maps every sub-check to one of 73 kinds by its template text (`evidence/kinds.py`) and
applies one rule per kind:

- **Test-evidenced kinds** — PASS only when a test tagged `@covers("<component>:<kind>")` ran and passed and no
  tagged test failed. Tags are audited claims; a tag for a kind the component does not have stops the evaluator
  (it caught 60 such tags in this build's own tests, all fixed). There is no cross-component credit.
- **Unit tests** — additionally need ≥ 80 % line coverage of the component's runtime module(s) (stdlib tracer).
- **Integration** — a real-dependency test or a passing lab scenario; the report says that counterparts are this
  package's own RFC implementations or kernel netfilter, not independent implementations.
- **Documents** (normative statement, interfaces, dependencies, parameters, runbook, protocol map/ADR, threat model)
  — generated from `evidence/registry.py`; interfaces also require every named symbol to exist (else FAIL).
- **Lab-matrix kinds** (full NAT matrix, pcaps of all six path types, OS transitions, IP-family matrix) —
  NOT-EVIDENCED with the covered subset stated.
- **Performance** — the component's benchmarks inside budget at both loads; budgets are proposals, not SLOs.
- **Human kinds** (owners, vulnerability SLA, escalation contacts) and **acceptance** — NOT-EVIDENCED.
- **Exit gate** — PASS only if every other item of the component is PASS or validly WAIVED.

## Defects found in the candidate (v4.2.0) and fixed

1. **Synchronised first retry.** `retry_delay()` rounded to whole seconds with a 1 s floor, so after a common
   failure every peer's first retry fell on exactly t+1 s. The 10,000-peer simulation measured 100 % of the fleet in
   one instant (the "per-path jitter de-synchronizes retry storms" claim held only from the third round). Fixed with
   millisecond resolution and a 0.5 s floor: worst 10 ms window now 2.3 % of the fleet. The v4.2.0 test pinned the
   old value (`retry_at == 1`); that assertion and one bound were updated and commented.
2. **Package not importable without `pk_core`.** `__init__.py` imported `component.py` → `pk_core` eagerly, so the
   "framework-independent" `path.py` could not be used through the package. Now lazy.

## Defects found in this pass's own work and fixed (each caught by the pass's own checks)

| Caught by | Defect |
|---|---|
| NAT lab | STUN client dropped RFC 5780 CHANGE-REQUEST answers from the alternate address → full cone read as port-restricted |
| NAT lab | CGNAT assessment ignored "gateway WAN ≠ mapped address" unless the WAN address was private |
| NAT lab | hole punching failed through Linux MASQUERADE (inbound-first conntrack forced the peer onto another port) → low-TTL priming |
| fuzzer | config validator crashed on type-invalid documents (20 crashers kept in `evidence/fuzz-regressions/`) |
| fuzzer | DNS decoder raised `struct.error` on truncated questions |
| unit test | DNS resolver deadlines used the injectable clock → a frozen test clock hung a lookup |
| benchmark | event-log suppression map grew per peer without bound (7 MB at 20k peers) |
| benchmark | ICE recomputed SHA-256 foundations in loops (31.7 → 1.6 ms); PathStore deep-copied per transition (200 → 7 µs) |
| benchmark review | timings were taken under tracemalloc (4–5× inflation) — methodology fixed, budgets unchanged |
| evaluator | 60 coverage tags claimed kinds their component does not have |
| syntax check | the tag-rewriting script itself corrupted two `b""` literals |
| unit tests | out-of-scope kill-switch controls were unaudited; controller mislabelled "no attempt inside backoff" as NET_UNREACHABLE |

## Checklist defects (reported, not repaired — the checklist is never edited)

14 component-specific items were copied into the wrong components by keyword: the STUN/TURN items appear under
**G12-D047** (TURN credential lifecycle), **G12-E062** (dependency health model) and **G12-I109** (Day-0 runbook);
the QUIC items appear under **G12-A016** (TLS/TCP fallback). They are evaluated as written, flagged
`checklist_defect`, and not credited from the component they were copied from. (G12-H087 legitimately carries the
STUN/TURN text — it is the interop-test component — and is NOT-EVIDENCED because no independent implementation exists.)

## What was actually exercised

- **Kernel NAT lab** (`lab/`): network namespaces, veth pairs over raw rtnetlink, netfilter NAT. STUN discovery
  (EIM/APDF → consistent; APDM → `DEP_INCONSISTENT`; UDP-blocked → `NET_UDP_BLOCKED`; 30 % loss → retransmission
  recovers), RFC 5780 classification of three NAT profiles, double-NAT CGNAT verdict "likely", TCP fallback when UDP is
  dropped, and two end-to-end controller runs: **direct fails → hole-punch succeeds** through two port-restricted NATs
  (pcap shows 198.51.100.1:40000 ↔ 192.0.2.1:40000), and **direct → hole-punch fail → TURN relay succeeds** through two
  symmetric NATs, each path admitted only after GAP-06-style attestation.
- **Retry storm**: 10,000 peers × 7 rounds on a virtual clock.
- **Fuzzing**: structure-aware, seeded, time- and memory-bounded (STUN/TURN, ChannelData, DNS, config, ICE, PCP).
- **Concurrency**: success/failure/reload/clock-jump/readers racing on one peer with deadlock detection.

## Not done, and why

QUIC (no stdlib stack), TURN over TCP/TLS and server failover, SSDP/HTTP for UPnP, live PCP/NAT-PMP gateways,
IPv6/NAT64/464XLAT anything, delay/jitter/reorder/corruption/MTU impairment (no tc), OS network-change events, soak
tests, interop with coturn or other independent servers, signed provenance, vulnerability scanning, and every
people-owned decision. Each is named on its items in `evidence/out/evaluation.json`.
