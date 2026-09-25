"""Shared conformance suite: every adapter runs the same checks (contract: 'Pass the shared
broker conformance checks').  Checks gated on a feature the adapter does not declare are
reported NOT_APPLICABLE, never PASS."""
from __future__ import annotations

import uuid
from typing import Any, Callable

from ..errors import BrokerError
from .base import BrokerAdapter


def _uniq(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _drain(a: BrokerAdapter, dest: str, group: str, n: int, rounds: int = 50):
    got = []
    for _ in range(rounds):
        batch = a.consume(dest, group, 10)
        for d in batch:
            got.append(d)
            a.ack(dest, group, d)
        if len(got) >= n:
            break
    return got


def check_roundtrip(a):
    d, g = _uniq("rt"), _uniq("g")
    a.consume(d, g, 1)  # register the group first (queue-style providers create per-group queues)
    a.publish(d, {"n": 1}, key="k")
    got = _drain(a, d, g, 1)
    assert [x.value for x in got] == [{"n": 1}], got


def check_per_key_order(a):
    d, g = _uniq("ord"), _uniq("g")
    for i in range(30):
        for k in ("a", "b", "c"):
            a.publish(d, {"k": k, "i": i}, key=k)
    got = _drain(a, d, g, 90)
    for k in ("a", "b", "c"):
        seq = [x.value["i"] for x in got if x.value["k"] == k]
        assert seq == list(range(30)), (k, seq[:10])


def check_independent_offsets(a):
    d = _uniq("ind")
    for i in range(5):
        a.publish(d, i, key="k")
    g1 = _drain(a, d, "g1", 5)
    g2 = a.consume(d, "g2", 2)
    assert len(g1) == 5 and [x.value for x in g2] == [0, 1]


def check_replay(a):
    d, g = _uniq("rp"), _uniq("g")
    for i in range(4):
        a.publish(d, i, key="k")
    got = _drain(a, d, g, 4)
    a.seek(d, g, got[1].position)
    again = [x.value for x in _drain(a, d, g, 3)]
    assert again[:3] == [1, 2, 3], again


def check_fanout(a):
    d = _uniq("fo")
    a.consume(d, "s1", 1), a.consume(d, "s2", 1)  # register subscribers
    for i in range(3):
        a.publish(d, i)
    s1 = [x.value for x in _drain(a, d, "s1", 3)]
    s2 = [x.value for x in _drain(a, d, "s2", 3)]
    assert s1 == s2 == [0, 1, 2], (s1, s2)


def check_ack_redelivery(a, advance=None):
    """An unacknowledged delivery must come back, flagged redelivered.  How it comes back is
    provider-specific: explicit nack (RabbitMQ), visibility-timeout expiry (SQS: the caller
    supplies ``advance`` to move the provider clock), or next consume (reference)."""
    d, g = _uniq("rd"), _uniq("g")
    a.consume(d, g, 1)
    a.publish(d, "x", dedup_id=_uniq("dd"))
    first = a.consume(d, g, 1)
    assert first, "nothing delivered"
    if hasattr(a, "nack"):
        a.nack(d, g, first[0])
    elif advance is not None:
        advance()
    again = a.consume(d, g, 1)
    assert first and again and again[0].value == "x" and again[0].redelivered
    a.ack(d, g, again[0])


def check_error_translation(a):
    try:
        a.seek(_uniq("e"), "g", "999:999999")
    except BrokerError:
        return
    except Exception as exc:  # a raw provider exception is a conformance failure
        raise AssertionError(f"untranslated {type(exc).__name__}") from exc


CHECKS: list[tuple[str, str | None, Callable[[Any], None]]] = [
    ("roundtrip", None, check_roundtrip),
    ("per_key_order", "per_key_order", check_per_key_order),
    ("independent_offsets", "independent_offsets", check_independent_offsets),
    ("replay", "replay", check_replay),
    ("fanout", "fanout", check_fanout),
    ("ack_redelivery", "ack_redelivery", check_ack_redelivery),
    ("error_translation", None, check_error_translation),
]


def run_conformance(adapter: BrokerAdapter, *, advance: Callable[[], None] | None = None) -> dict[str, str]:
    results: dict[str, str] = {}
    for name, feature, fn in CHECKS:
        if feature and feature not in adapter.features:
            results[name] = "NOT_APPLICABLE"
            continue
        try:
            fn(adapter, advance) if fn is check_ack_redelivery else fn(adapter)
            results[name] = "PASS"
        except Exception as exc:
            results[name] = f"FAIL: {type(exc).__name__}: {str(exc)[:200]}"
    return results
