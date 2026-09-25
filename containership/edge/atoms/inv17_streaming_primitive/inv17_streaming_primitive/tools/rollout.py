"""C092: canary / staged rollout controller with automatic rollback (in-process simulation).

Stages from operations/rollout.md: 1 canary instance -> 10% -> 50% -> 100%. Each instance is
a StreamRegistry running a synthetic workload; after each stage the controller checks health
and error budgets and rolls every upgraded instance back to the previous ConfigManager
revision on failure. ``--fail-at STAGE`` injects a bad candidate to exercise rollback.
Writes evidence/rollout-<outcome>.json."""
import argparse, json
from _tools_pkg import ROOT, mod

C = mod("control"); K = mod("configuration"); S = mod("stream")
STAGES = [("canary", 1), ("10%", 0.10), ("50%", 0.50), ("100%", 1.0)]


def registry_for(cfg):
    o = cfg["overload"]
    r = C.StreamRegistry(global_buffer_budget=o["global_buffer_budget"])
    r.breaker.threshold, r.breaker.cooldown = o["breaker_threshold"], o["breaker_cooldown_s"]
    return r


def workload(cfg, bursts=25, burst=8):
    """Reader grants up to ``burst`` credit per round; writer sends ``burst`` elements; reader drains.
    Error rate = refused writes / attempted writes under the candidate configuration."""
    reg = registry_for(cfg)
    tok = reg.authority.issue("w", "t", "w", ["open", "write"])
    s = reg.open(int, tenant="t", workload="w", token=tok, stream_id="w", config=K.to_stream_config(cfg))
    errors = attempts = 0
    for _ in range(bursts):
        room = s.config.max_credit - s.credit
        if room:
            s.grant(min(burst, room))
        for i in range(burst):
            attempts += 1
            try:
                reg.write("w", i, tenant="t", workload="w", token=tok)
            except S.StreamError:
                errors += 1
        while s.read() is not S.NOT_READY:
            pass
    return errors / attempts, reg.health().status


def run(fleet=20, fail_at=None, candidate=None):
    candidate = candidate or {"stream": {"max_credit": 512, "max_buffer": 512}}
    insts = [{"id": f"i{i}", "cfg": K.ConfigManager()} for i in range(fleet)]
    log, upgraded = [], []
    for name, frac in STAGES:
        target = max(1, int(round(frac * fleet))) if name != "canary" else 1
        for inst in insts[len(upgraded):target]:
            cand = {"stream": {"max_credit": 1, "max_buffer": 1}, "overload": {"global_buffer_budget": 1, "breaker_threshold": 1, "breaker_cooldown_s": 60}} if name == fail_at else candidate
            inst["cfg"].activate(cand, author="rollout-controller", source_revision="candidate", reason=f"stage {name}")
            upgraded.append(inst)
        results = [workload(i["cfg"].current) for i in upgraded]
        worst = max(r for r, _ in results)
        healthy = worst <= 0.01 and all(h in ("healthy", "degraded") for _, h in results)
        log.append({"stage": name, "instances": len(upgraded), "worst_error_rate": round(worst, 4), "healthy": healthy})
        if not healthy:
            for i in upgraded:
                i["cfg"].rollback(author="rollout-controller", reason=f"stage {name} failed")
            log.append({"action": "rollback", "instances": len(upgraded),
                        "restored_digests": sorted({i["cfg"].provenance.digest for i in upgraded})})
            return {"outcome": "rolled_back", "stages": log}
    return {"outcome": "completed", "stages": log}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--fail-at"); a = ap.parse_args()
    res = run(fail_at=a.fail_at)
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / f"rollout-{res['outcome']}.json").write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res))
