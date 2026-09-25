# Constraint precedence (MC-008)

Implemented in `precedence.py`; resolution is recorded in the node's explanation (`service.explain`).

1. Class order: **security > residency > availability > slo > cost**.
2. Within a class, `hard: true` beats soft.
3. Remaining ties: smallest canonical-JSON value (stable and order-independent).
4. Two hard constraints of the same class with different values on the same attribute are **rejected** (E0001) —
   the plane never guesses between hard requirements.
