"""The PA21 side of the bridge: read the delivery's ledger and gate on it.

An application that says it runs "on PA21.31" is making a claim about the
capability ledger beside it. This module makes that claim checkable: it finds
the delivery root, reads the newest capability ledger in a package, and answers
whether the specific ledger items an application declares are OPERATIONAL.

Nothing here promotes, edits or re-scores anything. It reads what the delivery
says about itself, and it reports the delivery's own status vocabulary
unchanged -- including the statuses that are not OPERATIONAL, which are the
interesting ones for an application deciding whether to run.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
from typing import Dict, List, Optional, Sequence, Tuple

LEDGER_GLOB = "*CAPABILITY_LEDGER.json"
PACKAGE_MARKERS = ("pamath", "reference")


def is_package(path: str) -> bool:
    return all(os.path.isdir(os.path.join(path, m)) for m in PACKAGE_MARKERS)


def find_packages(root: str) -> List[str]:
    """Every PA21 language package directly under `root` (and `root` itself)."""
    out = []
    if is_package(root):
        out.append(root)
    try:
        for name in sorted(os.listdir(root)):
            p = os.path.join(root, name)
            if os.path.isdir(p) and is_package(p):
                out.append(p)
    except OSError:
        pass
    return out


def _ledger_sort_key(path: str) -> Tuple[int, ...]:
    """Order ledgers by their round number, so 'newest' is not alphabetical.

    PA21.31 sorts before PA21.7 as text, which would silently pick a
    superseded ledger. The round is parsed instead.
    """
    base = os.path.basename(path)
    digits = ""
    for ch in base:
        if ch.isdigit() or ch == ".":
            digits += ch
        elif digits:
            break
    parts = [int(x) for x in digits.split(".") if x.isdigit()]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def find_ledger(package: str) -> Optional[str]:
    """The current capability ledger of a package: the highest round present."""
    reports = os.path.join(package, "reports")
    cands = sorted(glob.glob(os.path.join(reports, LEDGER_GLOB)),
                   key=_ledger_sort_key)
    return cands[-1] if cands else None


class Ledger:
    """A capability ledger, read as the delivery wrote it."""

    def __init__(self, path: str):
        self.path = path
        with open(path, encoding="utf-8") as fh:
            self.data = json.load(fh)
        self.items: Dict[int, dict] = {int(i["id"]): i
                                       for i in self.data.get("items", [])}

    # -- identity -------------------------------------------------------
    @property
    def round(self) -> str:
        pr = self.data.get("promotion_round") or {}
        return str(pr.get("round") or os.path.basename(self.path))

    @property
    def truth_rule(self) -> str:
        return str(self.data.get("truth_rule", ""))

    @property
    def distribution(self) -> Dict[str, int]:
        d = self.data.get("distribution")
        if isinstance(d, dict):
            return {str(k): int(v) for k, v in d.items()}
        counts: Dict[str, int] = {}
        for it in self.items.values():
            counts[it.get("status", "UNKNOWN")] = counts.get(
                it.get("status", "UNKNOWN"), 0) + 1
        return counts

    @property
    def sha256(self) -> str:
        h = hashlib.sha256()
        with open(self.path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    # -- queries --------------------------------------------------------
    def status(self, item_id: int) -> Optional[str]:
        it = self.items.get(int(item_id))
        return it.get("status") if it else None

    def describe(self, item_id: int) -> Dict[str, object]:
        it = self.items.get(int(item_id))
        if not it:
            return {"id": int(item_id), "present": False,
                    "status": None, "reason": "no such item in this ledger"}
        return {"id": int(item_id), "present": True,
                "status": it.get("status"),
                "upgrade": it.get("upgrade"),
                "evidence": it.get("evidence"),
                "test": it.get("test"),
                "priority": it.get("priority"),
                "domain": it.get("domain"),
                "ceiling": (it.get("ceiling") or {}).get("reason", "")}

    def require(self, item_ids: Sequence[int]) -> Dict[str, object]:
        """Are all of these OPERATIONAL? With the ones that are not, named.

        This is the gate an application declares. It fails closed: an item the
        ledger does not contain is a failure, not a pass, because an
        application cannot depend on a capability the delivery has never heard
        of.
        """
        details = [self.describe(i) for i in item_ids]
        blocking = [d for d in details if d["status"] != "OPERATIONAL"]
        return {"satisfied": not blocking,
                "required": [int(i) for i in item_ids],
                "blocking": blocking,
                "details": details,
                "ledger": os.path.basename(self.path),
                "round": self.round}

    def integrity(self) -> Dict[str, object]:
        integ = self.data.get("integrity") or {}
        return {
            "operational_without_evidence":
                integ.get("operational_without_evidence", []),
            "operational_without_test":
                integ.get("operational_without_test", []),
            "note": integ.get("check", ""),
        }


def survey(root: str) -> Dict[str, object]:
    """Everything the studio needs to know about a PA21 delivery root."""
    packages = find_packages(root)
    if not packages:
        return {"root": root, "found": False,
                "reason": "no PA21 package (a directory holding both pamath/ "
                          "and reference/) was found here",
                "packages": []}
    entries = []
    ledger_obj = None
    for p in packages:
        lp = find_ledger(p)
        entry = {"package": os.path.basename(p), "path": p, "ledger": None}
        if lp:
            try:
                led = Ledger(lp)
                entry["ledger"] = os.path.basename(lp)
                entry["round"] = led.round
                entry["distribution"] = led.distribution
                if ledger_obj is None:
                    ledger_obj = led
            except (OSError, ValueError) as e:
                entry["error"] = f"ledger unreadable: {e}"
        entries.append(entry)
    out = {"root": root, "found": True, "packages": entries,
           "package_count": len(packages)}
    if ledger_obj is not None:
        out.update({
            "round": ledger_obj.round,
            "ledger_path": ledger_obj.path,
            "ledger_sha256": ledger_obj.sha256,
            "distribution": ledger_obj.distribution,
            "operational": ledger_obj.distribution.get("OPERATIONAL", 0),
            "items": len(ledger_obj.items),
            "truth_rule": ledger_obj.truth_rule,
            "integrity": ledger_obj.integrity(),
        })
    return out


def verify_seal(package: str, limit: int = 0) -> Dict[str, object]:
    """Re-derive SHA256SUMS.txt for a package: the delivery's own G0 check."""
    sums = os.path.join(package, "SHA256SUMS.txt")
    if not os.path.isfile(sums):
        return {"package": os.path.basename(package), "sealed": False,
                "reason": "no SHA256SUMS.txt in this package"}
    listed, mismatched, missing = 0, [], []
    with open(sums, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            try:
                digest, rel = line.split("  ", 1)
            except ValueError:
                continue
            listed += 1
            if limit and listed > limit:
                break
            full = os.path.join(package, rel)
            if not os.path.isfile(full):
                missing.append(rel)
                continue
            h = hashlib.sha256()
            with open(full, "rb") as f2:
                for chunk in iter(lambda: f2.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != digest:
                mismatched.append(rel)
    return {"package": os.path.basename(package),
            "sealed": not mismatched and not missing,
            "files_listed": listed,
            "mismatched": mismatched[:10],
            "missing": missing[:10],
            "sampled": bool(limit),
            "reason": "" if not (mismatched or missing) else
                      f"{len(mismatched)} digest mismatch(es), "
                      f"{len(missing)} listed file(s) absent"}
