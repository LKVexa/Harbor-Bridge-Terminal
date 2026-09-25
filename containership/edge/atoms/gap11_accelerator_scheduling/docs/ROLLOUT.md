# GAP-11 rollout / rollback / mixed-version behaviour (GAP11-*.19)

Global: feature gates live in `config.feature_gates` (default off for gang allocation and preemption); WAL v1 and `ctl/leader` are shared by all 4.x controllers; see docs/COMPATIBILITY.md and RUNBOOK-02/03.

| Component | Rollout / compatibility note |
|---|---|
| GAP11-P0-01 | WAL format v1; readers skip records <= snapshot revision; a v2 format must be read-compatible for one release. |
| GAP11-P0-02 | Enable by default; there is no unfenced mode. |
| GAP11-P0-03 | Mixed-version controllers must share the ctl/leader format. |
| GAP11-P0-04 | lease_ttl_s / lease_grace_s are config; shortening TTL is a risky change requiring canary. |
| GAP11-P0-05 | Retention is config; lowering it below client retry horizons is unsafe. |
| GAP11-P0-06 | New vendor = new normalize() branch behind a feature gate. |
| GAP11-P0-07 | Profiles are data; adding one is additive. |
| GAP11-P0-08 | No mode disables scrub (dangerous_skip_scrub is forbidden by schema). |
| GAP11-P0-09 | Firmware allowlist is config. |
| GAP11-P0-10 | Key rotation overlap then retire. |
| GAP11-P0-11 | Rules additive; removal is a breaking change. |
| GAP11-P0-12 | See docs/COMPATIBILITY.md. |
| GAP11-P0-13 | Feature-gated behind mTLS termination for non-loopback. |
| GAP11-P0-14 | Caps are config. |
| GAP11-P0-15 | Event schema additive. |
| GAP11-P0-16 | Runs in ci.sh. |
| GAP11-P1-17 | feature_gates.gang_allocation default off. |
| GAP11-P1-18 | Scoring change = canary. |
| GAP11-P1-19 | Thresholds are config. |
| GAP11-P1-20 | Signal catalogue additive. |
| GAP11-P1-21 | n/a |
| GAP11-P1-22 | feature_gates.preemption default off. |
| GAP11-P1-23 | Precedence change = ADR. |
| GAP11-P1-24 | n/a |
| GAP11-P1-25 | n/a |
| GAP11-P1-26 | n/a |
| GAP11-P1-27 | n/a |
| GAP11-P1-28 | n/a |
| GAP11-P1-29 | Keys additive; removal = major. |
| GAP11-P1-30 | n/a |
| GAP11-P1-31 | n/a |
| GAP11-P1-32 | n/a |
| GAP11-P2-33 | n/a |
| GAP11-P2-34 | n/a |
| GAP11-P2-35 | n/a |
| GAP11-P2-36 | n/a |
| GAP11-P2-37 | n/a |
| GAP11-P2-38 | n/a |
| GAP11-P2-39 | Thresholds unapproved (owner decision). |
| GAP11-P2-40 | n/a |
| GAP11-P2-41 | n/a |
| GAP11-P2-42 | n/a |
| GAP11-P2-43 | n/a |
| GAP11-P2-44 | n/a |
| GAP11-P2-45 | n/a |
| GAP11-P2-46 | n/a |
| GAP11-P2-47 | n/a |
| GAP11-P2-48 | n/a |
| GAP11-P2-49 | n/a |
| GAP11-P2-50 | n/a |
