"""HTTP probe semantics (M16): /livez -> 200 iff live, /readyz -> 200 iff ready."""


def probe_status(report: dict, kind: str) -> int:
    return 200 if report["live" if kind == "live" else "ready"] else 503
