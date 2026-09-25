"""Adjacent-layer integration harness (MC-10; C030, C083).

    python -m inv64_application_model.tools.integration [--profile emulated|real] [--out evidence/INTEGRATION.json]

``emulated`` drives the full INV-64 service (authn -> authz -> validate ->
canonical) and then the adjacent handoff against the deterministic emulators
in :mod:`adjacent`, for every scenario in SCENARIOS. ``real`` needs the actual
INV-10/63/65/66 implementations; they are not in this archive, so the real
profile writes a FAIL record that says so (never a skip that could read as green).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from inv64_application_model.adjacent import CONTRACTS, Faults, default_adjacent
from inv64_application_model.audit import AuditLog
from inv64_application_model.auth import Authenticator, TrustConfig, mint
from inv64_application_model.authz import Authorizer
from inv64_application_model.errors import Inv64Error
from inv64_application_model.semantics import Deadline
from inv64_application_model.service import ApplicationModelService

K = b"i" * 32
OK = {"schema": "app/v1", "components": [{"name": "api", "type": "web"}, {"name": "w", "type": "worker"}],
      "providers": [{"name": "kv"}], "links": [{"from": "api", "to": "kv"}], "traits": [{"type": "spread", "component": "api"}]}
SCENARIOS = [
    # id, adjacent layer, manifest mutation, faults, expected code (None = success)
    ("happy-path", "all", {}, {}, None),
    ("inv10-unresolved-type", "INV-10", {"components": [{"name": "api", "type": "gpu-magic"}]}, {}, "manifest.invalid"),
    ("inv10-unavailable", "INV-10", {}, {"inv10": Faults(unavailable=True)}, "admission.overloaded"),
    ("inv10-version-too-new", "INV-10", {}, {"inv10": Faults(version=9)}, "version.unsupported"),
    ("inv66-guardrail-deny", "INV-66", {"traits": [{"type": "privileged", "component": "api"}]}, {}, "authz.denied"),
    ("inv66-malformed", "INV-66", {}, {"inv66": Faults(malformed=True)}, "internal"),
    ("inv65-provider-not-granted", "INV-65", {"providers": [{"name": "kv"}, {"name": "gpu"}]}, {}, "authz.denied"),
    ("inv65-slow-past-deadline", "INV-65", {}, {"inv65": Faults(latency_s=3.0)}, "deadline.exceeded"),
    ("inv63-unavailable-no-partial", "INV-63", {}, {"inv63": Faults(unavailable=True)}, "admission.overloaded"),
    ("inv63-malformed-no-partial", "INV-63", {}, {"inv63": Faults(malformed=True)}, "internal"),
    ("inv63-min-version", "INV-63", {}, {"inv63": Faults(version=1)}, None),
    ("inv10-min-version", "INV-10", {}, {"inv10": Faults(version=1)}, None),
]


class Clock:
    def __init__(self):
        self.t = time.time()

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def run_emulated() -> dict:
    out = []
    with tempfile.TemporaryDirectory() as d:
        for sid, layer, mut, faults, want in SCENARIOS:
            clk = Clock()
            trust = TrustConfig("t", "inv64", {"iss": {"k": ("HS256", K)}})
            pol = {"format": "PK_APP_AUTHZ_POLICY/1", "version": "p", "grants": [{"id": "g", "roles": ["dev"],
                   "capabilities": ["app.submit"], "tenants": ["acme"], "environments": ["prod"], "sites": ["*"], "resources": ["apps/*"]}]}
            svc = ApplicationModelService(authenticator=Authenticator(lambda: trust, clock=clk), authorizer=Authorizer(pol),
                                          audit=AuditLog(Path(d) / f"{sid}.jsonl"), clock=clk)
            m = dict(OK, **mut)
            tok = mint({"iss": "iss", "sub": "ci", "aud": "inv64", "tid": "acme", "kind": "workload", "roles": ["dev"],
                        "iat": clk(), "exp": clk() + 600, "jti": sid}, kid="k", key=K)
            tp_in = "00-" + "ab" * 16 + "-" + "cd" * 8 + "-01"
            resp = svc.handle({"format": "PK_APP_SUBMIT_REQUEST/1", "version": "PK_APP_SUBMIT/2", "operation": "submit",
                               "tenant": "acme", "environment": "prod", "site": "s1", "app": "shop",
                               "manifest_json": json.dumps(m), "idempotency_key": f"idem-{sid}-xxxxxxxx"},
                              token=tok, traceparent=tp_in)
            adj = default_adjacent(**faults)
            for emu in (adj.inv10, adj.inv63, adj.inv65, adj.inv66):
                emu.sleep = clk.sleep
            code = resp["error"]["code"] if resp["error"] else None
            trace_ok = resp["traceparent"].split("-")[1] == "ab" * 16
            if code is None:
                try:
                    dl = Deadline.for_operation("activate", 2_000, clock=clk)
                    adj.handoff(m, tenant="acme", correlation_id=resp["correlation_id"], traceparent=resp["traceparent"], deadline=dl)
                except Inv64Error as e:
                    code = e.code
            ctx_ok = all((c.get("ctx") or {}).get("tenant", "acme") == "acme" for emu in (adj.inv10, adj.inv65, adj.inv66) for c in emu.calls)
            partial = bool(adj.inv65.bound.get("acme")) and not adj.inv63.deployed
            ok = code == want and trace_ok and ctx_ok and not partial
            out.append({"id": sid, "layer": layer, "expected": want, "observed": code, "trace_propagated": trace_ok,
                        "tenant_context_preserved": ctx_ok, "partial_activation": partial, "pass": ok})
    return {"schema": "PK_APP_INTEGRATION/1", "profile": "emulated", "contracts": CONTRACTS,
            "adjacent_versions": {k: f"emulator (contract {v['contract']} v{v['supported'][0]}..v{v['supported'][1]})" for k, v in CONTRACTS.items()},
            "scenarios": out, "result": "PASS" if all(s["pass"] for s in out) else "FAIL"}


def run_real() -> dict:
    return {"schema": "PK_APP_INTEGRATION/1", "profile": "real", "result": "FAIL",
            "reason": "BLOCKED_EXTERNAL: the real INV-10/INV-63/INV-65/INV-66 implementations are not part of this archive; "
                      "certification against them cannot be run from the repository bootstrap path.", "scenarios": []}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="emulated", choices=["emulated", "real"])
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = run_emulated() if a.profile == "emulated" else run_real()
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    for s in res["scenarios"]:
        print(("PASS " if s["pass"] else "FAIL ") + s["id"], s["observed"])
    print(res["result"], res.get("reason", ""))
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
