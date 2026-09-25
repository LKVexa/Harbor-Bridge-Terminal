"""Restart / replay semantics (component P1-15; C057, C095).

Normative:
  RST-1 Readiness is NOT persisted.  A pollable's readiness reflects a live host
        resource; after a process restart the host MUST re-create pollables and
        re-derive readiness from the resource.  Restoring a stale "ready" bit could
        report readiness for an operation that no longer exists (a false wake).
  RST-2 Consumers MUST treat restart as "all pollables unready, re-poll"; because
        the model is level-triggered, a resource that is still ready is re-observed
        on the first poll after re-creation (no lost wakeup across restart).
  RST-3 Aggregate counters, lifecycle state and config version ARE checkpointed,
        atomically (write temp + fsync + os.replace) with a SHA-256 digest; a
        corrupt or wrong-schema checkpoint is refused (PK_CHECKPOINT_CORRUPT) and
        the process starts from safe defaults with lifecycle DEPRECATED -- it never
        silently restores a partially-read state.
  RST-4 Replay: in-flight polls at crash time are not replayed; the caller's
        retry is the recovery path (polls are idempotent reads of readiness).
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile

try:
    from .errors import Inv14Error
    from .lifecycle import STATES
except ImportError:
    from errors import Inv14Error
    from lifecycle import STATES

CHECKPOINT_SCHEMA = "PK_POLL_CHECKPOINT/1"
COUNTER_KEYS = ("deprecated_uses", "polls_ready", "polls_timeout", "polls_cancelled",
                "cross_instance_refusals", "invalid_requests", "total_pollables", "max_set_size_seen")
MAX_BYTES = 16_384


class CheckpointError(Inv14Error):
    default_code = "PK_CHECKPOINT_CORRUPT"


def build(metrics: dict, lifecycle_state: str, config_version: str) -> dict:
    body = {"schema": CHECKPOINT_SCHEMA, "lifecycle_state": lifecycle_state, "config_version": config_version,
            "counters": {k: int(metrics.get(k, 0)) for k in COUNTER_KEYS}, "readiness_persisted": False}
    body["digest"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return body


def save(path: str, cp: dict) -> None:
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".cp-")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(cp, fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load(path: str) -> dict:
    try:
        raw = open(path, "rb").read(MAX_BYTES + 1)
    except OSError:
        raise CheckpointError("checkpoint unreadable", code="PK_CHECKPOINT_MISSING") from None
    if len(raw) > MAX_BYTES:
        raise CheckpointError("checkpoint too large")
    try:
        cp = json.loads(raw)
        dg = cp.pop("digest")
    except Exception:
        raise CheckpointError("checkpoint not parseable") from None
    if hashlib.sha256(json.dumps(cp, sort_keys=True).encode()).hexdigest() != dg:
        raise CheckpointError("checkpoint digest mismatch")
    if cp.get("schema") != CHECKPOINT_SCHEMA or cp.get("lifecycle_state") not in STATES \
            or cp.get("readiness_persisted") is not False \
            or set(cp.get("counters", {})) != set(COUNTER_KEYS) \
            or not all(isinstance(v, int) and v >= 0 for v in cp["counters"].values()):
        raise CheckpointError("checkpoint schema invalid")
    cp["digest"] = dg
    return cp


def restore_or_default(path: str) -> tuple:
    """Return (checkpoint_or_None, error_code_or_None).  Never raises."""
    try:
        return load(path), None
    except CheckpointError as e:
        return None, e.code
