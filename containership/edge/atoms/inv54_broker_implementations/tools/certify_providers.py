"""Run the shared conformance suite against REAL providers (components 13-15, 83, 90).

Requires environment: INV54_KAFKA_BOOTSTRAP, INV54_RABBITMQ_URL, INV54_SQS_REGION (+ AWS creds via
the standard chain).  A provider without its variable or client library is reported SKIPPED,
never PASS.  Output: evidence/provider_certification.json
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
from importlib import import_module  # noqa: E402

conf = import_module(f"{PKG.name}.adapters.conformance")
errors = import_module(f"{PKG.name}.errors")


def attempt(name, env, build):
    if not os.environ.get(env):
        return {"status": "SKIPPED", "reason": f"{env} not set (no provisioned {name} environment)"}
    try:
        a = build(os.environ[env])
    except errors.BrokerError as e:
        return {"status": "SKIPPED", "reason": e.message, "code": e.code.code}
    res = conf.run_conformance(a)
    a.close()
    ok = all(v in ("PASS", "NOT_APPLICABLE") for v in res.values())
    return {"status": "PASS" if ok else "FAIL", "checks": res}


def main() -> int:
    k = import_module(f"{PKG.name}.adapters.kafka")
    r = import_module(f"{PKG.name}.adapters.rabbitmq")
    s = import_module(f"{PKG.name}.adapters.sqs")
    out = {"schema": "inv54.provider_certification/1", "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "providers": {
               "kafka": attempt("kafka", "INV54_KAFKA_BOOTSTRAP",
                                lambda v: k.KafkaAdapter(k.build_config(v.split(",")))),
               "rabbitmq": attempt("rabbitmq", "INV54_RABBITMQ_URL", lambda v: r.RabbitMQAdapter(v)),
               "sqs": attempt("sqs", "INV54_SQS_REGION", lambda v: s.SQSAdapter(region=v))}}
    (PKG / "evidence" / "provider_certification.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 1 if any(p["status"] == "FAIL" for p in out["providers"].values()) else 0


if __name__ == "__main__":
    sys.exit(main())
