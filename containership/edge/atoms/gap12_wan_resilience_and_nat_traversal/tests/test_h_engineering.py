"""Group H — contract tests, fuzzing, concurrency, security negatives and the
fleet retry-storm simulation."""
import json
import os
import random
import resource
import sys
import threading
import time
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gap12_wan_resilience_and_nat_traversal.tests._covers import covers  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.path import Partitioned, Path  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.wan import (config as cfgm, contracts, dns, ice, portmap,  # noqa: E402
                                                        security as sec, state as st, stun, turn)

CORPUS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidence", "fuzz-corpus")
SEED = 20260922


class ContractTest(unittest.TestCase):
    @covers("G12-H086:unit,impl-doc,interfaces", "G12-A001:interfaces", "G12-C040:interfaces")
    def test_every_state_the_machine_can_reach_matches_its_schema(self):
        rng = random.Random(SEED)
        for trial in range(300):
            p = Path(f"peer-{trial}", _jitter_seed=trial)
            now = 0.0
            for step in range(rng.randint(1, 12)):
                now += rng.choice([0.0, 0.5, 5, 31, 61, 120])
                try:
                    p.connect(lambda s: rng.random() < 0.3, now)
                except Partitioned:
                    pass
                if p.strategy == "relay" and rng.random() < 0.5:
                    p.record_relay_bytes(rng.randint(0, 10_000))
                for doc, name in ((p.state(now), "PK_PATH_STATE/1"), (contracts.backoff_doc(p), "PK_BACKOFF/1"),
                                  (contracts.relay_accounting_doc(p), "PK_RELAY_ACCOUNTING/1")):
                    self.assertEqual(contracts.validate(doc, name), [], (name, doc))
                self.assertLessEqual(contracts.backoff_doc(p)["delay_s"], 60)
        self.assertEqual(contracts.validate(contracts.path_request("site-b"), "PK_PATH_REQUEST/1"), [])

    @covers("G12-H086:unit")
    def test_schemas_reject_drift(self):
        good = Path("x", _jitter_seed=1).state(0)
        for mutate in (lambda d: d.pop("status"), lambda d: d.update(status="up"), lambda d: d.update(extra=1),
                       lambda d: d.update(failures=-1), lambda d: d.update(healthy="yes")):
            d = dict(good)
            mutate(d)
            self.assertTrue(contracts.validate(d, "PK_PATH_STATE/1"))


def _gen_stun(rng):
    m = stun.Message(rng.choice([1, 3, 4, 8, 9]), rng.randrange(4))
    for _ in range(rng.randint(0, 6)):
        m.add(rng.choice([0x20, 0x01, 0x09, 0x14, 0x15, 0x802C, 0x0013, rng.randrange(0x10000)]),
              bytes(rng.randrange(256) for _ in range(rng.randint(0, 40))))
    wire = bytearray(m.encode(fingerprint=rng.random() < 0.5))
    for _ in range(rng.randint(0, 4)):                         # structure-aware then mutate
        wire[rng.randrange(len(wire))] = rng.randrange(256)
    if rng.random() < 0.2:
        wire = wire[: rng.randrange(len(wire) + 1)]
    return bytes(wire)


class FuzzTest(unittest.TestCase):
    """Deterministic, structure-aware fuzzing with a time and memory ceiling.  Any
    exception other than the parser's documented error type is a finding and the
    input is written to the crash corpus."""

    def _fuzz(self, name, gen, target, allowed, n=4000, seconds=8.0):
        rng = random.Random(SEED + zlib.crc32(name.encode()) % 1000)
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, hard))           # memory ceiling
        crashes = []
        t0 = time.monotonic()
        try:
            for i in range(n):
                if time.monotonic() - t0 > seconds:
                    break
                data = gen(rng)
                try:
                    target(data)
                except allowed:
                    pass
                except Exception as exc:                                         # finding
                    crashes.append((data, repr(exc)))
        finally:
            resource.setrlimit(resource.RLIMIT_AS, (soft, hard))
        os.makedirs(os.path.join(CORPUS, name), exist_ok=True)
        for i, (data, why) in enumerate(crashes[:20]):
            with open(os.path.join(CORPUS, name, f"crash-{i}.bin"), "wb") as fh:
                fh.write(data if isinstance(data, bytes) else json.dumps(data).encode())
        return crashes

    @covers("G12-H094:spec1,spec2,unit,impl-doc", "G12-A001:fault", "G12-H096:neg-security")
    def test_stun_turn_decoder(self):
        def target(b):
            m = stun.decode(b)
            stun.check_fingerprint(m)
            stun.unknown_required(m)
            for t, v in m.attrs:
                if t in (0x20, 0x16, 0x12):
                    stun.decode_address(v, xor=True, txid=m.txid)
        self.assertEqual(self._fuzz("stun", _gen_stun, target, (stun.StunError,)), [])
        self.assertEqual(self._fuzz("channeldata", lambda r: bytes(r.randrange(256) for _ in range(r.randint(0, 30))),
                                    turn.parse_channel_data, (ValueError,)), [])

    @covers("G12-H094:spec1,spec2,unit", "G12-B023:fault")
    def test_dns_decoder(self):
        def gen(rng):
            q = dns.encode_query("a.example", "A", rng.randrange(65536))
            r = bytearray(dns.encode_response(q, ["192.0.2.1"] * rng.randint(0, 3), soa_min=rng.choice([None, 30])))
            for _ in range(rng.randint(0, 5)):
                r[rng.randrange(len(r))] = rng.randrange(256)
            return bytes(r[: rng.randint(0, len(r))])
        self.assertEqual(self._fuzz("dns", gen, dns.decode_response, (ValueError, IndexError, UnicodeError)), [])

    @covers("G12-H094:spec1,spec2,unit", "G12-F068:config-tests", "G12-F067:config-tests")
    def test_config_validator_never_crashes(self):
        keys = list(cfgm.SCHEMA) + ["version", "x-ext", "junk"]
        vals = [None, 0, -1, 1e308, "x", "secret://a", [], {}, ["a:1"], {"direct": "yes"}, True, [{"name": 1}]]

        def gen(rng):
            d = cfgm.defaults()
            for _ in range(rng.randint(1, 6)):
                d[rng.choice(keys)] = rng.choice(vals)
            return d
        self.assertEqual(self._fuzz("config", gen, cfgm.validate, ()), [])

    @covers("G12-H094:spec1,unit", "G12-A003:fault")
    def test_ice_candidates_and_pcp_parser(self):
        def gen_cands(rng):
            out = []
            for _ in range(rng.randint(0, 80)):
                try:
                    out.append(ice.Candidate(rng.choice(["host", "srflx", "relay", "prflx"]),
                                             f"10.{rng.randrange(256)}.{rng.randrange(256)}.{rng.randrange(1, 255)}",
                                             rng.randint(1, 65535), component=rng.randint(1, 2)))
                except ValueError:
                    pass
            return out

        def target(c):
            a = ice.Agent(True, 1)
            a.set_candidates(c, list(reversed(c)))
            assert len(a.pairs) <= ice.MAX_PAIRS
            a.run_checks(lambda p: zlib.crc32(f'{p.local.ip}|{p.remote.ip}'.encode()) % 7 == 0)
        self.assertEqual(self._fuzz("ice", gen_cands, target, (), n=400), [])
        self.assertEqual(self._fuzz("pcp", lambda r: bytes(r.randrange(256) for _ in range(r.choice([0, 24, 60, 64, 61]))),
                                    portmap.pcp_parse_response, (ValueError,)), [])


class FuzzRegressionTest(unittest.TestCase):
    """Replays every crasher ever written to the corpus; each must now be handled."""

    @covers("G12-H094:spec1,unit", "G12-H085:coverage")
    def test_corpus_replay(self):
        n = 0
        for name, target, allowed in (("config", lambda b: cfgm.validate(json.loads(b)), ()),
                                      ("dns", dns.decode_response, (ValueError,)),
                                      ("stun", stun.decode, (stun.StunError,))):
            d = os.path.join(os.path.dirname(CORPUS), "fuzz-regressions", name)
            for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                with open(os.path.join(d, f), "rb") as fh:
                    data = fh.read()
                try:
                    target(data)
                except allowed:
                    pass
                n += 1
        self.assertGreater(n, 0)


class ConcurrencyTest(unittest.TestCase):
    @covers("G12-H095:impl-doc,unit", "G12-E056:race-tests", "G12-E057:race-tests")
    def test_simultaneous_success_failure_cancel_shutdown_reload_clock(self):
        clk = st.FakeClock()
        store = st.PathStore(clk)
        cfg = cfgm.ConfigManager()
        stop = threading.Event()
        errors = []

        def prober_factory(ok):
            return lambda s: ok and s == "hole-punch"

        def succeed():
            while not stop.is_set():
                try:
                    store.transition("p", lambda p, now: p.connect(prober_factory(True), now))
                except Exception as exc:
                    errors.append(repr(exc))

        def fail():
            while not stop.is_set():
                try:
                    store.transition("p", lambda p, now: p.connect(prober_factory(False), now))
                except Exception as exc:
                    errors.append(repr(exc))

        def reload():
            i = 0
            while not stop.is_set():
                i += 1
                cfg.apply({"environment": "lab"}, {"backoff_ceiling_s": 10 + i % 50}, source="t", author="t")

        def clock():
            while not stop.is_set():
                clk.advance(0.7)
                clk.jump_wall(-1)

        def reader():
            while not stop.is_set():
                s = store.snapshot("p")
                errs = contracts.validate({k: v for k, v in s.items() if k not in ("generation", "revalidate")}, "PK_PATH_STATE/1")
                if errs or (s["healthy"] and s["status"] != "healthy"):
                    errors.append((errs, s))
        ts = [threading.Thread(target=f) for f in (succeed, fail, reload, clock, reader, reader)]
        [t.start() for t in ts]
        time.sleep(1.5)
        stop.set()
        [t.join(5) for t in ts]
        self.assertFalse(any(t.is_alive() for t in ts), "deadlock / lost wakeup")
        self.assertEqual(errors, [])
        self.assertGreater(store.snapshot("p")["generation"], 50)


class SecurityNegativeTest(unittest.TestCase):
    @covers("G12-H096:neg-security,unit,impl-doc")
    def test_turn_allocation_cannot_be_hijacked_or_reused_by_other_tenant(self):
        import socket
        with turn.TurnServer(("127.0.0.1", 0), {"a": "pa", "b": "pb"}) as srv:
            ca = turn.TurnClient(srv.address, "a", "pa")
            ca.allocate()
            # attacker shares the 5-tuple? it cannot: a different source port is a different allocation;
            # a request for a's allocation from b's credentials on a's 5-tuple is rejected
            sock = ca.sock
            cb = turn.TurnClient(srv.address, "b", "pb", sock=sock)
            with self.assertRaises(turn.TurnError) as cm:
                cb.allocate()
            self.assertIn(cm.exception.code, (437,))
            peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            peer.bind(("127.0.0.1", 0))
            peer.sendto(b"unsolicited", ca.relayed)                    # no permission -> dropped
            self.assertIsNone(ca.recv(0.3))
            ca.close()
            peer.close()


class RetryStormTest(unittest.TestCase):
    @covers("G12-H098:impl-doc,unit", "G12-D050:spec2")
    def test_fleet_of_10000_peers_does_not_synchronise(self):
        """A 10,000-peer fleet loses every path at t=0 and retries with the real Path
        backoff on a virtual clock (6 rounds each).  Metric: the largest share of the
        fleet retrying inside any 10 ms window.  The v4.2.0 formula (whole-second
        ceiling, 1 s floor) is replayed alongside as the counterfactual."""
        import math as _m
        peers = [Path(f"site-{i}", _jitter_seed=i * 7919 + 1) for i in range(10_000)]
        buckets: dict[int, int] = {}
        old_buckets: dict[int, int] = {}
        for p in peers:
            t = 0.0
            for _ in range(7):
                try:
                    p.connect(lambda s: False, t)
                except Partitioned:
                    pass
                if _ == 0:
                    pass
                t = p.retry_at
                buckets[int(t * 100)] = buckets.get(int(t * 100), 0) + 1
                bound = p.backoff()
                rng = random.Random(p._jitter_seed ^ p.failures)
                old = min(60, max(1, _m.ceil(bound * (0.5 + rng.random() * 0.5))))
                old_buckets.setdefault(p.failures, {})
                old_buckets[p.failures][old] = old_buckets[p.failures].get(old, 0) + 1
        peak_share = max(buckets.values()) / 10_000
        old_first_wave = max(old_buckets[1].values()) / 10_000
        out = os.path.join(os.path.dirname(CORPUS), "out")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "retry_storm.json"), "w") as fh:
            json.dump({"fleet": 10000, "rounds": 7, "window_ms": 10, "peak_share_v430": peak_share,
                       "first_wave_share_in_one_instant_v420_formula": old_first_wave,
                       "note": "simulation of the real Path backoff on a virtual clock; fleet-level volume is "
                               "bounded separately by CircuitBreaker/RetryBudget (G12-D050)"}, fh, indent=1)
        self.assertEqual(old_first_wave, 1.0)            # the v4.2.0 defect this pass fixed
        self.assertLess(peak_share, 0.05)


if __name__ == "__main__":
    unittest.main()
