# Third-party notices — INV-55 4.3.0

## Runtime dependencies
None beyond the CPython standard library (Python Software Foundation License). Modules used include `ssl`, `urllib`, `json`, `hmac`, `hashlib`, `threading`, `dataclasses`, `random`, `secrets`, `re`, `base64`, `fnmatch`.

CPython's `ssl` module links the platform OpenSSL, whose license applies to the host distribution, not to this repository.

## Test dependencies
- `jsonschema` (MIT License), pinned in `requirements-test.txt`, used by `tests/test_schemas_fixtures.py`. Not a runtime dependency (`pyproject.toml` declares none).
- Tests otherwise use `unittest`; `tests/test_vault_adapter.py` invokes the system `openssl` binary to mint a test CA.

## Optional / external
- `pk_core` (conformance tooling) — required by `contract.py`/`component.py`; not bundled; license not determined here.
- HashiCorp Vault — external server, not distributed with this package.
