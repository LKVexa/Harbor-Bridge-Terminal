"""INV-13 production host layer (v4.3.0).

Dependency-free (stdlib only) implementations of the MC-001..MC-032 host
components that can be built and objectively tested without a Wasm engine.
Components whose closure needs an external engine, fleet, or organisation
are shipped as enforced interfaces with their gap recorded in
``COMPONENT_STATUS.json`` -- never as mocks presented as production.
"""
