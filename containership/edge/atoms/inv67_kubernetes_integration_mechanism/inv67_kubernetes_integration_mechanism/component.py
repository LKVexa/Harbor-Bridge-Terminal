"""INV-67 - Kubernetes integration mechanism.

The checklist harness in this module is deliberately thin. Untrusted Pod parsing
and translation lives in :mod:`translator`, which has no ``pk_core`` dependency
and is independently testable.
"""
from __future__ import annotations

from typing import Any

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .translator import PHASES, InvalidPod, TranslationError, Unsupported, project_status, quantity, translate


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class KubernetesIntegrationMechanismComponent(Component):
    """Master-applied checklist component for INV-67."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _pod(self, **extra):
        pod: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "web",
                "namespace": "default",
                "labels": {"app": "web"},
                "annotations": {"inv67.example/source": "fixture"},
            },
            "spec": {
                "containers": [{
                    "name": "c",
                    "image": "registry/web:1",
                    "resources": {
                        "requests": {"cpu": "250m", "memory": "512Mi"},
                        "limits": {"cpu": "1", "memory": "1Gi"},
                    },
                }]
            },
        }
        pod["spec"].update(extra)
        return pod

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        req = translate(self._pod())
        u = req["units"][0]
        _verify(
            u["cpu"] == 0.25
            and u["memory"] == 512 * 1024**2
            and u["limits"] == {"cpu": 1, "memory": 1024**3}
            and req["labels"] == {"app": "web"}
            and req["annotations"] == {"inv67.example/source": "fixture"},
            "translation did not preserve requests, limits, labels, and annotations",
        )
        _verify(
            project_status("exited-0") == "Succeeded" and project_status("weird") == "Unknown",
            "status projection failed",
        )
        findings[0] = self.satisfied(
            items[0],
            "The reference translator preserves requests, limits, labels and annotations for the supported "
            "Pod subset, rejects unsupported semantics by field path, and projects runtime state back into "
            "Kubernetes Pod phases.",
            *self._evidence("translator.py::translate", "translator.py::project_status"),
        )
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        pod = self._pod(hostNetwork=True, volumes=[{"name": "docker", "hostPath": {"path": "/var/run"}}])
        pod["spec"]["containers"][0]["securityContext"] = {"privileged": True}
        try:
            translate(pod)
        except Unsupported as exc:
            refusal = exc.to_dict()
        else:
            raise AssertionError("unsafe pod was not refused")
        fields = {d["field"] for d in refusal["details"]}
        _verify(
            {"spec.hostNetwork", "spec.volumes[0].hostPath", "spec.containers[0].securityContext.privileged"}
            <= fields,
            "security refusal did not identify all unsafe fields",
        )
        findings[0] = self.satisfied(
            items[0],
            "Host networking, hostPath mounts, and privileged containers are refused in one structured "
            "error with machine-readable field paths, rather than being silently weakened or ignored.",
            *self._evidence("translator.py::translate", "translator.py::TranslationError.to_dict"),
        )
        return findings


COMPONENT = KubernetesIntegrationMechanismComponent

__all__ = [
    "COMPONENT",
    "KubernetesIntegrationMechanismComponent",
    "PHASES",
    "TranslationError",
    "Unsupported",
    "InvalidPod",
    "quantity",
    "translate",
    "project_status",
]
