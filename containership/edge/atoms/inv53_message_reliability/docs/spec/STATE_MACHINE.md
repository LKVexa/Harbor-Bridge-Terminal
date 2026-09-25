# Normative lifecycle state machine (C015) — `inv53.store/1`

States: **READY**, **IN_FLIGHT(lease, deadline, attempt)**, **DEAD_LETTERED(reason, attempts, last_lease)**,
**SETTLED** (acked; removed), **PURGED** (dead letter removed by an operator).

The table below is normative. `tests/test_repository.py` checks that every journal op in the table exists
in `durable._State.apply` and vice versa.

| # | Journal op | From | To | Guard | Effect |
|---|---|---|---|---|---|
| T1 | `put` | — | READY | id not active; size ≤ max_message_bytes; ready < max_ready | append to ready tail |
| T2 | `lease` | READY (head) | IN_FLIGHT | in_flight < max_in_flight; attempt+1 ≤ max_attempts | new token; deadline = now + visibility |
| T3 | `ack` | IN_FLIGHT | SETTLED | token == current; now < deadline | acks += 1; attempt state dropped |
| T4 | `requeue` | IN_FLIGHT | READY | (nack with requeue, attempt < max) or (expiry with attempt < max); ready < max_ready | redeliveries += 1 |
| T5 | `dead` | IN_FLIGHT | DEAD_LETTERED | (nack requeue=false) or attempt ≥ max_attempts; dlq < max_dead_letters | reason recorded |
| T6 | `extend` | IN_FLIGHT | IN_FLIGHT | token == current; now < deadline; extension ≤ max_lease_extension | deadline = now + extension |
| T7 | `redrive` | DEAD_LETTERED | READY | id not active again; ready < max_ready | attempt budget reset; audited |
| T8 | `purge` | DEAD_LETTERED | PURGED | operator (service_owner) | audited |
| T9 | `epoch` | — | — | new writer opened the store | fencing marker |

Expiry is evaluated before every receive/ack/nack/extend at the supplied `now`, in id order, and emits T4
or T5 for each expired lease. There is no transition out of SETTLED or PURGED.
