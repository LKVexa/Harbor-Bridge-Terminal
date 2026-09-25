# Local contracts and trust model — UC-2.3.0

## Selected execution boundary

The operator, current OS account, Python, compiler/toolchain, mutable runtime root, bundled engines and hull are trusted. Cargo authors may supply source and manifest data, but this release does not establish a distinct authenticated author role or an isolated tenant boundary. Native engines are ordinary host processes, not guest VMs. There is no guest/VMM/device-broker entry point in this release.

| Surface / actor | Authority or asset | Implemented boundary | Still missing |
|---|---|---|---|
| Operator CLI | Load, run, unmount, local seal and recovery | OS account, portable-name checks, cooperative ship lock, selected transaction wrapper | Per-action authorization, independent review/approval |
| Cargo author / archive input | Source bytes and declarations | Existing ZIP/path admission; new strict ship JSON parsing | Native build sandbox; authenticated provenance |
| Ship management process | Registry, metadata, journals, local identities | Managed-resource allowlist, verified backups, generation checks | Protection from an attacker with workspace write access |
| Engine / hull | Native execution and local picture state | Existing native verdict checks; bounded ship launch helper where integrated | Host isolation, global quotas, all-adapter supervision |
| File/graph/object caller | Declarative graph and bounded object bytes | Exact graph fields, digest/edge checks, bounded atomic object publication | Automatic build graph integration; signing authority |
| Workflow input | 96,000 original task statements | Preserved source ZIP hash and separate line-by-line accounting | Task execution engine or automatic engineering-completion oracle |
| Guest, tenant, broker, remote worker | No implemented service | Requests requiring hypervisor isolation refuse | Guest ABI, identity, IPC, broker, networking, federation |

Secrets and signing keys must not be added to cargo, state pictures, command arguments, test logs or the task ledger. This release has no secret storage/redaction service. Host administrators and concurrent malicious filesystem writers are outside the selected trust boundary. Display names, seals and witness values do not grant authority.

## Request schema: UC/CONTROL_REQUEST/1

Exactly these fields are required; unknown fields or incompatible versions are refused:

```json
{"schema":"UC/CONTROL_REQUEST/1","operation":"invoke","workload":"vm_small","generation":1,"isolation":"host-process","capabilities":["native-interpretation"]}
```

Operations in the vocabulary are inspect, invoke, boot, stop, snapshot and restore. `contract-check` only validates; it never executes them. Only local inspect/invoke equivalents exist. Boot/stop/snapshot/restore validation reports unimplemented and returns 3. A hypervisor request returns 3 before execution or snapshot preparation; no host-process fallback is permitted. This is compatibility validation, not authorization.

A workload name uses the inherited portable-name rules. Generation is an exact integer from 1 through 2^63-1, not a Boolean. The capability list is unique, at most 16 strings, and currently limited to inspect/native-interpretation/metadata-witness. Capability claims cannot establish an unavailable backend.

## JSON and canonical bytes

Every ship-owned JSON import uses `strictjson`. Duplicate keys (including escaped duplicates), NaN/Infinity, exponent overflow, invalid UTF-8/scalars, over-deep or oversized inputs are refused before downstream conversion. Legacy positive finite floats are permitted by strict reads where their own schema allows them. `UC-CJSON/1` for new graph, request and event values is integer-only, sorts string keys, emits compact UTF-8 and preserves code points. It is intentionally not RFC 8785 and performs no lossy Unicode normalization. Existing seal byte conventions remain unchanged. General migration/downgrade conversion for old artifacts is not implemented; unknown new contract versions are refused instead.

## Local identity and observed state

`_runs/control/state.sqlite` uses a versioned schema, SQLite transactions and FULL synchronous mode. UUID identity survives replacement/unload/recovery; names only locate it. Each load/unload invalidates older generations, including failed attempts; pending recovery advances generation again so an old token cannot publish after restoration. An operation token binds UUID, generation and operation ID. Finishing with an old token refuses.

The transition model distinguishes admitted, staged, built, booting, ready, running, draining, stopped, failed and quarantined. It stores desired separately from observed state. Existing BERTH.json presence initially means staged only. The CLI completion wrapper cannot assert ready, booting or running. The standalone transition model is not a hardware-observed readiness service, and its string evidence references are not an independent verifier. No full reconciliation loop is present.

## Graph and object scope

`UC/ARTIFACT_GRAPH/1` accepts explicit typed nodes with id/kind/sha256/dependencies. Kahn ordering rejects cycles and unknown edges without recursion; `graph affected` returns the changed nodes and exactly their transitive descendants. Node digests bind data, not signature authority. Graph lists are not automatically generated from the compiler or linked runtime. The local `_runs/objects` store atomically publishes bounded blobs addressed by SHA-256 and verifies reads; a corrupt existing object is refused rather than silently replaced. No GC, remote replication, image signature enrollment or automatic build consumption is implied.

## Selected defensive limits

These are development safety defaults chosen to bound the new operations, not performance measurements or universal workload requirements. Changing them requires review and repeated valid/boundary/negative tests.

| Mechanism | Default bound | Selection rationale / caveat |
|---|---:|---|
| Ship JSON document | 32 MiB; depth 64; integer literal 1,024 digits | Large enough for delivered inventories; caps parsing input, not total process RAM |
| Canonical event payload | 8 KiB | Small operation records, no embedded cargo |
| Local event/workload rows | 100,000 / 10,000 | Stops uncontrolled metadata growth; no automatic pruning |
| Artifact DAG | 10,000 nodes / 100,000 edges | Bounded local graph inspection; not an infinite build index |
| Single object / object store | 64 MiB / 1 GiB | Small local artifact baseline; no global tenant quota |
| Snapshot | 50,000 entries; 512 MiB total | Development workspaces only; larger mutations refuse |
| Managed retained transactions | 256 transactions / 2 GiB admission estimate | Retain recoverable evidence rather than deleting it |
| Minimum free-space cushion | 64 MiB | Preflight reserve estimate, not filesystem allocation guarantee |
| Helper output | 1 MiB combined trigger, at most 1 MiB retained tail per stream | Over-limit child group terminates; imported adapters not universally intercepted |
| Helper timeout | Per caller, maximum 7,200 s | Positive finite bound; deadline failure is explicit |
| Buffered command stdout | 4 Mi characters | Withheld until managed commit; excessive reporting aborts |
| Workflow record | 64 KiB per line, exactly 96,000 records | Reject truncated/oversized/missing task records |

`supervisor.run` returns timeout 124 or output-limit 125, records actual native exit otherwise, and performs same-process-group cleanup on POSIX. The Windows taskkill branch is best-effort and was not natively tested. Parent death, deliberately escaped groups, resource quotas and hostile process isolation remain separate requirements.

## Assurance classes

Byte integrity, signature authenticity, metadata-witness agreement, application semantics and host isolation are distinct. `capabilities` lists these separately and reports absent capabilities. Neither a graph hash, a local seal, a passing witness nor a workflow accounting result promotes application correctness or isolation. This trust model is a development artifact, not an independent security assessment.

## Primary API references consulted during implementation

The following support the API choices, not claims of platform certification: Python 3.13 JSON documentation (duplicate-pair hooks and strict numeric handling), Python 3.13 subprocess documentation (sessions, process control and output capture), and SQLite's atomic-commit design. No third-party upstream runtime was installed by citing these references.

- https://docs.python.org/3.13/library/json.html
- https://docs.python.org/3.13/library/subprocess.html
- https://www.sqlite.org/atomiccommit.html
