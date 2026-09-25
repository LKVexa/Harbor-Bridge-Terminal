"""Fault-injection, partition/reconnect, concurrency soak and restart suites (MC-043, MC-047)."""
from __future__ import annotations

import os
import random
import tempfile
import threading
import unittest

from _helpers import audit_log, cfg_with, config, durability, make_plane, runtime

SOAK_OPS = int(os.environ.get("PK_SOAK_OPS", "4000"))


class FaultInjection(unittest.TestCase):
    def test_mc043_random_adapter_outages_preserve_invariants(self):
        cfg = cfg_with(degraded={"allow_local_buffer": True, "read_only_on_partition": True},
                       limits={**config.DEFAULT["limits"], "retry_max_attempts": 3, "breaker_failure_threshold": 1000,
                               "rate_per_tenant_per_s": 1e9, "burst_per_tenant": 10**9})
        gp, tok, _, _, ad = make_plane(cfg=cfg)
        rng = random.Random(7)
        accepted = {}
        for i in range(SOAK_OPS // 4):
            ad["messaging"].available = rng.random() > 0.3
            ad["state"].available = rng.random() > 0.3
            idem = f"i{rng.randint(0, 400)}"
            try:
                r = gp.publish("api", "t1", "q", idem.encode(), idem, token=tok)
                if r.accepted:
                    accepted.setdefault(idem, idem.encode())
            except runtime.RuntimePlaneError:
                pass
            try:
                gp.state_set("api", "t1", f"k{i % 17}", b"v", token=tok)
            except runtime.RuntimePlaneError as exc:
                self.assertIn(exc.code, {"PK_ADAPTER_UNAVAILABLE", "PK_DEADLINE_EXCEEDED"})
        ad["messaging"].available = True
        gp.reconcile()
        delivered = gp.core.subscribe("api", "t1", "q")
        self.assertEqual(len(delivered), len(set(delivered)), "duplicate delivery")
        self.assertEqual(set(delivered), set(accepted.values()), "accepted message lost")
        self.assertEqual(gp.admission.in_flight, 0, "admission slot leaked")
        self.assertTrue(audit_log.verify_chain(gp.audit.events)[0])

    def test_mc043_handler_exceptions_do_not_leak_slots(self):
        gp, tok, *_ = make_plane()
        gp.core._bindings["api:invoke"].register_target("t1:boom", lambda p: 1 / 0)
        for _ in range(50):
            with self.assertRaises(ZeroDivisionError):
                gp.invoke("api", "t1", "boom", b"", token=tok)
        self.assertEqual(gp.admission.in_flight, 0)


class Soak(unittest.TestCase):
    def test_mc047_concurrent_multi_tenant_soak(self):
        cfg = cfg_with(limits={**config.DEFAULT["limits"], "rate_per_tenant_per_s": 1e9, "burst_per_tenant": 10**9,
                               "max_concurrency_per_tenant": 64, "max_concurrency_global": 256})
        gp, _, issuer, *_ = make_plane(cfg=cfg)
        toks = {f"t{i}": issuer.mint("api", f"t{i}", {"state", "messaging"}) for i in range(8)}
        errors = []

        def worker(tenant):
            try:
                for i in range(SOAK_OPS // 8):
                    gp.state_set("api", tenant, f"k{i % 50}", tenant.encode(), token=toks[tenant])
                    self.assertEqual(gp.state_get("api", tenant, f"k{i % 50}", token=toks[tenant]), tenant.encode())
                    gp.publish("api", tenant, "q", f"{tenant}:{i}".encode(), f"{i}", token=toks[tenant])
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
        ts = [threading.Thread(target=worker, args=(t,)) for t in toks]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(errors, [])
        for t in toks:
            msgs = gp.core.subscribe("api", t, "q")
            self.assertEqual(len(msgs), SOAK_OPS // 8)
            self.assertTrue(all(m.startswith(t.encode() + b":") for m in msgs))
        self.assertEqual(gp.admission.in_flight, 0)
        self.assertTrue(audit_log.verify_chain(gp.audit.events)[0])


class DisasterRecovery(unittest.TestCase):
    def test_mc047_mc050_restart_restore_from_journal_copy(self):
        with tempfile.TemporaryDirectory() as d:
            j = os.path.join(d, "primary.wal")
            a = durability.DurableAdapter("s", j, fsync=False)
            for i in range(200):
                a.set(f"t1/k{i}", str(i).encode())
            backup = os.path.join(d, "backup.wal")
            with open(j, "rb") as src, open(backup, "wb") as dst:
                dst.write(src.read())                       # backup = copy of journal
            os.remove(j)                                    # disaster: primary lost
            restored = durability.DurableAdapter("s", backup, fsync=False)
            self.assertEqual(restored.get("t1/k199"), b"199")
            self.assertEqual(restored.replayed, 200)


if __name__ == "__main__":
    unittest.main()
