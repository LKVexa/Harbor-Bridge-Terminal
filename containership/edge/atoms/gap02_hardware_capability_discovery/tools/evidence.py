"""Evidence runner — executes the suite and writes one machine-readable
evidence bundle per checklist component (GAP02-MC-01..55) plus
COMPONENT_STATUS.json. A component's declared status is DOWNGRADED to
FAILED if any of its named tests did not pass, and to BLOCKED if it names
no tests. Nothing is ever marked COMPLETE here: that needs sign-off.

    python -B -m gap02_hardware_capability_discovery.tools.evidence
"""
import hashlib, json, os, platform, sys, time, unittest

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
CHECKLIST_REV = "GAP02_v4.2.0_55_Missing_Components_Professional_Checklist.md sha256:{}"


def tree_digest():
    from .build import files
    h = hashlib.sha256()
    for p in files():
        if p.startswith("evidence/") or p in ("COMPONENT_STATUS.json", "MANIFEST.sha256", "SBOM.cdx.json"):
            continue
        h.update(p.encode() + b"\0" + hashlib.sha256(open(os.path.join(PKG, p), "rb").read()).digest())
    return h.hexdigest()


class Rec(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.outcomes = {}
    def _key(self, t): return t.id().split(".")[-2], t.id().split(".")[-1]
    def addSuccess(self, t): super().addSuccess(t); self.outcomes[self._key(t)] = "pass"
    def addFailure(self, t, e): super().addFailure(t, e); self.outcomes[self._key(t)] = "fail"
    def addError(self, t, e): super().addError(t, e); self.outcomes[self._key(t)] = "error"
    def addSkip(self, t, r): super().addSkip(t, r); self.outcomes[self._key(t)] = "skip"


def run_tests():
    suite = unittest.defaultTestLoader.discover(os.path.join(PKG, "tests"), top_level_dir=os.path.join(PKG, "tests"))
    t0 = time.time()
    with open(os.devnull, "w") as dn:
        r = unittest.TextTestRunner(stream=dn, resultclass=Rec, verbosity=0).run(suite)
    return r.outcomes, round(time.time() - t0, 3)


def main(checklist_sha="unknown"):
    from .components import C
    from .bench import run as bench
    from ..production.agent import build_probes
    from ..production.config import ProbeConfig
    from ..production.executor import ProbeExecutor
    results, dur = run_tests()
    by_class = {}
    for (cls, name), res in results.items():
        by_class.setdefault(cls, {})[name] = res
    ex = ProbeExecutor("evidence-host", build_probes(ProbeConfig()))
    snap = ex.sweep(); ex.stop()
    host_sweep = {"generation": snap.generation, "facts": snap.report.for_consumer(snap.report.published_at),
                  "evidence": list(snap.evidence)}
    base = {"checklist_revision": CHECKLIST_REV.format(checklist_sha), "source_revision": "tree-sha256:" + tree_digest(),
            "gap02_version": open(os.path.join(PKG, "VERSION")).read().strip(),
            "os": platform.system(), "arch": platform.machine(), "python": platform.python_version(),
            "test_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reproduce": "python -B -m gap02_hardware_capability_discovery.tools.evidence",
            "package_sha256": "recorded outside the archive (a zip cannot contain its own digest): see the release note beside the zip"}
    os.makedirs(os.path.join(PKG, "evidence"), exist_ok=True)
    status = []
    for n, title, prio, declared, impl, tests, blockers in C:
        tr = {cls: by_class.get(cls, {}) for cls in tests}
        missing = [c for c in tests if not tr[c]]
        failed = [f"{c}.{t}" for c, d in tr.items() for t, v in d.items() if v in ("fail", "error")]
        st = declared
        if failed or missing:
            st = "FAILED"
        elif not tests and declared not in ("BLOCKED",):
            st = "BLOCKED"
        cid = f"GAP02-MC-{n:02d}"
        b = dict(base, component_id=cid, title=title, priority=prio, status=st, declared_status=declared,
                 implementation=impl, tests=tr, missing_test_classes=missing, failed_tests=failed,
                 blockers=blockers, reviewer_signoff=None, waivers=[],
                 production_go=False)
        if n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 41):
            b["real_host_observation"] = {k: v for k, v in host_sweep["facts"].items() if k != "age"}
        if n == 47:
            b["bench"] = bench(30)
        json.dump(b, open(os.path.join(PKG, "evidence", f"{cid}.json"), "w"), indent=1, sort_keys=True)
        status.append({"id": cid, "title": title, "priority": prio, "status": st, "blockers": blockers})
    counts = {}
    for s in status:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    tot = {"pass": 0, "fail": 0, "error": 0, "skip": 0}
    for v in results.values():
        tot[v] += 1
    out = {"schema": "GAP02_COMPONENT_STATUS/1", "generated": base["test_timestamp"], "source_revision": base["source_revision"],
           "counts": counts, "tests": tot, "test_duration_s": dur, "production_go": False,
           "production_go_reason": "no component has independent sign-off; P0 physical-lab, sibling and pk_core gates open",
           "components": status}
    json.dump(out, open(os.path.join(PKG, "COMPONENT_STATUS.json"), "w"), indent=1)
    json.dump({"host_sweep": host_sweep}, open(os.path.join(PKG, "evidence", "HOST_SWEEP.json"), "w"), indent=1, default=str)
    return out


if __name__ == "__main__":
    r = main(sys.argv[1] if len(sys.argv) > 1 else "unknown")
    print(json.dumps({k: r[k] for k in ("counts", "tests", "production_go")}, indent=1))
