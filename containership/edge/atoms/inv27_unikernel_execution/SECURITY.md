# Security policy — INV-27

**Supported versions:** see `ops/EOL.json`. 4.3.x is supported; 4.2.0 and earlier are not (they
trust caller-supplied seal metadata).

**Reporting a vulnerability:** privately, to the `inv27-security-owner` (`ops/OWNERS.md`). The
private channel is not yet named (W-OWNERS). Until it is, do not open public issues for seal,
trust or isolation bypasses.

**Response targets** (ops/EOL.json `patch_policy`):

- acknowledge within 2 working days
- fix a critical seal bypass within 2 days
- fix high severity within 7 days
- fix medium severity within 30 days

Disclosure is coordinated with the reporter after a fix ships.

**In scope:** parser memory or CPU exhaustion, seal bypass, signature or provenance bypass, isolation
plan escape, authz bypass, audit or journal tampering, and secret leakage in telemetry.

**Handling malicious sample binaries:** keep them only under `tests/fixtures/`, build them from
source with `build_fixtures.sh`, pin their sha256 in `FIXTURES.json`, and never execute them on a
host (only the VMM test double reads them).
