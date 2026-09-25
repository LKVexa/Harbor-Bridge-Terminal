"""Deployment preflight (MC-050-02): config, runtime, TLS, backend pin, disk, secrets. Exit 1 on any problem."""
import argparse, json, os, shutil, sys
import _path  # noqa: F401
from inv05_current_control_state_system.backend import ExternalBackendContract, runtime_self_test
from inv05_current_control_state_system.config import load_layers
from inv05_current_control_state_system.security import SecretProvider, check_tls_context, server_tls_context


def run(a):
    problems, info = [], {}
    layers = {"base": a.config}
    if a.env: layers["environment"] = a.env
    if a.site: layers["site"] = a.site
    try:
        cfg = load_layers(layers)
        info["config_sha256"] = cfg.sha256
    except Exception as e:  # noqa: BLE001
        return [f"config invalid: {e}"], info
    rt = runtime_self_test(require_pk_core=a.require_pk_core)
    problems += rt["problems"]
    sp = SecretProvider(a.secret_dir)
    for k in ("storage.data_key", "audit.key") + (("auth.token_key",) if cfg["auth.allow_tokens"] else ()):
        try:
            sp.get(cfg[k])
        except Exception:  # noqa: BLE001
            problems.append(f"secret for {k} unavailable")
    if cfg["tls.enabled"]:
        try:
            ctx = server_tls_context(cfg["tls.cert_file"], sp.get(cfg["tls.key_file"]).decode(), cfg["tls.ca_file"])
            problems += check_tls_context(ctx, server=True)
        except Exception as e:  # noqa: BLE001
            problems.append(f"TLS material invalid: {type(e).__name__}")
    d = cfg["storage.data_dir"]
    probe = d if os.path.isdir(d) else os.path.dirname(os.path.abspath(d))
    free = shutil.disk_usage(probe).free
    info["free_bytes"] = free
    if free < a.min_free_bytes:
        problems.append(f"insufficient free disk: {free} < {a.min_free_bytes}")
    if a.require_ha_backend:
        problems += ExternalBackendContract().preflight()
    return problems, info


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--env"); ap.add_argument("--site")
    ap.add_argument("--secret-dir"); ap.add_argument("--min-free-bytes", type=int, default=2 * 1024**3)
    ap.add_argument("--require-ha-backend", action="store_true"); ap.add_argument("--require-pk-core", action="store_true")
    a = ap.parse_args()
    p, info = run(a)
    print(json.dumps({"ok": not p, "problems": p, **info}, indent=2))
    sys.exit(1 if p else 0)
