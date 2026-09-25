# Memory handling and secret-name privacy (checklist #49, #50)

**Memory.** CPython `str` objects are immutable and cannot be zeroized; copies may persist in freed memory until reused. The runtime minimises copies (values stay inside `_SecretValue`, revealed only by `use()`), blocks pickling, and keeps plaintext off every serialised channel. A memory-hard guarantee (mlock, zeroization, no swap/core dumps) needs a native helper or process isolation — **not achievable in pure Python; residual risk T-17 pending acceptance (W-005)**. Deployment MUST disable core dumps (`ulimit -c 0`) and swap for the INV-55 process.

**Secret names.** Names are tenant-prefixed and may be sensitive. They appear in audit records (needed for accountability) but **never** as metric labels (bounded cardinality and privacy) and never in public error messages. Denials for unknown and unauthorized names are identical (T-01).
