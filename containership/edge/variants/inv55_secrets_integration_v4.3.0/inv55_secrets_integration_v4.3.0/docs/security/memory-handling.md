# Secret memory handling

| ID | INV55-SEC-MEMORY | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: security-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

- `SecretValue` stores plaintext in a `bytearray`; `wipe()` zeroes it in place (`secretvalue.py`). It redacts repr/str/format, blocks pickle/copy/deepcopy, is unhashable, and compares in constant time.
- `drain()` wipes all lease values. Leases that expire or are dropped are NOT wiped (`_drop`), because the same `SecretValue` object is shared with the TTL cache — open waiver WVR-037.
- Best effort only: `reveal()` creates a Python `str`; request `value` arrives as `str`; Vault JSON bodies and the Vault token header are `str`/`bytes` copies that cannot be zeroed.
- Not implemented: mlock/locked memory, guaranteed zeroisation, swap exclusion. Deployments MUST disable core dumps (`ulimit -c 0`, `RLIMIT_CORE=0`, `PR_SET_DUMPABLE=0`) and swap or use encrypted swap. Hard confidentiality requires process isolation.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | WVR-037 |
