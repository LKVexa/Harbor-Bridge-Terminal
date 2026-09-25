"""PA21 Language Studio -- a scriptable installer and runtime for COLUMNED
LCTL applications running against a PA21.31 delivery.

Scripting surface:

    from pa21studio import Studio

    s = Studio()                                  # default root, or Studio(root)
    s.plan_install(vm_source="Large.zip")         # what an install would do
    s.install(vm_source="Large.zip", pa21_root="…/PA21.2")
    s.new_app("pricing", template="loop", requires_operational=[181, 262])
    s.build_app("pricing")
    s.run_app("pricing")                          # -> registers, status, trap
    s.verify_app("pricing")
    s.uninstall()

Every method returns a JSON-serialisable dict and raises `StudioError` with a
`detail` mapping when it refuses. Nothing writes outside the studio root, and
nothing is reported as installed until a canonical application has been
compiled from source and executed on the runtime that was just built.
"""

from .core import (APP_MANIFEST, MANIFEST_NAME, SCHEMA, VERSION, Studio,
                   StudioError, default_root, utc_now)
from . import ledger, lctlc, probe

__all__ = ["Studio", "StudioError", "VERSION", "SCHEMA", "MANIFEST_NAME",
           "APP_MANIFEST", "default_root", "utc_now", "ledger", "lctlc",
           "probe"]
__version__ = VERSION
