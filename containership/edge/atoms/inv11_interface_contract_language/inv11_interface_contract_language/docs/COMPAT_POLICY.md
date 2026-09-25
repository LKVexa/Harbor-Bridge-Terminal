# Compatibility policy INV11-COMPAT-POLICY/1 (generated from wit/compat.py POLICY)

Direction: old release → new release of the same package (producer evolution). Versions never decide.

| Code | Class | Rationale | Fixture |
|---|---|---|---|
| `alias-retargeted` | breaking | alias target structure changed | tests/fixtures/policy/alias-retargeted |
| `alias-retargeted-equal` | compatible | alias now points at a structurally identical type | tests/fixtures/policy/alias-retargeted-equal |
| `enum-case-added` | breaking | receivers cannot decode the new discriminant | tests/fixtures/policy/enum-case-added |
| `enum-cases-changed` | breaking | discriminant assignment changes | tests/fixtures/policy/enum-cases-changed |
| `flags-added` | breaking | new bits are not understood by old receivers; flag layout may widen | tests/fixtures/policy/flags-added |
| `flags-changed` | breaking | bit assignment changes | tests/fixtures/policy/flags-changed |
| `func-added` | additive | consumers that do not call it are unaffected | tests/fixtures/policy/func-added |
| `func-async-changed` | breaking | sync/async changes the canonical ABI lowering | tests/fixtures/policy/func-async-changed |
| `func-kind-changed` | breaking | method/static/constructor/freestanding changes the ABI | tests/fixtures/policy/func-kind-changed |
| `func-removed` | breaking | callers lose the function | tests/fixtures/policy/func-removed |
| `gate-changed` | compatible | feature gates/deprecation metadata do not change structure | tests/fixtures/policy/gate-changed |
| `interface-added` | additive | new interface; existing consumers unaffected | tests/fixtures/policy/interface-added |
| `interface-removed` | breaking | consumers importing it can no longer link | tests/fixtures/policy/interface-removed |
| `named-type-swapped` | compatible | value types are structural in the component model; a same-shape named type is ABI-identical (bindings may rename) | tests/fixtures/policy/named-type-swapped |
| `param-count-changed` | breaking | arity is part of the lowered signature | tests/fixtures/policy/param-count-changed |
| `param-renamed` | breaking | parameter names are part of the WIT contract and generated bindings | tests/fixtures/policy/param-renamed |
| `param-type-changed` | breaking | lowered representation changes | tests/fixtures/policy/param-type-changed |
| `record-field-type-changed` | breaking | field representation changes | tests/fixtures/policy/record-field-type-changed |
| `record-fields-changed` | breaking | records are exact: add/remove/reorder/rename changes layout | tests/fixtures/policy/record-fields-changed |
| `resource-method-added` | additive | existing handle users unaffected | tests/fixtures/policy/resource-method-added |
| `resource-method-changed` | breaking | method signature changed | tests/fixtures/policy/resource-method-changed |
| `resource-method-removed` | breaking | callers lose the method | tests/fixtures/policy/resource-method-removed |
| `result-changed` | breaking | lifted representation changes | tests/fixtures/policy/result-changed |
| `type-added` | additive | unreferenced by existing signatures | tests/fixtures/policy/type-added |
| `type-kind-changed` | breaking | e.g. record -> variant changes representation | tests/fixtures/policy/type-kind-changed |
| `type-removed` | breaking | consumers `use`-ing the type lose it | tests/fixtures/policy/type-removed |
| `variant-case-added` | breaking | receivers built against the old variant cannot decode the new case | tests/fixtures/policy/variant-case-added |
| `variant-cases-changed` | breaking | removed/renamed/reordered cases change discriminants | tests/fixtures/policy/variant-cases-changed |
| `variant-payload-changed` | breaking | case payload representation changes | tests/fixtures/policy/variant-payload-changed |
| `version-only` | compatible | identical structure; version strings never decide compatibility | tests/fixtures/policy/version-only |
| `world-added` | additive | new world; existing targets unaffected | tests/fixtures/policy/world-added |
| `world-export-added` | additive | hosts that ignore it are unaffected | tests/fixtures/policy/world-export-added |
| `world-export-changed` | breaking | exported item changed | tests/fixtures/policy/world-export-changed |
| `world-export-removed` | breaking | hosts lose an export they may call | tests/fixtures/policy/world-export-removed |
| `world-import-added` | breaking | hosts must now supply an extra import | tests/fixtures/policy/world-import-added |
| `world-import-changed` | breaking | hosts must supply a different import | tests/fixtures/policy/world-import-changed |
| `world-import-removed` | compatible | hosts may keep supplying it; nothing is lost | tests/fixtures/policy/world-import-removed |
| `world-removed` | breaking | components targeting it lose their contract | tests/fixtures/policy/world-removed |
