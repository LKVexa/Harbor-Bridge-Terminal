# Patching, vulnerability and EOL policy (M80) — DRAFT, owner decision required

Proposed defaults (not commitments until OWNERSHIP.json names an owner and the owner approves):
- Critical CVE in a pinned dependency: patched release ≤ 7 days; High ≤ 30 days; Medium ≤ 90 days.
- Supported release lines: current minor and previous minor. EOL announced ≥ 90 days ahead.
- Upstream EOL (wasmCloud/NATS/wadm): matrix entry moves to `deprecated` on announcement, `blocked` at EOL.
