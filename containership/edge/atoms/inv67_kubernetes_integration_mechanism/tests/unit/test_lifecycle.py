"""Model-based lifecycle tests (item 04): every legal and illegal transition."""
import unittest

import _support as S

L = S.lifecycle


class Lifecycle(unittest.TestCase):
    def test_every_pair_is_decided_and_enforced(self):
        table = L.transition_table()
        self.assertEqual(len(table), len(L.State) ** 2)
        for a, b, ok in table:
            src, dst = L.State(a), L.State(b)
            if ok:
                self.assertEqual(L.transition(src, dst), dst)
            else:
                with self.assertRaises(L.IllegalTransition):
                    L.transition(src, dst)

    def test_terminal_states_only_go_to_deleting_or_revalidate(self):
        for t in L.TERMINAL:
            outs = {b for a, b, ok in L.transition_table() if ok and a == t.value and b != a}
            self.assertTrue(outs <= {"Deleting", "Validating"}, (t, outs))

    def test_every_state_reaches_deleting(self):
        for s in L.State:
            if s is not L.State.DELETING:
                self.assertTrue(L.legal(s, L.State.DELETING) or s is L.State.CANCELLED or L.legal(s, L.State.CANCELLED), s)

    def test_error_taxonomy(self):
        self.assertTrue(L.PlaneError("INV67_DOWNSTREAM_UNAVAILABLE", "x").retryable)
        self.assertFalse(L.PlaneError("INV67_UNAUTHORIZED", "x").retryable)
        with self.assertRaises(ValueError):
            L.PlaneError("MADE_UP", "x")
        d = L.PlaneError("INV67_CONFLICT", "c", k=1).to_dict()
        self.assertEqual(set(d), {"code", "reason", "message", "retryable", "detail"})

    def test_attempt_ids_distinguish_generations_and_retries(self):
        ids = {L.attempt_id("u" * 8, g, a) for g in (1, 2) for a in (1, 2)}
        self.assertEqual(len(ids), 4)

    def test_aggregate(self):
        S_ = L.State
        self.assertEqual(L.aggregate_units([S_.RUNNING, S_.FAILED]), S_.FAILED)
        self.assertEqual(L.aggregate_units([S_.RUNNING, S_.SUCCEEDED]), S_.RUNNING)
        self.assertEqual(L.aggregate_units([S_.SUCCEEDED, S_.SUCCEEDED]), S_.SUCCEEDED)
        self.assertEqual(L.aggregate_units([S_.RUNNING, S_.UNKNOWN]), S_.UNKNOWN)
        self.assertEqual(L.aggregate_units([S_.PLACED, S_.STARTING]), S_.STARTING)
        self.assertEqual(L.aggregate_units([]), S_.UNKNOWN)

    def test_pod_phase_projection_is_total_and_in_status_enum(self):
        import json
        enum = json.loads((S.PKG_DIR / "schemas/PK_K8S_STATUS_v1.schema.json").read_text())["enum"]
        for s in L.State:
            self.assertIn(L.POD_PHASE[s], enum)


if __name__ == "__main__":
    unittest.main()


class Queue(unittest.TestCase):
    def test_dedupe_earliest_wins_and_delay_preserved_during_processing(self):
        c = S.Clock()
        q = S.controller.WorkQueue(c)
        q.add("k", 5); q.add("k", 1); q.add("k", 9)
        self.assertIsNone(q.pop_due())
        c.tick(1)
        self.assertEqual(q.pop_due(), "k")
        q.add("k", 3)            # requeue while processing: must keep its delay
        q.done("k")
        self.assertIsNone(q.pop_due())
        c.tick(3)
        self.assertEqual(q.pop_due(), "k")
        q.done("k")
        self.assertIsNone(q.pop_due())
