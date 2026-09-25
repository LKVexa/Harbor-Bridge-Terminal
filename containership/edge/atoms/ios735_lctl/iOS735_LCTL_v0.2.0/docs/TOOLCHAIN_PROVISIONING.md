# Toolchain provisioning (M01) and trust lock (M04)

The full verifier needs two external toolchains that are **not** part of this repository:

| Role | Version | Required file (relative to its root) |
|---|---|---|
| `lctl161` compiler | LCTL 1.6.1-RC1 | `runtime/bin/lctl-hyperfederated.jar` |
| `lctl160` runtime/verifier | LCTL 1.6.0-RC1 | `runtime/bin/lctl-runtime.jar` |

Prerequisites: Python 3.10+, Java 21+ (any vendor unless the lock pins one), ~1 GB free disk,
and authorised access to both toolchains. The root folder names are *not* a security boundary;
the SHA-256 pins in `toolchains/LOCK.json` are.

## Redistribution status — owner decision pending

Whether the toolchains may be bundled, attached to releases, mirrored privately, or only
retrieved from an owner-controlled source has **not** been decided. Until it is, the only
authorised mode is **manual/offline**: an operator who already holds approved copies points the
verifier at them. Nothing in this repository downloads, mirrors or redistributes the toolchains,
and no credentials are stored here. Record the decision (licence terms, export/platform limits,
who may approve a new build) in this section when it is made.

## Resolving the roots

In order of precedence: `--lctl161 PATH` / `--lctl160 PATH`, then the `LCTL161` / `LCTL160`
environment variables, then the first sibling folder matching `LCTL_1.6.1_RC1_*` /
`LCTL_1.6.0_RC1_*` next to the repository. Paths are resolved to absolute paths and may
contain spaces.

```text
python tools/toolchain_trust.py --lctl161 "<LCTL_1.6.1 root>" --lctl160 "<LCTL_1.6.0 root>"   # authenticate only
python tools/verify.py         --lctl161 "<LCTL_1.6.1 root>" --lctl160 "<LCTL_1.6.0 root>"   # full run
```

`tools/verify.py` calls the same authentication first and never reaches `java -jar` if it
fails. The JAR hashes are re-checked after the run; a JAR that changed mid-run fails the gate.

### Stable exit codes

| Code | Meaning |
|---|---|
| 0 | trusted |
| 10 | lock missing or malformed |
| 11 | unsupported lock schema |
| 12 | toolchain root or JAR missing / not a regular file |
| 13 | untrusted: pin pending, revoked, size or hash mismatch, wrong version marker |
| 14 | Java missing, unparseable, below 21, or outside the vendor/version policy |
| 15 | unsafe or failed archive extraction |
| 16 | access/authentication failure (reserved for an owner-approved retrieval mode) |

## Filling the lock (owner action)

1. Obtain each JAR's SHA-256 (and size, and signature material if the publisher signs) from the
   toolchain owner **through an authenticated channel independent of the local copy**.
2. In `toolchains/LOCK.json` set `sha256`, `size`, `status: "APPROVED"`, and
   `approval: {"approved_by": ..., "approved_on": ..., "change_ref": ...}`; bump `lock_version`.
3. Optionally add `version_marker` (a file inside the root that must contain the version string)
   and Java `max_major` / `allowed_vendors`.
4. `python tools/toolchain_trust.py --check-lock`, then run the full verifier (M02) and
   regenerate the SBOM (`python tools/sbom.py`).
5. Every lock change needs review (two-person approval recommended), a change note in
   `CHANGELOG.md`, and a fresh full verification. Old locks stay in history for audit.

## Archive-based provisioning

If the owner distributes the toolchains as archives, `toolchain_trust.safe_extract(archive,
dest, expected_sha256)` extracts them safely: it checks the archive digest first, rejects
absolute paths, `..`, drive letters, symlinks and device entries, extracts into a temporary
sibling and renames into place only when complete (an interrupted run leaves nothing that looks
valid; concurrent jobs cannot corrupt a shared cache). JAR pins are still checked on every run,
cache hit or not. Logs pass through `redact()` so signed URLs and bearer tokens never appear.

## When the toolchains are unavailable

Run `python -m unittest discover -s tests -v`. That proves offline integrity (round trip,
falsifiers, determinism, manifest, schemas, trust-policy negatives, and the verifier's
transactional behaviour against a **test-only simulator**). It is **not** a substitute for a
genuine owner-toolchain run, and simulator output is never release evidence.
