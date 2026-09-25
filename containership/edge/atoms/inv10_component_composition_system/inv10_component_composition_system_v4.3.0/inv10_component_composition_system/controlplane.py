"""MC-16..MC-18, MC-28..MC-31: the composition control plane.

* :class:`Registry` — namespace-governed component registry (MC-16).
* :class:`CompositionStore` — durable content-addressed store with
  immutability, verified reads, GC (MC-17). Plain files, atomic rename; no
  SQLite (safe on synced/network folders).
* :class:`ActivationController` — atomic promote/rollback with persisted
  previous-good lineage and compare-and-swap generations (MC-18, MC-40).
* :class:`ConfigLedger` — versioned limits/policy config with author, source,
  activation time and rollback lineage (MC-28).
* :class:`AdmissionController` — concurrency, per-tenant fairness, bounded
  queue, deadlines, load shedding (MC-29).
* :class:`CompositionService` — authenticated facade with idempotency keys,
  replay protection, restart recovery (MC-30) and quarantine/freeze (MC-31),
  audit, metrics, logs.
"""
from __future__ import annotations

import fnmatch
import json
import os
import pathlib
import secrets
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Iterator, Mapping

from . import __version__ as _VERSION
from .composition import CompositionError, CompositionLimits, DEFAULT_LIMITS, Unit, _canonical_digest, compose
from .errors import (Conflict, Frozen, IntegrityError, NotFound, Overloaded, PolicyRejected, Quarantined,
                     DependencyUnavailable)
from .schemas import validate_composition


def _atomic_write(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _dump(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------- registry


class Registry:
    """Authoritative registry: owners claim namespaces; versions are immutable."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.namespaces: dict[str, str] = {}  # glob -> owner
        self.entries: dict[tuple[str, str], dict[str, Any]] = {}  # (name, version) -> record
        self.lifecycle: dict[tuple[str, str], str] = {}  # active | deprecated | withdrawn

    def claim(self, pattern: str, owner: str) -> None:
        with self._lock:
            for p, o in self.namespaces.items():
                if o != owner and (fnmatch.fnmatchcase(pattern, p) or fnmatch.fnmatchcase(p, pattern)):
                    raise Conflict("namespace overlaps another owner's claim", pattern=pattern, existing=p, owner=o)
            self.namespaces[pattern] = owner

    def _owner(self, interface: str) -> str | None:
        hits = sorted((p for p in self.namespaces if fnmatch.fnmatchcase(interface, p)), key=len, reverse=True)
        return self.namespaces[hits[0]] if hits else None

    def register(self, unit: Unit, version: str, owner: str, **meta: Any) -> dict[str, Any]:
        with self._lock:
            for e in sorted(unit.exports):
                o = self._owner(e)
                if o is None or o != owner:
                    raise PolicyRejected("export outside owner's namespace", interface=e, owner=owner, namespace_owner=o)
            key = (unit.name, version)
            rec = {"name": unit.name, "version": version, "owner": owner, "imports": sorted(unit.imports),
                   "exports": sorted(unit.exports), **meta}
            if key in self.entries:
                if self.entries[key] != rec:
                    raise Conflict("version already registered with different content", name=unit.name, version=version)
                return self.entries[key]
            self.entries[key] = rec
            self.lifecycle[key] = "active"
            return rec

    def set_state(self, name: str, version: str, state: str) -> None:
        if state not in {"active", "deprecated", "withdrawn"}:
            raise ValueError(state)
        with self._lock:
            if (name, version) not in self.entries:
                raise NotFound("unknown component version", name=name, version=version)
            self.lifecycle[(name, version)] = state

    def resolve(self, name: str, version: str) -> Unit:
        with self._lock:
            rec = self.entries.get((name, version))
            if rec is None:
                raise NotFound("unknown component version", name=name, version=version)
            if self.lifecycle[(name, version)] == "withdrawn":
                raise PolicyRejected("component version withdrawn", name=name, version=version)
            return Unit(name, frozenset(rec["imports"]), frozenset(rec["exports"]))

    def providers_of(self, interface: str) -> list[dict[str, Any]]:
        with self._lock:
            return [r for k, r in sorted(self.entries.items())
                    if interface in r["exports"] and self.lifecycle[k] != "withdrawn"]


# ---------------------------------------------------------------- store


class CompositionStore:
    """Content-addressed, immutable, verified-on-read file store."""

    def __init__(self, root: str | os.PathLike) -> None:
        self.root = pathlib.Path(root)
        (self.root / "objects").mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, cid: str) -> pathlib.Path:
        if len(cid) != 64 or any(c not in "0123456789abcdef" for c in cid):
            raise NotFound("malformed composition id", composition=cid)
        return self.root / "objects" / cid[:2] / f"{cid}.json"

    def put(self, result: Mapping[str, Any]) -> str:
        validate_composition(dict(result))
        cid = result["composition"]
        path = self._path(cid)
        data = _dump(dict(result))
        with self._lock:
            if path.exists():
                if self.get(cid)["composition"] != cid:
                    raise IntegrityError("stored object corrupt", composition=cid)
                return cid  # immutable: identical id => identical graph
            _atomic_write(path, data)
        return cid

    def get(self, cid: str) -> dict[str, Any]:
        path = self._path(cid)
        if not path.exists():
            raise NotFound("composition not in store", composition=cid)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            validate_composition(doc)
        except (ValueError, CompositionError) as exc:
            raise IntegrityError("stored object unreadable", composition=cid) from exc
        units = {n: [set(), set()] for n in doc["components"]}
        for b in doc["bindings"]:
            units[b["consumer"]][0].add(b["interface"])
        for i, p in doc["providers"].items():
            units[p][1].add(i)
        material = {"schema": doc["schema"], "identity_profile": doc["identity_profile"],
                    "units": [{"name": n, "imports": sorted(u[0]), "exports": sorted(u[1])}
                              for n, u in sorted(units.items())],
                    "bindings": doc["bindings"], "external_imports": doc["external_imports"]}
        if _canonical_digest(material) != cid:
            raise IntegrityError("content does not match its address", composition=cid)
        return doc

    def ids(self) -> list[str]:
        return sorted(p.stem for p in (self.root / "objects").glob("*/*.json"))

    def fsck(self) -> dict[str, list[str]]:
        bad = []
        for cid in self.ids():
            try:
                self.get(cid)
            except CompositionError:
                bad.append(cid)
        return {"ok": [c for c in self.ids() if c not in bad], "corrupt": bad}

    def gc(self, retain: Iterable[str]) -> list[str]:
        keep = set(retain)
        removed = []
        with self._lock:
            for cid in self.ids():
                if cid not in keep:
                    self._path(cid).unlink()
                    removed.append(cid)
        return removed


# ---------------------------------------------------------------- activation


class ActivationController:
    """Pointer file ``active.json`` = {generation, active, previous[]}; CAS updates."""

    def __init__(self, store: CompositionStore, workload: str, history: int = 16) -> None:
        self.store, self.history = store, history
        self.path = store.root / "activation" / f"{workload}.json"
        self._lock = threading.Lock()

    def state(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"generation": 0, "active": None, "previous": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def activate(self, cid: str, *, expected_generation: int | None = None,
                 verify: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        doc = self.store.get(cid)  # verified read
        if verify:
            verify(doc)  # pre-promotion gate (e.g. environment resolver)
        with self._lock:
            st = self.state()
            if expected_generation is not None and st["generation"] != expected_generation:
                raise Conflict("stale activation generation", expected=expected_generation, actual=st["generation"])
            if st["active"] == cid:
                return st
            prev = ([st["active"]] if st["active"] else []) + st["previous"]
            new = {"generation": st["generation"] + 1, "active": cid, "previous": prev[: self.history],
                   "activated_at": time.time()}
            _atomic_write(self.path, _dump(new))
            return new

    def rollback(self, *, expected_generation: int | None = None) -> dict[str, Any]:
        with self._lock:
            st = self.state()
            if expected_generation is not None and st["generation"] != expected_generation:
                raise Conflict("stale activation generation", expected=expected_generation, actual=st["generation"])
            if not st["previous"]:
                raise NotFound("no previous-good composition to roll back to")
            target, rest = st["previous"][0], st["previous"][1:]
            self.store.get(target)
            new = {"generation": st["generation"] + 1, "active": target, "previous": rest,
                   "rolled_back_from": st["active"], "activated_at": time.time()}
            _atomic_write(self.path, _dump(new))
            return new


# ---------------------------------------------------------------- config ledger


class ConfigLedger:
    """Append-only config versions; activation and rollback are recorded entries."""

    def __init__(self, path: str | os.PathLike | None = None) -> None:
        self.path = pathlib.Path(path) if path else None
        self.entries: list[dict[str, Any]] = []
        if self.path and self.path.exists():
            self.entries = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]

    def _append(self, e: dict[str, Any]) -> dict[str, Any]:
        self.entries.append(e)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(e, sort_keys=True) + "\n")
        return e

    def propose(self, limits: CompositionLimits, *, author: str, source: str, policy_version: str = "0") -> dict[str, Any]:
        body = {"limits": dict(vars(limits)), "policy_version": policy_version}
        return self._append({"kind": "version", "id": _canonical_digest(body)[:16], "body": body,
                             "author": author, "source": source, "at": time.time()})

    def activate(self, config_id: str, *, actor: str) -> dict[str, Any]:
        if not any(e["kind"] == "version" and e["id"] == config_id for e in self.entries):
            raise NotFound("unknown config version", config=config_id)
        prev = self.active_id()
        return self._append({"kind": "activate", "id": config_id, "previous": prev, "actor": actor, "at": time.time()})

    def rollback(self, *, actor: str) -> dict[str, Any]:
        acts = [e for e in self.entries if e["kind"] == "activate"]
        if not acts or not acts[-1]["previous"]:
            raise NotFound("no previous config")
        return self._append({"kind": "activate", "id": acts[-1]["previous"], "previous": acts[-1]["id"],
                             "actor": actor, "at": time.time(), "rollback": True})

    def active_id(self) -> str | None:
        acts = [e for e in self.entries if e["kind"] == "activate"]
        return acts[-1]["id"] if acts else None

    def active_limits(self) -> CompositionLimits:
        cid = self.active_id()
        if cid is None:
            return DEFAULT_LIMITS
        body = next(e["body"] for e in self.entries if e["kind"] == "version" and e["id"] == cid)
        return CompositionLimits(**body["limits"])


# ---------------------------------------------------------------- admission


class AdmissionController:
    def __init__(self, *, max_concurrent: int = 8, max_per_tenant: int = 4, max_queue: int = 64,
                 queue_timeout: float = 1.0) -> None:
        self.max_concurrent, self.max_per_tenant = max_concurrent, max_per_tenant
        self.max_queue, self.queue_timeout = max_queue, queue_timeout
        self._cv = threading.Condition()
        self.running = 0
        self.per_tenant: dict[str, int] = {}
        self.waiting = 0
        self.shed = 0

    @contextmanager
    def admit(self, tenant: str, *, deadline: float | None = None) -> Iterator[None]:
        end = time.monotonic() + (self.queue_timeout if deadline is None else deadline)
        with self._cv:
            busy = self.running >= self.max_concurrent or self.per_tenant.get(tenant, 0) >= self.max_per_tenant
            if busy and self.waiting >= self.max_queue:
                self.shed += 1
                raise Overloaded("admission queue full", queue=self.max_queue)
            self.waiting += 1
            try:
                while self.running >= self.max_concurrent or self.per_tenant.get(tenant, 0) >= self.max_per_tenant:
                    left = end - time.monotonic()
                    if left <= 0:
                        self.shed += 1
                        raise Overloaded("admission deadline exceeded", tenant=tenant)
                    self._cv.wait(left)
            finally:
                self.waiting -= 1
            self.running += 1
            self.per_tenant[tenant] = self.per_tenant.get(tenant, 0) + 1
        try:
            yield
        finally:
            with self._cv:
                self.running -= 1
                self.per_tenant[tenant] -= 1
                self._cv.notify_all()


# ---------------------------------------------------------------- quarantine


class QuarantineList:
    def __init__(self) -> None:
        self.components: set[str] = set()
        self.interfaces: set[str] = set()  # globs
        self.frozen = False
        self._lock = threading.Lock()

    def check(self, units: Iterable[Unit]) -> None:
        with self._lock:
            for u in units:
                if u.name in self.components:
                    raise Quarantined("component is quarantined", component=u.name)
                for i in sorted(u.imports | u.exports):
                    if any(fnmatch.fnmatchcase(i, g) for g in self.interfaces):
                        raise Quarantined("interface namespace is quarantined", component=u.name, interface=i)


# ---------------------------------------------------------------- service


@dataclass
class ServiceDeps:
    store: CompositionStore
    auth: Any  # security.Authenticator
    audit: Any  # security.AuditTrail
    metrics: Any  # observability.Metrics
    logger: Any  # observability.StructuredLogger
    policy: Any | None = None  # governance.LinkPolicy
    environment: Any | None = None  # governance.EnvironmentResolver
    config: ConfigLedger | None = None
    admission: AdmissionController | None = None


class CompositionService:
    """Stateful wrapper around the pure linker. Restart-safe: all state that
    matters (store, activation pointer, idempotency journal, audit) is on disk."""

    def __init__(self, deps: ServiceDeps) -> None:
        self.d = deps
        self.quarantine = QuarantineList()
        self._idem_path = deps.store.root / "idempotency.jsonl"
        self._idem: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        if self._idem_path.exists():  # restart recovery
            for line in self._idem_path.read_text().splitlines():
                if line.strip():
                    e = json.loads(line)
                    self._idem[e["key"]] = e
        self._seen_nonces: set[str] = set()

    def _principal(self, token: str, action: str) -> Any:
        p = self.d.auth.authenticate(token)
        self.d.auth.authorize(p, action)
        return p

    def publish(self, token: str, units: list[Unit], *, context: Any, external: Iterable[str] = frozenset(),
                idempotency_key: str | None = None, nonce: str | None = None,
                traceparent: str | None = None) -> dict[str, Any]:
        from .observability import child_traceparent
        tp = child_traceparent(traceparent)
        op = secrets.token_hex(8)
        principal = self._principal(token, "publish")
        if self.quarantine.frozen:
            self.d.audit.append("publish.refused", principal.actor, reason="frozen")
            raise Frozen("publication is frozen")
        if nonce is not None:
            with self._lock:
                if nonce in self._seen_nonces:
                    raise Conflict("replayed request nonce", nonce=nonce)
                self._seen_nonces.add(nonce)
        request_digest = _canonical_digest({"u": sorted([u.name, sorted(u.imports), sorted(u.exports)] for u in units),
                                            "x": sorted(external), "ctx": context.as_dict()})
        if idempotency_key:
            with self._lock:
                prior = self._idem.get(idempotency_key)
            if prior:
                if prior["request"] != request_digest:
                    raise Conflict("idempotency key reused with a different request", key=idempotency_key)
                return {**self.d.store.get(prior["composition"]), "idempotent_replay": True}
        admission = self.d.admission.admit(context.tenant) if self.d.admission else _null()
        start = time.perf_counter()
        with admission:
            try:
                self.quarantine.check(units)
                limits = self.d.config.active_limits() if self.d.config else DEFAULT_LIMITS
                result = compose(units, external=frozenset(external), limits=limits)
                decisions = self.d.policy.enforce(context, result["bindings"]) if self.d.policy else []
                if self.d.environment is not None:
                    self.d.environment.resolve(context, result["external_imports"])
                cid = self.d.store.put(result)
            except CompositionError as exc:
                ms = (time.perf_counter() - start) * 1000
                self.d.metrics.record_outcome("refused", error=exc.as_dict(), latency_ms=ms)
                self.d.audit.append("publish.refused", principal.actor, op=op, tenant=context.tenant,
                                    error=exc.as_dict())
                self.d.logger.log("warning", "publish.refused", operation_id=op, traceparent=tp,
                                  tenant=context.tenant, workload=context.workload, code=exc.code)
                raise
        ms = (time.perf_counter() - start) * 1000
        self.d.metrics.record_outcome("published", result=result, latency_ms=ms)
        self.d.audit.append("publish", principal.actor, op=op, tenant=context.tenant, workload=context.workload,
                            composition=cid, policy_decisions=len(decisions))
        self.d.logger.log("info", "publish", operation_id=op, traceparent=tp, tenant=context.tenant,
                          workload=context.workload, composition=cid, latency_ms=round(ms, 3))
        if idempotency_key:
            e = {"key": idempotency_key, "request": request_digest, "composition": cid}
            with self._lock:
                self._idem[idempotency_key] = e
                with self._idem_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(e, sort_keys=True) + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
        return result

    def quarantine_component(self, token: str, name: str, reason: str) -> None:
        p = self._principal(token, "quarantine")
        with self.quarantine._lock:
            self.quarantine.components.add(name)
        self.d.audit.append("quarantine", p.actor, component=name, reason=reason)

    def quarantine_namespace(self, token: str, pattern: str, reason: str) -> None:
        p = self._principal(token, "quarantine")
        with self.quarantine._lock:
            self.quarantine.interfaces.add(pattern)
        self.d.audit.append("quarantine", p.actor, namespace=pattern, reason=reason)

    def set_frozen(self, token: str, frozen: bool, reason: str) -> None:
        p = self._principal(token, "freeze")
        self.quarantine.frozen = frozen
        self.d.audit.append("freeze" if frozen else "unfreeze", p.actor, reason=reason)

    def health(self) -> dict[str, Any]:
        from .observability import health_report
        deps: dict[str, Callable[[], bool]] = {
            "store": lambda: self.d.store.root.exists(),
            "keys": lambda: self.d.auth.keys.available,
            "audit": lambda: self.d.audit.verify() >= 0,
        }
        limits = self.d.config.active_limits() if self.d.config else DEFAULT_LIMITS
        return health_report(version=_VERSION, limits=limits, dependencies=deps, frozen=self.quarantine.frozen)


@contextmanager
def _null() -> Iterator[None]:
    yield
