"""MC-042 - policy-controlled descriptor delegation by re-issuance.

Decision (ADR-0002): delegation is implemented as *re-issuance*.  Keys are never
shared between tables.  The destination table mints a fresh descriptor under its
own key; a ``PK_DESCRIPTOR_DELEGATION/1`` record links the two non-secretly.

* ``mode="move"``  - source descriptor is closed atomically with issuance; if the
  destination refuses (full, destroyed, disabled) the source is left untouched.
* ``mode="share"`` - both remain valid; closing either is independent.

The descriptor model has no rights beyond resource type, so attenuation means
the destination type must equal the source type (no amplification is possible).
Policy is a callable ``policy(src_fp, dst_fp, resource_type, mode) -> bool``;
the default policy denies everything.  Transaction ids make retries idempotent:
the same ``txn_id`` returns the original result and never duplicates authority.
Both tables must be in-process; cross-process delegation = send the *new*
descriptor over :mod:`transport`.
"""
from __future__ import annotations

import re
import threading
import time

try:
    from . import descriptors as _d
except ImportError:
    import descriptors as _d  # type: ignore

DELEGATION_SCHEMA = "PK_DESCRIPTOR_DELEGATION/1"
_TXN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class DelegationDenied(_d.DescriptorError, PermissionError):
    code = "delegation_denied"


def deny_all(src_fp, dst_fp, resource_type, mode) -> bool:
    return False


class Delegator:
    def __init__(self, policy=deny_all, *, audit=None, max_txns: int = 65_536):
        self._policy = policy
        self._audit = audit
        self._lock = threading.Lock()
        self._done: dict[str, tuple] = {}
        self._max = max_txns

    def delegate(self, src, dst, descriptor, *, txn_id: str, mode: str = "move"):
        if mode not in ("move", "share"):
            raise ValueError("mode must be 'move' or 'share'")
        if not isinstance(txn_id, str) or not _TXN.fullmatch(txn_id):
            raise ValueError("txn_id must match [A-Za-z0-9_-]{8,64}")
        if src is dst:
            raise DelegationDenied("source and destination are the same table")
        with self._lock:
            if txn_id in self._done:
                key, result = self._done[txn_id]
                if key != (id(src), id(dst), descriptor, mode):
                    raise DelegationDenied("txn_id reused for a different request")
                return result
            # Lock ordering: always src then dst by id to avoid deadlock.
            first, second = sorted((src, dst), key=id)
            with first._lock, second._lock:
                resource = src._resolve_locked(descriptor)
                rtype = descriptor.resource_type
                allowed = False
                try:
                    allowed = bool(self._policy(src.fingerprint, dst.fingerprint, rtype, mode))
                except Exception:  # noqa: BLE001 - policy failure is a denial
                    allowed = False
                if not allowed:
                    self._record(src, dst, rtype, mode, txn_id, "delegation_denied")
                    raise DelegationDenied("delegation policy denied request")
                new = dst._open(rtype, resource)  # raises before any source change
                if mode == "move":
                    src._close(descriptor)
            record = {"schema": DELEGATION_SCHEMA, "txn_id": txn_id, "mode": mode, "type": rtype,
                      "src_fp": src.fingerprint, "src_number": descriptor.number,
                      "dst_fp": dst.fingerprint, "dst_number": new.number, "ts": time.time()}
            if len(self._done) >= self._max:
                self._done.pop(next(iter(self._done)))
            self._done[txn_id] = ((id(src), id(dst), descriptor, mode), (new, record))
        self._record(src, dst, rtype, mode, txn_id, "ok")
        return new, record

    def _record(self, src, dst, rtype, mode, txn_id, outcome):
        if self._audit is not None:
            self._audit({"schema": "PK_DESCRIPTOR_EVENT/1", "op": f"delegate_{mode}", "table_fp": src.fingerprint,
                         "outcome": outcome, "type": rtype, "number": None, "ts": time.time(),
                         "detail": f"dst={dst.fingerprint} txn={txn_id}"})
