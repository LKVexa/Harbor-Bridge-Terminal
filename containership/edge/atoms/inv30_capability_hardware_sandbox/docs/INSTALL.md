# Install (INV30-GAP-001, GAP-026)

## Model-only (no framework)
```
python -m venv .venv && . .venv/bin/activate      # Python >=3.10,<3.14
pip install .                                      # no third-party deps
python -c "import inv30_capability_hardware_sandbox as m; print(m.__version__)"
```
## Estate install (with pk_core, offline)
Place the package under `<estate>/pk/pk_components/` next to `pk_core` (4.0.x). No network is needed.
```
cd <estate>/pk
python -m pk_core list | grep INV-30
python -m unittest discover -s pk_components/inv30_capability_hardware_sandbox/tests -t .
python -m pk_components.inv30_capability_hardware_sandbox.ops env
```
An unsupported pk_core raises `DependencyIncompatible` (`DEPENDENCY_INCOMPATIBLE`) at component import; the
dependency-free model keeps working.
