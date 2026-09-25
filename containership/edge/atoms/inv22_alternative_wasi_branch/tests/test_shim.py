"""PK_BRANCH_SHIM/1 service, reference translator proofs and resilience (MC-07, 13, 14, 15, 17, 26, 34, 35)."""
import importlib
import itertools
import json
import random
import threading
import unittest

from _support import PKG, PKG_DIR

shim = importlib.import_module(f"{PKG}.shim")
matrix = importlib.import_module(f"{PKG}.matrix")
errors = importlib.import_module(f"{PKG}.errors")
telemetry = importlib.import_module(f"{PKG}.telemetry")
E = errors.Inv22Error

M = matrix.parse(json.loads((PKG_DIR / "data/matrix.json").read_text()))
STD_DOMAIN = [{"open": sorted(o), "rights": sorted(r)}
              for n in range(5) for o in itertools.combinations(shim.OFLAGS, n)
              for k in range(3) for r in itertools.combinations(shim.RIGHTS, k)]
FORK_DOMAIN = [{"oflags": o, "rights_base": r} for o in range(16) for r in (0, 2, 64, 66)]


def req(**kw):
    base = {"contract": "PK_BRANCH_SHIM/1", "interface": shim.FS_IFACE, "operation": "open-at",
            "source_branch": "standards", "target_branch": "fork", "encoding": "json-canonical",
            "correlation_id": "c-1", "payload": {"open": ["create"], "rights": ["read"]}}
    base.update(kw)
    return base


def svc(**kw):
    return shim.ShimService(M, shim.default_registry(), **kw)


class ExhaustiveRoundTrip(unittest.TestCase):
    """The reference domain is finite (64 values each way) so the inverse property is proven exhaustively."""

    def test_domains_are_complete(self):
        self.assertEqual(len(STD_DOMAIN), 64)
        self.assertEqual(len(FORK_DOMAIN), 64)

    def test_std_fork_std(self):
        for x in STD_DOMAIN:
            self.assertEqual(shim.fs_fork_to_std(shim.fs_std_to_fork(x)), x)

    def test_fork_std_fork(self):
        for y in FORK_DOMAIN:
            self.assertEqual(shim.fs_std_to_fork(shim.fs_fork_to_std(y)), y)

    def test_bijection(self):
        images = {json.dumps(shim.fs_std_to_fork(x), sort_keys=True) for x in STD_DOMAIN}
        self.assertEqual(len(images), 64)

    def test_rights_never_widen(self):
        for x in STD_DOMAIN:
            self.assertLessEqual(shim.fs_rights(shim.fs_std_to_fork(x), "fork"), shim.fs_rights(x, "standards"))
        for y in FORK_DOMAIN:
            self.assertLessEqual(shim.fs_rights(shim.fs_fork_to_std(y), "standards"), shim.fs_rights(y, "fork"))

    def test_canonical_order_normalises(self):
        self.assertEqual(shim.fs_fork_to_std(shim.fs_std_to_fork({"open": ["truncate", "create"], "rights": []})),
                         {"open": ["create", "truncate"], "rights": []})


class MutationDetection(unittest.TestCase):
    """Deliberately corrupted translators must be caught by the same property checks."""

    def property_holds(self, fwd, back):
        try:
            for x in STD_DOMAIN:
                y = fwd(x)
                if back(y) != x or not shim.fs_rights(y, "fork") <= shim.fs_rights(x, "standards"):
                    return False
        except Exception:
            return False
        return True

    def test_reference_passes(self):
        self.assertTrue(self.property_holds(shim.fs_std_to_fork, shim.fs_fork_to_std))

    def test_mutants_are_killed(self):
        fwd, back = shim.fs_std_to_fork, shim.fs_fork_to_std
        mutants = {
            "drop_truncate": lambda x: dict(fwd(x), oflags=fwd(x)["oflags"] & ~8),
            "remap_excl_to_trunc": lambda x: dict(fwd(x), oflags=(fwd(x)["oflags"] & ~4) | (8 if fwd(x)["oflags"] & 4 else 0)),
            "widen_rights": lambda x: dict(fwd(x), rights_base=fwd(x)["rights_base"] | 64),
            "drop_rights": lambda x: dict(fwd(x), rights_base=0),
            "sign_flip": lambda x: dict(fwd(x), oflags=-fwd(x)["oflags"]),
        }
        for name, m in mutants.items():
            with self.subTest(name):
                self.assertFalse(self.property_holds(m, back))


class PropertyFuzz(unittest.TestCase):
    def test_out_of_domain_inputs_refused(self):
        rng = random.Random(2209)
        for _ in range(3000):
            y = {"oflags": rng.choice([rng.randrange(-5, 70000), rng.randrange(16)]),
                 "rights_base": rng.choice([rng.randrange(2**65), rng.choice([0, 2, 64, 66]), -1])}
            try:
                out = shim.fs_fork_to_std(y)
            except E as e:
                self.assertEqual(e.code, "INV22.TRANSLATE.NOT_REPRESENTABLE")
            else:
                self.assertEqual(shim.fs_std_to_fork(out), y)

    def test_bad_shapes(self):
        for bad in ({}, {"open": ["create"]}, {"open": ["x"], "rights": []}, {"open": ["create", "create"], "rights": []},
                    {"open": "create", "rights": []}, [], None, {"oflags": True, "rights_base": 0}):
            with self.assertRaises(E):
                shim.fs_std_to_fork(bad) if isinstance(bad, dict) and "oflags" not in bad else shim.fs_fork_to_std(bad)


class Service(unittest.TestCase):
    def test_success_carries_provenance(self):
        r = svc().translate(req())
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["payload"], {"oflags": 1, "rights_base": 2})
        self.assertEqual(r["shim"], {"shim_id": "fs-open-flags", "version": "1.0.0"})
        self.assertEqual(r["matrix_digest"], M.digest)
        self.assertTrue(r["source_baseline"].startswith("sha256:"))

    def test_fixture_corpus(self):
        s = svc()
        files = sorted((PKG_DIR / "fixtures/shim").glob("*.json"))
        self.assertGreaterEqual(len(files), 7)
        for f in files:
            fx = json.loads(f.read_text())
            with self.subTest(f.name):
                r = s.translate(fx["document"])
                if fx["expect"] == "ok":
                    self.assertEqual(r["status"], "ok")
                else:
                    self.assertEqual(r["status"], "error")
                    self.assertEqual(r["error"]["code"], fx["expect"])
                    self.assertNotIn("payload", r)

    def test_identity_same_branch(self):
        r = svc().translate(req(target_branch="standards"))
        self.assertEqual(r["payload"], req()["payload"])

    def test_malicious_translator_cannot_escalate(self):
        reg = shim.Registry()
        reg.register(shim.Translator("fs-open-flags", "evil", shim.FS_IFACE, "standards", "fork",
                                     lambda p: {"oflags": 0, "rights_base": 66}, shim.fs_rights))
        r = shim.ShimService(M, reg).translate(req(payload={"open": [], "rights": ["read"]}))
        self.assertEqual(r["error"]["code"], "INV22.TRANSLATE.CAPABILITY_ESCALATION")

    def test_translator_must_match_matrix_shim_id(self):
        reg = shim.Registry()
        reg.register(shim.Translator("other", "1", shim.FS_IFACE, "standards", "fork", shim.fs_std_to_fork))
        self.assertEqual(shim.ShimService(M, reg).translate(req())["error"]["code"], "INV22.TRANSLATE.NO_TRANSLATOR")

    def test_translator_crash_is_structured(self):
        reg = shim.Registry()
        reg.register(shim.Translator("fs-open-flags", "1", shim.FS_IFACE, "standards", "fork", lambda p: 1 / 0))
        r = shim.ShimService(M, reg).translate(req())
        self.assertEqual(r["error"]["code"], "INV22.INTERNAL")
        self.assertNotIn("division", json.dumps(r))

    def test_registry_refuses_ambiguity(self):
        reg = shim.default_registry()
        with self.assertRaises(E):
            reg.register(shim.Translator("fs-open-flags", "2", shim.FS_IFACE, "standards", "fork", shim.fs_std_to_fork))

    def test_request_validation(self):
        s = svc()
        for bad in (req(extra=1), req(encoding="pickle"), req(source_branch="beta"), req(deadline_ms=0),
                    req(correlation_id=""), req(payload={"x": "y" * 70000}), "not json", req(contract="PK_BRANCH_SHIM/2")):
            with self.subTest(str(bad)[:40]):
                r = s.translate(bad)
                self.assertEqual(r["status"], "error")
                self.assertNotIn("payload", r)

    def test_deep_payload_bounded(self):
        p = cur = {}
        for _ in range(40):
            cur["a"] = {}
            cur = cur["a"]
        self.assertEqual(svc().translate(req(payload=p))["error"]["code"], "INV22.VALIDATION.LIMIT")


class Resilience(unittest.TestCase):
    def test_deadline_exceeded(self):
        t = iter([0.0, 10.0])
        s = shim.ShimService(M, shim.default_registry(), clock=lambda: next(t))
        self.assertEqual(s.translate(req(deadline_ms=5))["error"]["code"], "INV22.TIMEOUT.DEADLINE_EXCEEDED")

    def test_cancelled(self):
        tok = shim.CancelToken()
        tok.cancel()
        self.assertEqual(svc().translate(req(), tok)["error"]["code"], "INV22.TIMEOUT.CANCELLED")

    def test_overload_is_bounded_and_recovers(self):
        gate, started = threading.Event(), threading.Event()
        reg = shim.Registry()

        def slow(p):
            started.set()
            gate.wait(5)
            return shim.fs_std_to_fork(p)
        reg.register(shim.Translator("fs-open-flags", "1", shim.FS_IFACE, "standards", "fork", slow))
        metrics = telemetry.Metrics()
        s = shim.ShimService(M, reg, max_concurrency=1, default_deadline_ms=10_000, metrics=metrics)
        th = threading.Thread(target=s.translate, args=(req(),))
        th.start()
        started.wait(5)
        self.assertEqual(s.translate(req())["error"]["code"], "INV22.RESOURCE.OVERLOADED")
        gate.set()
        th.join(5)
        self.assertEqual(s.translate(req())["status"], "ok")
        self.assertGreaterEqual(metrics.total("shim_refusals"), 1)

    def test_idempotent(self):
        s = svc()
        a, b = s.translate(req()), s.translate(req())
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
