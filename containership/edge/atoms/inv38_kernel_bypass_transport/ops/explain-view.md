# Operator explain view (INV-38-C077)

`tools/inv38-explain` (backed by `decisions.py::explain`) resolves a decision or
operation ID into an ordered causal chain: request accepted → authn/authz →
version negotiation → admission → region validation → provider choice → submission
→ completion/fallback/rejection, with the exact stable reason codes and which
constraint won (links to `policy/constraint-precedence.yaml`). Human and
machine-readable modes. Golden incident fixtures (bypass, kernel fallback, OOB,
stale key, policy denial, provider stall, mixed-version) are exercised in
`tests/test_decisions.py`. **Status:** `DONE`.
