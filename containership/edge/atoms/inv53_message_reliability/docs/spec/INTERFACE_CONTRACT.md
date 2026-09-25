# Interface contract: timeouts, cancellation, retry, idempotency, backpressure (C025, C028, C029)

- **Timeouts.** Visibility is the only timeout. At the wire boundary it is evaluated on the **broker's clock**;
  the request field `now` is deprecated (5.1.0) and ignored, because a client-chosen time would let one consumer
  expire another's lease. The in-process `ReliableQueue`/`DurableQueue` APIs keep an explicit `now` for
  deterministic tests and simulations. Transports must bound their own request timeouts; a timed-out *request* is an indeterminate outcome.
- **Cancellation.** A consumer cancels work with `nack(requeue=true)`; abandoning a lease is equivalent after the
  deadline. There is no server-side cancel of an in-flight message by id — that would break fencing.
- **Retry.** Only `retryable`/`refused` kinds are retried, with full-jitter exponential backoff
  (`service.backoff`, base 0.1 s, cap 30 s). Refusals include `retry_after`.
- **Idempotency.** `put` is idempotent on (id, canonical content). `ack`/`nack` are idempotent in effect: a repeat
  returns `E_LEASE_STALE` without changing state. `redrive` of an id that is active again is refused.
- **Backpressure.** Signalled by `E_QUOTA`, `E_SHED`, `E_CAPACITY` and the `mode` in health; clients must slow down,
  not spin. Consumers are never shed.
- **Conformance fixtures.** `fixtures/wire/*.json` are request/expected-validation pairs executed by
  `test_protocol_config.py::ProtocolTest::test_conformance_fixtures`; adapters for other languages should run
  the same files.
