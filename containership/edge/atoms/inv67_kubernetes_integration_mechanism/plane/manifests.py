"""Source of truth for Kubernetes artifacts (items 10, 17, 25).

CRD, RBAC, Deployment, NetworkPolicy, PDB and overlays are generated from
these dicts by ``python -m <pkg>.plane.manifests --write`` so the YAML on disk
can be drift-checked in CI (tests/contract/test_manifests.py)."""
from __future__ import annotations

import json
import pathlib
import sys

from .kube import GROUP, KIND, PLURAL, VERSION

NS = "inv67-system"
SA = "inv67-controller"
IMAGE = "registry.example.org/inv67/controller@sha256:" + "0" * 64   # placeholder: set by the release pipeline

_quantity = {"type": "string", "pattern": r"^[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+|Ki|Mi|Gi|Ti|Pi|Ei|n|u|m|k|M|G|T|P|E)?$",
             "maxLength": 128}
_resources = {"type": "object", "additionalProperties": False,
              "properties": {"cpu": _quantity, "memory": _quantity}}
_container = {"type": "object", "required": ["name", "image"], "additionalProperties": False,
              "properties": {"name": {"type": "string", "maxLength": 63, "pattern": "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"},
                             "image": {"type": "string", "minLength": 1, "maxLength": 512},
                             "resources": {"type": "object", "additionalProperties": False,
                                           "properties": {"requests": _resources, "limits": _resources}}}}


def crd() -> dict:
    spec_schema = {
        "type": "object", "required": ["template"],
        "properties": {"template": {"type": "object", "required": ["spec"], "properties": {
            "metadata": {"type": "object", "additionalProperties": False, "properties": {
                "labels": {"type": "object", "additionalProperties": {"type": "string"}},
                "annotations": {"type": "object", "additionalProperties": {"type": "string"}}}},
            "spec": {"type": "object", "required": ["containers"],
                     # Unknown Pod fields are preserved so the controller can refuse them by path
                     # (no silent pruning = no silent drop).
                     "x-kubernetes-preserve-unknown-fields": True,
                     "properties": {"containers": {"type": "array", "minItems": 1, "maxItems": 32, "items": _container}}}}}},
    }
    status_schema = {"type": "object", "x-kubernetes-preserve-unknown-fields": True, "properties": {
        "observedGeneration": {"type": "integer"}, "phase": {"type": "string",
                                                             "enum": ["Pending", "Running", "Succeeded", "Failed", "Unknown"]},
        "state": {"type": "string"}, "appId": {"type": "string", "nullable": True}, "attempt": {"type": "integer"},
        "attemptId": {"type": "string"},
        "conditions": {"type": "array", "x-kubernetes-list-type": "map", "x-kubernetes-list-map-keys": ["type"],
                       "items": {"type": "object", "required": ["type", "status", "reason", "lastTransitionTime"],
                                 "properties": {"type": {"type": "string"}, "status": {"type": "string", "enum": ["True", "False", "Unknown"]},
                                                "reason": {"type": "string"}, "message": {"type": "string", "maxLength": 512},
                                                "lastTransitionTime": {"type": "string", "format": "date-time"},
                                                "observedGeneration": {"type": "integer"}}}}}}
    return {
        "apiVersion": "apiextensions.k8s.io/v1", "kind": "CustomResourceDefinition",
        "metadata": {"name": f"{PLURAL}.{GROUP}", "annotations": {"inv67.linearfinance.org/owner": "see docs/OWNERSHIP.md"}},
        "spec": {"group": GROUP, "scope": "Namespaced",
                 "names": {"plural": PLURAL, "singular": "wasmworkload", "kind": KIND, "shortNames": ["wwl"],
                           "categories": ["inv67"]},
                 "versions": [{
                     "name": VERSION, "served": True, "storage": True,
                     "subresources": {"status": {}},
                     "additionalPrinterColumns": [
                         {"name": "Phase", "type": "string", "jsonPath": ".status.phase"},
                         {"name": "State", "type": "string", "jsonPath": ".status.state"},
                         {"name": "Ready", "type": "string", "jsonPath": ".status.conditions[?(@.type==\"Ready\")].status"},
                         {"name": "Age", "type": "date", "jsonPath": ".metadata.creationTimestamp"}],
                     "schema": {"openAPIV3Schema": {"type": "object", "required": ["spec"], "properties": {
                         "apiVersion": {"type": "string"}, "kind": {"type": "string"}, "metadata": {"type": "object"},
                         "spec": spec_schema, "status": status_schema},
                         "x-kubernetes-validations": [
                             {"rule": "self.metadata.name.size() <= 63", "message": "name must be <= 63 chars"}]}}}]}}


def rbac() -> list[dict]:
    return [
        {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": {"name": SA, "namespace": NS},
         "automountServiceAccountToken": True},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole", "metadata": {"name": "inv67-controller"},
         "rules": [
             {"apiGroups": [GROUP], "resources": [PLURAL], "verbs": ["get", "list", "watch", "update"]},
             {"apiGroups": [GROUP], "resources": [f"{PLURAL}/status"], "verbs": ["get", "update"]},
             {"apiGroups": [""], "resources": ["events"], "verbs": ["create"]},
             {"apiGroups": ["authentication.k8s.io"], "resources": ["tokenreviews"], "verbs": ["create"]}]},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRoleBinding", "metadata": {"name": "inv67-controller"},
         "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "ClusterRole", "name": "inv67-controller"},
         "subjects": [{"kind": "ServiceAccount", "name": SA, "namespace": NS}]},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "Role", "metadata": {"name": "inv67-leader-election", "namespace": NS},
         "rules": [{"apiGroups": ["coordination.k8s.io"], "resources": ["leases"], "verbs": ["get", "create", "update"]}]},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding", "metadata": {"name": "inv67-leader-election", "namespace": NS},
         "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": "inv67-leader-election"},
         "subjects": [{"kind": "ServiceAccount", "name": SA, "namespace": NS}]},
    ]


def deployment(replicas: int = 2) -> dict:
    return {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "inv67-controller", "namespace": NS,
                                                                        "labels": {"app.kubernetes.io/name": "inv67"}},
            "spec": {"replicas": replicas, "selector": {"matchLabels": {"app.kubernetes.io/name": "inv67"}},
                     "strategy": {"type": "RollingUpdate", "rollingUpdate": {"maxUnavailable": 0, "maxSurge": 1}},
                     "template": {"metadata": {"labels": {"app.kubernetes.io/name": "inv67"}},
                                  "spec": {"serviceAccountName": SA,
                                           "securityContext": {"runAsNonRoot": True, "seccompProfile": {"type": "RuntimeDefault"}},
                                           "containers": [{
                                               "name": "controller", "image": IMAGE,
                                               "args": ["--config=/etc/inv67/config.json"],
                                               "ports": [{"name": "metrics", "containerPort": 9090}, {"name": "health", "containerPort": 8081}],
                                               "livenessProbe": {"httpGet": {"path": "/healthz", "port": "health"}, "periodSeconds": 10},
                                               "readinessProbe": {"httpGet": {"path": "/readyz", "port": "health"}, "periodSeconds": 5},
                                               "resources": {"requests": {"cpu": "100m", "memory": "128Mi"},
                                                             "limits": {"cpu": "1", "memory": "512Mi"}},
                                               "securityContext": {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True,
                                                                   "capabilities": {"drop": ["ALL"]}},
                                               "volumeMounts": [{"name": "config", "mountPath": "/etc/inv67", "readOnly": True},
                                                                {"name": "secrets", "mountPath": "/var/run/inv67/secrets", "readOnly": True},
                                                                {"name": "state", "mountPath": "/var/lib/inv67"}]}],
                                           "volumes": [{"name": "config", "configMap": {"name": "inv67-config"}},
                                                       {"name": "secrets", "secret": {"secretName": "inv67-secrets", "defaultMode": 0o400}},
                                                       {"name": "state", "emptyDir": {}}]}}}}


def network_policy() -> dict:
    return {"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy", "metadata": {"name": "inv67-controller", "namespace": NS},
            "spec": {"podSelector": {"matchLabels": {"app.kubernetes.io/name": "inv67"}}, "policyTypes": ["Ingress", "Egress"],
                     "ingress": [{"ports": [{"port": 9090}, {"port": 8081}]}],
                     "egress": [{"ports": [{"port": 443}, {"port": 6443}]}, {"ports": [{"port": 53, "protocol": "UDP"}]}]}}


def pdb() -> dict:
    return {"apiVersion": "policy/v1", "kind": "PodDisruptionBudget", "metadata": {"name": "inv67-controller", "namespace": NS},
            "spec": {"minAvailable": 1, "selector": {"matchLabels": {"app.kubernetes.io/name": "inv67"}}}}


def namespace() -> dict:
    return {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": NS, "labels": {
        "pod-security.kubernetes.io/enforce": "restricted"}}}


def to_yaml(obj, indent=0) -> str:
    pad = "  " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = []
        for k, v in obj.items():
            key = json.dumps(k) if not str(k).replace("-", "").replace("_", "").replace(".", "").replace("/", "").isalnum() else k
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{pad}{key}:\n{to_yaml(v, indent + 1)}")
            else:
                lines.append(f"{pad}{key}: {to_yaml(v, 0)}")
        return "\n".join(lines)
    if isinstance(obj, list):
        if not obj:
            return "[]"
        lines = []
        for v in obj:
            if isinstance(v, dict) and v:
                body = to_yaml(v, indent + 1)
                lines.append(f"{pad}- {body.lstrip()}")
            else:
                lines.append(f"{pad}- {to_yaml(v, 0)}")
        return "\n".join(lines)
    return json.dumps(obj)


def files() -> dict[str, str]:
    doc = lambda objs: "\n---\n".join(to_yaml(o) for o in objs) + "\n"  # noqa: E731
    return {
        "api/crds/wasmworkloads.inv67.linearfinance.org.yaml": doc([crd()]),
        "deploy/base/namespace.yaml": doc([namespace()]),
        "deploy/base/rbac.yaml": doc(rbac()),
        "deploy/base/deployment.yaml": doc([deployment()]),
        "deploy/base/networkpolicy.yaml": doc([network_policy()]),
        "deploy/base/pdb.yaml": doc([pdb()]),
        "deploy/base/kustomization.yaml": doc([{"apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
                                                "resources": ["namespace.yaml", "../../api/crds/wasmworkloads.inv67.linearfinance.org.yaml",
                                                              "rbac.yaml", "deployment.yaml", "networkpolicy.yaml", "pdb.yaml"]}]),
        "deploy/overlays/dev/kustomization.yaml": doc([{"apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
                                                        "resources": ["../../base"],
                                                        "patches": [{"target": {"kind": "Deployment", "name": "inv67-controller"},
                                                                     "patch": "- op: replace\n  path: /spec/replicas\n  value: 1\n"}]}]),
        "deploy/overlays/prod/kustomization.yaml": doc([{"apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
                                                         "resources": ["../../base"],
                                                         "patches": [{"target": {"kind": "Deployment", "name": "inv67-controller"},
                                                                      "patch": "- op: replace\n  path: /spec/replicas\n  value: 3\n"}]}]),
    }


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[1]
    drift = []
    for rel, text in files().items():
        p = root / rel
        if "--write" in sys.argv:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        elif not p.exists() or p.read_text() != text:
            drift.append(rel)
    if drift:
        print("manifest drift:", *drift, sep="\n  ")
        sys.exit(1)
    print("manifests in sync")
