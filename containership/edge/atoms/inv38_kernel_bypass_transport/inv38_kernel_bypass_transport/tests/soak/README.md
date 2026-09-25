# Soak tests (INV-38-C088)
`test_model_soak.py` runs a long model loop asserting no leak / counter drift /
stale-key accumulation. Fleet-scale soak on real hardware is BLOCKED.
