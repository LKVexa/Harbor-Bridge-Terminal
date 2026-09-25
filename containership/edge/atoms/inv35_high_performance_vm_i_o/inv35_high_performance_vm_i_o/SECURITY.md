# Security policy — INV-35 High-performance VM I/O

**Report privately.** Do not open public issues for suspected guest→host escapes,
isolation breaks, authentication bypasses or audit tampering.

* Contact: security_owner in `governance/OWNERS.json` (**currently UNASSIGNED**; until assigned, the accountable owner: davidpaulrussell@linearfinance.org).
* Include: version (`VERSION`), tree digest (`conformance/PK_GATE_RESULTS.json`), reproducer (a fixture JSON is ideal), impact.
* Response targets: `docs/operations/PATCHING_AND_EOL.md`.
* Supported versions: latest MINOR of the current MAJOR, plus the previous MINOR for 90 days.
