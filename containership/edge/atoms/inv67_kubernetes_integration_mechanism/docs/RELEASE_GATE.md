# Formal release / exit gate (item 63)
`python -m inv67_kubernetes_integration_mechanism.governance.gate --release` must exit 0. It requires:
1. every test referenced by `docs/requirements.json` passing (no required skips);
2. all 68 components `IMPLEMENTED_LOCALLY_VERIFIED` **and** acceptance gates MET, or an unexpired approved waiver in `docs/governance/exceptions.json`;
3. every ownership role filled (`docs/governance/ownership.json`);
4. release manifest verified and signed (HMAC/Sigstore key from the protected release workflow);
5. sign-off rows below complete.
In this archive the gate runs in `--local` mode and reports **NO_GO** with named blockers — see `evidence/GATE_RESULT.json`.

| Role | Identity | Decision | Date | Reference |
|---|---|---|---|---|
| INV-67 accountable owner | | | | |
| Platform/Kubernetes reviewer | | | | |
| Security reviewer | | | | |
| SRE/Operations reviewer | | | | |
| Downstream scheduler/runtime owner | | | | |
| Release authority | | | | |
