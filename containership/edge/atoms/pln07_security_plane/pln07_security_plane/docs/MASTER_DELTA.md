# MASTER.md status and delta record (MC-01)

`MASTER.md` is **not present** in the supplied 4.2.0 archive, and the checklist forbids rebuilding it from README text. It stays an open external blocker.

When the owner restores it:
1. Put it at the package root **verbatim**, record its provenance (commit/tag/digest/signature) in `MASTER.provenance.json`.
2. Diff it against `contract.py`, `CHECKLIST.json`, `ADR-0001` and this release. Record every semantic difference below; do not edit MASTER.md.
3. Run `python -m pln07_security_plane.ci.gate --reseal`.

## Known post-4.2.0 deltas to reconcile
| Area | 4.3.0 behaviour | Needs MASTER check |
|---|---|---|
| Grant body | `PK_GRANT/2` fields (boundary, replay, instance) | Field names and stickiness |
| Revocation key | Full fingerprint, legacy id kept | Revocation record format |
| Signing | `PK_SIG/1` Ed25519/HMAC envelope | Algorithm policy |
| Depth | Global cap 5 + policy limits (min wins) | Per-tenant limits |
| Service | `api_version` "1", JSON envelopes | Transport contract |
