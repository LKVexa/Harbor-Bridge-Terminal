"""M33 - deterministic, idempotent bootstrap of a reference fabric site.

python3 -B tools/bootstrap.py --dir ./site-a --env production
Creates/validates: rendered config, trust-domain issuer key (0600), state store,
audit ledger, and one-time enrolment codes (printed once, only their hashes kept).
Runs health checks and writes bootstrap-evidence.json. Re-running converges.
Does NOT provision NATS/wasmCloud/wadm (W-M25): it records them as 'not_provisioned'
and the evidence is ok=false for --env production unless --reference is given."""
import argparse, hashlib, json, os, pathlib, platform, sys, time
PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent)); sys.dont_write_bytecode = True
from inv60_wasm_application_fabric.fabric import config as cf, identity, signing
from inv60_wasm_application_fabric.fabric.fabric import Fabric, VERSION
from inv60_wasm_application_fabric.fabric.ledger import AuditLedger


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True); ap.add_argument("--env", default="development")
    ap.add_argument("--reference", action="store_true", help="accept the reference tier (no real lattice)")
    ap.add_argument("--hosts", default="h1,h2,h3")
    a = ap.parse_args(argv)
    d = pathlib.Path(a.dir); d.mkdir(parents=True, exist_ok=True)
    log = open(d / "bootstrap.log", "a"); checks = {}
    def note(k, ok, detail=""):
        checks[k] = {"ok": bool(ok), "detail": detail}; log.write(f"{time.time():.3f} {k} {ok} {detail}\n")
    base = json.loads((PKG / "config/base.json").read_text())
    ovp = PKG / "config/overlays" / f"{a.env}.json"
    try:
        cfg = cf.render(base, (a.env, json.loads(ovp.read_text())))
        (d / "config.rendered.json").write_text(json.dumps(cfg, indent=1, sort_keys=True))
        note("config_valid", True, cf.digest(cfg))
    except Exception as e:
        note("config_valid", False, str(e)); cfg = None
    keyf = d / "issuer.key"
    if keyf.exists():
        seed = keyf.read_bytes(); note("issuer_key", len(seed) == 32, "reused")
    else:
        seed = os.urandom(32); keyf.write_bytes(seed); os.chmod(keyf, 0o600); note("issuer_key", True, "created")
    td = identity.TrustDomain(f"{a.env}.inv60", issuer_seed=seed)
    enrol = {}
    codes_file = d / "enrolment-codes.sha256.json"
    if not codes_file.exists():
        for h in a.hosts.split(","):
            c = td.issue_enrolment_code("host", h, "infra"); enrol[h] = c
        codes_file.write_text(json.dumps({h: hashlib.sha256(c.encode()).hexdigest() for h, c in enrol.items()}, indent=1))
        note("enrolment_codes", True, f"{len(enrol)} issued (printed once)")
    else:
        note("enrolment_codes", True, "already issued; not re-issued")
    fab = Fabric(trust=td, policy=signing.TrustPolicy(), state_dir=d / "state", ledger_path=d / "audit.jsonl")
    if not fab.ledger.records:
        fab.ledger.append("bootstrap", "bootstrap", {"env": a.env, "version": VERSION})
    note("ledger_verifies", fab.ledger.verify() >= 1)
    st = fab.status()
    note("status_live", st["live"])
    note("dependencies", all(st["dependencies"].values()), json.dumps(st["dependencies"]))
    for dep in ("nats", "wasmcloud_host", "wadm", "secret_backend", "telemetry_export"):
        note(f"external:{dep}", a.reference, "not_provisioned (reference tier accepted)" if a.reference else "not_provisioned")
    ok = all(c["ok"] for c in checks.values())
    ev = {"schema": "inv60.bootstrap/1", "ok": ok, "env": a.env, "version": VERSION, "python": platform.python_version(),
          "config_digest": cfg and cf.digest(cfg), "ledger_head": list(fab.ledger.head), "checks": checks,
          "release_digest": hashlib.sha256((PKG / "SHA256SUMS").read_bytes()).hexdigest() if (PKG / "SHA256SUMS").exists() else None}
    (d / "bootstrap-evidence.json").write_text(json.dumps(ev, indent=1, sort_keys=True))
    for h, c in enrol.items():
        print(f"enrolment code for {h}: {c}")
    print(json.dumps({"ok": ok, "failed": [k for k, v in checks.items() if not v["ok"]]}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
