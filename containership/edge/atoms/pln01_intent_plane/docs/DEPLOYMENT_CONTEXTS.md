# Deployment contexts and disconnected-site semantics (MC-004)

Sites are declared in config (`sites.<id>.context`) and carried as the `site` attribute of a node. A plan may span
sites but never merges their state.

| Context | Default staleness limit | Reporter cadence (expected) | Writer placement | Behaviour when report older than limit |
|---|---|---|---|---|
| cloud | 60 s | 15 s | regional primary | site `disconnected`; steps held `site-disconnected` |
| datacenter | 120 s | 30 s | regional primary | same |
| near-edge | 600 s | 120 s | regional primary (edge never writes intent) | same |
| far-edge | 3600 s | opportunistic | regional primary | same; drift is **unknown**, never inferred |

Rules (implemented in `service.py`, tested in `DisconnectedSites`):

1. **Staleness:** `age = now − observed_at`; `age > limit` ⇒ `disconnected`. Steps targeting nodes at that site are
   emitted with `held: "site-disconnected"` so executors do not act on unverifiable state.
2. **Ordering:** a report with lower `sequence` or older `observed_at` than the last accepted one for the site is
   ignored (`accepted: false`) — out-of-order delivery after reconnect cannot roll state back.
3. **Clock skew:** `observed_at` more than 300 s in the future is rejected (`PLN01-E0001`).
4. **Queueing:** edge sites do not queue intent mutations locally; intent is authored centrally. Reporters may
   buffer reports and replay on reconnect; only the newest per site is kept.
5. **Merge:** there is no merge of divergent intent — a single writer (ADR-0002) owns the graph.
6. **Reconnect:** the first in-order fresh report flips the site to `connected`; held steps are released in the next plan.
