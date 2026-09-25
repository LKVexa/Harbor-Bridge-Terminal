"""Component 10 / 02.20: a non-Python (Node.js) reporter produces byte-identical
CSP/1 envelopes and signatures that the Python verifier accepts.
Declared lane: requires ``node`` on PATH; reported NOT_RUN (skip with reason)
otherwise -- a skip is never a PASS."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from fixtures import SK_A, PK_A, sample, make_stack, tmpdir
from gap09_unified_observability.components import ed25519
from gap09_unified_observability.components.canonical import canonicalize, submission_envelope

NODE = shutil.which("node")
REPORTER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reporters", "node_reporter.mjs")


@unittest.skipUnless(NODE, "LANE node: Node.js not on PATH -- cross-language check NOT_RUN")
class TestNodeReporter(unittest.TestCase):
    def _run(self, env):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(env, fh)
        try:
            out = subprocess.run([NODE, REPORTER, SK_A.hex(), fh.name], capture_output=True, text=True, timeout=60, check=True)
        finally:
            os.unlink(fh.name)
        return json.loads(out.stdout)

    def test_byte_identical_and_verifiable(self):
        samples = [sample(value=v, at=100 + i) for i, v in enumerate([0.1, 1e21, 1e-7, 123.0, -5.5, 333333333.3333333])]
        env = submission_envelope("rep-a", "node-1", 1000, samples, "k1")
        r = self._run(env)
        self.assertEqual(r["public"], PK_A.hex())
        self.assertEqual(r["canonical"], canonicalize(env))
        self.assertTrue(ed25519.verify(PK_A, r["canonical"].encode(), bytes.fromhex(r["signature"])))
        # and it passes the full ingest path (signature produced by Node, verified by Python)
        ingest, *_ = make_stack(tmpdir())
        n = ingest.submit(reporter="rep-a", samples=samples[:1], submission_id="node-2", issued_at=1000,
                          signature=self._run(submission_envelope("rep-a", "node-2", 1000, samples[:1], "k1"))["signature"],
                          key_id="k1")
        self.assertEqual(n, 1)

    def test_unicode_key_and_string(self):
        env = {"z": "é€\U0001F600", "€": 1, "a": [None, True, 2**60, 1e21], "\r": 0.5}
        self.assertEqual(self._run(env)["canonical"], canonicalize(env))


if __name__ == "__main__":
    unittest.main()
