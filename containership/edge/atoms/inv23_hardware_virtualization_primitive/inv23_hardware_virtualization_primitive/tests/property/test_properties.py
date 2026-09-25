"""MC-10: property-based / fuzz tests.

Uses Hypothesis when installed (``pip install .[test]``; examples persisted in
``.hypothesis/`` and replayed by CI).  Without it, a deterministic seeded generator
runs the same properties so the invariants are always exercised.
"""

import json
import os
import random
import string
import unittest

from tests._boot import mod

model = mod("model")
own = mod("ownership")
ob = mod("ownership.base")
schema = mod("schema")
lk = mod("backends.linux_kvm")
base = mod("backends.base")
probe = mod("probe")

SEED = int(os.environ.get("INV23_FUZZ_SEED", "20260923"))
N = int(os.environ.get("INV23_FUZZ_EXAMPLES", "400"))
WEIRD = ["", " ", "\t", "\x00", "‮", "é", "\U0001f600", "a" * 4096, "\n\r", "None", "0"]


def rstr(r):
    k = r.random()
    if k < 0.3:
        return r.choice(WEIRD)
    return "".join(r.choice(string.printable + "é​\x00") for _ in range(r.randint(0, 40)))


def rval(r):
    return r.choice([None, True, False, 0, 1, -1, 2**63, -(2**63), 1.0, float("nan"), rstr(r), [], {}])


class ConstructorProperties(unittest.TestCase):
    def test_constructor_never_accepts_bad_types(self):
        r = random.Random(SEED)
        for _ in range(N):
            host, depth = r.choice([rstr(r), rval(r)]), rval(r)
            flags = [rval(r) for _ in range(3)]
            try:
                vp = model.VirtPrimitive(host, *flags, nesting_depth=depth)
            except (ValueError, TypeError):
                continue
            self.assertIsInstance(vp.host, str)
            self.assertTrue(vp.host and vp.host == vp.host.strip())
            self.assertIs(type(vp.nesting_depth), int)
            self.assertGreaterEqual(vp.nesting_depth, 0)
            self.assertTrue(all(type(f) is bool for f in flags))
            rep = vp.report()
            if vp.nesting_depth > 0:
                self.assertFalse(rep["bare_metal"])
            schema.validate(rep)


class StateMachineProperties(unittest.TestCase):
    """Random sequences of probe updates, claims, releases, firmware/device/policy changes."""

    def test_random_sequences(self):
        r = random.Random(SEED + 1)
        for _ in range(max(40, N // 10)):
            vp = model.VirtPrimitive("n", True, True, True, nesting_depth=r.choice([0, 1, 2]))
            owner = None
            for _ in range(60):
                op = r.choice(["claim", "release", "fw", "dev", "cpu", "depth", "bad_release"])
                if op == "claim":
                    h = r.choice(["a", "b", " c ", "", 7])
                    try:
                        vp.claim(h, max_nesting=r.choice([0, 1, 2, -1, True]))
                        self.assertIsNone(owner, "second claim succeeded while owned")
                        owner = vp.holder
                    except (model.PrimitiveUnavailable, ValueError):
                        self.assertEqual(vp.holder, owner)
                elif op in ("release", "bad_release"):
                    who = owner if op == "release" and owner else r.choice(["zz", None, ""])
                    try:
                        vp.release(who)
                        if owner and who != owner:
                            self.fail("unauthorised release succeeded")
                        owner = None if who == owner or owner is None else owner
                    except model.PrimitiveUnavailable:
                        self.assertIsNotNone(owner)
                    self.assertEqual(vp.holder, owner)
                elif op == "fw":
                    vp.firmware_enabled = r.random() < 0.5
                elif op == "dev":
                    vp.device_openable = r.random() < 0.5
                elif op == "cpu":
                    vp.cpuid_present = r.random() < 0.8
                elif op == "depth":
                    vp.nesting_depth = r.choice([0, 1, 3])
                st, rep = vp.state(), vp.report()
                self.assertIn(st, ("usable", "present-disabled", "absent", "claimed"))
                if not vp.cpuid_present:
                    self.assertEqual(st, "absent")
                if st in ("usable", "claimed"):
                    self.assertTrue(vp.cpuid_present and vp.firmware_enabled and vp.device_openable)
                if vp.nesting_depth > 0:
                    self.assertFalse(rep["bare_metal"])
                self.assertEqual(rep["state"], st)


class OwnershipProperties(unittest.TestCase):
    def test_exclusivity_and_authorisation(self):
        r = random.Random(SEED + 2)
        clock = [1e6]
        p = own.MemoryClaimProvider(clock=lambda: clock[0])
        live, claims, last_gen = None, [], 0
        for _ in range(N):
            op = r.random()
            if op < 0.4:
                try:
                    c = p.acquire(r.choice(["a", "b", "c"]), lease_s=r.choice([1, 5, 30]))
                    self.assertGreater(c.generation, last_gen)
                    last_gen = c.generation
                    live = c
                    claims.append(c)
                except own.ClaimConflict:
                    self.assertIsNotNone(live)
                    self.assertGreater(live.lease_expires_at, clock[0])
            elif op < 0.7 and claims:
                c = r.choice(claims)
                if r.random() < 0.3:
                    c = ob.Claim(c.resource, c.claim_id, c.generation, rstr(r) or "x")
                try:
                    p.release(c)
                    self.assertIs(c, live)
                    live = None
                except own.OwnershipError:
                    pass
            else:
                clock[0] += r.choice([0.5, 2, 40])
                # an expired lease stays "current" (releasable) until someone takes it over
            st = p.status()
            if st["state"] == "held":
                self.assertEqual(st["generation"], last_gen)


class SchemaFuzz(unittest.TestCase):
    def test_single_field_mutations(self):
        r = random.Random(SEED + 3)
        good = base.ProbeResult(
            host="n",
            backend="linux-kvm",
            backend_version="1",
            platform="linux",
            architecture="x86_64",
            state="usable",
            reason="ok",
            facility_usable=True,
            virtualized=False,
            nesting_depth=0,
        ).to_report()
        schema.validate(good)
        for _ in range(N):
            d = json.loads(json.dumps(good))
            k = r.choice(list(d))
            d[k] = rval(r)
            if k == "state" and isinstance(d[k], str):
                d[k] = r.choice(["USABLE", "Usable", "usable ", "claimed"])
            try:
                schema.validate(d, "PK_VIRT_PRIMITIVE/2")
            except schema.SchemaError:
                continue
            # anything accepted must still satisfy the invariants
            if d["state"] == "usable":
                self.assertEqual(d["reason"], "ok")
            if d["bare_metal"]:
                self.assertEqual(d["nesting_depth"], 0)

    def test_unknown_fields_and_big_ints(self):
        d = {"schema": "PK_VIRT_PRIMITIVE/1", "host": "n", "state": "usable", "nesting_depth": 2**70, "bare_metal": False}
        with self.assertRaises(schema.SchemaError):
            schema.validate(d)
        d.update(nesting_depth=0, extra=1)
        with self.assertRaises(schema.SchemaError):
            schema.validate(d)


class BackendFuzz(unittest.TestCase):
    def test_malformed_evidence_never_usable(self):
        r = random.Random(SEED + 4)

        class Fuzzed:
            name, version = "linux-kvm", "f"

            def supports(self, p, a):
                return True

            def probe(self, host):
                b = lk.LinuxKvmBackend(
                    "/nonexistent",
                    ioctl=lambda fd: r.choice([12, "12", None, -1, 2**40]),
                    opener=lambda *a, **k: (_ for _ in ()).throw(
                        r.choice([OSError(5, "EIO"), PermissionError(13, "x"), FileNotFoundError()])
                    ),
                )
                text = r.choice(["", "flags: vmx", "garbage", "\x00" * 10, rstr(r), "vendor_id: X\nflags: svm npt"])
                b._read = lambda path: text if path.endswith("cpuinfo") else r.choice([None, "Y", "\x00"])
                return b.probe(host)

        p = probe.Prober([Fuzzed()], host="h", platform="linux", architecture="x86_64", cache_ttl_s=0)
        for _ in range(N):
            self.assertNotEqual(p.probe().state, "usable")


try:  # optional Hypothesis layer
    from hypothesis import given, settings
    from hypothesis import strategies as st

    class HypothesisLayer(unittest.TestCase):
        @settings(max_examples=300, deadline=None)
        @given(st.one_of(st.text(), st.none(), st.integers()), st.one_of(st.integers(), st.booleans(), st.none()))
        def test_constructor(self, host, depth):
            try:
                vp = model.VirtPrimitive(host, nesting_depth=depth)
            except (ValueError, TypeError):
                return
            self.assertTrue(vp.host.strip())
            self.assertIs(type(vp.nesting_depth), int)

        @settings(max_examples=200, deadline=None)
        @given(st.text(max_size=300))
        def test_cpuinfo_parser(self, text):
            try:
                out = lk.parse_cpuinfo(text)
            except base.ProbeError as e:
                self.assertEqual(e.reason, "malformed_probe_response")
                return
            self.assertIsInstance(out["flags"], set)
except ImportError:  # pragma: no cover
    pass


if __name__ == "__main__":
    unittest.main()
