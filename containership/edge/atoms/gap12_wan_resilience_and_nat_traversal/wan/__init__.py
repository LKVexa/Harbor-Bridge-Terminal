"""GAP-12 v4.3.0 stdlib runtime: concrete traversal, network awareness, trust,
state, configuration, observability and release machinery built around the
v4.2.0 path state machine.  Nothing here imports ``pk_core``.

Every module states its own unsupported sub-cases in its docstring; the
checklist evaluator (``evidence/evaluate.py``) is the only place that decides
whether a checklist item is PASS, FAIL or NOT-EVIDENCED.
"""
