"""WP #42 exhaustive contract tests, #44 fuzz/property tests, #45 concurrency/soak/burst (short CI mode).

Seeds are fixed and printed on failure; set PK06_FUZZ_ITERATIONS / PK06_SOAK_SECONDS for longer runs.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import random
import string
import struct
import time
import unittest

from _support import Env, load_schema, validate_schema
from pln06_data_plane import DataPlane, config, integrity, lifecycle
from pln06_data_plane import data_plane as dp
from pln06_data_plane import transports as t
from pln06_data_plane.observability import StructuredLogger

ITER = int(os.environ.get("PK06_FUZZ_ITERATIONS", "400"))
SOAK = float(os.environ.get("PK06_SOAK_SECONDS", "1.5"))
SEED = int(os.environ.get("PK06_FUZZ_SEED", "20260923"))


def jsonschema_check(instance, schema):
    try:
        import jsonschema  # optional cross-check when installed
    except ImportError:
        return
    jsonschema.validate(instance, schema)


class ContractTest(unittest.TestCase):
    def assertConforms(self, obj, name):
        schema = load_schema(name)
        obj = json.loads(json.dumps(obj, default=str))
        self.assertEqual(validate_schema(obj, schema), [], name)
        jsonschema_check(obj, schema)

    def test_every_schema_is_well_formed_and_versioned(self):
        from _support import PKG_DIR
        for p in sorted((PKG_DIR / "schemas").glob("*.json")):
            s = json.loads(p.read_text())
            self.assertEqual(s["$schema"], "https://json-schema.org/draft/2020-12/schema", p.name)
            self.assertRegex(s["$id"], r"^PK_[A-Z_]+/\d+$", p.name)

    def test_emitted_objects_conform(self):
        e = Env()
        self.addCleanup(e.close)
        for loc in dp.LOCALITY_FLOOR:
            if loc == "vm_control":
                continue
            d = e.plane.admit(tenant="t", workload="w", size=10, classification="public", destination="eu", locality=loc)
            self.assertConforms(d, "pk_transfer_v1.schema.json")
            e.plane.cancel(d)
        r = e.send(b"x" * 100)
        self.assertConforms(e.plane.health(), "pk_data_plane_health_v1.schema.json")
        self.assertConforms(e.plane.metrics(), "pk_data_plane_metrics_v1.schema.json")
        self.assertConforms(e.svc.health(), "pk_data_plane_health_v2.schema.json")
        self.assertConforms(e.svc.explain(e.op(), r["transfer_id"]), "pk_explain_v1.schema.json")
        for rec in e.audit.records():
            self.assertConforms(rec, "pk_audit_record_v1.schema.json")
        self.assertConforms(integrity.build_manifest("t", b"abc" * 1000, 512).as_dict(),
                            "pk_payload_manifest_v1.schema.json")
        self.assertConforms(StructuredLogger(node="n").log("INFO", "e", operation="o"), "pk_log_v1.schema.json")
        self.assertConforms(config.load({"residency": {"eu": ["pii"]}}), "pk_config_v1.schema.json")

    def test_schema_rejects_mutations(self):
        schema = load_schema("pk_transfer_v1.schema.json")
        good = DataPlane({"s": {"c"}}).admit(tenant="t", workload="w", size=1, classification="c", destination="s")
        for k, v in (("tier", "warp"), ("size", -1), ("digest_required", False), ("extra", 1), ("locality", "moon")):
            self.assertNotEqual(validate_schema({**good, k: v}, schema), [], k)
        bad = dict(good)
        del bad["tenant"]
        self.assertNotEqual(validate_schema(bad, schema), [])

    def test_error_codes_are_stable_and_unique(self):
        import inspect

        from pln06_data_plane import integrations, resilience, security, service
        codes = {}
        for mod in (dp, security, integrity, t, lifecycle, resilience, integrations, service):
            for _, cls in inspect.getmembers(mod, inspect.isclass):
                if issubclass(cls, dp._StructuredError) and cls is not dp._StructuredError:
                    codes.setdefault(cls.code, set()).add(cls.__name__)
        for code, names in codes.items():
            self.assertRegex(code, r"^PK_[A-Z0-9_]+$")
            self.assertEqual(len(names), 1, (code, names))
        self.assertGreaterEqual(len(codes), 25)

    def test_boundaries(self):
        f = DataPlane.tier_for
        lim = dp.CONTROL_INLINE_LIMIT
        self.assertEqual([f(lim), f(lim + 1), f(64 << 20), f((64 << 20) + 1), f(64 << 30)],
                         ["inline", "local", "local", "bulk", "bulk"])
        with self.assertRaises(dp.NoTransportTier):
            f((64 << 30) + 1)


def rand_text(rng, n=12):
    alphabet = string.printable + "é中\x00퟿"
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, n)))


def rand_value(rng, depth=0):
    kinds = [lambda: None, lambda: rng.randint(-2**40, 2**40), lambda: rng.random(), lambda: rand_text(rng),
             lambda: rng.choice([True, False]), lambda: os.urandom(rng.randint(0, 8))]
    if depth < 2:
        kinds += [lambda: [rand_value(rng, depth + 1) for _ in range(rng.randint(0, 3))],
                  lambda: {rand_text(rng, 4): rand_value(rng, depth + 1) for _ in range(rng.randint(0, 3))},
                  lambda: {rand_text(rng, 4) for _ in range(rng.randint(0, 3))}]
    return rng.choice(kinds)()


class FuzzTest(unittest.TestCase):
    """Property: hostile input only ever yields a *structured* error, never a crash or silent acceptance."""

    def test_admit_fuzz(self):
        rng = random.Random(SEED)
        plane = DataPlane({"s": {"c"}}, inflight_limit=10_000)
        for i in range(ITER):
            kw = {k: rand_value(rng) for k in ("tenant", "workload", "size", "classification", "destination",
                                              "locality", "digest")}
            if rng.random() < 0.3:
                kw.update(size=rng.randint(0, 1 << 20), classification="c", destination="s", tenant="t", workload="w",
                          locality="auto", digest=None)
            try:
                d = plane.admit(**kw)
            except (dp.InvalidRequest, dp.ResidencyViolation, dp.NoTransportTier, dp.Backpressure):
                continue
            except Exception as exc:  # noqa: BLE001
                self.fail(f"seed={SEED} iter={i}: unstructured {type(exc).__name__}: {exc!r} for {kw!r}")
            self.assertEqual(d["destination"], "s")
            self.assertIn("c", plane.residency_snapshot()[d["destination"]])   # never admits illegally
            plane.cancel(d)
        self.assertEqual(plane.inflight, 0)

    def test_residency_config_fuzz(self):
        rng = random.Random(SEED + 1)
        for i in range(ITER):
            cfg = rand_value(rng)
            try:
                DataPlane(cfg if isinstance(cfg, dict) else {"x": cfg})
            except dp.InvalidRequest:
                pass
            except Exception as exc:  # noqa: BLE001
                self.fail(f"seed={SEED + 1} iter={i}: {type(exc).__name__} for {cfg!r}")

    def test_completion_record_fuzz(self):
        rng = random.Random(SEED + 2)
        plane = DataPlane({"s": {"c"}}, inflight_limit=4)
        live = plane.admit(tenant="t", workload="w", size=1 << 20, classification="c", destination="s")
        for i in range(ITER):
            forged = dict(live)
            key = rng.choice(list(forged))
            forged[key] = rand_value(rng)
            try:
                released = plane.complete(forged)
            except dp.InvalidCompletion:
                continue
            except Exception as exc:  # noqa: BLE001
                self.fail(f"seed={SEED + 2} iter={i}: {type(exc).__name__}")
            if released:
                self.assertEqual(forged, {**live, key: forged[key]})
                self.assertIn(key, ("reason", "digest", "digest_required", "digest_algorithm"))  # non-binding fields
                live = plane.admit(tenant="t", workload="w", size=1 << 20, classification="c", destination="s")

    def test_config_fuzz(self):
        rng = random.Random(SEED + 3)
        keys = list(config.SECURE_DEFAULTS)
        for i in range(ITER):
            ov = {rng.choice(keys + ["junk"]): rand_value(rng) for _ in range(rng.randint(1, 3))}
            try:
                config.load(ov)
            except dp.InvalidRequest:
                pass
            except Exception as exc:  # noqa: BLE001
                self.fail(f"seed={SEED + 3} iter={i}: {type(exc).__name__} for {ov!r}")

    def test_manifest_and_frame_parser_fuzz(self):
        import socket
        rng = random.Random(SEED + 4)
        for i in range(ITER // 4):
            data = os.urandom(rng.randint(0, 5000))
            m = integrity.build_manifest("x", data, rng.randint(1, 700))
            parts = list(enumerate(integrity.chunks(data, m.chunk_size)))
            rng.shuffle(parts)
            if parts and rng.random() < 0.5:
                j = rng.randrange(len(parts))
                blob = bytearray(parts[j][1] or b"\x00")
                blob[rng.randrange(len(blob))] ^= 1 + rng.randrange(255)
                parts[j] = (parts[j][0], bytes(blob))
                with self.assertRaises(integrity.IntegrityMismatch, msg=f"seed={SEED + 4} iter={i}"):
                    integrity.reassemble(m, parts)
            else:
                self.assertEqual(integrity.reassemble(m, parts), data)
            a, b = socket.socketpair()
            try:
                junk = struct.pack("!II", rng.randint(0, 1 << 20), rng.randint(0, 1 << 23)) + os.urandom(rng.randint(0, 64))
                a.sendall(junk)
                a.close()
                with self.assertRaises((t.TransportError, t.ControlPathViolation, ValueError, UnicodeDecodeError)):
                    t._recv_frame(b)
            finally:
                b.close()


class ConcurrencySoakTest(unittest.TestCase):
    def test_burst_never_oversubscribes_and_leaks_nothing(self):
        plane = DataPlane({"s": {"c"}}, inflight_limit=16, per_tenant_inflight_limit=4)
        peak = [0]
        rng = random.Random(SEED + 5)
        tenants = [f"t{i}" for i in range(8)]

        def worker(n):
            ok = 0
            for _ in range(n):
                try:
                    d = plane.admit(tenant=rng.choice(tenants), workload="w", size=1 << 20, classification="c",
                                    destination="s")
                except dp.Backpressure:
                    continue
                peak[0] = max(peak[0], plane.inflight)
                (plane.complete if rng.random() < 0.8 else plane.cancel)(d)
                ok += 1
            return ok
        with concurrent.futures.ThreadPoolExecutor(32) as ex:
            total = sum(ex.map(worker, [200] * 32))
        self.assertGreater(total, 0)
        self.assertLessEqual(peak[0], 16)
        self.assertEqual(plane.inflight, 0)

    def test_soak_governed_service_bounded_state(self):
        e = Env(inflight_limit=64, ptl=64)
        self.addCleanup(e.close)
        end = time.monotonic() + SOAK
        n = 0
        while time.monotonic() < end:
            e.send(os.urandom(70_000) if n % 5 == 0 else b"x" * 32, locality="same_node" if n % 5 == 0 else "auto")
            n += 1
        self.assertGreater(n, 10)
        self.assertEqual(e.plane.inflight, 0)
        self.assertEqual(e.journal.open_transfers(), {})
        self.assertEqual(e.svc.adapters["shared-memory"].live_segments(), 0)
        self.assertLessEqual(len(e.svc.log.ring), e.svc.log.ring.maxlen)
        self.assertEqual(e.audit.verify(), len(e.audit.records()))


if __name__ == "__main__":
    unittest.main()
