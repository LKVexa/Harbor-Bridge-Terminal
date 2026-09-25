# 01 — Audit of candidate v5.0.0

**Map profile:** none. The yard office is absent, so `yard_query` and RCG could not run. There is no context graph;
the audit was done by reading every file and running the tests.

**What it is:** a dependency-free Python reference component. It has an HMAC `PK_SIGNATURE/2` envelope, a
`TrustStore` with signer roles, rotation and revocation, a `PK_PROVENANCE/2` hash chain and a local `AuditLedger`,
plus a `pk_core` adapter (`component.py`, `contract.py`) and a 100-control `CHECKLIST.json`.

**Tests at intake:** 19 discovered, 17 pass, 2 skipped (`pk_core` absent).

**Gaps:** the candidate's own `MISSING_COMPONENTS.md` lists 48 production gaps. The attached checklist expands those
into 1,005 gate items. Main themes: no asymmetric crypto, no KMS, no certificate trust, no attestations, no
transparency, no persistence or distribution, no policy adapter, no admission hook, no trusted time, no ops or
assurance programme.

**Licence of candidate:** no LICENSE file in the zip (flag for the owner if it will be distributed).
