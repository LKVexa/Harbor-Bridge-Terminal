# Owner decisions still required

These items cannot be closed by engineering work: they need the repository owner (and legal or
security owners where named). Nothing here has been invented or assumed. The release gate
(`python tools/release.py preflight`) keeps each one visibly OPEN until it is done, and rejects
placeholder text (`TODO`, `TBD`, `PLACEHOLDER`, `example.com`, `<owner>`, `<email>`).

## M05 — licence and notices

Decide and record:

1. Copyright owner(s) of the repository-authored material (tools, tests, docs, generated
   `source/`, `canonical/`, `map/`, `evidence/`).
2. Licensing status of `input/iOS735_Skeleton/` (the Swift skeleton inputs) — same owner/terms, or
   different?
3. Whether the LCTL toolchain terms impose notice obligations on generated canonical output or on
   the retained 1.6.0 analysis text in `evidence/lctl160/`.
4. The licence itself (internal use / modification / redistribution / commercial / patents), with
   legal review where appropriate.

Then add a root `LICENSE` with the full text and an `SPDX-License-Identifier:` line (the SBOM
reads it), `NOTICE` / `THIRD_PARTY_NOTICES.md` if required, a README licence section, and run
`python tools/sbom.py && python tools/manifest.py --write`.

Third-party inventory found in this repository (for the notices decision): **no third-party code
is vendored**; Python tooling is standard-library only. Build-time only, not redistributed:
GitHub Actions `actions/checkout`, `actions/setup-python`, `actions/setup-java`,
`actions/upload-artifact` (verify each licence against its authoritative LICENSE before citing
it); CPython (PSF-2.0); a Java 21 runtime (vendor-specific terms); the LCTL toolchains (terms
unknown — see M01).

## M06 — security policy

Decide: the security owner/team; a real, monitored private channel (GitHub private
vulnerability reporting, a role mailbox with optional PGP key, or a ticket intake — prefer a role
over a personal address); supported versions (suggested: latest minor only while pre-1.0);
acknowledgement target; coordinated-disclosure window; whether CVEs/advisories are issued; and
whether safe-harbour wording is approved.

Then create root `SECURITY.md` covering: supported versions; the exact private channel; "do not
file public issues"; what to include (version, reproduction, impact, logs, PoC, mitigation);
triage and severity handling; disclosure; scope (tools, verifier, provisioning, lock, CI,
signing/provenance, release artifacts, supply chain); out of scope; routing for defects in the
external LCTL toolchains or Java to their owners; and the incident workflow — evidence
preservation, private fix branch, rotation of toolchain pins / signing key / CI credentials after
compromise, advisory publication, post-incident review. Send a test report from an external
account and record that it arrived.

## M08 — signing identity

Create the Ed25519 release-signing key in owner-controlled storage, name authorised signers, and
publish the public key as `provenance/release-signing-public.pem` plus through a second
authenticated channel. Document rotation and revocation in `docs/RELEASE_PROCESS.md`.

## M01 / M04 — toolchains

Confirm the toolchain owner/publisher, the redistribution decision, and supply the two JAR
digests through an authenticated channel (procedure: `docs/TOOLCHAIN_PROVISIONING.md`).

## M03 — CI governance

Environment, runner, variables, required checks, CODEOWNERS with real handles, action SHA pins:
see `docs/RELEASE_PROCESS.md`.

## Appendix B — review roles to assign

Repository owner / release approver · LCTL toolchain owner or authorised distributor · security
owner · CI/release engineering owner · signing/provenance owner · legal/licence approver ·
independent reviewer for M04 trust-root changes · independent reviewer for final release evidence.
