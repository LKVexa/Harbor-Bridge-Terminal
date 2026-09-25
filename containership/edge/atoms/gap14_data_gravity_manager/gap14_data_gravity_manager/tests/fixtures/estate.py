"""Source-controlled estate fixtures: signed fake GAP-13/GAP-03/GAP-05/SCH-01/PLN-06.

Each fake produces artifacts in the *same* wire format the real services are
contracted to produce (schemas/), signed with fixture keys.  Faults are injected
by flipping attributes (``outage``, ``delay``, ``tamper``, ``stale_by`` ...).
These fixtures prove GAP-14's side of each contract; they are not evidence that
the live services conform (that needs the live estate-integration run).
"""
from __future__ import annotations

import io
import pathlib
import sys
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gap14_data_gravity_manager.audit import MemoryAuditSink  # noqa: E402
from gap14_data_gravity_manager.config import CONFIG_ISSUER, ConfigManager  # noqa: E402
from gap14_data_gravity_manager.errors import G14Error  # noqa: E402
from gap14_data_gravity_manager.identity import Authenticator  # noqa: E402
from gap14_data_gravity_manager.observability import StructuredLogger  # noqa: E402
from gap14_data_gravity_manager.service import REQUEST_SCHEMA, DecisionService  # noqa: E402
from gap14_data_gravity_manager.trust import FakeClock, Key, KeyRing, digest  # noqa: E402

ISSUERS = {"k-gap13": "gap13-policy", "k-gap03": "gap03-topology", "k-gap05": "gap05-replication",
           "k-sch01": "sch01-placement", "k-pln06": "pln06-dataplane", "k-id": "estate-identity",
           "k-cfg": CONFIG_ISSUER, "k-g14": "gap14-data-gravity", "k-audit": "gap14-audit"}


def keyring() -> KeyRing:
    return KeyRing(Key(kid, iss, (kid * 16).encode()[:32].ljust(32, b"#")) for kid, iss in ISSUERS.items())


class FakeService:
    def __init__(self, estate: "Estate", kid: str):
        self.estate, self.kid = estate, kid
        self.outage = False
        self.delay = 0.0
        self.tamper = False
        self.stale_by = 0.0
        self.version = 1
        self.calls = 0
        self.fail_times = 0          # fail the next N calls (then recover)

    def _gate(self, timeout: float) -> None:
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise G14Error("G14_DEPENDENCY_UNAVAILABLE", "injected transient failure")
        if self.outage:
            raise G14Error("G14_DEPENDENCY_UNAVAILABLE", "injected outage")
        if self.delay > timeout:
            self.estate.clock.advance(timeout)
            raise G14Error("G14_DEPENDENCY_TIMEOUT", "injected delay")
        self.estate.clock.advance(self.delay)

    def _sign(self, body: dict[str, Any]) -> dict[str, Any]:
        sig = self.estate.keys.sign(body, self.kid)
        if self.tamper:  # modify after signing: MAC must no longer verify
            body = {**body}
            if "issued_at" in body:
                body["issued_at"] -= 1
            else:
                body["status"] = str(body.get("status")) + "-forged"
        return {"body": body, "sig": sig}

    @property
    def issued_at(self) -> float:
        return self.estate.clock.now() - self.stale_by


class Policy(FakeService):
    def __init__(self, estate: "Estate"):
        super().__init__(estate, "k-gap13")
        self.residency = {"dub": {"public", "pii"}, "ams": {"public"}, "fra": {"public", "pii"}}
        self.obligations = {"dub": {"encryption_domain": "eu-kms"}}
        self.rebind = False

    def __call__(self, req: Mapping[str, Any], timeout: float) -> dict[str, Any]:
        self._gate(timeout)
        site = req["destination_site"]
        allow = req["classification"] in self.residency.get(site, set())
        h = digest(req) if not self.rebind else digest({**req, "dataset": "other"})
        return self._sign({"schema": "PK_POLICY_VERDICT/1", "decision_id": f"pv-{self.calls}", "request_hash": h,
                           "allow": allow, "policy_version": self.version,
                           "rule_ids": [f"R-{site}-{req['classification']}"],
                           "obligations": self.obligations.get(site, {}) if allow else {},
                           "issued_at": self.issued_at, "ttl_s": 300})


class Topology(FakeService):
    def __init__(self, estate: "Estate"):
        super().__init__(estate, "k-gap03")
        self.routes = {("dub", "ams"): 1.0, ("ams", "dub"): 1.0, ("dub", "fra"): 1.2, ("fra", "dub"): 1.2,
                       ("ams", "fra"): 0.8, ("fra", "ams"): 0.8}
        self.egress = {}
        self.unavailable: set[tuple[str, str]] = set()

    def __call__(self, req: Mapping[str, Any], timeout: float) -> dict[str, Any]:
        self._gate(timeout)
        routes = [{"from": a, "to": b, "available": (a, b) not in self.unavailable, "locality_multiplier": m,
                   "egress_per_gb": self.egress.get((a, b), 1.0), "bandwidth_gbps": 10.0, "congestion": 0.1}
                  for (a, b), m in sorted(self.routes.items())]
        return self._sign({"schema": "PK_TOPOLOGY_SNAPSHOT/1", "snapshot_id": f"topo-{self.version}",
                           "version": self.version, "issued_at": self.issued_at, "routes": routes})


class Replication(FakeService):
    def __init__(self, estate: "Estate"):
        super().__init__(estate, "k-gap05")
        self.unconverged: set[str] = set()
        self.wrong_dataset = False

    def __call__(self, req: Mapping[str, Any], timeout: float) -> dict[str, Any]:
        self._gate(timeout)
        ds = req["dataset"] if not self.wrong_dataset else "someone-else"
        conflicts = 3 if req["dataset"] in self.unconverged else 0
        return self._sign({"schema": "PK_CONVERGENCE_PROOF/1", "tenant_id": req["tenant_id"], "dataset": ds,
                           "dataset_version": self.version, "converged": conflicts == 0, "open_conflicts": conflicts,
                           "watermark": f"wm-{self.version}", "issued_at": self.issued_at})


class Placement(FakeService):
    def __init__(self, estate: "Estate"):
        super().__init__(estate, "k-sch01")
        base = {"available": True, "architectures": ["x86_64", "arm64"], "runtimes": ["python3.11"],
                "free_cpu": 64, "free_gpu": 0, "quota_remaining_gb": 10_000, "storage_free_gb": 50_000}
        self.sites = {"dub": dict(base), "ams": dict(base), "fra": {**base, "free_gpu": 8}}

    def __call__(self, req: Mapping[str, Any], timeout: float) -> dict[str, Any]:
        self._gate(timeout)
        return self._sign({"schema": "PK_PLACEMENT_SNAPSHOT/1", "snapshot_id": f"pl-{self.version}", "version": self.version,
                           "tenant_id": req["tenant_id"], "issued_at": self.issued_at,
                           "sites": {s: v for s, v in self.sites.items() if s in req["sites"]}})


class DataPlane(FakeService):
    def __init__(self, estate: "Estate"):
        super().__init__(estate, "k-pln06")
        self.received: list[dict[str, Any]] = []
        self.reject = False

    def __call__(self, signed: Mapping[str, Any], timeout: float) -> dict[str, Any]:
        self._gate(timeout)
        # PLN-06 verifies GAP-14's signature on the handoff (its side of the contract)
        self.estate.keys.verify(signed["body"], signed["sig"], expected_issuer="gap14-data-gravity", now=self.estate.clock.now())
        seen = any(r["handoff_id"] == signed["body"]["handoff_id"] for r in self.received)
        if not seen:
            self.received.append(dict(signed["body"]))
        return self._sign({"schema": "PK_DATA_MOVE_ACK/1", "handoff_id": signed["body"]["handoff_id"],
                           "accepted": not self.reject, "status": "queued" if not seen else "already-queued"})


class Estate:
    def __init__(self, *, mode: str = "production", config_extra: Mapping[str, Any] | None = None, audit_fail: bool = False):
        self.clock = FakeClock()
        self.keys = keyring()
        self.policy, self.topology = Policy(self), Topology(self)
        self.replication, self.placement, self.dataplane = Replication(self), Placement(self), DataPlane(self)
        self.config = ConfigManager(self.keys)
        body = {"schema": "PK_GAP14_CONFIG/1", "revision": 1, "mode": mode,
                "knobs": {"decision_deadline_s": 0.5, "dependency_timeout_s": 0.05},
                "site_jurisdictions": {"dub": ["IE", "EU"], "ams": ["NL", "EU"], "fra": ["DE", "EU"]}}
        body.update(config_extra or {})
        self.config.activate(self.signed_config(body), self.clock.now())
        self.audit = MemoryAuditSink(self.keys, "k-audit", fail=audit_fail)
        self.logs = io.StringIO()
        self.auth = Authenticator(self.keys)
        self.slept: list[float] = []
        self.service = DecisionService(
            keyring=self.keys, signing_kid="k-g14", config=self.config, audit=self.audit, authenticator=self.auth,
            transports={"GAP-13": self.policy, "GAP-03": self.topology, "GAP-05": self.replication,
                        "SCH-01": self.placement, "PLN-06": self.dataplane},
            clock=self.clock, logger=StructuredLogger(self.logs, clock=self.clock.now), sleep=self.slept.append)
        self._n = 0

    def signed_config(self, body: Mapping[str, Any]) -> dict[str, Any]:
        return {"body": dict(body), "sig": self.keys.sign(body, "k-cfg")}

    def token(self, tenants=("t-acme",), scopes=("gravity:recommend", "gravity:handoff", "gravity:explain", "gravity:simulate"),
              subject="svc-scheduler", ttl=900.0):
        return self.auth.mint(subject=subject, tenants=list(tenants), scopes=list(scopes), kid="k-id",
                              now=self.clock.now(), ttl_s=ttl, token_id=f"tok-{self.clock.now():.0f}")

    def request(self, *, name="lake", site="dub", size=500.0, cls="public", compute="ams", tenant="t-acme",
                dataset_tenant=None, profile=None, requirements=None) -> dict[str, Any]:
        self._n += 1
        r = {"schema": REQUEST_SCHEMA, "request_id": f"req-{self._n}",
             "workload": {"tenant_id": tenant, "workload_id": "wl-etl"},
             "dataset": {"name": name, "tenant_id": dataset_tenant or tenant, "site": site, "size_gb": size,
                         "classification": cls},
             "compute_site": compute}
        if profile is not None:
            r["profile"] = profile
        if requirements is not None:
            r["requirements"] = requirements
        return r

    def decide(self, **kw) -> dict[str, Any]:
        return self.service.decide(self.request(**kw), self.token())
