# Unikernel Containership -- capability ledger

Release UC-2.1.3. Rule: No item is operational because its source file exists. Operational status requires native executable evidence satisfying that item's promotion gate.

Distribution: BLOCKED 1, BLOCKED_CAPABILITY_ABSENT 1, BLOCKED_EXTERNAL_AUTHORITY 1, IMPLEMENTED 1, NOT_CLAIMED 2, OPERATIONAL 15, SKIPPED 1, SPECIFIED 1, VERIFIED 1. `operational_without_evidence`: []; `operational_without_passing_gate`: [].

| item | title | status | statement | gates |
|---|---|---|---|---|
| `UC-01` | ship integrity | `VERIFIED` | every delivered byte hashed; MANIFEST inventory matches disk | `U0.1`=SKIPPED, `U0.2`=SKIPPED |
| `UC-02` | hull carried unchanged | `OPERATIONAL` | hull/ equals the pinned digest of PA Language Studio 2.0.0 | `U0.3`=PASS |
| `UC-03` | hold carried unchanged | `OPERATIONAL` | the five DF containers equal their pinned digests and DF_SHA256SUMS.txt | `U0.4`=PASS |
| `UC-04` | schemas and citations | `OPERATIONAL` | every ship artifact validates; every ledger citation resolves | `U0.5`=PASS, `U0.6`=PASS |
| `UC-05` | sort policy | `OPERATIONAL` | shipped policy equals the code; documented placements hold | `U1`=PASS |
| `UC-06` | engines | `OPERATIONAL` | extracted from the hold by digest, own sums re-checked, built, bound | `U2`=PASS |
| `UC-07` | hull installed | `OPERATIONAL` | the studio installs from the Large engine's VM package into _studio/ | `U3`=PASS |
| `UC-08` | the hull's own verifier | `OPERATIONAL` | hull/verify_studio.py: 135 checks pass against the Large engine (incl. the reversible TIFF fabric) | `U4`=PASS |
| `UC-09` | bill of lading | `OPERATIONAL` | equals a fresh scan of berths/; never appended | `U5`=PASS |
| `UC-10` | loading: break up + sort + own scaffold | `OPERATIONAL` | 6 berths loaded; each berth's battery B0-B11 passes (hashes, ledger re-derived, bundles sealed, hull face source, witnesses on the engines, studio answer, runnable cargo, the six .tif fabrics present and reversible, a tick executes the pictures, hull cargo where carried) | `U6.sub_mssl_to_lctlc`=PASS, `U6.sub_pa21_language_studio`=PASS, `U6.vm_large`=PASS, `U6.vm_medium`=PASS, `U6.vm_small`=PASS, `U6.vm_xtra_large`=PASS |
| `UC-11` | studio test over berths | `OPERATIONAL` | every berth container answers its declared expectation | `U7`=PASS |
| `UC-12` | the .tif fabric codec | `OPERATIONAL` | the hull's PA21FABTIF/1 codec is present and a synthetic container fabric survives the round trip byte for byte | `U8`=PASS |
| `UC-13` | every container's own .tif fabric | `OPERATIONAL` | in every berth, the four node containers, the fabric container and the hull face each have their own reversible .tif rooted at a sealed genesis (B9 in each of the 6 berth batteries) | `U6.sub_mssl_to_lctlc`=PASS, `U6.sub_pa21_language_studio`=PASS, `U6.vm_large`=PASS, `U6.vm_medium`=PASS, `U6.vm_small`=PASS, `U6.vm_xtra_large`=PASS |
| `UC-14` | run on the .tif fabric | `OPERATIONAL` | a tick reads every picture, executes it on its engine (the hull face by the hull's VM), writes it back; the four agree with the CPython reference for the state read; painted cells are executed as painted and reported (B10 in each berth battery) | `U6.sub_mssl_to_lctlc`=PASS, `U6.sub_pa21_language_studio`=PASS, `U6.vm_large`=PASS, `U6.vm_medium`=PASS, `U6.vm_small`=PASS, `U6.vm_xtra_large`=PASS |
| `UC-15` | hull cargo: a container broken up is still that container | `IMPLEMENTED` | studio containers carried in berths re-assemble from the slots, verify with the hull's own seal verifier, mount in the hull with their own pictures and tick on them (no loaded berth carries a studio container; B11 SKIPPED everywhere) | - |
| `UC-20` | standalone (materialised) berths | `SPECIFIED` | copy the five DF containers into a berth so it can sail alone | - |
| `UC-21` | cargo interpretation | `BLOCKED_CAPABILITY_ABSENT` | executing arbitrary cargo rather than witnessing it | - |
| `UC-24` | CARGO.pal as a picture | `NOT_CLAIMED` | a cargo manifest of thousands of rows does not fit a 2x2-tile fabric image; it is witnessed from its seal, not ticked | - |
| `UC-25` | node engines executing their own pictures | `NOT_CLAIMED` | the Small/Medium/Xtra_Large engines have no device fabric of their own to persist; their pictures are read and written by the ship around a native run (the hull face's picture is executed by the VM itself) | - |
| `UC-22` | cross-machine federation | `BLOCKED` | NETWORK=deny; local processes on one host | - |
| `UC-26` | hosts without a C toolchain (Windows) | `SKIPPED` | the three C engines and the hull's runner cannot be built there: BUILD says BUILT_HOST_LIMITED, U2/B7/U7 and the hull-face parts of B10/B11 are SKIPPED with the reason, the QUORUM engine carries the witnesses alone, the hull is compile-only (faces built, pictures made, hull cargo mounted); a C toolchain with make lifts it | - |
| `UC-28` | delivered paths fit Windows Explorer | `OPERATIONAL` | no delivered path exceeds 140 characters, so the archive extracts through Explorer's own zip extractor (which is not long-path aware) into the folder it names after the archive; cargo and mirrors past the budget are stored under aliases and answer to their original names everywhere | - |
| `UC-27` | hosts without sh / fork / a UTF-8 console | `OPERATIONAL` | the QUORUM column verifier is invoked directly through java (lctl_column_verify=JVM_DIRECT); multi-process profiles run multi_thread_deterministic and say so; the ship's Python runs in UTF-8 mode -- each adaptation recorded in the BUILD/VERIFY/tick records | - |
| `UC-23` | physical quantum outputs | `BLOCKED_EXTERNAL_AUTHORITY` | PHYSICAL_PARALLEL_QPU_EXECUTION, PHYSICAL_DISTRIBUTED_QPU_EXECUTION | - |
