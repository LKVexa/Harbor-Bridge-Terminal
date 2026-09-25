"""Shared test harness: a fake fleet built from fixture sysfs trees."""
from __future__ import annotations

import importlib
import pathlib
import sys
import tempfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PKG_DIR.parent))

NAME = PKG_DIR.name
pkg = importlib.import_module(NAME)
attestation = importlib.import_module(f"{NAME}.attestation")
authz = importlib.import_module(f"{NAME}.authz")
auditlog = importlib.import_module(f"{NAME}.auditlog")
collector = importlib.import_module(f"{NAME}.collector")
config = importlib.import_module(f"{NAME}.config")
negotiation = importlib.import_module(f"{NAME}.negotiation")
placement = importlib.import_module(f"{NAME}.placement")
policy = importlib.import_module(f"{NAME}.policy")
registry = importlib.import_module(f"{NAME}.registry")
resilience = importlib.import_module(f"{NAME}.resilience")
rollout = importlib.import_module(f"{NAME}.rollout")
service = importlib.import_module(f"{NAME}.service")
telemetry = importlib.import_module(f"{NAME}.telemetry")

SYSFS_FIXTURES = PKG_DIR / "tests" / "fixtures" / "sysfs"

FULL = {  # a fully mitigated modern x86 node (kernel strings as Linux prints them)
    "spectre_v1": "Mitigation: usercopy/swapgs barriers and __user pointer sanitization",
    "spectre_v2": "Mitigation: Enhanced / Automatic IBRS; IBPB: conditional; RSB filling; PBRSB-eIBRS: SW sequence; BHI: BHI_DIS_S",
    "l1tf": "Not affected",
    "mds": "Not affected",
    "mmio_stale_data": "Mitigation: Clear CPU buffers; SMT disabled",
    "spec_store_bypass": "Mitigation: Speculative Store Bypass disabled via prctl",
    "retbleed": "Mitigation: Enhanced IBRS",
    "gather_data_sampling": "Mitigation: Microcode",
    "reg_file_data_sampling": "Not affected",
    "itlb_multihit": "Not affected",
    "srbds": "Not affected",
    "tsx_async_abort": "Not affected",
}
COSTS = {"spectre_v1": 0.4, "spectre_v2": 3.1, "mmio_stale_data": 0.8, "spec_store_bypass": 1.2,
         "retbleed": 2.2, "gather_data_sampling": 0.6}


def make_sysfs(root: pathlib.Path, vulns: dict[str, str], smt: str = "off", core_sched: bool = False) -> pathlib.Path:
    vd = root / collector.SYSFS_VULN_DIR
    vd.mkdir(parents=True, exist_ok=True)
    for k, v in vulns.items():
        (vd / k).write_text(v + "\n", encoding="ascii")
    sd = root / "sys/devices/system/cpu/smt"
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "control").write_text(smt + "\n")
    if core_sched:
        (root / "etc/inv43").mkdir(parents=True, exist_ok=True)
        (root / "etc/inv43/core_scheduling").write_text("enforced\n")
    return root


class Clock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t
        self.m = 1000.0

    def time(self):
        return self.t

    def mono(self):
        return self.m

    def advance(self, s: float):
        self.t += s
        self.m += s


class Fleet:
    """Registry + keys + principals + temp sysfs roots."""

    def __init__(self, nodes=("node-a", "node-b"), vulns=None, smt="off", core_sched=False, audit_path=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.clock = Clock()
        self.keys = attestation.KeyRegistry()
        self.az = authz.Authorizer()
        self.pol = policy.Policy.load()
        self.audit = auditlog.AuditLog(audit_path, key=b"k" * 32, clock=self.clock.time)
        self.reg = registry.PostureRegistry(keys=self.keys, authz=self.az, policy=self.pol, audit=self.audit,
                                            clock=self.clock.time, mono=self.clock.mono,
                                            release_digest="test-release")
        self.creds = {}
        self.seq = {}
        self.epoch = {}
        self.roots = {}
        for n in nodes:
            root = make_sysfs(pathlib.Path(self.tmp.name) / n, dict(vulns or FULL), smt, core_sched)
            self.roots[n] = root
            kid, sec = self.keys.enrol(n)
            self.creds[n] = (kid, sec)
            self.az.grant(f"collector-{n}", {"collector"}, node_scope={n})
            self.seq[n] = 0
            self.epoch[n] = 1
        self.az.grant("sched", {"scheduler"})
        self.az.grant("ops", {"operator"})
        self.az.grant("obs", {"observer"})
        self.az.grant("auditor", {"auditor"})

    def envelope(self, node, costs=None, epoch=None, readback=None, seq=None, ttl=300.0):
        rb = readback or collector.collect(node, root=self.roots[node], ttl_s=ttl, clock=self.clock.time,
                                           mono=self.clock.mono)
        payload = {"node": node, "readback": rb.to_dict(include_monotonic=False),
                   "measured_costs": dict(COSTS if costs is None else costs),
                   "epoch": self.epoch[node] if epoch is None else epoch}
        if seq is None:
            self.seq[node] += 1
            seq = self.seq[node]
        kid, sec = self.creds[node]
        return attestation.seal(payload, node=node, key_id=kid, secret=sec, seq=seq, now=self.clock.time())

    def attest(self, node, **kw):
        return self.reg.submit(f"collector-{node}", self.envelope(node, **kw))

    def close(self):
        self.tmp.cleanup()


def W(tenant, trust="tenant-standard", wid=None, lineage=None):
    d = {"tenant": tenant, "trust_class": trust, "id": wid or f"w-{tenant}"}
    if lineage:
        d["cpu_lineage"] = lineage
    return d
