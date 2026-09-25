# WIT fixture corpus (INV11-MC-10/12)

* `valid/` — 25 single-file packages covering every supported production.
* `invalid/` — 26 inputs, each with its expected stable diagnostic code in `EXPECTED.json`.
* `policy/<code>/{old,new}.wit` — one minimal pair per compatibility rule plus
  combination cases; expected class in `EXPECTED.json` (optional `config` for gated features).
* `multi/app` — multi-file package with a versioned `deps/` dependency.

All fixtures are original to this package (no third-party WIT). Reproduce any
case with `python -m inv11_interface_contract_language.wit check <file>` or
`... diff policy/<code>/old.wit policy/<code>/new.wit --expanded`.
Digests are recorded in `corpus_inventory.json` of each evidence bundle.
