# Release process: CI gates, SBOM, signing and verification (M03, M07, M08)

## Gate status at any time

```text
python tools/release.py preflight
```

prints one row per release gate (round trip, falsifiers, manifest, schemas, lock pins, genuine
VERIFY/2 evidence, release SBOM, LICENSE, SECURITY.md, signing public key) and
`RELEASE-GRADE: YES|NO`. Release packaging and signing refuse to run while any gate is open.

## CI (M03)

| Workflow | Trigger | Privilege | Purpose |
|---|---|---|---|
| `offline-integrity.yml` | every push / PR, incl. forks | none, no secrets | offline suite on Windows+Linux × Python 3.10/3.13, schemas, lock, SBOM |
| `owner-toolchain-verify.yml` | push to `main`, `v*` tags, manual dispatch | `owner-toolchain` environment on a self-hosted runner holding the approved roots | authenticate → full verifier → evidence acceptance → generated-file policy → retain evidence |

The privileged workflow has no `pull_request` / `pull_request_target` trigger, so untrusted code
never runs with access to the runner's toolchains. Owner configuration outside the repository
(record it as release-control evidence when done):

- create environment `owner-toolchain` with required reviewers and a `main`/`v*` deployment rule;
- set repository variables `LCTL161_ROOT` / `LCTL160_ROOT` to the runner-local roots;
- register the self-hosted runner with label `lctl-owner-toolchains`;
- make both `offline-integrity` and `owner-toolchain-verify / full-verify` required checks on
  `main`, and require review for `.github/workflows/`, `toolchains/`, `tools/toolchain_trust.py`,
  `tools/verify.py`, `tools/release.py` (CODEOWNERS with real owner handles);
- pin third-party actions to reviewed commit SHAs;
- document the emergency-bypass procedure (auditable admin approval only).

**Generated-file policy.** Default is *verification-only*: after the run, any diff under
`canonical/` or `evidence/lctl160/` fails the job. *release-generation* (tags / explicit
dispatch) may regenerate outputs; the release job then records its run ID in the provenance.
A canonical byte change under an unchanged, approved lock is a determinism incident — stop and
investigate (M02.6); a change caused by an approved toolchain change is a payload transition
that must be documented, never silently accepted.

## SBOM (M07)

`python tools/sbom.py` writes `sbom/iOS735_LCTL-<VERSION>.spdx.json` (SPDX 2.3) from `VERSION`,
`LICENSE` and `toolchains/LOCK.json`. It refuses to produce a release SBOM while either pin is
unapproved; `--draft` produces a candidate with the unpinned hashes and unresolved licences
recorded as `NOASSERTION` (never invented). `--check` validates structure, absence of local
paths/credentials, and consistency with VERSION, LICENSE and the lock. The Python tooling has no
third-party dependencies; `jsonschema` is optional (only for `schema_check.py --strict`). No
vulnerability-free claim is made for proprietary components without public identifiers;
findings for Java or LCTL route through `SECURITY.md` once it exists.

## Packaging, provenance, signing (M08)

Order (after every other gate passes):

```text
python tools/sbom.py
python tools/manifest.py --write && python tools/manifest.py
python tools/release.py package --out ../dist
python tools/release.py sign --provenance ../dist/iOS735_LCTL_v<V>.provenance.json --key <owner key OUTSIDE the repo>
```

- The ZIP is deterministic (sorted entries, fixed 1980-01-01 timestamps, normalised modes, only
  manifest-listed files + the manifest) — two builds of the same tree have the same digest.
- The provenance is an in-toto v1 Statement with an SLSA v1 predicate: subject = archive name +
  SHA-256; resolved dependencies = git commit, `MANIFEST.sha256`, `toolchains/LOCK.json`,
  `evidence/VERIFY.json` (+ its schema), the SBOM, and both observed JAR digests; builder and
  run IDs from CI.
- Signing is Ed25519 over the provenance (`openssl pkeyutl -rawin`). It refuses: candidate
  provenance, a key inside the repository, a subject that does not match the archive on disk,
  and any open preflight gate (so a failed full-verifier build can never be signed).
- The owner signing identity is **not yet created**. When it is: keep the private key in an
  HSM/KMS or offline store, publish the public key as `provenance/release-signing-public.pem`
  *and* through a second authenticated channel, name authorised signers, and document rotation
  and revocation here. CI signing (if chosen) must run only in a protected release environment.

## Verifying a release (end users)

```text
sha256sum -c iOS735_LCTL_v<V>.zip.sha256
python tools/release.py verify --archive iOS735_LCTL_v<V>.zip \
    --provenance iOS735_LCTL_v<V>.provenance.json --sig iOS735_LCTL_v<V>.provenance.sig \
    --pubkey release-signing-public.pem
```

`verify` checks the signature with the public key only, checks the archive digest and name
against the signed subject, extracts safely, runs the extracted `MANIFEST.sha256`, and checks
the manifest digest against the provenance. Any failure means: **do not use the artifact**.
(Without Python: `openssl pkeyutl -verify -rawin -pubin -inkey release-signing-public.pem -in
<provenance> -sigfile <sig>` and compare the subject digest to `sha256sum` of the ZIP.)
