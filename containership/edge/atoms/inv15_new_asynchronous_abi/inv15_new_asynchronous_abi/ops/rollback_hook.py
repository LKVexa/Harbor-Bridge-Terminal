"""Canary gate / automated rollback hook (components 68, 69).

Usage: python ops/rollback_hook.py BASELINE.prom CANARY.prom
Exit 0 PROCEED, 2 ROLLBACK, 3 INCOMPLETE (a required metric is missing:
absence is never read as healthy). Thresholds are PROPOSED, not approved.
"""
import json
import re
import sys

REQUIRED = ("pk_async_calls_total",)
RULES = [  # (metric, max absolute canary value, max ratio vs baseline)
    ("pk_async_foreign_handle_total", 0, None),
    ("pk_async_late_completions_total", None, 2.0),
    ("pk_async_memory_refusals_total", None, 2.0),
    ("pk_async_refusals_total", None, 1.5),
]


def parse(text):
    out = {}
    for line in text.splitlines():
        m = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+(\S+)$", line.strip())
        if m:
            out[m.group(1)] = out.get(m.group(1), 0.0) + float(m.group(3))
    return out


def evaluate(base_text, canary_text):
    b, c = parse(base_text), parse(canary_text)
    missing = [m for m in REQUIRED if m not in c]
    if missing:
        return "INCOMPLETE", {"missing": missing}
    calls_b, calls_c = max(b.get("pk_async_calls_total", 0), 1), max(c.get("pk_async_calls_total", 0), 1)
    why = []
    for metric, cap, ratio in RULES:
        cv = c.get(metric, 0.0)
        if cap is not None and cv > cap:
            why.append(f"{metric}={cv} > {cap}")
        if ratio is not None:
            rb, rc = b.get(metric, 0.0) / calls_b, cv / calls_c
            if rc > max(rb * ratio, 1e-4):
                why.append(f"{metric} rate {rc:.4g} > {ratio}x baseline {rb:.4g}")
    return ("ROLLBACK", {"reasons": why}) if why else ("PROCEED", {})


def main(argv):
    verdict, info = evaluate(open(argv[1]).read(), open(argv[2]).read())
    print(json.dumps({"verdict": verdict, **info}))
    return {"PROCEED": 0, "ROLLBACK": 2, "INCOMPLETE": 3}[verdict]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
