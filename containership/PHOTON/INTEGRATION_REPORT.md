# Photon integration report — Unikernel Containership v2.7.0 (MasterApplied)

**Integration id** `PHOTON-UC270-1.0.0` · **2026-09-22T16:46:25Z** · profile `VENDORED_UNBOUND`

## 1. What was done

The Photon was vendored into `C:\Users\russe\OneDrive\Desktop\New folder\Unikernel_Containership_v2.7.0_MasterApplied\UC270` as a single self-contained subtree,
`PHOTON/`, plus two dispatch launchers at the product root (`PHOTON.cmd`, `PHOTON.sh`).

Contents:

| Path | Source | Files |
|---|---|---|
| `PHOTON/control_plane/` | VEC1 Generic Photon v0.2.0 | headless control plane, `vecctl`, config, schemas, programs, governance, evidence, tests, UI |
| `PHOTON/shell/` | VEC1 Design Photon v0.6.0 | app shell, loopback service, runtime modules, dashboard, docs, tests |
| `PHOTON/bridge/` | written for this integration | host-bridge contract and the unbound reference implementation |
| `PHOTON/PHOTON_STATUS.py` | written for this integration | honest capability and integrity reporter |
| `PHOTON/*.cmd`, `PHOTON/*.sh` | written for this integration | Python-3.10+ resolving launchers |

## 2. What was deliberately left out

The two source packages each bundle a full DF VM suite — `DF_Small`, `DF_Medium`,
`DF_Large`, `DF_Xtra_Large`, `DF_Fabric`, roughly 65 MB and over 7,000 files per
package. None of it was copied here. Those trees are the *host* half of the original
assembly, and this product is the host now. Copying them would have put a second,
unrelated execution stack inside your product and doubled its size for nothing.

Consequently the shell's release-integrity chain (`PACKAGE_SHA256SUMS.txt`,
`RELEASE_MANIFEST.json`) was regenerated for the vendored subset. The upstream
`SHA256SUMS.txt` / `PACKAGE_MANIFEST.json` of the source packages were not copied,
because they describe file sets that do not exist here and would fail on first read.

## 3. What was NOT touched

No file that was already in `Unikernel Containership v2.7.0 (MasterApplied)` has been read-modified, renamed, moved
or deleted. The product's own `MANIFEST.json`, `SHA256SUMS.txt` and any release or
provenance chain it carries are byte-for-byte as they were, which also means the
Photon is **outside** that chain. If you want the Photon inside the product's
integrity envelope, regenerate the product's own manifest afterwards — that is a
deliberate second step, not something done behind your back.

## 4. Host surfaces observed but not wired

| `RUN.cmd / RUN` | not wired | candidate input to `attest()` / `fabric_run()` |
| `BUILD.cmd / BUILD` | not wired | candidate input to `attest()` / `fabric_run()` |
| `LOAD.cmd / LOAD` | not wired | candidate input to `attest()` / `fabric_run()` |
| `START.cmd` | not wired | candidate input to `attest()` / `fabric_run()` |
| `VERIFY.cmd / VERIFY, VERIFY_1BIT, VERIFY_TIFF, VERIFY_VWS` | not wired | candidate input to `attest()` / `fabric_run()` |
| `DOCTOR.cmd, SELFTEST.cmd, LIFECYCLE.cmd, RECOVER.cmd` | not wired | candidate input to `attest()` / `fabric_run()` |
| `MASTER_FLOW.cmd, ONEBIT_FLOW.cmd, TIFF_FLOW.cmd, VWS_WORKFLOW.cmd` | not wired | candidate input to `attest()` / `fabric_run()` |
| `uc.py` | not wired | candidate input to `attest()` / `fabric_run()` |

UC270 ships DOCTOR and SELFTEST already, which map cleanly onto attest() and the preflight half of build_required(). The several *_FLOW entry points are candidate workloads for fabric_run(); pick one and seal it rather than running all of them.

## 5. Verification performed

* both source archives unpacked and inventoried;
* control-plane and shell modules byte-compiled;
* `PHOTON_STATUS.py` run against the assembled tree;
* `PHOTON/SHA256SUMS.txt` generated and re-verified against disk;
* shell release-integrity chain regenerated and re-verified by the shell's own
  `verify_release()`;
* confirmed no path collides with an existing entry at the product root.

## 6. Verification NOT performed

* nothing was executed against Unikernel Containership v2.7.0 (MasterApplied) itself — the bridge is unbound, so there
  is nothing to execute;
* no Windows native build qualification;
* no claim that any VEC1 component checklist is closed.

## 7. Licensing

Both source packages state that no third-party or GitHub-Junkyard donor code was
copied into them: `vec1/`, `tests/`, `ui/` and the shell runtime are original work,
and the Python standard library is the only runtime dependency. The DF trees that
carried the `All rights reserved. (c) Russell Philip Smithson.` notice were not
vendored. `PHOTON/THIRD-PARTY-NOTICES.md` records this per-part.

## 8. Next step

Read `PHOTON/bridge/BRIDGE_CONTRACT.md`, then implement `attest()` and `fabric_run()`
in `PHOTON/control_plane/vec1/dfbridge.py` against the surfaces in section 4.
