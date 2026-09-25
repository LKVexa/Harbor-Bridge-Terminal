# Third-party notices — INV-52 v4.3.0

No third-party code is bundled. The package has no runtime dependencies beyond the Python standard library.

| Source | Part(s) | License | Note |
|---|---|---|---|
| INV-46 Distributed application runtime v4.3.0 (sibling car in the owner's GitHub Junkyard, work order `INV46-20260922`) | `TokenAuthority`, `AuditChain`, `redact`/`find_secrets`, `verify_artifact` (→ `security.py`); `verify_integrity.py`; `tools/cleanroom.py`; `tools/sbom.py`; `gate.py`; governance layout (`owners.json` RACI) | none declared (same owner; INV-46 `LICENSE-STATUS.md` reports BLOCKED) | adapted: error base class and `PK_MSG_*` codes; tenant bus, capabilities and everything else in `security.py` below "tenant bus" is new |
| Dapr (referenced, not bundled) | `deploy/dapr/*.yaml` follow Dapr's published component/subscription/resiliency schemas | Apache-2.0 (Dapr project) | configuration only |
| CloudEvents 1.0 specification (referenced) | attribute names in `adapters.py` | Apache-2.0 (spec) | no code copied |
