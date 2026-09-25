# Unikernel Containership -- what does not work, and why

Release UC-2.1.3. An undisclosed gap is the defect; a disclosed one is scope.

## `UC-01` ship integrity -- `VERIFIED`

every delivered byte hashed; MANIFEST inventory matches disk

*the seal gates run after sealing; VERIFIED post-seal by the launcher*

## `UC-15` hull cargo: a container broken up is still that container -- `IMPLEMENTED`

studio containers carried in berths re-assemble from the slots, verify with the hull's own seal verifier, mount in the hull with their own pictures and tick on them (no loaded berth carries a studio container; B11 SKIPPED everywhere)

## `UC-20` standalone (materialised) berths -- `SPECIFIED`

copy the five DF containers into a berth so it can sail alone

## `UC-21` cargo interpretation -- `BLOCKED_CAPABILITY_ABSENT`

executing arbitrary cargo rather than witnessing it

## `UC-24` CARGO.pal as a picture -- `NOT_CLAIMED`

a cargo manifest of thousands of rows does not fit a 2x2-tile fabric image; it is witnessed from its seal, not ticked

## `UC-25` node engines executing their own pictures -- `NOT_CLAIMED`

the Small/Medium/Xtra_Large engines have no device fabric of their own to persist; their pictures are read and written by the ship around a native run (the hull face's picture is executed by the VM itself)

## `UC-22` cross-machine federation -- `BLOCKED`

NETWORK=deny; local processes on one host

## `UC-26` hosts without a C toolchain (Windows) -- `SKIPPED`

the three C engines and the hull's runner cannot be built there: BUILD says BUILT_HOST_LIMITED, U2/B7/U7 and the hull-face parts of B10/B11 are SKIPPED with the reason, the QUORUM engine carries the witnesses alone, the hull is compile-only (faces built, pictures made, hull cargo mounted); a C toolchain with make lifts it

## `UC-23` physical quantum outputs -- `BLOCKED_EXTERNAL_AUTHORITY`

PHYSICAL_PARALLEL_QPU_EXECUTION, PHYSICAL_DISTRIBUTED_QPU_EXECUTION

## Inherited

* Every VM's own blockers, verbatim, through the DF containers (`hold/DF_*.zip` -> `reports/DF_BLOCKED_REGISTER.md` in each).
* The hull's own non-claims (`hull/README.md`, *What it does not claim*): a verified signature is not a provisioned trust chain; compiling is not executing on a host without a C compiler.
* The sort policy places by measured needs and complexity; it does not read meaning. A project whose scripts are mostly small JSON evidence files lands mostly on N_SMALL, and the ledger says so.
