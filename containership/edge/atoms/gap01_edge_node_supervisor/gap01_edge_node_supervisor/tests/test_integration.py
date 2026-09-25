"""Integration + chaos tests (47, 51): real UNIX socket endpoint, real OS
processes via ProcessAdapter, HTTP probes, and SIGKILL of the supervisor
process followed by restart and reconciliation.  POSIX only."""
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

from helpers import KEYS, QUIET, ROOT

from gap01_edge_node_supervisor import make_request
from gap01_edge_node_supervisor.client import call
from gap01_edge_node_supervisor.controller import SupervisorController
from gap01_edge_node_supervisor.health import SignalSpec
from gap01_edge_node_supervisor.runtime import ProcessAdapter, RuntimeManager, sleeper_argv
from gap01_edge_node_supervisor.security import Authenticator, AuthorizationPolicy
from gap01_edge_node_supervisor.server import ControlServer, make_probe_server, serve_background

POSIX = os.name == "posix" and hasattr(socket, "AF_UNIX")


@unittest.skipUnless(POSIX, "POSIX only")
class RealProcessIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="gap01-it-"))
        pol = AuthorizationPolicy()
        pol.bind("cp", "control-plane")
        pol.bind("hr", "health-reporter")
        self.adapter = ProcessAdapter()
        self.ctl = SupervisorController(
            "it-node", self.tmp / "state", runtime=RuntimeManager({"process": self.adapter}),
            authenticator=Authenticator({"cp": KEYS["cp"], "hr": KEYS["hr"]}), policy=pol,
            logger=QUIET, pressure_probe=lambda: {"under_pressure": False, "reasons": []})
        self.ctl.health.register(SignalSpec("runtime"))
        self.ctl.start()
        self.sock = str(self.tmp / "run" / "control.sock")
        self.srv = ControlServer(self.sock, self.ctl)
        serve_background(self.srv)
        self.probe = make_probe_server(self.ctl, 0)
        serve_background(self.probe)
        self.port = self.probe.server_address[1]

    def tearDown(self):
        for n in list(self.adapter.procs):
            self.adapter.kill(n)
        self.srv.shutdown(); self.srv.server_close()
        self.probe.shutdown(); self.probe.server_close()

    def rpc(self, caller, op, args=None):
        return call(self.sock, make_request(caller, KEYS[caller], op, args))

    def http(self, path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def test_socket_permissions(self):
        self.assertEqual(os.stat(self.sock).st_mode & 0o777, 0o600)

    def test_full_lifecycle_with_real_processes(self):
        self.assertEqual(self.http("/readyz")[0], 503)
        self.assertTrue(self.rpc("hr", "report_health", {"signal": "runtime", "ok": True})["ok"])
        self.assertTrue(self.rpc("cp", "transition", {"to": "ready"})["ok"])
        self.ctl.tick()
        self.assertEqual(self.http("/readyz")[0], 200)
        pids = []
        for i, t in enumerate(("trusted", "hostile", "first-party")):
            r = self.rpc("cp", "admit", {"workload": f"p{i}", "trust_class": t,
                                         "argv": list(sleeper_argv(60))})
            self.assertTrue(r["ok"], r)
            pids.append(int(r["result"]["handle"]))
        r = self.rpc("cp", "drain", {"timeout_s": 5})
        deadline = time.time() + 10
        while self.ctl.sup.state != "stopped" and time.time() < deadline:
            time.sleep(0.1)
            self.ctl.tick()
        self.assertEqual(self.ctl.sup.state, "stopped")
        for pid in pids:
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)
        code, body = self.http("/metrics")
        self.assertEqual(code, 200)
        self.assertIn("gap01_requests_total", body)
        self.assertEqual(self.http("/livez")[0], 200)

    def test_sigterm_ignoring_process_is_force_killed(self):
        self.rpc("hr", "report_health", {"signal": "runtime", "ok": True})
        self.rpc("cp", "transition", {"to": "ready"})
        argv = [sys.executable, "-c",
                "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"]
        pid = int(self.rpc("cp", "admit", {"workload": "stubborn", "trust_class": "untrusted",
                                           "argv": argv})["result"]["handle"])
        time.sleep(0.3)
        self.ctl.cfg = self.ctl.cfg.hot_reload({"drain_kill_after_s": 0})
        self.rpc("cp", "drain", {"timeout_s": 0})
        deadline = time.time() + 10
        while self.ctl.sup.state != "stopped" and time.time() < deadline:
            time.sleep(0.1)
            self.ctl.tick()
        self.assertEqual(self.ctl.sup.state, "stopped")
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)


@unittest.skipUnless(POSIX, "POSIX only")
class ProcessChaosTest(unittest.TestCase):
    """Boot the real entry point, mutate state over the socket, SIGKILL it,
    reboot, and verify the recovered state and audit chain."""

    def boot(self, tmp):
        args = [sys.executable, "-m", "gap01_edge_node_supervisor.bootstrap", "--node", "chaos",
                "--state-dir", str(tmp / "state"), "--socket", str(tmp / "run" / "c.sock"),
                "--probe-port", "0", "--simulate", "--tick-s", "0.2",
                "--manifest", str(tmp / "no-manifest.json"),
                "--caller-key", f"cp={tmp / 'cp.key'}", "--caller-key", f"hr={tmp / 'hr.key'}",
                "--bind", "cp=control-plane", "--bind", "hr=health-reporter"]
        env = dict(os.environ, PYTHONPATH=str(ROOT), GAP01_LOG_LEVEL="CRITICAL")
        p = subprocess.Popen(args, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        sock = tmp / "run" / "c.sock"
        for _ in range(100):
            if sock.exists():
                try:
                    call(str(sock), make_request("hr", KEYS["hr"], "status"))
                    break
                except (ConnectionRefusedError, FileNotFoundError, json.JSONDecodeError):
                    pass
            time.sleep(0.1)
        return p, str(sock)

    def test_sigkill_and_recover(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="gap01-chaos-"))
        for c in ("cp", "hr"):
            (tmp / f"{c}.key").write_bytes(KEYS[c])
            os.chmod(tmp / f"{c}.key", 0o600)
        p, sock = self.boot(tmp)
        try:
            r = call(sock, make_request("hr", KEYS["hr"], "report_health", {"signal": "runtime", "ok": True}))
            self.assertTrue(r["ok"], r)
            self.assertTrue(call(sock, make_request("cp", KEYS["cp"], "transition", {"to": "ready"}))["ok"])
            for i in range(3):
                self.assertTrue(call(sock, make_request("cp", KEYS["cp"], "admit",
                                {"workload": f"w{i}", "trust_class": "trusted", "kind": "wasm"}))["ok"])
            self.assertTrue(call(sock, make_request("cp", KEYS["cp"], "cordon"))["ok"])
        finally:
            p.send_signal(signal.SIGKILL)
            p.wait(10)
        self.assertTrue((tmp / "state" / "boot_attestation.json").exists())
        p2, sock = self.boot(tmp)
        try:
            st = call(sock, make_request("cp", KEYS["cp"], "status"))["result"]
            # Simulated runtimes are in-memory, so the workloads are "lost" on
            # process death and reconciliation must remove them; the cordon persists.
            self.assertEqual(st["state"], "cordoned")
            self.assertEqual(st["workloads"], {})
        finally:
            p2.terminate()
            p2.wait(10)
        from gap01_edge_node_supervisor.store import AuditLog
        self.assertTrue(AuditLog.verify(tmp / "state" / "audit.jsonl")[0])


if __name__ == "__main__":
    unittest.main()
