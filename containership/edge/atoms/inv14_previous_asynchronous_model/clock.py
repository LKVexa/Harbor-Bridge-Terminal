"""Clock / tick authority for INV-14 (component P1-16, C011-C013, C022, C031).

Normative (see schemas/pk_clock_config.schema.json):
  CLK-1 MUST: one tick is ``tick_nanoseconds`` of the host *monotonic* clock; the
        wall clock is never consulted for deadlines.
  CLK-2 MUST: the WASI mapping is ``wasi:clocks/monotonic-clock@0.2.0`` nanoseconds,
        so ``subscribe-duration(timeout_ticks * tick_nanoseconds)``.
  CLK-3 MUST: tick_nanoseconds is an integer in [1_000, 1_000_000_000]; the product
        with max_timeout_ticks MUST NOT exceed the 60 s hard ceiling.
  CLK-4 MUST NOT: floats in the declarative config (avoids cross-platform rounding).
  CLK-5 SHOULD: the Python default (1 ms/tick) is the declared default authority.
"""
from __future__ import annotations

try:
    from .errors import Inv14Error
    from .polling import MAX_POLL_DURATION_SECONDS
except ImportError:
    from errors import Inv14Error
    from polling import MAX_POLL_DURATION_SECONDS

CLOCK_SCHEMA = "PK_CLOCK_CONFIG/1"
DEFAULT_TICK_NS = 1_000_000
MIN_TICK_NS = 1_000
MAX_TICK_NS = 1_000_000_000
WASI_CLOCK = "wasi:clocks/monotonic-clock@0.2.0"
HARD_CEILING_NS = int(MAX_POLL_DURATION_SECONDS * 1_000_000_000)


class ClockConfigError(Inv14Error):
    default_code = "PK_CLOCK_INVALID_CONFIG"


def validate_clock_config(cfg: object) -> dict:
    if not isinstance(cfg, dict):
        raise ClockConfigError("clock config must be an object")
    if cfg.get("schema") != CLOCK_SCHEMA:
        raise ClockConfigError("wrong clock schema", code="PK_CLOCK_SCHEMA_MISMATCH",
                               details={"schema": cfg.get("schema")})
    allowed = {"schema", "tick_nanoseconds", "max_timeout_ticks", "clock_source"}
    extra = set(cfg) - allowed
    if extra:
        raise ClockConfigError("unknown clock config keys", details={"keys": sorted(extra)})
    tick = cfg.get("tick_nanoseconds")
    mx = cfg.get("max_timeout_ticks")
    for label, v in (("tick_nanoseconds", tick), ("max_timeout_ticks", mx)):
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            raise ClockConfigError(f"{label} must be a positive integer", details={label: repr(v)})
    if not MIN_TICK_NS <= tick <= MAX_TICK_NS:
        raise ClockConfigError("tick_nanoseconds out of range", code="PK_CLOCK_TICK_RANGE",
                               details={"tick_nanoseconds": tick})
    if tick * mx > HARD_CEILING_NS:
        raise ClockConfigError("tick * max_timeout_ticks exceeds the 60 s hard ceiling",
                               code="PK_CLOCK_CEILING", details={"product_ns": tick * mx})
    if cfg.get("clock_source", "monotonic") != "monotonic":
        raise ClockConfigError("only the monotonic clock may drive deadlines", code="PK_CLOCK_SOURCE")
    return {"schema": CLOCK_SCHEMA, "tick_nanoseconds": tick, "max_timeout_ticks": mx,
            "clock_source": "monotonic"}


def ticks_to_ns(ticks: int, cfg: dict) -> int:
    """Exact integer mapping used for the WASI subscribe-duration argument."""
    c = validate_clock_config(cfg)
    if not isinstance(ticks, int) or isinstance(ticks, bool) or ticks <= 0 or ticks > c["max_timeout_ticks"]:
        raise ClockConfigError("ticks out of range", code="PK_CLOCK_TICKS_RANGE", details={"ticks": repr(ticks)})
    return ticks * c["tick_nanoseconds"]


def pollset_kwargs(cfg: dict) -> dict:
    c = validate_clock_config(cfg)
    return {"tick_seconds": c["tick_nanoseconds"] / 1_000_000_000, "max_timeout_ticks": c["max_timeout_ticks"]}


DEFAULT_CLOCK_CONFIG = {"schema": CLOCK_SCHEMA, "tick_nanoseconds": DEFAULT_TICK_NS,
                        "max_timeout_ticks": 60_000, "clock_source": "monotonic"}
