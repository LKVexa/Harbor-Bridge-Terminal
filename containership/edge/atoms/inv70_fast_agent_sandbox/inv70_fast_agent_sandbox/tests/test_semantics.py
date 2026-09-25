"""C015 / C019 / C027 / C093 semantics tests."""
import importlib
import itertools
import unittest

import _path
s = importlib.import_module(_path.PKG + ".semantics")


class LifecycleTests(unittest.TestCase):
    def test_happy_path_and_terminal_finality(self):
        seen = []
        l = s.Lifecycle("r", on_transition=lambda *a: seen.append(a[2]))
        for st in (s.State.AUTHENTICATED, s.State.ADMITTED, s.State.VALIDATED, s.State.RUNNING, s.State.SUCCEEDED):
            l.to(st)
        self.assertTrue(l.terminal)
        self.assertEqual(len(seen), 5)
        for st in s.State:
            with self.assertRaises(s.IllegalTransition):
                l.to(st)

    def test_exhaustive_transition_table(self):
        for a, b in itertools.product(s.State, s.State):
            l = s.Lifecycle("r")
            l.state = a
            legal = b in s.TRANSITIONS.get(a, set())
            if legal:
                l.to(b)
            else:
                with self.assertRaises(s.IllegalTransition):
                    l.to(b)
        for t in s.TERMINAL:
            self.assertNotIn(t, s.TRANSITIONS)

    def test_cannot_skip_to_running(self):
        with self.assertRaises(s.IllegalTransition):
            s.Lifecycle("r").to(s.State.RUNNING)


class Precedence(unittest.TestCase):
    def test_security_beats_everything(self):
        opts = [{"action": "allow", "constraint": c} for c in s.RANK if c != "security"]
        opts.append({"action": "deny", "constraint": "security"})
        out = s.resolve_conflict(opts)
        self.assertEqual(out["winner"]["constraint"], "security")
        self.assertEqual(len(out["overridden"]), len(opts) - 1)

    def test_deterministic_and_deny_on_tie(self):
        opts = [{"action": "allow", "constraint": "availability"}, {"action": "deny", "constraint": "availability"}]
        self.assertEqual(s.resolve_conflict(opts)["winner"]["action"], "deny")
        self.assertEqual(s.resolve_conflict(list(reversed(opts))), s.resolve_conflict(opts))

    def test_unknown(self):
        with self.assertRaises(ValueError):
            s.resolve_conflict([{"action": "x", "constraint": "vibes"}])
        with self.assertRaises(ValueError):
            s.resolve_conflict([])


class Versions(unittest.TestCase):
    def test_negotiate(self):
        self.assertEqual(s.negotiate("PK_FASTBOX_RUN", [1, 2, 3]), 2)
        self.assertEqual(s.negotiate("PK_FASTBOX_RUN", [1]), 1)
        for bad in ([3], [], ["2"], None):
            with self.assertRaises(s.VersionError):
                s.negotiate("PK_FASTBOX_RUN", bad)
        with self.assertRaises(s.VersionError):
            s.negotiate("PK_NOPE", [1])

    def test_peer_window(self):
        s.check_peer_release("4.2.9")
        s.check_peer_release("4.3.0")
        for bad in ("4.1.0", "5.0.0", "junk"):
            with self.assertRaises(s.VersionError):
                s.check_peer_release(bad)

    def test_result_downgrade_is_v1_shape(self):
        ok = {"status": "ok", "value": 3, "fuel": 2, "reason": None}
        self.assertEqual(s.downgrade_result(ok, 1), {"ok": 3, "fuel": 2})
        tr = {"status": "trap", "value": None, "fuel": 5, "reason": "out of fuel"}
        self.assertEqual(s.downgrade_result(tr, 1), {"trap": "out of fuel", "fuel": 5})


if __name__ == "__main__":
    unittest.main()
