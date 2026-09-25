# UC-2.7.0 Supply-Chain Threat Model

The release binds delivered files with SHA-256 inventories and retains original workflow archives byte-for-byte. This detects accidental or malicious byte changes after sealing but does not establish independent publisher identity.

## Threats
- tampered input archive or substituted dependency;
- ambiguous/colliding archive path;
- generated artifact not derived from the recorded source;
- stale evidence reused across a changed dependency;
- compromised local build toolchain;
- unsigned release copied from an untrusted channel.

## Current controls
Strict archive staging, closed-world manifests, typed artifact dependency graphs, content-addressed objects, provenance records, source hashes, release resealing and independent file-inventory verification within the candidate.

## Unmet authority controls
No HSM/offline root, externally anchored transparency log, trusted builder quorum, independent signature authority or network vulnerability feed is bundled. Artifact signing/attestation therefore remains blocked rather than promoted.
