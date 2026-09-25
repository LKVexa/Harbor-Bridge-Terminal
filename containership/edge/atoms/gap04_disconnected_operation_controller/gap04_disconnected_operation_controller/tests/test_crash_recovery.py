"""C31 crash/restart qualification: real child processes are terminated with os._exit(137)
at every named persistence transition, and with SIGKILL at random times. After each
crash the state directory is reopened and invariants are checked:
  I1 every acknowledged decision is recovered (durability)
  I2 no decision is duplicated; request ids stay idempotent (replay safety)
  I3 hash chain + MACs verify (integrity) and generation strictly increases (fencing)
  I4 reconciliation resumes with the same txn id and completes exactly once."""
import os, random, signal, subprocess, sys, time, unittest
from pathlib import Path
from _util import T, Tmp, node
from gap04_disconnected_operation_controller.runtime import crypto
from gap04_disconnected_operation_controller.runtime.journal import Journal

HERE = Path(__file__).parent
SEED, PUB = crypto.generate_signing_key()
ENV = dict(os.environ, CP_SEED=SEED.hex(), CP_PUB=PUB, PYTHONDONTWRITEBYTECODE="1")


def run(d, phase, n=0, crash=None, start=0, timeout=60):
    env = dict(ENV, START=str(start))
    env.pop("GAP04_CRASHPOINT", None)
    if crash:
        env["GAP04_CRASHPOINT"] = crash
    p = subprocess.run([sys.executable, str(HERE / "crash_worker.py"), str(d), phase, str(n)], env=env,
                       capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.splitlines()


def reopen(d):
    cp = T.ControlPlane(); cp.seed, cp.pub = SEED, PUB
    return node(d, cp=cp)


class CrashRecovery(unittest.TestCase):
    def check(self, d, acked):
        n, cp, m = reopen(d)
        try:
            ids = [x["decision_id"] for x in n.controller.decisions]
            self.assertEqual(len(ids), len(set(ids)), "I2 duplicate decision")
            for rid, did in acked:
                self.assertIn(did, ids, f"I1 acked decision {rid} lost")
            Journal.verify_export(n.journal.export(0), bytes(n.keyring.audit_key))
            return n, ids
        except Exception:
            n.close(); raise

    def test_T_C31_decide_crashpoints(self):
        for cpnt in ("journal.before_write", "journal.partial_write", "journal.after_fsync", "decide.after_wal",
                     "decide.after_effect", "atomic.before_rename"):
            with self.subTest(crashpoint=cpnt), Tmp() as d:
                rc, out = run(d, "setup"); self.assertEqual(rc, 0, out)
                rc, out = run(d, "decide", 20, crash=f"{cpnt}:4")
                acked = [(l.split()[1], l.split()[2]) for l in out if l.startswith("ACK")]
                n, ids = self.check(d, acked)
                gen = n.generation
                n.clock.anchor_trusted(n.clock.hwm)
                # I2: retrying every attempted request id never duplicates
                for i in range(20):
                    n.decide("restart", f"ns/w{i}", f"req-{i:08d}")
                self.assertEqual(len(n.controller.decisions), 20)
                n.close()
                n2, _ = self.check(d, acked); self.assertGreater(n2.generation, gen); n2.close()

    def test_T_C31_reconcile_crashpoints(self):
        for cpnt in ("reconcile.after_begin", "reconcile.after_batch_ack", "reconcile.before_compact",
                     "compact.before_replace"):
            with self.subTest(crashpoint=cpnt), Tmp() as d:
                self.assertEqual(run(d, "setup")[0], 0)
                rc, out = run(d, "decide", 450)
                self.assertEqual(rc, 0, out[-3:])
                rc, out = run(d, "reconcile", crash=f"{cpnt}:1")
                self.assertEqual(rc, 137, out)
                n, cp, m = reopen(d)
                txn = (n.state["reconcile"] or {}).get("txn_id")
                n.close()
                rc, out = run(d, "reconcile")
                self.assertEqual(rc, 0, out)
                n, cp, m = reopen(d)
                last = n.state["last_reconciliation"]
                self.assertIsNotNone(last)
                if txn:
                    self.assertEqual(last["txn_id"], txn, "I4 txn id changed across resume")
                self.assertEqual(last["decision_count"], 450)
                self.assertIsNone(n.state["reconcile"])
                self.assertIsNone(n.controller.partitioned_since)
                self.assertEqual(n.controller.decisions, [])
                Journal.verify_export(n.journal.export(0), bytes(n.keyring.audit_key))
                n.close()

    def test_T_C31_random_sigkill(self):
        rnd = random.Random(int(os.environ.get("GAP04_SEED", "4")))
        with Tmp() as d:
            self.assertEqual(run(d, "setup")[0], 0)
            acked, start = [], 0
            for _ in range(int(os.environ.get("GAP04_KILL_ROUNDS", "6"))):
                env = dict(ENV, START=str(start))
                p = subprocess.Popen([sys.executable, str(HERE / "crash_worker.py"), str(d), "decide", "100000"],
                                     env=env, stdout=subprocess.PIPE, text=True)
                deadline = time.time() + rnd.uniform(0.6, 1.5)
                lines = []
                while time.time() < deadline:
                    line = p.stdout.readline()
                    if not line:
                        break
                    lines.append(line)
                os.kill(p.pid, signal.SIGKILL)
                rest = p.communicate()[0]
                lines += rest.splitlines()
                acked += [(l.split()[1], l.split()[2]) for l in lines if l.startswith("ACK")]
                if acked:
                    start = int(acked[-1][0].split("-")[1]) + 1
                n, _ = self.check(d, acked)
                n.close()
            self.assertGreater(len(acked), 0)


if __name__ == "__main__":
    unittest.main()
