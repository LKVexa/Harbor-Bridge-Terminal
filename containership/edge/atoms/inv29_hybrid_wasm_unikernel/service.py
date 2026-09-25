"""Service wiring for INV-29: one object that owns the admitter, lifecycle,
telemetry and readiness logic (MC079-MC083, MC087, MC089).

    svc = Service.build(keyring, policy, signing_key_id="...", state_dir=path)
    svc.serve(port=9829)          # /healthz /readyz /version /dependencies /metrics /decisions /explain
    svc.submit(request, traceparent=None)
"""
from __future__ import annotations

import io
import pathlib
import sys
import time
from typing import Dict, Optional, TextIO

from . import __version__
from . import deps as D
from . import telemetry as T
from .admission import AdmissionPolicy, AdmissionRequest, Admitter, Keyring, ReplayGuard
from .lifecycle import ControlFile, Lifecycle, Store


class Service:
    def __init__(self, admitter: Admitter, lifecycle: Lifecycle, control: ControlFile, *,
                 metrics: T.Metrics, decisions: T.DecisionLog, logger: T.Logger, release: str,
                 adapters: Optional[Dict[str, D.Adapter]] = None):
        self.admitter, self.lifecycle, self.control = admitter, lifecycle, control
        self.metrics, self.decisions, self.logger, self.release = metrics, decisions, logger, release
        self.adapters = adapters or {}

    @classmethod
    def build(cls, keyring: Keyring, policy: AdmissionPolicy, *, signing_key_id: str,
              state_dir: pathlib.Path, release: str = "unreleased", log_stream: TextIO = sys.stderr,
              adapters: Optional[Dict[str, D.Adapter]] = None, replay: Optional[ReplayGuard] = None,
              clock=time.time) -> "Service":
        metrics = T.Metrics()
        logger = T.Logger(log_stream, version=__version__, release=release)
        decisions = T.DecisionLog(metrics=metrics, logger=logger)
        admitter = Admitter(keyring, policy, signing_key_id=signing_key_id, on_decision=decisions,
                            replay=replay, clock=clock)
        state_dir = pathlib.Path(state_dir)
        lc = Lifecycle(admitter, Store(state_dir / "store"), clock=clock)
        svc = cls(admitter, lc, ControlFile(state_dir / "control.json"), metrics=metrics,
                  decisions=decisions, logger=logger, release=release, adapters=adapters)
        svc.control.apply(admitter)
        return svc

    # ------------------------------------------------------------ decisions
    def submit(self, req: AdmissionRequest, *, traceparent: Optional[str] = None) -> dict:
        tp = T.traceparent(traceparent)
        self.control.apply(self.admitter)
        t0 = time.perf_counter()
        try:
            doc = self.lifecycle.submit(req)
        finally:
            self.metrics.observe("inv29_admission_latency_ms", (time.perf_counter() - t0) * 1e3)
        self.logger.log("info", "submit", tp=tp, composition=doc["id"][:16], state=doc["state"])
        self.refresh_gauges()
        return doc

    def reconcile(self) -> dict:
        self.control.apply(self.admitter)
        out = self.lifecycle.reconcile()
        self.logger.log("info", "reconcile", **out)
        self.refresh_gauges()
        return out

    # ------------------------------------------------------------ status
    def refresh_gauges(self) -> None:
        for state, n in self.lifecycle.counts().items():
            self.metrics.set("inv29_hybrid_instances", n, state=state)
        cap = max(self.admitter.replay.capacity, 1)
        self.metrics.set("inv29_replay_cache_fill_ratio", len(self.admitter.replay) / cap)
        rep = D.dependency_report(self.adapters)
        for name, h in rep["dependencies"].items():
            self.metrics.set("inv29_dependency_available", 1.0 if h["state"] == D.AVAILABLE else 0.0, dependency=name)
        self.metrics.set("inv29_min_layer_count", float(self.admitter.policy.required_layers))

    def ready(self):
        reasons = []
        rep = D.dependency_report(self.adapters)
        if not rep["all_required_available"]:
            reasons.append("required dependency not AVAILABLE: " + ", ".join(
                n for n, h in rep["dependencies"].items()
                if D.DEPENDENCIES[n]["required"] and h["state"] != D.AVAILABLE))
        if self.admitter.disabled is not None:
            reasons.append(f"emergency disabled: {self.admitter.disabled}")
        try:
            self.admitter.keyring._get(self.admitter.signing_key_id)
        except Exception:
            reasons.append("record signing key unavailable")
        return (not reasons, {"reasons": reasons})

    def version_info(self) -> dict:
        from .records import SCHEMA_FILES
        return {"element": "INV-29", "version": __version__, "release": self.release,
                "policy_generation": self.admitter.policy.generation, "schemas": sorted(SCHEMA_FILES),
                "pk_core": D.pk_core_status().as_dict()}

    def serve(self, *, port: int, host: str = "127.0.0.1"):
        return T.serve(port=port, host=host, version_info=self.version_info, ready=self.ready,
                       dependencies=lambda: D.dependency_report(self.adapters), metrics=self.metrics,
                       decisions=self.decisions)
