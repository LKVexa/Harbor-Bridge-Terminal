# Identity, equality and resolution (INV11-MC-03/04, 02-007)

## Canonical identifiers

| Entity | Form | Example |
|---|---|---|
| package | `ns:name[@ver]` | `wasi:io@0.2.0` |
| interface / world | `ns:name/item[@ver]` | `wasi:io/streams@0.2.0` |
| type | `<interface-or-world-id>#name` | `wasi:io/streams@0.2.0#input-stream` |
| function | `<interface-id>.name` | `demo:app/api@1.0.0.get` |
| method | `<type-id>.name` | `…#bucket.get` |
| inline world interface | `<world-id>/<import|export>/<name>` | |
| world item (diff paths) | `<world-id>:<import|export>:<key>` | |

Identifiers are case-sensitive ASCII kebab-case; there is no Unicode
normalization because WIT identifiers are ASCII-only. `unversioned(id)` strips
every `@version` for cross-release comparison. Limitation: a pre-release
identifier after a dot must start with a digit to stay unambiguous against a
member suffix (`@1.0.0-rc.1` works; `@1.0.0-alpha.beta` does not).

Interfaces and worlds share one namespace per package (`E-DUP-DECL`).

## Equality, identity, equivalence

* **Source identity** — file + span; never used for semantics.
* **Nominal identity** — the canonical id above. Resources are compared
  nominally (two resources are equal iff their version-less ids match).
* **Structural equivalence** — records, variants, enums, flags, aliases and
  anonymous types compare by structure (component-model value types are
  structural). A swap between two same-shape named types is reported as
  `named-type-swapped` (compatible).
* AST dataclass `==` ignores spans and docs.

## Resolution (resolver precedence)

1. declarations local to the interface/world;
2. names imported with `use` (the alias maps to the target's canonical type id);
3. interfaces of the same package;
4. top-level `use` aliases;
5. dependency packages (`deps/`), selected by explicit version or, without a
   version, only when exactly one version is available — otherwise
   `E-RES-PACKAGE` ("pin one"). There is no "latest wins".

Cycles among interface `use` edges and world `include` edges are reported
with the full cycle path (`E-RES-CYCLE`). Recursive value types are illegal in
WIT and are reported as `E-RES-TYPECYCLE`; resource handles break cycles.
Resolution is offline: the resolver never contacts a registry.

## Renames and moves

A rename of an interface, function, parameter, field or case is classified as
remove + add, i.e. **breaking** (`param-renamed` for parameters). Moving a type
between interfaces changes its nominal id; if it is referenced through an
alias of identical structure the change is `named-type-swapped`/compatible.
