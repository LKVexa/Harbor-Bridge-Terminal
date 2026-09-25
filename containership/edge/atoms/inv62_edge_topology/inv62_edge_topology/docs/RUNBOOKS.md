# Runbooks — day 0 / day 1 / day 2 (MC-081, MC-084, MC-085)

All commands run from the directory that **contains** `inv62_edge_topology/`. They are executed by CI
(`tests/test_bootstrap.py`, `tools/ci.py`) against this artifact, so a stale command fails the build.
Owners for each runbook: see `OWNERSHIP.md` (roles currently UNBOUND — a blocking item).

## Day 0 — bootstrap a site
Prerequisites: Python 3.10–3.13; `pip install 'inv62-edge-topology[at-rest]'` if `encrypt_at_rest`; a secret
root with `0600` files for every `secret://` reference; an empty `state_dir` outside the artifact.
1. Verify the artifact: `python inv62_edge_topology/tools/release.py verify --dir <unpacked-release>` (must print `OK`).
2. Compose and dry-validate: bootstrap validates before activation; any error exits 2 with a `TOPO.*` code.
3. Bootstrap:
   ```
   python -m inv62_edge_topology.production.bootstrap --config inv62_edge_topology/examples/config.base.json \
     --overlay inv62_edge_topology/examples/overlays/prod.json --overlay inv62_edge_topology/examples/overlays/site-s1.json \
     --secrets-dir /etc/inv62/secrets --seed inv62_edge_topology/examples/seed.topology.json \
     --tenant tenant-a --state-dir /var/lib/inv62 --report /var/lib/inv62/bootstrap-report.json
   ```
4. Validate: report `ok: true`, expected `nodes`/`links`, `health().ready == true`. Archive the report.
Failure handling: exit ≠ 0 → nothing is activated; fix input and rerun (idempotent). Rollback: delete `state_dir`.

## Day 1 — deploy / upgrade (canary, staged, emergency disable)
1. **Canary** one site: install new artifact, restart instance (state recovers from WAL), run
   `python inv62_edge_topology/tools/ci.py --lanes unit,contract,security` on the host, watch alerts 30 min.
2. **Automatic abort** if any of: A-DEF-1 fires; A-DEP-* fires; wire p99 > 2.5 ms for 10 min; error ratio
   (terminal excluding NO_CAPABLE_NODE) > 0.5 %; readiness false > 2 min.
3. **Stage**: 10 % of sites → 50 % → 100 %, each stage held ≥ 1 h with no abort condition.
4. **Rollback**: stop instance, reinstall previous artifact, start (WAL format unchanged within 4.x); if the
   config changed, `admin(op, "rollback_config")` *first*. Validate with health + one resolve per site.
5. **Emergency disable**: `admin(op, "freeze")` stops all automated graph changes and lease grants while reads
   continue; to take a node out of routing, `admin(op, "quarantine", tenant=…, node=…)`. Both are audited.

## Day 2 — operate
* <a id="r-load"></a>**Load / latency:** check shed ratio and `in_flight`; raise `admission` limits via a site
  overlay (new config generation) or split tenants; confirm graph size vs `limits`.
* <a id="r-partition"></a>**Partition:** confirm with `PK_TOPO_PARTITION/1 status`; verify exactly one
  coordinator lease; on heal confirm `state: connected`, `coordinator: null`.
* <a id="r-links"></a>**Links down / flapping:** inspect probe feed (GAP-12); quarantine a flapping gateway if needed.
* <a id="r-policy"></a>**Policy rejections:** `explain(decision_id)` from the error details; check residency labels.
* <a id="r-dependency"></a>**Dependency failure:** health `dependencies` names the failed one (keys, policy,
  time, state_store, audit); the service is failing closed by design — restore the dependency; the breaker
  half-opens after 5 s.
* **Key rotation (tokens):** add new key ref to config → activate (new generation) → `keyring.rotate_to(new)` →
  wait ≥ 900 s → `retire_verify_only()` → remove old ref in next config generation.
* **State-key rotation:** `export_state()` → stop → switch `state_key` ref → start on empty `state/` →
  `import_state()` → `checkpoint()`.
* **Backup:** hourly `checkpoint()` then copy `state/snapshot.json`, `audit.jsonl`, `config/` to backup storage;
  record the audit head `(seq, digest)` externally.
* **Restore / reconstruction:** new host → bootstrap config only (no seed) → `import_state(backup)` →
  `checkpoint()` → verify health and audit head continuity. Migration between hosts is the same procedure.
* **Re-run gates** after any engine, contract, or config-schema change: `python inv62_edge_topology/tools/ci.py`.
