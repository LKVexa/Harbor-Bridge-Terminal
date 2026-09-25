"""MC-035 - Compatibility matrix and startup guard (GAP03-COMPAT/1)."""
from __future__ import annotations

import platform
import sys

from .errors import SchedulerError

MATRIX = {
    "python": {"supported": ["3.10", "3.11", "3.12", "3.13"], "implementations": ["CPython"], "eol": {"3.10": "2026-10-31"}},
    "os": {"supported": ["Linux", "Darwin", "Windows"]},
    "arch": {"supported": ["x86_64", "AMD64", "aarch64", "arm64"]},
    "schemas": {"PK_TOPOLOGY": ["1.0", "1.1"], "PK_LOCALITY_COST": ["1.0"], "PK_FAIR_SHARE": ["1.0"]},
    "adjacent": {"SCH-01": {"min": "1.0", "max": "1.1", "deprecated": {"1.0": "2027-03-31"}},
                 "GAP-02": {"min": "1.0", "max": "1.0", "deprecated": {}},
                 "GAP-14": {"min": "1.0", "max": "1.0", "deprecated": {}}, "PLN-05": {"min": "1.0", "max": "1.0", "deprecated": {}}},
    "schema_deprecation": {"PK_TOPOLOGY/1.0": "2027-03-31"},
    "dependencies": {"runtime": [], "note": "stdlib only; no third-party runtime dependency to pin"},
    "unsupported": [{"python": "<3.10", "reason": "PEP 604 unions / dataclass features"},
                    {"implementation": "PyPy", "reason": "not exercised in CI"}],
}
REQUIRED_CELLS = [(py, os_) for py in ("3.10", "3.11", "3.12", "3.13") for os_ in ("Linux", "Windows", "Darwin")]


def current() -> dict:
    return {"python": f"{sys.version_info.major}.{sys.version_info.minor}", "implementation": platform.python_implementation(),
            "os": platform.system(), "arch": platform.machine(), "byteorder": sys.byteorder,
            "maxsize_bits": sys.maxsize.bit_length() + 1}


def check(env: dict | None = None, *, allow_unverified: bool = False) -> dict:
    env = env or current()
    problems = []
    if env["python"] not in MATRIX["python"]["supported"]:
        problems.append(f"python {env['python']} unsupported")
    if env["implementation"] not in MATRIX["python"]["implementations"]:
        problems.append(f"implementation {env['implementation']} unsupported")
    if env["os"] not in MATRIX["os"]["supported"]:
        problems.append(f"os {env['os']} unsupported")
    if env["arch"] not in MATRIX["arch"]["supported"]:
        problems.append(f"arch {env['arch']} unsupported")
    if env.get("maxsize_bits", 64) < 64:
        problems.append("32-bit interpreters unsupported (integer bounds assume 64-bit)")
    if problems and not allow_unverified:
        raise SchedulerError("UNSUPPORTED_VERSION", "; ".join(problems))
    return {"env": env, "problems": problems, "supported": not problems}


def eol_block(env: dict | None = None, *, today=None, waiver_ok: bool = False) -> dict:
    """Refuse new deployments on an EOL runtime unless an approved, time-bounded waiver exists (MC-044-CHK-013)."""
    import datetime as dt
    env = env or current()
    today = today or dt.date.today()
    eol = MATRIX["python"]["eol"].get(env["python"])
    if eol and dt.date.fromisoformat(eol) <= today and not waiver_ok:
        raise SchedulerError("UNSUPPORTED_VERSION", f"python {env['python']} reached EOL {eol}")
    days = (dt.date.fromisoformat(eol) - today).days if eol else None
    return {"eol": eol, "days_to_eol": days, "notice": days is not None and days <= 90}
