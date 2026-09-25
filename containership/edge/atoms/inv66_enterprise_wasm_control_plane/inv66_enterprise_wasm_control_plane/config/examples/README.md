# Configuration examples (MC-022)

Layers: `base.json` < environment (`prod.json`) < site (`site-*.json`), deep-merged by `config.load_layers`
(dicts merge, lists and scalars replace).

* dev single-site: `base.json`
* prod single-site: `base.json prod.json site-eu-west-1.json`
* prod multi-site: one generation per site, e.g. `base.json prod.json site-us-east-1.json`

The signer public keys and IdP in these files are **throwaway example keys** generated for the
examples. Replace them. Secrets appear only as references (`env:`, `file:`, `kms:`, `vault:`).
Validate with `python -m inv66_enterprise_wasm_control_plane.production.cli validate-config <layers...>`.
