# UC-2.7.0 Local Control Protocol Specification

## Versioning
Control requests use explicit schema identifiers. Unknown incompatible schemas are rejected before mutation. Release identity is `UC-2.7.0`.

## Command classes
- **Inspection:** status, berths, capabilities, doctor, lifecycle, workflow/master-workflow status, TIFF/1-bit/pixel inspection, platform status.
- **Managed mutation:** build, load, unload, run, fabric mutation, pixel paint/checkpoint, 1-bit TIFF put, reseal.
- **Blocked classes:** public remote execution, multi-host consensus/federation, production signing authority, bootable hypervisor guest lifecycle.

## Mutation invariants
Managed mutation requires the repository lock, clean/pending transaction handling as applicable, contained canonical paths, generation validation where exposed, explicit bounded inputs and deterministic error reporting. A write never earns PASS merely because it returned exit code zero; relevant verification evidence is separate.

## VWS boundary
The VWS terminal is loopback-authenticated, read-only by default and permits only allowlisted `ship` subcommands. Control mode does not create authority for commands excluded by policy.

## Master-series traceability
Task IDs are `Cnnn.mmm.Tnn`. Every attached source record remains immutable in its source ZIP. Candidate disposition is carried separately in `masterflow/ledger.jsonl.gz`.
