"""M03 - cross-host TCP transport adapter tying every control together.

Wire: each message is a 4-byte big-endian length followed by the body. The first
three messages are the JSON handshake (security.py, bounded to 4 KiB each);
every later message is an AES-GCM record whose plaintext is either a request
frame (codec.encode_frame) or a response (0x00 + encoded results | 0x01 + JSON
typed error). Receiver order of checks - each one fails closed and is counted:

  size -> record auth/replay -> header decode -> deadline -> interface/version
  -> function -> fingerprint -> authorization -> idempotency -> admission
  -> argument decode -> dispatch -> result encode
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
import threading
import time

try:                                   # installed as inv61_distributed_wit_rpc.wrpc
    from ..rpc import fingerprint
except ImportError:                    # run from the package directory (tests, tools)
    from rpc import fingerprint
from .codec import CodecError, decode_args, decode_header, encode_args, encode_frame
from .controls import Admission, Authorizer, CircuitBreaker, IdempotencyCache, RetryPolicy
from .ops import AuditLog, Health, JsonLogger, Metrics, Tracer, child_traceparent, parse_traceparent
from .security import ClientHandshake, SecurityError, ServerHandshake
from .wit import Package, qualified

HS_LIMIT = 4096


class TransportError(Exception):
    pass


def _send(sock: socket.socket, body: bytes) -> None:
    sock.sendall(struct.pack(">I", len(body)) + body)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise TransportError("closed")
        buf += chunk
    return bytes(buf)


def _recv(sock: socket.socket, limit: int) -> bytes:
    n = struct.unpack(">I", _recv_exact(sock, 4))[0]
    if n > limit:
        raise TransportError("message-too-large")   # refuse before allocating
    return _recv_exact(sock, n)


def _err(error_code: str, **extra) -> bytes:
    return b"\x01" + json.dumps(dict(extra, error=error_code), sort_keys=True).encode()


class Node:
    """A wRPC server node exporting the functions of one parsed WIT package."""

    def __init__(self, cfg: dict, keyring, package: Package, impls: dict, peer_tenants: dict,
                 authorizer: Authorizer, audit: AuditLog | None = None, journal=None, log_sink=None,
                 span_exporter=None):
        self.cfg, self.keyring, self.pkg, self.impls = cfg, keyring, package, impls
        self.peer_tenants, self.authz = peer_tenants, authorizer
        self.audit = audit or AuditLog()
        self.metrics = Metrics()
        self.log = JsonLogger(log_sink or (lambda line: None), cfg["log_level"])
        self.tracer = Tracer(span_exporter)
        self.health = Health()
        self.idem = IdempotencyCache(cfg["idempotency_ttl_s"], journal=journal)
        self.admission = Admission(cfg["max_inflight"], cfg["max_queue"], cfg["per_tenant_inflight"])
        self._conn_slots = threading.BoundedSemaphore(cfg["max_connections"])
        self._stop = threading.Event()
        self._sock = None
        self._threads: list = []
        self._conns: set = set()
        self._conns_lock = threading.Lock()
        self.health.register("listener", lambda: self._sock is not None and not self._stop.is_set())
        self.audit_failures = 0
        self.audit_ok = True                  # last append result; readiness recovers when audit does
        self._deny_audit_window = [0, 0]      # [second, count] rate limit for unauthenticated denials
        self.health.register("audit-writable", lambda: self.audit_ok, critical=True)
        # receiver signatures, resolved once
        self.sigs = {}
        for iname, iface in package.interfaces.items():
            for fname, fn in iface.functions.items():
                self.sigs[(qualified(package, iname), fname)] = fn
        # fingerprints are computed once at start, not per call (M28)
        self.fps = {k: fingerprint(f.param_texts(), f.result_texts()) for k, f in self.sigs.items()}

    # ------------------------------------------------------------ lifecycle
    def start(self) -> tuple[str, int]:
        s = socket.socket(socket.AF_INET6 if ":" in self.cfg["listen_host"] else socket.AF_INET)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.cfg["listen_host"], self.cfg["listen_port"]))
        s.listen(128)
        s.settimeout(0.2)
        self._sock = s
        t = threading.Thread(target=self._accept_loop, name="inv61-accept", daemon=True)
        t.start()
        self._threads.append(t)
        self._audit("node-start", subject=self.cfg["node_id"], decision="ok")
        return s.getsockname()[:2]

    def drain(self, timeout_s: float = 5.0) -> bool:
        """Stop admitting: readiness fails, new connections are refused, new calls get the
        retryable ``unavailable``; then wait up to ``timeout_s`` for in-flight calls."""
        self.health.draining = True
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            if self.admission.inflight == 0:
                return True
            time.sleep(0.01)
        return self.admission.inflight == 0

    def _audit(self, *args, **kw) -> bool:
        """Audit append that never crashes the request path; a failure flips readiness."""
        try:
            self.audit.append(*args, **kw)
            self.audit_ok = True
            return True
        except Exception:
            self.audit_ok = False
            with self._conns_lock:
                self.audit_failures += 1
            self.metrics.inc("inv61_audit_failures_total")
            return False

    def _audit_deny_limited(self, peer: str, code: str) -> None:
        sec = int(time.time())
        w = self._deny_audit_window
        if w[0] != sec:
            w[0], w[1] = sec, 0
        w[1] += 1
        if w[1] <= 20:                 # at most 20 unauthenticated-deny records per second
            self._audit("authn", "", peer, "", "deny", code)
        else:
            self.metrics.inc("inv61_audit_suppressed_total")

    def stop(self) -> None:
        self._stop.set()
        with self._conns_lock:        # stop means stop: live sessions are torn down too
            for c in list(self._conns):
                try:
                    c.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        for t in self._threads:
            t.join(timeout=2)
        if self._sock:
            self._sock.close()
            self._sock = None
        self._audit("node-stop", subject=self.cfg["node_id"], decision="ok")

    def _accept_loop(self):
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except (socket.timeout, OSError):
                continue
            if self.health.draining:
                self.metrics.inc("inv61_connections_rejected_total")
                conn.close()
                continue
            if not self._conn_slots.acquire(blocking=False):
                self.metrics.inc("inv61_connections_rejected_total")
                conn.close()
                continue
            with self._conns_lock:
                self._conns.add(conn)
            t = threading.Thread(target=self._serve, args=(conn,), daemon=True)
            t.start()

    # ------------------------------------------------------------- per conn
    def _serve(self, conn: socket.socket):
        peer = "?"
        try:
            conn.settimeout(self.cfg["handshake_timeout_s"])
            hs = ServerHandshake(self.cfg["node_id"], self.keyring)
            hello = json.loads(_recv(conn, HS_LIMIT))
            _send(conn, json.dumps(hs.accept(hello)).encode())
            chan, peer, version = hs.complete(json.loads(_recv(conn, HS_LIMIT)))
            key_id = hello["key_id"]
            tenant = self.peer_tenants.get(peer)
            if tenant is None:
                raise SecurityError("peer-not-enrolled")
            self._audit("authn", tenant, peer, version, "allow", "handshake-ok")
            self.metrics.inc("inv61_handshakes_total", outcome="ok")
            conn.settimeout(self.cfg["idle_timeout_s"])
            while not self._stop.is_set():
                try:
                    record = _recv(conn, self.cfg["max_frame_bytes"] + 64)
                except socket.timeout:
                    break
                try:
                    body = chan.open(record)
                    # revocation/expiry applies to live sessions, not only new handshakes
                    self.keyring.lookup(key_id, peer)
                except SecurityError as e:
                    code = "credential-revoked" if e.code == "authentication-failed" else e.code
                    self._audit("record-reject", tenant, peer, f"session:{key_id}", "deny", code)
                    self.metrics.inc("inv61_record_rejects_total", outcome=code)
                    break      # a forged/replayed record or a revoked credential ends the session
                _send(conn, chan.seal(self.handle(body, tenant, peer)))
        except SecurityError as e:
            self._audit_deny_limited(peer, e.code)
            self.metrics.inc("inv61_handshakes_total", outcome=e.code)
        except (TransportError, OSError, ValueError, KeyError, TypeError):
            self.metrics.inc("inv61_handshakes_total", outcome="transport")
        finally:
            with self._conns_lock:
                self._conns.discard(conn)
            conn.close()
            self._conn_slots.release()

    # ----------------------------------------------------- request pipeline
    def handle(self, body: bytes, tenant: str, peer: str, now: float | None = None) -> bytes:
        t0 = time.perf_counter()
        now = time.time() if now is None else now
        outcome = "ok"
        iface = fn_name = "?"
        rid = trace_id = ""
        span = None
        try:
            try:
                h, payload = decode_header(body)
            except CodecError as e:
                outcome = "malformed-frame"
                return _err("malformed-frame", code=e.code)
            iface, fn_name, rid = h["interface"], h["function"], h["request_id"]
            tp, _, _ = child_traceparent(h["traceparent"] or None, self.cfg["trace_sample_ratio"])
            trace_id = tp[3:35]
            with self.tracer.span("inv61.handle", tp, status_fn=lambda: outcome, interface=iface, function=fn_name) as span:
                if now >= h["deadline"]:
                    outcome = "deadline-exceeded"
                    return _err(outcome)
                if not any(k[0] == iface for k in self.sigs):
                    outcome = "unknown-interface"
                    return _err(outcome)
                if h["version"] != self.pkg.version:
                    outcome = "version-mismatch"
                    return _err(outcome, expected=self.pkg.version)
                sig = self.sigs.get((iface, fn_name))
                if sig is None:
                    outcome = "unknown-function"
                    return _err(outcome)
                if h["fp"] != self.fps[(iface, fn_name)]:
                    outcome = "signature-mismatch"
                    return _err(outcome)
                allowed, rule, reason = self.authz.decide(tenant, peer, iface, fn_name, now)
                if not self._audit("authz", tenant, peer, f"{iface}#{fn_name} rid={rid}",
                                   "allow" if allowed else "deny", f"{reason}:{rule}"):
                    outcome = "unavailable"          # no audit, no decision: fail closed
                    return _err(outcome, retry_after_ms=1000)
                if not allowed:
                    outcome = "permission-denied"
                    return _err(outcome)
                digest = hashlib.sha256(f"{iface}#{fn_name}#{h['fp']}#".encode() + payload).hexdigest()
                result, _dup = self.idem.run((tenant, rid),
                                             lambda: self._execute(sig, iface, fn_name, payload, h, tenant),
                                             call_digest=digest)
                if isinstance(result, dict) and "error" in result:
                    outcome = result["error"]
                    extra = dict(result)
                    return _err(extra.pop("error"), **extra)
                return b"\x00" + bytes.fromhex(result["ok"])
        finally:
            dt = time.perf_counter() - t0
            self.metrics.inc("inv61_calls_total", interface=iface if (iface, fn_name) in self.sigs else "other",
                             outcome=outcome)
            self.metrics.observe("inv61_handle_seconds", dt)
            self.log.log("INFO" if outcome == "ok" else "WARNING", "call", tenant=tenant, peer=peer,
                         interface=iface, function=fn_name, outcome=outcome, duration_s=round(dt, 6),
                         request_id=rid, trace_id=trace_id)

    def _execute(self, sig, iface, fn_name, payload, h, tenant):
        """Returns (outcome, final). Non-final outcomes happen before any side effect and
        are not remembered by the idempotency cache, so a retry really runs."""
        if not self.admission.acquire(tenant, max(0.0, min(1.0, h["deadline"] - time.time()))):
            return {"error": "overloaded", "retry_after_ms": 100}, False
        try:
            # checked while holding an admission slot, so drain() cannot miss this call
            if self.health.draining:
                return {"error": "unavailable", "retry_after_ms": 200}, False
            try:
                args = decode_args([t for _, t in sig.params], payload)
            except CodecError as e:
                return {"error": "malformed-args", "code": e.code}, False
            impl = self.impls.get((iface, fn_name))
            if impl is None:
                return {"error": "unimplemented"}, False
            if time.time() >= h["deadline"]:          # re-check after queueing, before side effects
                return {"error": "deadline-exceeded"}, False
            try:
                value = impl(*args)
            except Exception:
                return {"error": "callee-trap"}, True
            if time.time() >= h["deadline"]:
                # the callee ran; say so, so the caller does not assume nothing happened
                return {"error": "deadline-exceeded", "executed": True}, True
            try:
                results = encode_args(sig.results, [] if not sig.results else [value])
            except CodecError as e:
                return {"error": "result-type", "code": e.code}, True
            return {"ok": results.hex()}, True
        finally:
            self.admission.release(tenant)


class Client:
    """Caller side: handshake, typed call with deadline, breaker, retry, reconnect."""

    def __init__(self, host: str, port: int, peer: str, key_id: str, psk: bytes, server_id: str,
                 package: Package, connect_timeout_s: float = 2.0, retry: RetryPolicy | None = None,
                 breaker: CircuitBreaker | None = None):
        self.addr, self.peer, self.kid, self.psk, self.server_id = (host, port), peer, key_id, psk, server_id
        self.pkg, self.connect_timeout = package, connect_timeout_s
        self.retry = retry or RetryPolicy()
        self.breaker = breaker or CircuitBreaker()
        self._sock = self._chan = None
        self._lock = threading.Lock()
        self.version = None

    def _connect(self):
        s = socket.create_connection(self.addr, timeout=self.connect_timeout)
        try:
            hs = ClientHandshake(self.peer, self.kid, self.psk)
            _send(s, json.dumps(hs.hello).encode())
            fin, chan, version = hs.finish(json.loads(_recv(s, HS_LIMIT)), self.server_id)
            _send(s, json.dumps(fin).encode())
        except BaseException:
            s.close()
            raise
        self._sock, self._chan, self.version = s, chan, version

    def close(self):
        if self._sock:
            self._sock.close()
        self._sock = self._chan = None

    def call(self, interface: str, function: str, args: list, timeout_s: float = 2.0,
             idempotent: bool = True, traceparent: str | None = None, request_id: str | None = None):
        sig = self.pkg.interfaces[interface].functions[function]
        deadline = time.time() + timeout_s
        rid = request_id or os.urandom(16).hex()      # SAME id across retries => server dedups
        payload = encode_args([t for _, t in sig.params], args)
        tp = traceparent if traceparent and parse_traceparent(traceparent) else child_traceparent(None, 1.0)[0]
        frame = encode_frame({"interface": qualified(self.pkg, interface), "version": self.pkg.version,
                              "function": function, "fp": fingerprint(sig.param_texts(), sig.result_texts()),
                              "deadline": deadline, "request_id": rid, "traceparent": tp}, payload)

        def attempt(_n):
            if not self.breaker.allow():
                return {"error": "circuit-open"}
            with self._lock:
                try:
                    if self._sock is None:
                        self._connect()
                    self._sock.settimeout(max(0.001, deadline - time.time()))
                    _send(self._sock, self._chan.seal(frame))
                    resp = self._chan.open(_recv(self._sock, (1 << 20) + 64))
                except socket.timeout:
                    self.close()
                    self.breaker.record(False)
                    return {"error": "deadline-exceeded"}
                except (OSError, TransportError, SecurityError, ValueError):
                    self.close()
                    self.breaker.record(False)
                    return {"error": "transport"}
            self.breaker.record(True)
            try:
                if resp[:1] == b"\x00":
                    vals = decode_args(sig.results, resp[1:])
                    return {"ok": vals[0] if vals else None}
                err = json.loads(resp[1:])
                if not isinstance(err, dict) or not isinstance(err.get("error"), str):
                    raise ValueError
                return err
            except (CodecError, ValueError):
                return {"error": "malformed-response"}

        return self.retry.call(attempt, deadline, idempotent)
