# Linearization points and memory ordering (reference host)

All state lives behind one `threading.RLock` (`AsyncHost._lock`). Acquire/release of that lock is the only happens-before edge; readers never read row fields outside it.

| Operation | Linearization point |
|---|---|
| allocation | `_slots[slot] = row` |
| publication (complete/trap/expire) | `row.state` leaves PENDING, after payload, error, byte charge and `ready_ns` are written in the same critical section |
| wait / subscribe registration | waiter appended, then state re-checked in the same critical section (check-and-subscribe: no lost-wakeup window) |
| take / cancel / abandon / invalidate | `_retire`: state set, accounting released, tombstone written, slot generation incremented |
| reclamation | `_free_slot`: row pointer cleared (poisoned) before the slot re-enters the free list |

Callbacks (subscriptions, `on_ready`, payload `release`) run after the lock is released.

**Not production.** A production host (component 19) must re-derive these points with runtime-native atomics (acquire on the state load, release on the state store, generation compared with the slot under the same load). None of that exists here; the Python GIL plus one lock is what makes this model correct.
