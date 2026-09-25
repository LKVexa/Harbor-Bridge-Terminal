# 04 — Master prompt and workflow

The master contract is the attached `GAP07_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST_v5.0.0.md`. A copy is
bundled in the package at `docs/`. The work followed its recommended closure sequence: P0 crypto/trust (1–7, 12),
then P0 enforcement (8–11), then external packaging (44–48), P1 (13–28) and P2 (29–43), then release evidence.

Governing rules added by the merge:
(a) every refusal carries a catalogued code;
(b) nothing may return runnable except `AdmissionController.admit` → `allow`;
(c) all signed objects use distinct `ld_encode` domains;
(d) every item that cannot be closed in-package is traced as `blocked` with its owner or dependency. It is never
claimed as done.
