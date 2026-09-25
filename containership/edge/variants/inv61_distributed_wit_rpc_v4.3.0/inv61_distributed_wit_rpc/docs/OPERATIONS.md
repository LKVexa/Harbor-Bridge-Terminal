# INV-61 Operations, Release & Governance Package (4.3.0)

Owner and escalation: see `OWNERS.md`. Exceptions and debt: `WAIVERS.md`.

## 1. SLOs and error budgets (C091)

| SLO | Objective | Window | Budget | Alert |
|---|---|---|---|---|
| No misreads | 0 calls dispatched against a mismatched signature | always | none | any `inv61_requests_total{status="signature-mismatch"}` spike is informational; a dispatched misread is Sev-1 |
| Deadlines | 0 responses after deadline | always | none | `INV61DeadlineBreaches` |
| Availability | 99.9 % of authenticated, authorised calls not `internal`/`unavailable` | 30 d | 43 min | `INV61AvailabilityBurn` (fast/slow burn) |
| Overhead | p99 in-process framing overhead < 50 µs | release | 1 % | release gate (`tools/perf_gate.py`) |

Support commitment: two most recent minor releases supported; security fixes backported to both.

## 2. Rollout (C092)

1. **Pre-flight**: `bootstrap.sh --verify-only` on the target (checksums, config validation, TLS files readable).
2. **Canary**: 1 node per site, 5 % traffic, 30 min. Promote only if: no Sev-1/2, error ratio ≤ baseline + 0.1 %, p99 ≤ baseline × 1.2.
3. **Staged**: 25 % → 50 % → 100 % per site, 30 min holds, same criteria.
4. **Rollback** (automatic when canary criteria fail, or operator-driven): `bootstrap.sh --rollback` reinstalls the previous verified wheel; config rollback via `ConfigStore.rollback`; state checkpoints are forward/backward compatible within `inv61-state/1`.
5. **Emergency disable**: `RpcService.set_disabled(True, actor)` (exposed through the operator control socket of the host process). Persisted; survives restart; audited. Re-enable is explicit.

## 3. Runbooks (C096)

**Day 0 — bootstrap**: `./bootstrap.sh --wheel dist/<wheel> --config /etc/inv61/config.json` → creates venv, verifies SHA256SUMS, installs with `--no-deps --require-hashes`, validates config, runs `python -m inv61_distributed_wit_rpc.selfcheck`.
**Day 1 — deploy**: rollout §2; confirm readiness `pass`, capability list matches release manifest, config digest recorded.
**Day 2 — operate**: watch dashboards; rotate keys (`KeyRing.rotate` with overlap ≥ max deadline + skew window); rotate TLS certs before expiry (≥ 7 days); verify audit chain daily (`AuditLog.verify` with anchored head); review `WAIVERS.md` monthly.

**Key compromise**: revoke key id → push ring → confirm `unauthenticated` for that key id in audit → rotate peer → incident record.
**Audit chain broken**: node refuses to start (fail closed). Preserve file, restore from backup, investigate as Sev-2 security incident.
**Stuck callee**: breaker opens automatically; if not, emergency-disable the node, drain, restart.

## 4. Backup / restore / reconstruction (C095)

State (see `docs/STATE_INVENTORY.md`): `state.json` checkpoint + `audit.jsonl`. Backup both atomically (checkpoint first) every 15 min and on drain. Restore: stop node → copy both → start; startup refuses an audit log shorter than the checkpoint's anchored sequence. If lost entirely: node starts empty; idempotency protection is lost for keys issued in the TTL window — clients MUST be told to regenerate keys (documented degradation). Restore drill is exercised by `test_restart_preserves_idempotency_disable_and_epoch`.

## 5. Incident management (C097)

| Sev | Definition | Page | Response | Update cadence |
|---|---|---|---|---|
| 1 | Misread dispatched, auth bypass, cross-tenant exposure, audit forgery | immediately, 24×7 | 15 min | 30 min |
| 2 | Availability SLO fast burn, audit chain broken, key compromise | 24×7 | 30 min | 1 h |
| 3 | Slow burn, single node degraded | business hours | 4 h | daily |
| 4 | Cosmetic / docs | none | next sprint | — |

Containment order: emergency-disable → revoke keys/grants → drain → preserve audit/state → recover → post-incident review within 5 business days.

## 6. Patching, vulnerability, EOL (C094)

Critical CVE (CVSS ≥ 9): fix released ≤ 72 h. High: ≤ 14 d. Medium: ≤ 90 d. Python runtime EOL: support dropped one release after upstream EOL. Component EOL announced two minors ahead (see `COMPAT_MATRIX.json.rules.deprecation_notice_releases`).

## 7. Recurring reviews (C098)

| Review | Cadence | Evidence |
|---|---|---|
| Access (key ring, grants) | monthly | signed review record in release repo |
| Policy (authz grants/denies) | monthly | policy version diff |
| Dependencies / SBOM / CVEs | weekly automated, monthly human | `evidence/` + scanner output |
| Configuration drift | per deploy | provenance digests |
| Architecture / ADRs | quarterly | ADR status updates |
| Waivers | monthly | `WAIVERS.md` |

## 8. Production exit gate (C100)

`tools/exit_gate.py` produces `evidence/EXIT_GATE.json` from machine evidence (tests, traceability, SBOM/checksums, benchmarks, runtime matrix, waivers). Verdict rules: any failing gate → `NO_GO`; any open waiver without owner/expiry → `NO_GO`; external evidence missing but waived with owner and expiry → `CONDITIONAL_GO`; everything present → `GO`. A human approver records the final decision; the tool never self-approves.
