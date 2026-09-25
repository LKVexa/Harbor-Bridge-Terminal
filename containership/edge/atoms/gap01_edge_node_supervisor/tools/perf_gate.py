"""Performance regression gate (70): fail the release when benchmarks exceed
the thresholds approved in docs/CAPACITY.md."""
import json
import sys

THRESHOLDS = {  # (section, key, field): max
    ("no_fsync", "admit", "p99_ms"): 10.0,
    ("fsync", "admit", "p99_ms"): 25.0,
    ("no_fsync", "status", "p99_ms"): 5.0,
    ("no_fsync", "drain", "per_workload_ms"): 1.0,
    ("no_fsync", "restart_recovery_s", None): 1.0,
    ("no_fsync", "metrics_render_ms", None): 20.0,
}


def main(path: str) -> int:
    d = json.load(open(path))
    bad = []
    for (sec, key, fld), mx in THRESHOLDS.items():
        v = d[sec][key] if fld is None else d[sec][key][fld]
        status = "PASS" if v <= mx else "FAIL"
        print(f"{status} {sec}.{key}{'.' + fld if fld else ''} = {v} (max {mx})")
        if v > mx:
            bad.append(key)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
