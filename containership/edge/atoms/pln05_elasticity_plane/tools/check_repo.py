"""Repository consistency checks (MC-01, MC-09, MC-32, MC-34 and the global gates).

    python tools/check_repo.py      # prints JSON, exit 1 on any failure
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

RUNTIME = ["__init__.py", "__main__.py", "audit.py", "cli.py", "configuration.py", "controller.py",
           "errors.py", "health.py", "iam.py", "keys.py", "plane.py", "reliability.py", "spec.py",
           "state.py", "supplychain.py", "telemetry.py", "wire.py", "component.py", "contract.py"]
REQUIRED_DOCS = ["README.md", "CHANGELOG.md", "MASTER.md", "SECURITY.md", "NOTICE", "CODEOWNERS",
                 "pyproject.toml", "requirements-lock.txt", "docs/adr/ADR-0001-pln05-authoritative-scope.md",
                 "spec/pln05_semantics.md", "spec/pln05_nfr.json", "spec/pln05_state_machine.mmd",
                 "spec/pln05_scope.json", "spec/interface_reliability.md", "spec/state_schema.json",
                 "spec/status_schema.json", "spec/explain_schema.json", "security/iam-model.md",
                 "security/capabilities.json", "security/threat-model.md", "security/threats.json",
                 "security/isolation-model.md", "security/crypto-policy.md",
                 "security/security_dependency_failure_policy.md", "security/approved-versions.json",
                 "ops/oncall.json", "ops/reliability/failure_matrix.json", "ops/reliability/fault_scenarios.json",
                 "ops/reliability/degraded_modes.md", "performance/efficiency-analysis.md",
                 "observability/telemetry-policy.md", "observability/alerts.json", "observability/dashboards.json",
                 "docs/release-policy.md", "docs/runbooks/day0-bootstrap.md", "docs/runbooks/day1-operations.md",
                 "docs/runbooks/day2-incidents.md", "docs/runbooks/backup-restore.md",
                 "docs/operations/ownership-and-escalation.md", "compatibility/supported-versions.json",
                 "governance/waivers.json", "governance/reviews.json", "governance/approvals.json",
                 "traceability/requirements.json", "traceability/REQUIREMENTS_MATRIX.md",
                 "benchmarks/thresholds.json", "benchmarks/baseline.json", "ci/performance_gate.py",
                 ".github/workflows/ci.yml", ".github/workflows/release.yml", "source/SOURCE.json"]
FORBIDDEN = [r"^\s*import (socket|subprocess|urllib|http|ftplib|smtplib|ctypes)\b",
             r"^\s*from (socket|subprocess|urllib|http|ctypes)\b", r"os\.environ", r"os\.system", r"\bexec\(", r"\beval\("]


def version_consistency() -> list[str]:
    errs = []
    v = (ROOT / "VERSION").read_text().strip()
    init = re.search(r'^__version__\s*=\s*"([^"]+)"', (ROOT / "__init__.py").read_text(), re.M).group(1)
    py = re.search(r'^version\s*=\s*"([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    appr = json.loads((ROOT / "security" / "approved-versions.json").read_text())["artifacts"]["pln05-elasticity-plane"]
    readme = re.search(r"\*\*Version:\*\*\s*([0-9.]+)", (ROOT / "README.md").read_text()).group(1)
    ch = re.search(r"^## ([0-9.]+)", (ROOT / "CHANGELOG.md").read_text(), re.M).group(1)
    for name, val in (("__init__", init), ("pyproject", py), ("README", readme), ("CHANGELOG top", ch)):
        if val != v:
            errs.append(f"version mismatch: VERSION={v} {name}={val}")
    if v not in appr:
        errs.append(f"version {v} not in approved-versions")
    return errs


def scope_drift() -> list[str]:
    from pln05_elasticity_plane import spec
    errs = []
    scope = json.loads((ROOT / "spec" / "pln05_scope.json").read_text())
    for key, val in (("responsibility", spec.RESPONSIBILITY), ("matrix", spec.RESPONSIBILITY_MATRIX),
                     ("owns", spec.OWNS), ("not_owns", spec.NOT_OWNS), ("non_goals", spec.NON_GOALS),
                     ("interfaces", spec.INTERFACES)):
        if scope.get(key) != val:
            errs.append(f"spec/pln05_scope.json:{key} differs from spec.py")
    readme = (ROOT / "README.md").read_text()
    if spec.RESPONSIBILITY not in readme:
        errs.append("README responsibility differs from spec.py")
    for item in spec.OWNS + spec.NOT_OWNS + spec.NON_GOALS:
        if f"- {item}" not in readme:
            errs.append(f"README missing scope line: {item}")
    adr = (ROOT / spec.SCOPE_ADR).read_text()
    for resp, cls in spec.RESPONSIBILITY_MATRIX.items():
        if not re.search(rf"\|\s*{re.escape(resp)}\s*\|\s*{cls}\s*\|", adr):
            errs.append(f"ADR matrix row differs: {resp}={cls}")
    if scope.get("adr_status") not in ("PROPOSED", "ACCEPTED"):
        errs.append("scope adr_status invalid")
    return errs


def required_documents() -> list[str]:
    return [f"missing {p}" for p in REQUIRED_DOCS if not (ROOT / p).exists()]


def governance() -> list[str]:
    errs = []
    if not ((ROOT / "LICENSE").exists() or (ROOT / "LICENSE-PENDING.md").exists()):
        errs.append("neither LICENSE nor LICENSE-PENDING.md present")
    lic = json.loads((ROOT / "security" / "approved-versions.json").read_text())["license"]
    if f'"{lic}"' not in (ROOT / "pyproject.toml").read_text():
        errs.append("pyproject license differs from approved-versions license")
    roles = json.loads((ROOT / "ops" / "oncall.json").read_text())["roles"]
    for need in ("pln05.service-owner", "pln05.release-approver", "pln05.security-contact", "pln05.oncall-primary"):
        if need not in roles:
            errs.append(f"ops/oncall.json missing role {need}")
    if "Supported versions" not in (ROOT / "SECURITY.md").read_text():
        errs.append("SECURITY.md lacks supported versions")
    return errs


def ambient_authority() -> list[str]:
    errs = []
    for f in RUNTIME:
        text = (ROOT / f).read_text()
        for pat in FORBIDDEN:
            if re.search(pat, text, re.M):
                errs.append(f"{f}: forbidden ambient authority pattern {pat}")
    return errs


def code_hygiene() -> list[str]:
    errs = []
    for f in RUNTIME:
        text = (ROOT / f).read_text()
        if re.search(r"^\s*assert\s", text, re.M):
            errs.append(f"{f}: bare assert (stripped under -O)")
        if re.search(r"\b(TODO|FIXME|XXX)\b|NotImplemented", text):
            errs.append(f"{f}: placeholder marker")
    return errs


def references() -> list[str]:
    """Backticked repo paths in the top-level docs must exist."""
    errs = []
    for doc in ["README.md", "MASTER.md", "SECURITY.md", "docs/release-policy.md", "LICENSE-PENDING.md"]:
        for ref in re.findall(r"`([A-Za-z0-9_./-]+\.(?:md|json|py|mmd|toml|txt))`", (ROOT / doc).read_text()):
            if "<" in ref or ref.startswith(("pk_core", "python", "evidence/")):
                continue
            if not (ROOT / ref).exists() and not (ROOT / ref.split("/")[-1]).exists():
                errs.append(f"{doc}: broken reference {ref}")
    return errs


def threat_tests() -> list[str]:
    errs = []
    text = (ROOT / "tests" / "security" / "test_adversarial.py").read_text()
    for t in json.loads((ROOT / "security" / "threats.json").read_text())["threats"]:
        fn = t["test"].split("::")[-1]
        if f"def {fn}(" not in text:
            errs.append(f"{t['id']}: missing test {fn}")
    return errs


def failure_matrix() -> list[str]:
    errs = []
    fm = json.loads((ROOT / "ops" / "reliability" / "failure_matrix.json").read_text())
    sc = json.loads((ROOT / "ops" / "reliability" / "fault_scenarios.json").read_text())["scenarios"]
    for f in fm["failures"]:
        s = f["scenario"]
        if s.startswith("FS") and s not in sc:
            errs.append(f"{f['id']}: scenario {s} missing")
        if not s.startswith("FS") and not s.startswith(("UNDETECTABLE", "N/A")):
            errs.append(f"{f['id']}: neither a scenario nor a documented limitation")
    return errs


CHECKS = {"version": version_consistency, "scope": scope_drift, "documents": required_documents,
          "governance": governance, "ambient_authority": ambient_authority, "hygiene": code_hygiene,
          "references": references, "threat_tests": threat_tests, "failure_matrix": failure_matrix}


def main() -> int:
    res = {k: fn() for k, fn in CHECKS.items()}
    print(json.dumps(res, indent=1))
    return 1 if any(res.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
