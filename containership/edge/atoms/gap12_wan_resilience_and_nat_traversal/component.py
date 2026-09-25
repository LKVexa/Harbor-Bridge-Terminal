"""GAP-12 - WAN resilience and NAT traversal.

The production contract is evaluated through ``pk_core`` while the isolated path
state machine lives in :mod:`.path` so its failure semantics can be tested without
the framework installed.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component
from pk_core.integration import resolve as sibling

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .path import BACKOFF_CEILING, PROBE_FRESHNESS, STRATEGIES, Partitioned, Path


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


def _expect_partitioned(path: Path, prober, now: int) -> None:
    try:
        path.connect(prober, now=now)
    except Partitioned:
        return
    raise AssertionError("expected Partitioned")


class WanResilienceAndNatTraversalComponent(Component):
    """Master-applied component for GAP-12."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        # Implementation/configuration findings are left to the framework's
        # documentary evidence.  Path-selection behaviour belongs to resilience,
        # not to configuration-provenance checklist slots.
        return super().assess_implementation(items)

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        inv36 = sibling("INV-36")

        # C047: encrypt sensitive data in transit.  GAP-12 owns path selection, not
        # transport encryption, so the result depends on the adjacent control
        # transport actually being installed and verified.
        if inv36 is None:
            findings[6] = self.partial(
                items[6],
                "Path selection keeps relay as untrusted transit, but end-to-end transport protection is an adjacent-layer dependency.",
                note="INV-36 Control transport is not installed here",
            )
        else:
            a = inv36.Session("site-a", "site-b", b"attested")
            b = inv36.Session("site-b", "site-a", b"attested")
            relay = inv36.Relay()
            msg = b"LEASE renew node-7"
            _verify(b.open(relay.forward(a.seal(msg))) == msg, "relayed frame failed to open")
            _verify(all(msg not in frame for frame in relay.seen), "relay observed plaintext")
            findings[6] = self.satisfied(
                items[6],
                "Relayed traffic is protected end to end by INV-36 while GAP-12 treats the relay as untrusted transit.",
                *self._evidence("contract.py"), "INV-36/Session", "INV-36/Relay",
            )

        # C048: safe behavior when identity/key dependencies are unavailable.  This
        # package can prove honest path health locally but cannot certify the full
        # dependency-failure policy without the adjacent trust subsystem.
        p = Path("ams", _jitter_seed=1)
        p.connect(lambda s: s == "direct", now=0)
        _verify(p.healthy_at(PROBE_FRESHNESS), "fresh path should be healthy")
        _verify(not p.healthy_at(PROBE_FRESHNESS + 1), "stale path still reported healthy")
        if inv36 is None:
            findings[7] = self.partial(
                items[7],
                f"Path health expires after {PROBE_FRESHNESS}s, but identity/key-service outage policy requires the absent trust transport integration.",
                note="INV-36 not installed; dependency-outage behavior is only partially testable in this package",
            )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)

        # C052: automated health/stall detection.
        health = Path("ams", _jitter_seed=1)
        health.connect(lambda s: s == "direct", now=0)
        _verify(health.state(PROBE_FRESHNESS)["healthy"], "fresh path not healthy")
        _verify(not health.state(PROBE_FRESHNESS + 1)["healthy"], "stale path still healthy")
        findings[1] = self.satisfied(
            items[1],
            f"Path readiness expires after the {PROBE_FRESHNESS}s freshness window instead of trusting stale success evidence.",
            *self._evidence("path.py::Path.healthy_at"),
        )

        # C053: bounded retry with backoff and jitter.
        p = Path("dub", _jitter_seed=42)
        _expect_partitioned(p, lambda s: False, now=0)
        first_retry = p.retry_at
        calls: list[str] = []
        _expect_partitioned(p, lambda s: calls.append(s) or True, now=0)
        _verify(not calls, "a retry ran before its backoff elapsed")
        _verify(first_retry is not None and first_retry > 0, "no retry delay was scheduled")
        for i in range(1, 13):
            _expect_partitioned(p, lambda s: False, now=i * BACKOFF_CEILING)
        _verify(p.backoff() == BACKOFF_CEILING, f"backoff escaped its ceiling: {p.backoff()}")
        findings[2] = self.satisfied(
            items[2],
            f"Retry uses exponential backoff with per-path jitter, blocks attempts inside retry windows, and is capped at {BACKOFF_CEILING}s.",
            *self._evidence("path.py::Path.backoff"), *self._evidence("path.py::Path.retry_delay"),
        )

        # C055/C056: cost-ordered failover and degraded relay operation.
        fallback = Path("fra", _jitter_seed=7)
        result = fallback.connect(lambda s: s == "relay", now=0)
        _verify(result["tried"] == list(STRATEGIES), "relay was reached before cheaper strategies")
        findings[4] = self.satisfied(
            items[4],
            "Failover is deterministic and cost-ordered: relay is attempted only after direct and hole-punch paths fail.",
            *self._evidence("path.py::Path.connect"),
        )
        findings[5] = self.satisfied(
            items[5],
            "When direct traversal is unavailable, the component can degrade to relay operation rather than falsely claiming the link is healthy on a failed direct path.",
            *self._evidence("path.py::Path.connect"),
        )
        return findings


COMPONENT = WanResilienceAndNatTraversalComponent
