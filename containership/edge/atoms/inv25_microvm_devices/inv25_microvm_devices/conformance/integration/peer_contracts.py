"""Version-pinned CONTRACT FIXTURES for INV-25's adjacent layers (item 14, C030/C083).

These are NOT the real INV-24 / INV-35 / INV-26 / GAP-13 / INV-43 implementations
(all externally owned).  They encode the behaviour INV-25 requires of each peer so
that (a) INV-25's side of every boundary is exercised in CI, and (b) each peer team
can run the same scenarios against its real implementation by providing an object
with the same methods.  Evidence from these fixtures is recorded as
``contract-fixture`` and never as peer certification.
"""
from __future__ import annotations

FIXTURE_VERSIONS = {"INV-24": "fixture-1", "INV-35": "fixture-1", "INV-26": "fixture-1",
                    "GAP-13": "fixture-1", "INV-43": "fixture-1"}


class PeerError(Exception):
    def __init__(self, code: str, msg: str = "") -> None:
        super().__init__(msg or code)
        self.code = code


class PolicyEngine:          # GAP-13: may narrow, never expand
    def __init__(self, deny=(), available=True):
        self.deny, self.available = set(deny), available

    def decide(self, workload, env, requested, catalogue_digest, permitted):
        if not self.available:
            raise PeerError("INV25_DEPENDENCY_UNAVAILABLE", "policy engine unavailable")
        allowed = sorted(d for d in requested if d in permitted and d not in self.deny)
        return {"allowed": allowed, "denied": sorted(set(requested) - set(allowed)),
                "catalogue_digest": catalogue_digest, "reason": "policy-narrowing"}


class IoBackend:             # INV-35
    def __init__(self, backends=("virtio-net", "virtio-block")):
        self.backends = set(backends)

    def has_backend(self, device):
        return device in self.backends


class Runtime:               # INV-24
    def __init__(self, store, policy, io, transient=None):
        self.store, self.policy, self.io, self.transient = store, policy, io, transient

    def boot(self, workload, requested, correlation_id):
        snap = self.store.active
        permitted = {d["name"]: d for d in snap.document["devices"] if self.store.permits(d["name"])}
        for dev in requested:
            if dev not in permitted:
                raise PeerError("INV25_UNAUTHORIZED", f"{dev} not catalogued")
        decision = self.policy.decide(workload, self.store.environment, requested, snap.digest, set(permitted))
        if decision["denied"]:
            raise PeerError("INV25_UNAUTHORIZED", "policy denied " + ",".join(decision["denied"]))
        for dev in requested:
            if not self.io.has_backend(dev):
                raise PeerError("INV25_DEPENDENCY_UNAVAILABLE", f"no backend for {dev}")  # never substitute
        risk = self.transient.assess(requested) if self.transient else {"status": "not-evaluated"}
        return {"vm": workload, "devices": {d: permitted[d]["version"] for d in requested},
                "surface": {d: sorted(permitted[d]["registers"]) for d in requested},
                "catalogue_digest": snap.digest, "correlation_id": correlation_id, "transient": risk}


class Snapshotter:           # INV-26
    def save(self, vm):
        return {"devices": dict(vm["devices"]), "surface": dict(vm["surface"]),
                "catalogue_digest": vm["catalogue_digest"]}

    def restore(self, snap, store):
        current = {d["name"]: d for d in store.active.document["devices"]}
        for dev, ver in snap["devices"].items():
            cur = current.get(dev)
            if cur is None or cur["version"] != ver or sorted(cur["registers"]) != snap["surface"][dev]:
                raise PeerError("INV25_COMPATIBILITY_MISMATCH", f"{dev} surface/version changed")
        return True


class TransientDefense:      # INV-43 (optional)
    def __init__(self, sensitive=()):
        self.sensitive = set(sensitive)

    def assess(self, devices):
        hits = sorted(set(devices) & self.sensitive)
        return {"status": "evaluated", "speculation_sensitive": hits}
