# Start here — UC-2.8.0

UC-2.8.0 combines the **99 supplied edge-component atoms** with UC-2.7.0. There are 86 canonical atoms in `edge/atoms/`, 85 of them bound to PK elements, and every archive is kept byte-for-byte. Start from a short new folder such as `D:\UC280`:

```bat
EDGE.cmd status
EDGE.cmd check --deep
EDGE.cmd test PLN-07
EDGE.cmd test all --jobs 4
```

Read `docs/edge/EDGE_INTEGRATION.md`. Recorded atom evidence: 9,833 passed / 41 failed / 0 errors (59 suites green, 27 red), all classified. Everything below about UC-2.7.0 still applies.

## UC-2.7.0

UC-2.7.0 applies the attached **15-volume / 150-component / 375,000-record master prompt-and-workflow series** to the UC-2.6.0 1BNCF candidate as a conservative implementation and qualification pass. It preserves the existing TIFF/GIF pixel infrastructure, bounded 1-bit communication fabric, and authenticated VWS terminal.

The exact master-series source volumes are retained under `masterflow/source/`. Generated engineering tasks are requirements, not executable code, and are never promoted to PASS without task-specific evidence. The current source ledger remains **265,000 OPEN / 110,000 BLOCKED / 0 PASS**. Component-level mapping is **68 IN_PROGRESS / 38 OPEN / 44 BLOCKED**.

Start on Windows from a short new directory such as `D:\UC280`:

```bat
MASTER_FLOW.cmd status
MASTER_FLOW.cmd check --deep
MASTER_FLOW.cmd execute
python uc.py platform status
VERIFY.cmd --quick --no-hull
```

The VWS terminal exposes read-only `ship master-workflow status` and `ship platform status` in addition to the retained TIFF/GIF and one-bit inspection surfaces. Live mutation/control remains behind the existing local capability boundary.

UC-2.7.0 adds bounded local platform primitives (eventing, hash-chained audit records, metrics/traces/log records, queue backpressure/idempotency, configuration validators, capacity planning, hardware/health inspection, compatibility reporting, and a pixel-kernel ABI descriptor). These are not relabeled as a bootable unikernel guest, hypervisor sandbox, multi-host consensus system, production key authority, or public deployment.

This is a tested local integration candidate, **not Production GO**. Existing installations and live state are not overwritten.
