# Third-party notices: INV-69 v4.3.0

**Runtime.** The runtime uses only the Python standard library (PSF-2.0, part of the interpreter).

**Parts copied from the yard.** None. This pass was a junkyard chop-shop job run in degraded mode:
- The yard office on this computer holds only work orders. There is no map, ledger or engine.
- The sibling INV-44 and INV-31 work orders were read as pattern references only: the fail-closed
  release gate with a falsifier, the declared skip lanes, and the "build the desk, bind nobody"
  approval rule.
- No code or text was copied from them.

**Test-only dependency.** `jsonschema==4.26.0` (MIT), used by the schema-conformance lane. It is not
redistributed.

**Licence of this component.** Undecided. `pyproject.toml` records this, and the owner must choose.
