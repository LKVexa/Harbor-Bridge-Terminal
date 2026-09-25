# Vulnerability, patching and lifecycle policy

Traceability: C045, C094; MC-004-06, MC-049-03.

| Severity (CVSS v3.1) | Triage | Fix / mitigation SLA | Release |
|---|---|---|---|
| Critical ≥ 9.0 | 24 h | 72 h (mitigation within 24 h) | emergency patch |
| High 7.0–8.9 | 3 d | 14 d | next patch |
| Medium 4.0–6.9 | 10 d | 45 d | next minor |
| Low < 4.0 | 30 d | best effort | scheduled |

* Exceptions require a compensating control, an owner and an expiry ≤ 90 days, recorded in `docs/EXCEPTIONS.json`.
* Dependency scanning: `tools/sbom.py` output is fed to the organisation's scanner (e.g. `pip-audit -r requirements.lock`) in CI; the release gate blocks on open Critical/High without exception.
* Backend CVEs: the pinned backend release is re-evaluated on every upstream advisory; emergency upgrade path = rolling member replacement (CONSENSUS_CONTRACT).
* Support/EOL: each minor is supported for 12 months after the next minor ships; N-1 minor receives security fixes only.
* Reporting: security contact defined in `docs/GOVERNANCE.md`.
