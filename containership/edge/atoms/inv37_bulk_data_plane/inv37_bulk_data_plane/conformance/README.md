# INV-37 conformance fixtures

`fixtures/*.json` — one case each: `{id, kind, input, expect{ok, code, ...}}`; kinds `manifest | chunk | object | resume | negotiate`. Byte inputs are hex; expected SHA-256 values are included so other languages can check exact behaviour. `FIXTURES.lock` pins every fixture's SHA-256; the runner reports `modified:`/`missing:`/`unlocked:` and fails.

Run against this package: `python conformance/run.py --out report.json`.
Run against another implementation: provide a module exposing `validate_manifest`, `manifest`, `Receiver` (with `accept`, `assemble`, `resume_token`), `negotiate`, whose errors carry `.code` from the INV-37 registry, then `python conformance/run.py --adapter mymod:factory`.

Changing expected results requires regenerating with `tools/gen_conformance.py` **and** architecture review of the schema/contract change (CODEOWNERS).
