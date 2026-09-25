# Immutable / config / state boundary (INV-38-C032)

Immutable artifacts (source/package, backend libs, schema & policy bundles) are
content-addressed and never mutated at runtime. Mutable configuration and runtime
state are separate classes with distinct paths, permissions and lifecycles
(`config/layout.schema.json`). Credentials live in neither. Startup drift checks
detect artifact/schema/config/state mismatch before activation. Tests:
`tests/test_config_layout.py`. **Status:** `DONE`.
