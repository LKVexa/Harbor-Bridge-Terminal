# ADR-0002: Sync→async bridge

**Status:** accepted (4.3.0). **Decision:** the bridge is a runtime library (`bridge.SyncBridge`), not link-time
generated code; INV-10 composition calls it for sync-caller/async-callee edges.
Algorithm: refuse on event-loop threads and beyond `max_depth`; reserve a bounded waiter slot; `invoke`
(counted as a bridge); register a one-shot terminal listener **before** starting the callee (no lost wake-up;
already-terminal calls return their tombstone); start; fast path returns without allocating an Event when the
callee completed inline; otherwise wait on an Event with the INV-16 lock released; on deadline or caller
cancellation, cancel with a structured reason — if cancel loses the race the completion wins; keep waiting
until the terminal listener has fired, then return the value or raise `CallCancelled`/`CallTrapped`/`BridgeTimeout` once.
**Seam:** a production runtime replaces the `threading.Event` in `_Waiter` with its native waitable.
