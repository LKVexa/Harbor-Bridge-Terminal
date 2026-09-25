# ADR-0001: Close what INV-16 owns; surrogate what it does not

**Status:** accepted (4.3.0). **Context:** 42 closure items; many require sibling components (INV-15/10/11/17/20),
`pk_core`, a compiler backend and owner decisions that are not in this archive.
**Decision:** implement and prove every INV-16-owned behaviour locally; model each sibling as a *surrogate*
fixture behind the interface INV-16 consumes, flagged `SURROGATE = True`; never record PASS for an item whose
Definition of Done requires the real sibling. **Consequence:** integration items are PARTIAL until the real
fixture replaces the surrogate and the same tests pass.
