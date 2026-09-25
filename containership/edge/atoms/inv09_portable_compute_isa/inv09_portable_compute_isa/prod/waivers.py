"""M51 - exception/waiver register.

A waiver is NOT a pass.  It is valid only with an approver, owner, exact item
scope, compensating control and an unexpired expiry date.  Items whose failure
could cause a false ACCEPT are never waivable (security rule).
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass

REQUIRED = {"id", "items", "scope", "owner", "approver", "compensating_control", "expires", "reason"}
NEVER_WAIVABLE_PREFIXES = ("M01-", "M02-", "M03-", "M08-", "M10-", "M11-")


@dataclass(frozen=True)
class Waiver:
    id: str
    items: tuple[str, ...]
    scope: str
    owner: str
    approver: str
    compensating_control: str
    expires: dt.date
    reason: str

    def valid_on(self, day: dt.date) -> bool:
        return day <= self.expires


def load(path: str) -> list[Waiver]:
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("schema") != "PK_WAIVER_REGISTER/1":
        raise ValueError("waiver register schema")
    out = []
    for w in doc["waivers"]:
        if set(w) != REQUIRED or not all(w[k] for k in REQUIRED):
            raise ValueError(f"waiver {w.get('id')}: all of {sorted(REQUIRED)} required and non-empty")
        bad = [i for i in w["items"] if i.startswith(NEVER_WAIVABLE_PREFIXES) and i.endswith(("-051", "-052"))]
        if bad:
            raise ValueError(f"waiver {w['id']}: false-ACCEPT definition-of-done items are not waivable: {bad}")
        if w["owner"] == w["approver"]:
            raise ValueError(f"waiver {w['id']}: owner cannot approve their own waiver")
        out.append(Waiver(w["id"], tuple(w["items"]), w["scope"], w["owner"], w["approver"],
                          w["compensating_control"], dt.date.fromisoformat(w["expires"]), w["reason"]))
    return out
