"""Item 11 (error contract, C026) and item 13 (resource ceilings, C017/C028/C067)."""
import json
import unittest

from _support import errors, model, schema, schemavalidate, spec

ERR_SCHEMA = schema("PK_DEVICE_ERROR_1.schema.json")


def code_of(fn):
    try:
        fn()
    except errors.Inv25Error as exc:
        return exc.code
    raise AssertionError("no error raised")


class ErrorContractTest(unittest.TestCase):
    CASES = {
        "INV25_INVALID_NAME": lambda: model.DeviceCatalogue("prod").register(spec(name="../x")),
        "INV25_INVALID_CLASS": lambda: model.DeviceCatalogue("prod").register(
            model.DeviceSpec("x", "emulated-ide", "1.0", frozenset(), "r", "s")),
        "INV25_FORBIDDEN_LEGACY_EMULATION": lambda: model.DeviceCatalogue("prod").register(
            model.DeviceSpec("x", "legacy-emulation", "1.0", frozenset(), "r", "s")),
        "INV25_FORBIDDEN_HOST_EXPOSURE": lambda: model.DeviceCatalogue("prod").register(
            model.DeviceSpec("x", "raw-mmio", "1.0", frozenset(), "r", "s")),
        "INV25_INVALID_VERSION": lambda: model.DeviceCatalogue("prod").register(spec(version="latest")),
        "INV25_INVALID_REGISTER": lambda: model.DeviceCatalogue("prod").register(spec(regs=("bad reg",))),
        "INV25_MISSING_RATIONALE": lambda: model.DeviceCatalogue("prod").register(
            model.DeviceSpec("x", "paravirtual", "1.0", frozenset(), "  ", "s")),
        "INV25_MISSING_REVIEWER": lambda: model.DeviceCatalogue("prod").register(
            model.DeviceSpec("x", "paravirtual", "1.0", frozenset(), "r", "")),
        "INV25_REPLACE_TARGET_ABSENT": lambda: model.DeviceCatalogue("prod").replace(spec()),
        "INV25_LIMIT_EXCEEDED": lambda: model.DeviceCatalogue("prod").register(
            spec(regs=[f"r{i}" for i in range(model.MAX_REGISTERS_PER_DEVICE + 1)])),
    }

    def test_one_stable_code_per_condition_and_schema_valid(self):
        for code, fn in self.CASES.items():
            with self.subTest(code=code):
                self.assertEqual(code_of(fn), code)
                self.assertEqual(code_of(fn), code)  # deterministic
                try:
                    fn()
                except errors.Inv25Error as exc:
                    rec = errors.to_error(exc, operation="register", correlation_id="c-1")
                self.assertEqual(schemavalidate.validate(rec, ERR_SCHEMA), [])
                self.assertEqual(rec["code"], code)

    def test_replace_required_and_version_not_changed(self):
        cat = model.DeviceCatalogue("prod")
        cat.register(spec())
        self.assertEqual(code_of(lambda: cat.register(spec(version="1.1", regs=("a",)))), "INV25_REPLACE_REQUIRED")
        self.assertEqual(code_of(lambda: cat.replace(spec(regs=("a",)))), "INV25_VERSION_NOT_CHANGED")

    def test_every_code_serializes(self):
        for code in errors.CODES:
            rec = errors.to_error(errors.Inv25Error(code=code), operation="op")
            self.assertEqual(schemavalidate.validate(rec, ERR_SCHEMA), [], code)

    def test_unknown_failures_map_to_safe_generic(self):
        rec = errors.to_error(KeyError("/etc/shadow secret"), operation="op")
        self.assertEqual(rec["code"], "INV25_INTERNAL")
        self.assertNotIn("shadow", json.dumps(rec))

    def test_redaction(self):
        exc = errors.Inv25Error(code="INV25_UNAUTHENTICATED", token="abc", path="/srv/app/x", note="a\nb", ok="fine")
        rec = errors.to_error(exc, operation="op")
        self.assertEqual(rec["details"], {"note": "[redacted]", "ok": "fine"})

    def test_library_exception_types_preserved(self):
        with self.assertRaises(PermissionError):
            model.DeviceCatalogue("prod").register(spec(name=""))


class LimitsTest(unittest.TestCase):
    def test_registers_per_device_boundaries(self):
        m = model.MAX_REGISTERS_PER_DEVICE
        for n, ok in ((m - 1, True), (m, True), (m + 1, False)):
            with self.subTest(n=n):
                cat = model.DeviceCatalogue("prod")
                s = spec(regs=[f"r{i}" for i in range(n)])
                if ok:
                    cat.register(s)
                else:
                    self.assertRaises(model.LimitExceeded, cat.register, s)

    def test_device_count_boundaries(self):
        cat = model.DeviceCatalogue("prod")
        for i in range(model.MAX_DEVICES):
            cat.register(spec(name=f"d{i}", regs=()))
        self.assertRaises(model.LimitExceeded, cat.register, spec(name="overflow", regs=()))

    def test_aggregate_register_ceiling(self):
        cat = model.DeviceCatalogue("prod")
        per = model.MAX_REGISTERS_PER_DEVICE
        n = model.MAX_AGGREGATE_REGISTERS // per
        for i in range(n):
            cat.register(spec(name=f"d{i}", regs=[f"r{j}" for j in range(per)]))
        self.assertEqual(cat.total_surface(), model.MAX_AGGREGATE_REGISTERS)
        self.assertRaises(model.LimitExceeded, cat.register, spec(name="one-more", regs=("x",)))
        self.assertRaises(model.LimitExceeded, cat.replace,
                          spec(name="d0", version="2.0", regs=[f"q{j}" for j in range(per)] + ["extra"]))

    def test_field_lengths(self):
        for field, lim in (("rationale", 1024), ("reviewer", 256)):
            ok = dict(rationale="r", reviewer="s")
            ok[field] = "a" * lim
            model.DeviceCatalogue("prod").register(model.DeviceSpec("x", "paravirtual", "1.0", frozenset(), **ok))
            ok[field] = "a" * (lim + 1)
            self.assertRaises(model.LimitExceeded, model.DeviceCatalogue("prod").register,
                              model.DeviceSpec("x", "paravirtual", "1.0", frozenset(), **ok))

    def test_oversized_payload_rejected_before_parse(self):
        blob = b"[" * (model.MAX_EXPORT_BYTES + 1)
        with self.assertRaises(model.LimitExceeded):
            model.catalogue_from_export(blob)

    def test_huge_input_bounded(self):
        with self.assertRaises(model.LimitExceeded):
            model.DeviceCatalogue("prod").register(spec(name="a" * 10_000_000))


if __name__ == "__main__":
    unittest.main()
