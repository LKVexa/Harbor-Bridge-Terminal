"""Edge paths flagged by the coverage gate: listeners, observability, preflight, bridge races."""
import io
import json
import pathlib
import random
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

from _util import rt, sub

AF = rt.AsyncFunctions


class Edges(unittest.TestCase):
    def test_invoke_type_checks(self):
        f = AF("i", declared={"a": True})
        with self.assertRaises(TypeError):
            f.invoke("a", caller_is_async=1)
        with self.assertRaises(ValueError):
            f.invoke(["a"])

    def test_listener_contract(self):
        f = AF("i", declared={"a": True})
        c = f.invoke("a")
        self.assertIsNone(f.add_terminal_listener(c.call_id, lambda *a: None))
        with self.assertRaises(ValueError):
            f.add_terminal_listener(c.call_id, lambda *a: None)
        f.complete(c.call_id, 1)
        self.assertEqual(f.add_terminal_listener(c.call_id, lambda *a: None).outcome, rt.Outcome.COMPLETED)
        with self.assertRaises(ValueError):
            f.add_terminal_listener(999, lambda *a: None)
        f.remove_terminal_listener(999)

    def test_bridge_registers_on_already_terminal_call(self):
        br = sub("bridge")
        holder = {}

        def sink(ev):  # cancels the queued call during invoke's post-lock dispatch
            if ev["type"] == "call_queued":
                holder["f"].cancel(ev["call_id"], "operator")

        f = AF("i", declared={"q": True}, reentrancy={"q": rt.ReentrancyPolicy(rt.ReentrancyMode.QUEUE, 1)},
               event_sink=sink)
        holder["f"] = f
        f.invoke("q")
        with self.assertRaises(rt.CallCancelled):
            br.SyncBridge(f).call("q", lambda st: None)

    def test_histogram_quantiles_and_overflow(self):
        obs = sub("observability")
        h = obs.Histogram(lo_exp=2, hi_exp=4)
        self.assertIsNone(h.quantile(0.5))
        for v in (1, 5, 9, 100):
            h.record(v)
        self.assertEqual(h.quantile(0.25), 4)
        self.assertEqual(h.quantile(1.0), -1)            # overflow bucket
        self.assertEqual(h.counts, [1, 1, 1, 1])

    def test_eventlog_sampling_hashing_eviction_writer(self):
        obs = sub("observability")
        lines = []
        log = obs.EventLog(capacity=3, sample_rate=0.0, writer=lines.append, rng=random.Random(1))
        log({"type": "call_completed", "severity": "debug"})
        self.assertEqual(log.sampled_out, 1)
        log.sample_rate = 1.0
        log({"type": "call_cancelled", "tenant": "acme", "workload": "w1"})
        log({"type": "double_delivery", "severity": "critical"})
        log({"type": "call_cancelled"})
        log({"type": "callee_trapped"})                    # full: evicts oldest non-critical
        evs = log.events()
        self.assertEqual([e["type"] for e in evs], ["double_delivery", "call_cancelled", "callee_trapped"])
        self.assertTrue(all("acme" not in l for l in lines))
        self.assertTrue(json.loads(lines[0])["tenant"].startswith("h:"))
        crit = obs.EventLog(capacity=1)
        crit({"type": "double_delivery"}); crit({"type": "callee_trapped"})
        self.assertEqual(crit.dropped, 1)

        def bad(_l):
            raise OSError
        b = obs.EventLog(writer=bad)
        b({"type": "x"})
        self.assertEqual(b.write_failures, 1)

    def test_preflight_cli_and_good_pk_core(self):
        pre = sub("preflight")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = pre.main([])
        self.assertIn("PREFLIGHT", buf.getvalue())
        self.assertEqual(code, 0)
        with redirect_stdout(io.StringIO()) as j:
            pre.main(["--json"])
        self.assertIn("package_version", json.loads(j.getvalue()))
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / "goodpk"
            root.mkdir()
            (root / "__init__.py").write_text("__version__ = '1.4.0'\n")
            for m in ("contract", "checklist", "component", "integration"):
                (root / f"{m}.py").write_text("")
            sys.path.insert(0, d)
            try:
                rep = pre.run(require_pk_core=True, pk_core_module="goodpk")
                bad = root.parent / "brokenpk"
                bad.mkdir()
                (bad / "__init__.py").write_text("raise ImportError('corrupted')\n")
                rep2 = pre.run(require_pk_core=True, pk_core_module="brokenpk")
            finally:
                sys.path.remove(d)
                for k in [k for k in sys.modules if k.startswith(("goodpk", "brokenpk"))]:
                    del sys.modules[k]
        self.assertTrue(rep["ok"], rep["errors"])
        self.assertEqual(rep["pk_core"]["version"], "1.4.0")
        self.assertFalse(rep2["ok"])
        self.assertIn("import failed", " ".join(rep2["errors"]))


if __name__ == "__main__":
    unittest.main()
