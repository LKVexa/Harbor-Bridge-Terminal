#!/usr/bin/env python3
"""Installed-package smoke test (MC-028-T08): start `inv66 serve` as a real process against a fake
INV-63, admit one signed manifest over HTTP with a real bearer token, check health/ready/version,
then stop with SIGTERM.  Usage: python tools/smoke.py [path/to/inv66]"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "inv66_enterprise_wasm_control_plane" / "tests"))
import support  # noqa: E402

received = []


class INV63(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        received.append(body["delivery_id"])
        out = json.dumps({"delivery_id": body["delivery_id"], "accepted": True, "ref": "smoke"}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)


def main() -> int:
    exe = sys.argv[1] if len(sys.argv) > 1 else shutil.which("inv66")
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "anchor.key").write_bytes(os.urandom(32).hex().encode()); os.chmod(tmp / "anchor.key", 0o600)
    cfg = support.config()
    cfg["secrets"] = {"anchor_key": f"file://{tmp}/anchor.key"}
    cfg["identity"] = {"issuers": {"https://idp.acme": {"algorithm": "HS256", "keys": {"k1": "env://INV66_SMOKE_HS"}}}}
    (tmp / "config.json").write_text(json.dumps(cfg))
    dep = ThreadingHTTPServer(("127.0.0.1", 0), INV63)
    threading.Thread(target=dep.serve_forever, daemon=True).start()
    port = 18466
    env = dict(os.environ, INV66_SMOKE_HS=support.IDP_HS_KEY.decode())
    proc = subprocess.Popen([exe, "serve", "--config", str(tmp / "config.json"), "--store", str(tmp / "store"),
                             "--node-id", "smoke", "--org", "acme", "--port", str(port),
                             "--deploy-url", f"http://127.0.0.1:{dep.server_address[1]}/"], env=env,
                            stderr=subprocess.PIPE, text=True)
    base = f"http://127.0.0.1:{port}"
    result = {}
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(base + "/readyz", timeout=1) as r:
                    result["readyz"] = r.status
                    break
            except Exception:
                time.sleep(0.1)
        with urllib.request.urlopen(base + "/version") as r:
            result["version"] = json.loads(r.read())["version"]
        req = urllib.request.Request(base + "/v1/admit", data=json.dumps(support.request()).encode(), method="POST",
                                     headers={"Authorization": "Bearer " + support.token("user:ops")})
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read())
        result["admitted"] = resp["admitted"]
        result["delivered"] = resp["decision_id"] in received
        with urllib.request.urlopen(base + "/healthz") as r:
            result["healthz"] = r.status
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        dep.shutdown()
    result["exit_code"] = proc.returncode
    result["log_events"] = [json.loads(l)["event"] for l in proc.stderr.read().splitlines() if l.startswith("{")]
    ok = result.get("readyz") == 200 and result.get("admitted") and result.get("delivered") and result["exit_code"] == 0
    result["verdict"] = "PASS" if ok else "FAIL"
    print(json.dumps(result))
    (ROOT / "governance" / "SMOKE_RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
