"""C086/C088: randomized race + soak suite. INV17_SOAK_SECONDS extends the run (default ~1.5 s).

Mixed concurrent grant/write/read/drop/freeze threads hammer shared streams; afterwards the
accounting identity  transferred == reads + dropped_items + buffered  must hold, no element
may be duplicated or reordered per writer, and no thread may observe an undeclared error.
"""
import os
import random
import threading
import time
import unittest

from _pkg import control as C, stream as S, open_stream, registry

SECONDS = float(os.environ.get("INV17_SOAK_SECONDS", "1.5"))
ALLOWED = (S.CreditExhausted, S.BufferLimitExceeded, S.EndDropped, S.StreamClosed, S.StreamFrozen,
           S.CreditLimitExceeded, S.StreamTimeout)


class RaceSoakTest(unittest.TestCase):
    def test_mixed_concurrency_preserves_accounting(self):
        deadline = time.monotonic() + SECONDS
        streams = [S.Stream(tuple, config=S.StreamConfig(max_credit=64, max_buffer=32)) for _ in range(4)]
        unexpected, received = [], {i: [] for i in range(len(streams))}

        def writer(wid, idx):
            rng = random.Random(wid); n = 0; s = streams[idx]
            while time.monotonic() < deadline:
                try:
                    s.write((wid, n)); n += 1
                except ALLOWED:
                    time.sleep(0)
                except Exception as e:  # pragma: no cover
                    unexpected.append(e); return

        def reader(idx):
            s = streams[idx]; rng = random.Random(idx)
            while time.monotonic() < deadline:
                try:
                    if rng.random() < 0.6:
                        s.grant(rng.randint(1, 8))
                    v = s.read()
                    if isinstance(v, tuple):
                        received[idx].append(v)
                except ALLOWED:
                    time.sleep(0)
                except Exception as e:  # pragma: no cover
                    unexpected.append(e); return

        def chaos():
            rng = random.Random(42)
            while time.monotonic() < deadline:
                s = rng.choice(streams)
                s.freeze("chaos"); time.sleep(0.001); s.unfreeze()
                s.stats(); _ = s.state
                time.sleep(0.002)

        threads = [threading.Thread(target=writer, args=(w, w % 4)) for w in range(8)]
        threads += [threading.Thread(target=reader, args=(i,)) for i in range(4)]
        threads.append(threading.Thread(target=chaos))
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(unexpected, [])
        total = 0
        for idx, s in enumerate(streams):
            st = s.stats()
            self.assertEqual(st.transferred, st.reads + st.dropped_items + st.buffered)
            self.assertLessEqual(st.buffered, 32)
            seq = received[idx] + list(s.buffer)
            self.assertEqual(len(seq), len(set(seq)), "duplicate element")
            for wid in {w for w, _ in seq}:
                ns = [n for w, n in seq if w == wid]
                self.assertEqual(ns, sorted(ns), "per-writer order violated")
            total += st.transferred
        self.assertGreater(total, 100)

    def test_concurrent_drop_while_writing(self):
        for trial in range(20):
            s = S.Stream(int, config=S.StreamConfig(max_credit=10_000, max_buffer=10_000)); s.grant(10_000)
            errors = []
            def w():
                for i in range(2000):
                    try:
                        s.write(i)
                    except S.EndDropped:
                        return
                    except Exception as e:  # pragma: no cover
                        errors.append(e); return
            t = threading.Thread(target=w); t.start()
            time.sleep(0.0005 * (trial % 3)); s.drop_reader(); t.join()
            st = s.stats()
            self.assertEqual(errors, [])
            self.assertEqual(st.buffered, 0)
            self.assertEqual(st.transferred, st.dropped_items)
            with self.assertRaises(S.EndDropped): s.write(1)

    def test_registry_concurrent_open_quota(self):
        r = registry(quotas={"t": C.TenantQuota(max_streams=10)})
        ok, denied, errors = [], [], []
        def opener(i):
            try:
                open_stream(r, f"s{i}", tenant="t"); ok.append(i)
            except C.QuotaExceeded:
                denied.append(i)
            except Exception as e:  # pragma: no cover
                errors.append(e)
        ts = [threading.Thread(target=opener, args=(i,)) for i in range(40)]
        for t in ts: t.start()
        for t in ts: t.join()
        self.assertEqual((len(ok), len(denied), errors), (10, 30, []))
        self.assertEqual(r.audit.verify(), [])


if __name__ == "__main__":
    unittest.main()
