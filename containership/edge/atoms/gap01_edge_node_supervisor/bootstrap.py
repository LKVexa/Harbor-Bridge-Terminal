"""Node bootstrap controller (1) and process entry point.

Deterministic, ordered boot phases.  Each phase has a retry budget; when a
phase exhausts it the supervisor enters *recovery mode*: it stays in
``joining``, never becomes placement-ready, and serves only status and
diagnostics until an operator intervenes.  On success a boot-complete
attestation (keyed MAC over the phase record and inventory digest) is
emitted and persisted to ``boot_attestation.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from collections.abc import Callable

from . import inventory
from .config import SecretBoundary, SupervisorConfig, load_config
from .controller import SupervisorController, Watchdog, sd_notify
from .errors import SupervisorError
from .health import HealthRegistry, SignalSpec
from .observability import get_logger, log_event
from .runtime import FakeRuntime, ProcessAdapter, RuntimeAdapter, RuntimeManager
from .security import Authenticator, AuthorizationPolicy, NodeIdentity
from .store import atomic_write

PHASES = ("integrity", "config", "state_dir", "identity", "inventory", "runtime", "health_registry",
          "recover", "endpoint")


@dataclass
class BootRecord:
    phases: list = field(default_factory=list)
    recovery_mode: bool = False
    failed_phase: str | None = None
    attestation: dict | None = None


def run_phases(steps: dict[str, Callable[[], object]], *, retries: int = 2,
               backoff_s: float = 0.2, sleep=time.sleep) -> BootRecord:
    rec = BootRecord()
    for name in PHASES:
        if name not in steps:
            continue
        for attempt in range(retries + 1):
            t0 = time.monotonic()
            try:
                steps[name]()
                rec.phases.append({"phase": name, "ok": True, "attempt": attempt,
                                   "seconds": round(time.monotonic() - t0, 4)})
                break
            except Exception as exc:  # noqa: BLE001
                rec.phases.append({"phase": name, "ok": False, "attempt": attempt,
                                   "error": getattr(exc, "code", type(exc).__name__)})
                if attempt == retries:
                    rec.recovery_mode = True
                    rec.failed_phase = name
                    return rec
                sleep(backoff_s * (2 ** attempt))
    return rec


def build(args: argparse.Namespace):
    log = get_logger()
    ctx: dict = {}

    def p_integrity():
        """Verify the installed package against RELEASE_MANIFEST.json (19)."""
        from .security import verify_artifacts
        pkg = pathlib.Path(__file__).resolve().parent
        manifest = pathlib.Path(args.manifest) if args.manifest else pkg / "RELEASE_MANIFEST.json"
        if not manifest.exists():
            if args.require_manifest:
                raise SupervisorError("E_SIGNATURE", "release manifest missing")
            return
        key = SecretBoundary.from_file(args.release_key).reveal() if args.release_key else None
        problems = [p for p in verify_artifacts(pkg, manifest, key)
                    if not p.startswith(("CHECKSUMS", "RELEASE_MANIFEST"))]
        if problems:
            raise SupervisorError("E_SIGNATURE", "; ".join(problems[:5]))

    def p_config():
        key = SecretBoundary.from_file(args.config_key).reveal() if args.config_key else None
        if args.config and key is None and not args.allow_unsigned_config:
            raise SupervisorError("E_SIGNATURE", "config signature key required (or --allow-unsigned-config)")
        ctx["cfg"] = load_config(args.config, key=key) if args.config else SupervisorConfig()

    def p_state():
        d = pathlib.Path(args.state_dir)
        d.mkdir(parents=True, exist_ok=True)
        os.chmod(d, 0o700)
        probe = d / ".write-probe"
        atomic_write(probe, b"ok")
        probe.unlink()

    def p_identity():
        key = SecretBoundary.from_file(args.node_key).reveal() if args.node_key else os.urandom(32)
        ctx["identity"] = NodeIdentity(args.node, key)

    def p_inventory():
        ctx["inventory"] = inventory.snapshot((args.state_dir,))

    def p_runtime():
        adapters: dict[str, RuntimeAdapter] = {"process": ProcessAdapter()}
        if args.simulate:
            adapters = {"process": FakeRuntime("process"), "wasm": FakeRuntime("wasm")}
        ctx["runtime"] = RuntimeManager(adapters)

    def p_health():
        reg = HealthRegistry(max_signals=ctx["cfg"].max_health_signals)
        specs: list[dict] = (json.loads(pathlib.Path(args.signals).read_text()) if args.signals
                             else [{"name": "runtime", "required": True}])
        for spec in specs:
            reg.register(SignalSpec(spec["name"], spec.get("required", True),
                                    spec.get("staleness_s", ctx["cfg"].health_staleness_s),
                                    frozenset(spec.get("reporters", []))))
        ctx["health"] = reg

    def p_recover():
        keys = {c: SecretBoundary.from_file(p).reveal() for c, p in
                (kv.split("=", 1) for kv in args.caller_key)}
        policy = AuthorizationPolicy()
        for binding in args.bind:
            caller, roles = binding.split("=", 1)
            policy.bind(caller, *roles.split(","))
        ctl = SupervisorController(args.node, args.state_dir, config=ctx["cfg"],
                                   runtime=ctx["runtime"], health=ctx["health"],
                                   authenticator=Authenticator(keys, skew_s=ctx["cfg"].request_skew_s,
                                                               window=ctx["cfg"].replay_window),
                                   policy=policy, logger=log)
        ctl.start()
        ctx["ctl"] = ctl

    def p_endpoint():
        from .server import ControlServer, make_probe_server, serve_background
        ctx["control"] = ControlServer(args.socket, ctx["ctl"])
        ctx["probe"] = make_probe_server(ctx["ctl"], args.probe_port)
        serve_background(ctx["control"])
        serve_background(ctx["probe"])

    rec = run_phases({"integrity": p_integrity, "config": p_config, "state_dir": p_state,
                      "identity": p_identity,
                      "inventory": p_inventory, "runtime": p_runtime,
                      "health_registry": p_health, "recover": p_recover, "endpoint": p_endpoint})
    if not rec.recovery_mode:
        digest = hashlib.sha256(json.dumps(rec.phases, sort_keys=True).encode()).hexdigest()
        rec.attestation = ctx["identity"].attest(
            {"phases_sha256": digest, "inventory_digest": ctx["inventory"]["digest"],
             "version": _version()}, nonce=uuid.uuid4().hex)
        atomic_write(pathlib.Path(args.state_dir) / "boot_attestation.json",
                     json.dumps(rec.attestation, sort_keys=True).encode())
    log_event(log, "GAP01-BOOT", "bootstrap finished", recovery_mode=rec.recovery_mode,
              failed_phase=rec.failed_phase, phases=rec.phases)
    return rec, ctx


def _version() -> str:
    from . import __version__
    return __version__


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gap01-supervisor")
    ap.add_argument("--node", required=True)
    ap.add_argument("--state-dir", default="/var/lib/gap01")
    ap.add_argument("--socket", default="/run/gap01/control.sock")
    ap.add_argument("--probe-port", type=int, default=9101)
    ap.add_argument("--config")
    ap.add_argument("--config-key")
    ap.add_argument("--node-key")
    ap.add_argument("--signals")
    ap.add_argument("--caller-key", action="append", default=[], help="caller=/path/to/keyfile")
    ap.add_argument("--bind", action="append", default=[], help="caller=role1,role2")
    ap.add_argument("--release-key", help="HMAC key verifying RELEASE_MANIFEST.json signature")
    ap.add_argument("--allow-unsigned-config", action="store_true",
                    help="explicit opt-in to accept an unsigned config file (not for production)")
    ap.add_argument("--manifest", help="release manifest path (default: the package's RELEASE_MANIFEST.json)")
    ap.add_argument("--require-manifest", action="store_true", help="refuse to boot without a manifest")
    ap.add_argument("--simulate", action="store_true", help="use fake runtimes (testing only)")
    ap.add_argument("--tick-s", type=float, default=1.0)
    ap.add_argument("--once", action="store_true", help="boot, tick once, exit (smoke)")
    args = ap.parse_args(argv)
    rec, ctx = build(args)
    if rec.recovery_mode:
        print(json.dumps({"recovery_mode": True, "failed_phase": rec.failed_phase,
                          "phases": rec.phases}), file=sys.stderr)
        return 3
    ctl: SupervisorController = ctx["ctl"]
    wd = Watchdog(ctl, interval=max(1.0, ctl.cfg.watchdog_timeout_s / 3))
    wd.start()
    sd_notify("READY=1")
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))
    while not stop["flag"]:
        ctl.tick()
        if args.once:
            break
        time.sleep(args.tick_s)
    sd_notify("STOPPING=1")
    ctx["control"].shutdown()
    ctx["probe"].shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
