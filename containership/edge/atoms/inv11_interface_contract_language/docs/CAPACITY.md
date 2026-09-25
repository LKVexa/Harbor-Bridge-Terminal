# Capacity model (INV11-MC-28) — model version CAP/1

Inputs: B source bytes, K tokens, D declarations, F functions, T named types,
E type-reference edges, N syntax nesting depth, P packages.

| Stage | Time | Memory | Notes |
|---|---|---|---|
| lexer | O(B) | O(K) tokens | single pass |
| parser | O(K) | O(D) AST | recursion depth ≤ N (bounded by `max_nesting`) |
| resolver | O(D + E) | O(D + E) | one DFS per interface/world; cycle detection linear |
| normalization / fingerprint | O(D + E) | O(output) | cached per immutable `Resolved` |
| classify | O(F + T + E) | O(T²) worst case memo, O(F + T) typical | memo keyed by type pair |
| diff rendering | O(changes) | O(changes) | |

**Quadratic risk:** the comparator memo holds one entry per compared type
pair; a hostile pair of packages whose functions cross-reference many distinct
types could approach O(T_old × T_new) entries. `max_compare_steps` bounds the
total work and fails closed with `E-LIMIT`.

**Measured (see `evidence/perf.json`):** classify time grows linearly in F
(scaling ratio vs linear ≈ 1.0 across 25→800 functions). The SLO "p99 < 5 ms
per interface pair" holds up to the capacity-fit estimate recorded in the
evidence bundle with fingerprints cached; the first comparison of a fresh
`Resolved` also pays fingerprinting (~3× the warm cost).

**Limits → assumptions they protect**

| Limit | Default | Protects |
|---|---|---|
| `max_source_bytes` | 4 MiB per file and aggregate | lexer time/memory |
| `max_tokens` | 1,000,000 | parser time |
| `max_nesting` | 64 | interpreter stack (recursive descent) |
| `max_identifier` | 256 | output amplification in diagnostics |
| `max_declarations` | 100,000 | resolver / memo size |
| `max_diagnostics` | 200 | output amplification |
| `max_compare_steps` | 5,000,000 | comparator work |
| `max_json_bytes` | 16 MiB | schema ingestion |

Operators may raise limits only through an explicit `Limits` object; limits
are never relaxed from input claims or version strings. Raising `max_nesting`
above ~500 also requires raising the interpreter recursion limit.
