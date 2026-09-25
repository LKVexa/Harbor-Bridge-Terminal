"""C089 (disaster/partition/reconnect), C055/C058 (failover N/A), C095 (backup N/A):
applicability records are machine-checked and the local reconnect behaviour is exercised."""
import json
import unittest

from _pkg import PKG_DIR, control as C, security as X, stream as S


class ApplicabilityTest(unittest.TestCase):
    def test_matrix_dispositions_complete(self):
        m = json.loads((PKG_DIR / "deployment" / "applicability-matrix.json").read_text())
        tiers = {"cloud", "datacenter", "near-edge", "far-edge"}
        self.assertEqual(set(m["tiers"]), tiers)
        for concern in m["concerns"]:
            for tier in tiers:
                d = concern["disposition"][tier]
                self.assertIn(d["status"], {"applicable", "not_applicable", "delegated"})
                self.assertTrue(d["rationale"])
                if d["status"] == "delegated":
                    self.assertTrue(d.get("owner_element"))
                if d["status"] != "applicable":
                    self.assertTrue(concern.get("evidence"), concern["id"])


class PartitionReconnectTest(unittest.TestCase):
    def test_partitioned_peer_is_a_dropped_end_not_a_silent_eof(self):
        # A transport partition between two instances surfaces at the INV-17 seam as the
        # adjacent layer dropping the end; the reader must see an error, never EOF.
        s = S.Stream(bytes); s.grant(2); s.write(b"before-partition")
        s.drop_writer()
        self.assertEqual(s.read(), b"before-partition")
        with self.assertRaises(S.EndDropped): s.read()

    def test_reconnect_is_a_new_stream_with_idempotent_resend(self):
        auth = X.CapabilityAuthority()
        old = C.StreamRegistry(authority=auth)
        t = auth.issue("s-1", "t", "w", ["open", "write", "read"])
        s = old.open(int, tenant="t", workload="w", token=t, stream_id="s-1"); s.grant(2)
        s.write(1, idempotency_key="op-1")
        new = C.StreamRegistry(authority=auth)  # instance lost; peer reconnects elsewhere
        with self.assertRaises(C.StreamNotFound):
            new.get("s-1", tenant="t", workload="w", token=t, right="write")
        t2 = auth.issue("s-2", "t", "w", ["open", "write"])
        s2 = new.open(int, tenant="t", workload="w", token=t2, stream_id="s-2"); s2.grant(2)
        self.assertTrue(s2.write(1, idempotency_key="op-1"))
        self.assertFalse(s2.write(1, idempotency_key="op-1"))


if __name__ == "__main__":
    unittest.main()
