"""INV-38-C079 — Telemetry retention/sampling/export policy enforcement."""
from __future__ import annotations
from dataclasses import dataclass, field

CLASSES = ("metrics", "logs", "traces", "security_audit", "diagnostics", "release_evidence")

@dataclass
class TelemetryPolicy:
    retention_days: dict = field(default_factory=lambda: {
        "metrics": 15, "logs": 7, "traces": 3, "security_audit": 365,
        "diagnostics": 2, "release_evidence": 3650})
    sample_rate: dict = field(default_factory=lambda: {
        "metrics": 1.0, "logs": 0.1, "traces": 0.01,
        "security_audit": 1.0, "diagnostics": 1.0, "release_evidence": 1.0})
    export_allowlist: tuple = ("otlp-collector.internal",)

    def effective_sample_rate(self, cls: str, *, is_error_or_security: bool) -> float:
        # Mandatory security audit events are NEVER sampled out (C079-T03).
        if cls == "security_audit" or is_error_or_security:
            return 1.0
        return self.sample_rate[cls]

    def validate(self) -> list[str]:
        problems = []
        if self.sample_rate["security_audit"] != 1.0:
            problems.append("security_audit must not be sampled")
        if self.retention_days["security_audit"] < 90:
            problems.append("security_audit retention too short")
        return problems
