"""Item 20: deterministic adversarial/fuzz regression suite (C050, C085, C087).

Stdlib only.  Seeds are fixed (checked-in corpus under conformance/fuzz/); the
bounded CI smoke run uses INV25_FUZZ_ITER (default 3000).  The invariant is
closed-fail: every input either yields a valid catalogue that round-trips, or
raises an Inv25Error - never another exception, hang, or silent acceptance of a
forbidden class.
"""
import json
import os
import random
import unittest

from _support import PKG_DIR, errors, model

ITER = int(os.environ.get("INV25_FUZZ_ITER", "3000"))
SEEDS = [1, 25, 4242, 20260923]
NASTY = ["", " ", "\x00", "\x7f", "‮", "﻿", "​", "../../etc", "a" * 70, "A", "virtio-net",
         "VIRTIO-NET", "virtio‑net", "ｖirtio", "1.0", "1.0.0-" + "x" * 80, "01.0", "1..0", "-1.0",
         "legacy-emulation", "Legacy-Emulation", "host-passthrough", "raw-mmio", "paravirtual", "paravirtual ",
         "{\"x\":1}", "$(rm -rf)", "status\nforged=1", 0, None, True, 1.5, [], {}]


def rand_value(r):
    return r.choice(NASTY) if r.random() < 0.7 else "".join(chr(r.randrange(0, 0x3000)) for _ in range(r.randrange(0, 20)))


def rand_regs(r):
    k = r.random()
    if k < 0.1:
        return {"status"}
    if k < 0.15:
        return frozenset(f"r{i}" for i in range(r.choice([255, 256, 257, 5000])))
    if k < 0.2:
        return frozenset({"Status", "status"})
    return frozenset(v for v in (rand_value(r) for _ in range(r.randrange(0, 5))) if isinstance(v, str) or True
                     if not isinstance(v, (list, dict)))


class FuzzTest(unittest.TestCase):
    def check(self, fn):
        try:
            return fn()
        except errors.Inv25Error:
            return None

    def test_devicespec_and_catalogue_closed_fail(self):
        for seed in SEEDS:
            r = random.Random(seed)
            for _ in range(ITER // len(SEEDS)):
                cat = model.DeviceCatalogue("prod")
                cls = r.choice(["paravirtual"] * 3 + [rand_value(r)])
                s = model.DeviceSpec(rand_value(r) if r.random() < .5 else "virtio-net", cls,
                                     rand_value(r) if r.random() < .5 else "1.0", rand_regs(r),
                                     rand_value(r) if r.random() < .3 else "why", rand_value(r) if r.random() < .3 else "sec")
                got = self.check(lambda: cat.register(s))
                if got is not None:
                    self.assertEqual(got.device_class, "paravirtual")
                    self.assertNotIn(got.device_class, model.FORBIDDEN_CLASSES)
                    rt = model.catalogue_from_export(json.dumps(cat.export()))
                    self.assertEqual(rt.digest(), cat.digest())

    def test_parser_closed_fail(self):
        base = model.DeviceCatalogue("prod")
        base.register(model.DeviceSpec("virtio-net", "paravirtual", "1.0", frozenset({"a"}), "r", "s"))
        good = json.dumps(base.export())
        r = random.Random(7)
        payloads = ["[" * 100_000, "{" * 5000, '{"schema":"PK_DEVICE_CATALOGUE/1"}', "NaN", "1e999",
                    json.dumps({**base.export(), "extra": 1}), good.replace("paravirtual", "host-passthrough"),
                    good.replace('"a"', '"a","a"'), good.replace("PK_DEVICE_CATALOGUE/1", "PK_DEVICE_CATALOGUE/2"),
                    b"\xff\xfe", json.dumps({**base.export(), "devices": [base.export()["devices"][0]] * 2})]
        for _ in range(ITER // 3):
            b = bytearray(good.encode())
            for _ in range(r.randrange(1, 6)):
                b[r.randrange(len(b))] = r.randrange(256)
            payloads.append(bytes(b))
        for p in payloads:
            c = self.check(lambda: model.catalogue_from_export(p))
            if c is not None:
                for d in c.devices.values():
                    self.assertEqual(d.device_class, "paravirtual")

    def test_checked_in_regression_corpus(self):
        corpus = PKG_DIR / "conformance" / "fuzz" / "regressions.json"
        cases = json.loads(corpus.read_text())
        self.assertGreater(len(cases), 0)
        for case in cases:
            with self.subTest(case["id"]):
                s = model.DeviceSpec(case["name"], case["class"], case["version"], frozenset(case["registers"]),
                                     case["rationale"], case["reviewer"])
                if case["expect"] == "accept":
                    model.DeviceCatalogue("prod").register(s)
                else:
                    with self.assertRaises(errors.Inv25Error) as cm:
                        model.DeviceCatalogue("prod").register(s)
                    self.assertEqual(cm.exception.code, case["expect"])


if __name__ == "__main__":
    unittest.main()
