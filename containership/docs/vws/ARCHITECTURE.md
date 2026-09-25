# UC-2.4.0 integration architecture

## Implemented data path

```text
Browser / VT renderer / SPIRAL transport adapter
  -> authenticated hermit.vws.v2 WebSocket
  -> gateway: exact Origin + credentials + session ownership + byte-credit flow
  -> thread worker (default) or supervised process worker
  -> registered virtual `ship` command
  -> typed ship.request control record (operation ID, argv only)
  -> gateway capability check + fixed command grammar + reservation lease
  -> one gateway-owned Python child: -I -X utf8 -B <fixed ship root>/uc.py
  -> existing UC lock / generation fence / transaction / engines / TIFF fabric
  -> bounded captured stdout/stderr -> typed 4 KiB result chunks
  -> worker incremental UTF-8 decoder -> original terminal output path
```

The gateway, not an untrusted worker, chooses the absolute Python executable and ship root. These paths and gateway credentials are not placed in the ship worker's configuration. Legacy direct-DF bridge activation is refused in the integrated ship profile to prevent an alternate build/execution privilege path. Browser and Photon host capabilities remain denied to headless workers.

The external protocol stays the supplied RAMWS `hermit.vws.v2`: JSON controls and seven-byte-header binary terminal data. Additive ship capability fields are omitted from legacy non-ship gateway hello messages. The bridge schema adds request/cancel/chunk/result types with strict properties, ID format, array cardinality, per-argument size, base64 shape and output limits. The schema validator was extended to implement bounded array validation rather than treating array requirements as documentation.

## Resource boundaries

There is one active ship child globally, no waiting queue and one pending request per session. Default combined stdout/stderr capture is 131,072 bytes. Each delivery chunk is at most 4,096 decoded bytes. The gateway ledger reserves 16 times the capture cap for bridge buffers/copies while delivering a result; this is a conservative logical allowance, not proof of physical RAM residency. Default read/control deadlines are 60,000/180,000 milliseconds. Overflow/deadline/cancellation are classified separately and yield nonzero command codes.

The child environment is allowlisted; Python is isolated and no command shell is used. Output is captured, then delivered; this is not streaming native-process progress. A browser may remain responsive while a ship operation runs without producing visible output.

**Python/native child memory is not OS-enforced by this integration.** Worker heap admission does not apply to the gateway's Python/native descendants. Telemetry explicitly exposes `childMemoryLimit: NOT_ENFORCED`. Native child output capture and concurrency are bounded, but the inherited ship may create its normal persistent report and TIFF files.

## Lifetime and persistence

Close, signal, worker failure, disconnect and gateway shutdown cancel gateway-owned jobs. POSIX process-group termination was exercised. Windows uses best-effort taskkill and is not equivalent to a tested Job Object boundary. An abrupt gateway kill can still leave a native descendant; inspect operating-system processes and lifecycle state before recovery.

Terminal sessions/VFS/output queues remain LOCAL_VOLATILE and are lost on restart. Credentials are hashed in `_runs/vws/principals.json`; ship lifecycle, managed transactions, reports and live TIFF state remain on disk. A memory-only terminal is not a diskless containership. Read-only mode forbids control operations but may create lock/lifecycle bookkeeping as part of existing UC inspection.

The root Python launcher releases/bypasses the long-lived ship lock while the gateway runs; each actual UC call still acquires its own lock. Holding the parent lock across the service lifetime would make every bridge call fail.

## Preserved assets

All four engines, six berths and the original hull are retained. The 38 original files under hull/ and hold/ were compared byte-for-byte after the native build and remained identical. Machine-specific extracted/compiled outputs and live qualification state are omitted from delivery. Existing source reports and terminal ledger claims are historical, not re-certified by this release.
