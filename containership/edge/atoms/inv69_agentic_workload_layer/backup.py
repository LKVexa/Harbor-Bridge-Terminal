"""Backup, restore and reconstruction of INV-69 state (C095).

State inventory (authoritative source -> method):

| state class               | authoritative source        | backup? | method                              |
|---------------------------|-----------------------------|---------|-------------------------------------|
| run-event chain           | this component              | yes     | export + chain verify on restore    |
| kernel transcripts        | this component              | yes     | export + verify_transcript per agent|
| config provenance chain   | this component              | yes     | export + verify chain               |
| idempotency / effect keys | INV-57 durable execution    | yes*    | copy of committed keys (replay guard)|
| run checkpoints           | INV-57 durable execution    | no      | reconstruct from INV-57             |
| live one-use approvals    | none (ephemeral by design)  | NEVER   | discarded: re-approval required     |
| trust caches              | identity/policy services    | no      | re-fetch; never restored            |

Bundles are integrity-protected with HMAC-SHA256 over a canonical manifest
(key from the operator's key service; encryption at rest is delegated to the
storage backend, INV-47).  Restore happens into a staging object; activation
only after every chain verifies and the replay guard is loaded.
"""
from __future__ import annotations

from typing import Any, Mapping
import hashlib
import hmac
import json
import time

from .errors import AgentError

BACKUP_SCHEMA = "PK_AGENT_BACKUP/1"


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


def _verify_chain(events: list[Mapping[str, Any]], head: str, *, seq_key: str, hash_key: str,
                  base_seq: int = 0, base_head: str = "0" * 64) -> bool:
    prev = base_head
    for i, ev in enumerate(events):
        body = {k: v for k, v in ev.items() if k != hash_key}
        if ev.get(seq_key) != base_seq + i or ev.get("prev_hash") != prev:
            return False
        if hashlib.sha256(_canon(body)).hexdigest() != ev.get(hash_key):
            return False
        prev = ev[hash_key]
    return prev == head


def create_backup(runtime, *, key: bytes, actor: str, clock=time.time) -> dict[str, Any]:
    transcripts = {rid: r.agent.export_transcript() for rid, r in runtime.runs.items()}
    body = {
        "schema": BACKUP_SCHEMA,
        "component_version": "4.3.0",
        "created_at": clock(),
        "actor": actor,
        "run_events": {"head": runtime.head, "events": runtime.events, "base_seq": runtime._base_seq,
                       "base_head": runtime._base_head},
        "config_provenance": runtime.config.export_provenance(),
        "transcripts": transcripts,
        "effects": dict(runtime.durable.effects),
        "excluded": ["live approvals (ephemeral; replay prevention)", "trust caches", "run checkpoints (INV-57)"],
    }
    manifest = {k: hashlib.sha256(_canon(v)).hexdigest() for k, v in body.items()}
    mac = hmac.new(key, _canon(manifest), hashlib.sha256).hexdigest()
    return {"body": body, "manifest": manifest, "mac": mac}


def restore_to_staging(bundle: Mapping[str, Any], *, key: bytes, actor: str, target_version: str = "4.3.0",
                       clock=time.time) -> dict[str, Any]:
    """Validate a bundle completely and return a staged state + a restore record. Nothing is activated."""
    try:
        body, manifest, mac = bundle["body"], bundle["manifest"], bundle["mac"]
    except (KeyError, TypeError):
        raise AgentError("AGT-INT-001", "malformed backup bundle") from None
    if not hmac.compare_digest(hmac.new(key, _canon(manifest), hashlib.sha256).hexdigest(), str(mac)):
        raise AgentError("AGT-INT-001", "backup MAC mismatch")
    for k, v in body.items():
        if manifest.get(k) != hashlib.sha256(_canon(v)).hexdigest():
            raise AgentError("AGT-INT-001", "backup manifest digest mismatch", details={"section": k})
    if body.get("schema") != BACKUP_SCHEMA:
        raise AgentError("AGT-CMP-001", "unsupported backup schema")
    rev = body["run_events"]
    if not _verify_chain(rev["events"], rev["head"], seq_key="seq", hash_key="event_hash",
                         base_seq=rev.get("base_seq", 0), base_head=rev.get("base_head", "0" * 64)):
        raise AgentError("AGT-INT-001", "run-event chain broken in backup")
    cp = body["config_provenance"]
    if not _verify_chain(cp["records"], cp["head"], seq_key="generation", hash_key="record_hash"):
        raise AgentError("AGT-INT-001", "config provenance chain broken in backup")
    from .runtime import _event_digest
    for rid, t in body["transcripts"].items():
        prev = "0" * 64
        for i, ev in enumerate(t["events"]):
            e = dict(ev)
            claimed = e.pop("event_hash")
            if e.get("step") != i or e.get("prev_hash") != prev or _event_digest(e) != claimed:
                raise AgentError("AGT-INT-001", "kernel transcript chain broken", details={"run": rid})
            prev = claimed
        if prev != t["head"]:
            raise AgentError("AGT-INT-001", "kernel transcript head mismatch", details={"run": rid})
    record = {"schema": "PK_AGENT_RESTORE_RECORD/1", "actor": actor, "source_mac": mac,
              "source_created_at": body["created_at"], "source_version": body["component_version"],
              "target_version": target_version, "validated": True, "activated_at": None, "staged_at": clock(),
              "replay_guard_keys": len(body["effects"]), "approvals_restored": 0}
    return {"staged": body, "record": record}


def activate_restore(staged: Mapping[str, Any], durable, *, clock=time.time) -> dict[str, Any]:
    """Load the replay guard into the durable adapter (so committed effects are never re-executed)."""
    for k, v in staged["staged"]["effects"].items():
        durable.effects.setdefault(k, v)
    rec = dict(staged["record"], activated_at=clock())
    return rec
