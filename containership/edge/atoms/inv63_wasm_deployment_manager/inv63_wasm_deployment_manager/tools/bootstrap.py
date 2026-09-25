"""Deterministic day-0 bootstrap (INV-63-C040).

    python tools/bootstrap.py --state-dir /var/lib/inv63 --config-dir deploy/config --env prod --site edge-site-a \
        --hosts hosts.json [--reference-time <unix ts>]

Steps (each fails closed with a structured error and non-zero exit):
 1. compose + validate config (defaults <- base <- env <- site)
 2. resolve secret refs (token keys, data key) -- never from config literals
 3. create state dir 0700, open/verify journal (sealed), acquire leader epoch
 4. run preflight; required checks must pass
 5. construct the service and print its status JSON
Idempotent: re-running on an initialised state dir replays the journal.
"""
import argparse, json, os, pathlib, sys

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
import importlib
m = lambda n: importlib.import_module(f"{PKG.name}.{n}")


def main(argv=None, env=None):
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True); ap.add_argument("--config-dir", default=str(PKG / "deploy/config"))
    ap.add_argument("--env", required=True); ap.add_argument("--site", required=True)
    ap.add_argument("--hosts", required=True, help="JSON file: {host: spread_label}")
    ap.add_argument("--reference-time", type=float)
    a = ap.parse_args(argv)
    errors = m("errors"); security = m("security"); config = m("config")
    try:
        cfg = config.compose(*config.load_layers(a.config_dir, a.env, a.site))
        refs = cfg["secret_refs"]
        for need in ("token_keys", "data_key"):
            if need not in refs:
                raise errors.DeploymentError(errors.ErrorCode.CONFIG_INVALID, f"secret_refs.{need} required")
        token_keys = json.loads(security.resolve_secret_ref(refs["token_keys"], env))
        tokens = security.TokenAuthority({k: bytes.fromhex(v) for k, v in token_keys.items()})
        sealer = security.Sealer({"d1": bytes.fromhex(security.resolve_secret_ref(refs["data_key"], env).decode())})
        sd = pathlib.Path(a.state_dir); sd.mkdir(parents=True, exist_ok=True); os.chmod(sd, 0o700)
        hosts = json.loads(pathlib.Path(a.hosts).read_text())
        journal = m("store").Journal(sd, sealer=sealer)
        adapter = m("adapter").WadmAdapter(None)   # production transport is injected by the host process
        checks = m("preflight").run(hosts=hosts, state_dir=sd, adapter=adapter, reference_time=a.reference_time,
                                    max_clock_skew_s=cfg["max_clock_skew_s"])
        if not m("preflight").ready(checks):
            failed = [c.to_dict() for c in checks if c.required and not c.ok]
            raise errors.DeploymentError(errors.ErrorCode.PRECONDITION_FAILED, "preflight failed", {"checks": failed})
        trusted = {}
        if "artifact_keys" in refs:   # JSON {key_id: ed25519 public key hex}; absent -> every deploy fails closed
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            trusted = {k: Ed25519PublicKey.from_public_bytes(bytes.fromhex(v))
                       for k, v in json.loads(security.resolve_secret_ref(refs["artifact_keys"], env)).items()
                       if k in cfg["trusted_key_ids"]}
        svc = m("service").DeploymentService(config=cfg, hosts=hosts, adapter=adapter, journal=journal, tokens=tokens,
                                             verifier=security.ArtifactVerifier(trusted))
        print(json.dumps(svc.status(reference_time=a.reference_time), indent=2, default=str))
        return 0
    except errors.DeploymentError as exc:
        print(json.dumps(exc.to_dict(), indent=2), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
