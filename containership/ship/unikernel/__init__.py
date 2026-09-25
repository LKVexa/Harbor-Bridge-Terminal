"""unikernel -- the Unikernel Containership ship layer.

The ship (UC) combines two things the user already has:

* the **hull**: PA Language Studio 2.0.0, the hollow containership scaffold --
  a scriptable installer/runtime for COLUMNED LCTL containers built on the
  BOTTLE ROCKET 4.7.0 VM and bound to a PA21 delivery (`hull/`, UC-patched TIFF codec since 2.5.0),
  whose 2.0.0 fabric is a picture you can run: a container's device fabric
  persisted as a tiled, multi-page .tif, read back as the state of the next run;
* the **hold**: the DF scaffold -- the four DF node containers and DF_Fabric
  (`hold/`, unchanged), whose four VMs are the ship's *engines*.

What the ship adds is the loading discipline the user described: when a
product or project (a VM or a sub-system) is added to the ship, it is broken up
**script by script**, every script is **sorted into one of the four nodes by
its measured needs and complexity**, and the project is given **its own blank
four-node-plus-fabric scaffold** -- a *berth* -- to hold the sorted cargo, its
declarations (as PA-LCTL bundles), its seals, and its studio face. Every berth
pulls from the same engines in the hold; nothing in a berth duplicates a VM.

Since UC-2.1.1 the ship runs on the .tif distributed fabric: every container of every berth --
the four node containers, the fabric container and the hull face -- gets its own
.tif fabric image (`tif_fabric.py`); a RUN is a tick that reads every picture,
executes it on its engine, and writes it back as a new frame. UC-2.1.2 sails on
limited hosts (Windows without a C toolchain, no `sh`, no `fork`, a cp1252
console) and says so: `host.py` records every adaptation, and every gate that
cannot be observed there is SKIPPED with the reason, never failed or passed.

Governing rule (inherited from the corpora, the DF containers and the studio):

    No item is operational because its source file exists. Operational status
    requires native executable evidence satisfying that item's promotion gate.

Vocabulary: ship · hull · hold · engine · berth · slot · cargo · manifest
(the sort ledger) · bill of lading (the ship registry). Nothing here is
quantum, physical or networked: NETWORK=deny, BACKEND=none, every engine is a
local classical VM, cross-machine anything is BLOCKED.
"""

from __future__ import annotations

UC_RELEASE = "UC-2.8.0"
UC_NAME = "Unikernel Containership"
DF_RELEASE_EXPECTED = "DF-PA21.2-1.0.0"
STUDIO_VERSION_EXPECTED = "2.0.0"
LANGUAGE = "PA-LCTL"

NODE_IDS = ("N_SMALL", "N_MEDIUM", "N_LARGE", "N_XLARGE")
NODE_CONTAINER = {"N_SMALL": "DF_Small", "N_MEDIUM": "DF_Medium",
                  "N_LARGE": "DF_Large", "N_XLARGE": "DF_Xtra_Large"}
FABRIC_CONTAINER = "DF_Fabric"
SLOTS = ("DF_Small", "DF_Medium", "DF_Large", "DF_Xtra_Large", "DF_Fabric")
BERTH_KINDS = ("vm", "subsystem")

#: the smallest node bound: 84 rows per lowering (BOTTLE ROCKET 256-instruction ceiling)
SEGMENT_ROWS = 84
#: BERTH.pal must fit one lowering on every engine, including the hull's runtime -- and, since
#: UC-2.1.1, the hull face's field rows too (3*rows + 15 <= 256) and two declaration tiles (116)
BERTH_PAL_MAX_ROWS = 80

STATUS_VOCABULARY = ("BLOCKED", "SPECIFIED", "SCAFFOLDED", "IMPLEMENTED", "VERIFIED",
                     "OPERATIONAL", "QUALIFIED", "BLOCKED_EXTERNAL_AUTHORITY",
                     "BLOCKED_CAPABILITY_ABSENT", "SKIPPED", "NOT_CLAIMED")


def face_container_name(berth: str) -> str:
    """The berth's hull-face container name: `berth_<name>`, or -- when that would exceed the
    studio's 64-character container-name limit -- `berth_<first 45>_<8 hex of sha256(name)>`,
    deterministic, recorded in BERTH.json#studio_face.container_name."""
    import hashlib as _h
    n = f"berth_{berth}"
    if len(n) <= 64:
        return n
    return f"berth_{berth[:45]}_{_h.sha256(berth.encode('utf-8')).hexdigest()[:8]}"


class ShipError(RuntimeError):
    def __init__(self, message: str, detail=None):
        super().__init__(message)
        self.detail = dict(detail or {})

    def as_dict(self):
        return {"error": str(self), "detail": self.detail}


class Refusal(ShipError):
    """The ship refuses; nothing was done for the refused part."""
