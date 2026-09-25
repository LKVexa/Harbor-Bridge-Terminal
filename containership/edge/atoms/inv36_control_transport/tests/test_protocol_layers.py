"""Errors, IDL-generated constants, PK_CTRL_MSG/1 and PK_CTRL_STREAM/1."""
from __future__ import annotations

import json
import pathlib
import threading
import unittest

import _util  # noqa: F401

from inv36_control_transport import _wire, messages, schema_check, stream
from inv36_control_transport.errors import ErrorCode, Inv36Error, code_by_number, error_dict
from inv36_control_transport.transport import AuthFailure, MAX_WIRE_FRAME

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"


class ErrorTaxonomyTest(unittest.TestCase):
    """REQ: INV36-REQ-034 | KIND: unit"""

    def test_codes_unique_ranged_and_schema_valid(self):
        schema = schema_check.load("error.schema.json")
        numbers = [c.number for c in ErrorCode]
        self.assertEqual(len(numbers), len(set(numbers)))
        for c in ErrorCode:
            self.assertTrue(100 <= c.number < 1000)
            self.assertIs(code_by_number(c.number), c)
            schema_check.validate(Inv36Error("x", code=c).to_dict(), schema)

    def test_transport_exceptions_carry_codes_and_stay_value_errors(self):
        e = AuthFailure("bad")
        self.assertIsInstance(e, ValueError)
        self.assertEqual(e.code, ErrorCode.AUTH_FAILURE)
        self.assertTrue(e.to_dict()["terminal"])

    def test_detail_is_bounded_and_single_line(self):
        e = Inv36Error("m", detail={f"k{i}": "v\n" * 500 for i in range(50)})
        d = e.to_dict()
        self.assertLessEqual(len(d["detail"]), 8)
        for v in d["detail"].values():
            self.assertNotIn("\n", v)
            self.assertLessEqual(len(v), 256)
        self.assertEqual(error_dict(RuntimeError("secret-value"))["message"], "RuntimeError")

    def test_retry_after_only_for_retryable(self):
        self.assertNotIn("retry_after_s", Inv36Error("x", code=ErrorCode.AUTH_FAILURE, retry_after_s=1).to_dict())
        self.assertIn("retry_after_s", Inv36Error("x", code=ErrorCode.OVERLOADED, retry_after_s=1).to_dict())


class WireIdlTest(unittest.TestCase):
    """REQ: INV36-REQ-040, INV36-REQ-009 | KIND: unit"""

    def test_generated_module_matches_idl(self):
        from inv36_control_transport.tools import gen_wire
        py, md = gen_wire.render()
        self.assertEqual(py, (pathlib.Path(_wire.__file__)).read_text(), "run tools/gen_wire.py")
        self.assertEqual(md, gen_wire.OUT_MD.read_text())

    def test_record_bound_equals_frame_bound(self):
        self.assertEqual(stream.MAX_RECORD, MAX_WIRE_FRAME)


class MessageCodecTest(unittest.TestCase):
    """REQ: INV36-REQ-040, INV36-REQ-006, INV36-REQ-044 | KIND: unit"""

    def test_round_trip_and_canonical(self):
        for name in messages.MESSAGE_TYPES:
            m = messages.ControlMessage.of(name, "tenant-a", b"body", traceparent="00-" + "1" * 32 + "-" + "2" * 16 + "-01")
            enc = m.encode()
            self.assertEqual(messages.decode(enc), m)
            self.assertEqual(messages.decode(enc).encode(), enc)

    def test_golden_fixture(self):
        fx = json.loads((FIXTURES / "golden_messages.json").read_text())
        for case in fx["cases"]:
            m = messages.ControlMessage.of(case["type"], case["tenant"], bytes.fromhex(case["body"]),
                                           op_id=bytes.fromhex(case["op_id"]), traceparent=case["traceparent"])
            self.assertEqual(m.encode().hex(), case["encoded"], case["type"])

    def test_rejections(self):
        good = messages.ControlMessage.of("HEARTBEAT", "t1").encode()
        bad_cases = {
            "version": bytes([2]) + good[1:],
            "flags": good[:1] + b"\x01" + good[2:],
            "ext": good[:4] + b"\x00\x01" + good[6:],
            "trailing": good + b"\x00",
            "truncated": good[:-1],
            "empty": b"",
            "tenant_zero": good[:22] + b"\x00" + good[23:],
        }
        for name, data in bad_cases.items():
            with self.subTest(name), self.assertRaises(Inv36Error):
                messages.decode(data)
        unknown = good[:2] + (0x7FFF).to_bytes(2, "big") + good[4:]
        with self.assertRaises(messages.UnknownMessageType):
            messages.decode(unknown)
        with self.assertRaises(messages.MessageFormatError):
            messages.ControlMessage.of("HEARTBEAT", "UPPER")
        with self.assertRaises(messages.MessageFormatError):
            messages.ControlMessage.of("HEARTBEAT", "t", b"x" * (messages.BODY_MAX + 1))

    def test_malicious_length_claims(self):
        m = messages.ControlMessage.of("PLACEMENT", "t1", b"abc").encode()
        # body length claims 4 GiB
        forged = m[:-7] + b"\xff\xff\xff\xff" + m[-3:]
        with self.assertRaises(messages.MessageFormatError):
            messages.decode(forged)

    def test_registry_ranges(self):
        lo, hi = _wire.MESSAGE_TYPE_RANGES["assigned"]
        for v in messages.MESSAGE_TYPES.values():
            self.assertTrue(lo <= v <= hi)


class StreamTest(unittest.TestCase):
    """REQ: INV36-REQ-011, INV36-REQ-009, INV36-REQ-001 | KIND: unit"""

    def conn_pair(self, **plans):
        a, b = stream.FakeStream.pair(**plans)
        return stream.Connection(a, read_timeout=1, write_timeout=1), stream.Connection(b, read_timeout=1,
                                                                                         write_timeout=1)

    def test_preamble_and_records_with_fragmentation_at_every_size(self):
        for chunk in (1, 2, 3, 5, 6, 7, 64):
            a, b = self.conn_pair(a_plan=stream.FaultPlan(max_chunk=chunk), b_plan=stream.FaultPlan(max_chunk=chunk))
            t = threading.Thread(target=a.exchange_preamble)
            t.start()
            b.exchange_preamble()
            t.join()
            payloads = [b"", b"x", bytes(range(256)) * 3]
            for p in payloads:
                a.send_record(stream.FRAME, p)
            for p in payloads:
                self.assertEqual(b.recv_record(), (stream.FRAME, p))

    def test_legacy_peer_rejected_before_payload(self):
        a_raw, b_raw = stream.FakeStream.pair()
        b = stream.Connection(b_raw, read_timeout=1)
        # PK_CTRL_FRAME/1 peers start directly with an 8-byte sequence number
        a_raw.send(b"\x00" * 8 + b"legacy", 1)
        with self.assertRaises(stream.StreamLengthInvalid):
            b.exchange_preamble()
        self.assertTrue(b.closed)

    def test_huge_advertised_length_rejected_before_allocation(self):
        with self.assertRaises(stream.StreamLengthInvalid):
            stream.parse_record_header(b"\x02\x00\xff\xff\xff\xff")
        with self.assertRaises(stream.StreamLengthInvalid):
            stream.parse_record_header(b"\x02\x00" + (MAX_WIRE_FRAME + 1).to_bytes(4, "big"))
        stream.parse_record_header(b"\x02\x00" + MAX_WIRE_FRAME.to_bytes(4, "big"))
        for bad in (b"\x09\x00\x00\x00\x00\x00", b"\x02\x01\x00\x00\x00\x00", b"\x03\x00\x00\x00\x00\x01"):
            with self.assertRaises(stream.StreamLengthInvalid):
                stream.parse_record_header(bad)

    def test_eof_semantics(self):
        a, b = self.conn_pair()
        a.send_record(stream.FRAME, b"abc")
        a.stream.send(b"\x02\x00\x00\x00\x00\x10abc", 1)  # partial record then EOF
        a.stream.close()
        self.assertEqual(b.recv_record(), (stream.FRAME, b"abc"))
        with self.assertRaises(stream.StreamTruncated):
            b.recv_record()
        a2, b2 = self.conn_pair()
        a2.close(graceful=True)
        with self.assertRaises(stream.StreamEOF):
            b2.recv_record()
        a3, b3 = self.conn_pair()
        a3.stream.close()
        with self.assertRaises(stream.StreamEOF):
            b3.recv_record()

    def test_timeouts_resets_and_short_writes(self):
        a, b = self.conn_pair(b_plan=stream.FaultPlan(stall_reads=True))
        with self.assertRaises(stream.StreamTimeout):
            b.recv_record()
        self.assertTrue(b.closed)
        a, b = self.conn_pair(a_plan=stream.FaultPlan(reset_after_bytes=10))
        with self.assertRaises(stream.StreamReset):
            a.send_record(stream.FRAME, b"y" * 100)
        with self.assertRaises((stream.StreamReset, stream.StreamTruncated)):
            b.recv_record()
        a, b = self.conn_pair(a_plan=stream.FaultPlan(short_write=3))
        a.send_record(stream.FRAME, b"z" * 50)
        self.assertEqual(b.recv_record(), (stream.FRAME, b"z" * 50))

    def test_single_reader_ownership(self):
        a, b = self.conn_pair()
        got = []

        def reader():
            try:
                got.append(b.recv_record())
            except stream.StreamError as exc:
                got.append(exc)

        t = threading.Thread(target=reader)
        t.start()
        import time
        time.sleep(0.05)
        with self.assertRaises(stream.StreamBusy):
            b.recv_record()
        a.send_record(stream.FRAME, b"only-once")
        t.join()
        self.assertEqual(got[0], (stream.FRAME, b"only-once"))

    def test_concurrent_writers_never_interleave(self):
        a, b = self.conn_pair(a_plan=stream.FaultPlan(max_chunk=3))
        msgs = [bytes([i]) * 200 for i in range(20)]
        ts = [threading.Thread(target=a.send_record, args=(stream.FRAME, m)) for m in msgs]
        for t in ts:
            t.start()
        received = [b.recv_record()[1] for _ in msgs]
        for t in ts:
            t.join()
        self.assertEqual(sorted(received), sorted(msgs))

    def test_close_is_idempotent_and_clears_buffers(self):
        a, b = self.conn_pair()
        closes = []
        b.on_close = lambda: closes.append(1)
        b.close()
        b.close()
        self.assertEqual(closes, [1])
        with self.assertRaises(stream.StreamReset):
            b.recv_record()


if __name__ == "__main__":
    unittest.main()
