"""Rollout-window and maintenance-policy engine (component 18).

Forward progress (new waves, deferred retries) is allowed only inside a site's
maintenance window, outside blackouts and change freezes.  Rollback and
quarantine are *always* allowed — a window can delay an update, never a
recovery.  Sites use fixed UTC offsets so evaluation needs no tz database;
DST-observing sites publish their offset through signed configuration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .errors import PolicyDenied


@dataclass(frozen=True)
class Window:
    weekdays: frozenset[int]   # 0=Mon .. 6=Sun, local time
    start_min: int             # minutes after local midnight
    end_min: int               # exclusive; may be < start for windows crossing midnight

    def contains(self, local: datetime) -> bool:
        m = local.hour * 60 + local.minute
        if self.start_min <= self.end_min:
            return local.weekday() in self.weekdays and self.start_min <= m < self.end_min
        # crosses midnight: the part after midnight belongs to the previous day's window
        if m >= self.start_min:
            return local.weekday() in self.weekdays
        prev = (local.weekday() - 1) % 7
        return m < self.end_min and prev in self.weekdays


@dataclass
class MaintenancePolicy:
    site_offsets_min: dict[str, int] = field(default_factory=dict)
    site_windows: dict[str, list[Window]] = field(default_factory=dict)
    default_windows: list[Window] = field(default_factory=list)   # empty => always open
    blackouts: list[tuple[float, float, str]] = field(default_factory=list)  # (start, end, reason) epoch UTC
    change_freeze: tuple[float, float, str] | None = None

    def check(self, site: str, now: float, *, recovery: bool = False) -> None:
        if recovery:
            return
        if self.change_freeze and self.change_freeze[0] <= now < self.change_freeze[1]:
            raise PolicyDenied(f"change freeze: {self.change_freeze[2]}", resource=site)
        for s, e, why in self.blackouts:
            if s <= now < e:
                raise PolicyDenied(f"blackout: {why}", resource=site)
        windows = self.site_windows.get(site, self.default_windows)
        if not windows:
            return
        offset = self.site_offsets_min.get(site)
        if offset is None:
            raise PolicyDenied(f"site {site} has windows but no configured UTC offset", resource=site)
        local = datetime.fromtimestamp(now, tz=timezone(timedelta(minutes=offset)))
        if not any(w.contains(local) for w in windows):
            raise PolicyDenied(f"outside maintenance window for site {site} (local {local:%a %H:%M})", resource=site)
