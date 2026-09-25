"""M03/M31 - independent client and server processes over TCP."""
import json
import os
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wrpc import node, wit  # noqa: E402
from tools_serve_wit import DEMO_WIT  # noqa: E402  (tiny shim below)


class TwoProcessTest(unittest.TestCase):
    def test_separate_server_process(self):
        psk = os.urandom(32)
        env = dict(os.environ, INV61_PSK=psk.hex())
        p = subprocess.Popen([sys.executable, "-B", str(ROOT / "tools" / "serve.py"), "--peer", "svc-a",
                              "--tenant", "t1", "--key-id", "k1"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, env=env, text=True)
        try:
            ready = json.loads(p.stdout.readline())
            self.assertTrue(ready["ready"])
            c = node.Client(ready["host"], ready["port"], "svc-a", "k1", psk, "node-local", wit.parse(DEMO_WIT))
            self.assertEqual(c.call("store", "put", ["x", 9]), {"ok": None})
            self.assertEqual(c.call("store", "get", ["x"]), {"ok": 9})
            remote_pid = c.call("store", "pid", [])["ok"]
            self.assertNotEqual(remote_pid, os.getpid())
            self.assertEqual(remote_pid, p.pid)
            c.close()
        finally:
            p.stdin.close()
            self.assertEqual(p.wait(timeout=10), 0)          # clean drain + stop on stdin close


if __name__ == "__main__":
    unittest.main()
