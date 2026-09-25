# INV-68 configuration (MC-10, MC-11; C032–C039)

`PK_PACK_CONFIG/1` — schema `schemas/PK_PACK_CONFIG_1.schema.json`, normative
validation `config.validate()`, secure defaults `config.DEFAULTS`
(example: `examples/config.json`).

| Key | Default | Range | Meaning |
|---|---|---|---|
| `headroom` | 0.10 | [0, 1) | reserve on every dimension of every host |
| `cpu_overcommit` | 1.5 | [1, 4] | CPU ratio; **memory is always 1.0 and has no key** |
| `limits.*` | see INTERFACES.md | per key | payload, workloads, name length, concurrency, queue, timeout, staleness |
| `tenants.default_quota` / `overrides` | 2000 workloads/request, 120 req/min | ≥ 1 | fairness |
| `provenance` | required | — | author, change_ref, created, layers |

**Immutable vs mutable:** code and schemas are immutable artifacts (wheel digest);
configuration is versioned, digest-addressed data; the only runtime mutable state is
the store (`ACTIVE`, journal, `FROZEN`) and in-memory caches.

**Overlays:** `compose(base, ("environment:prod", {...}), ("site:edge-7", {...}))`
(RFC 7386 merge; later layers win; schema/provenance not overridable; layers recorded).

**Activation:** `PackingService.activate_config(token, cfg, expected_digest=...)` —
`config:activate`, CAS on the active digest, controller epoch fence, inter-process lock,
audit fail-closed, snapshot fsync, journal append, atomic pointer swap.
**Rollback:** `rollback_config(token)` re-activates the previous snapshot (audited).
**Secrets:** only `secretref://` references; inline credentials → `SECRET_IN_CONFIG`.
