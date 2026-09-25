"""Standalone security and protocol tests for PK_CTRL_FRAME/2.

These tests intentionally do not depend on ``pk_core``.
"""
from __future__ import annotations

import hashlib
import pathlib
import struct
import subprocess
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv36_control_transport import (  # noqa: E402
    FRAME_VERSION,
    MAX_FRAME,
    MAX_WIRE_FRAME,
    AuthFailure,
    FrameFormatError,
    FrameTooLarge,
    OutOfOrder,
    Relay,
    Replay,
    SequenceExhausted,
    Session,
    SessionClosed,
)
from inv36_control_transport.transport import HEADER_SIZE, MAX_SEQUENCE, TAG_SIZE  # noqa: E402


def pair(session_id: bytes = b"S" * 16):
    shared = hashlib.sha256(b"unit-test authenticated shared secret").digest()
    return (
        Session("node-a", "node-b", shared, session_id=session_id),
        Session("node-b", "node-a", shared, session_id=session_id),
    )


class TransportTest(unittest.TestCase):
    """REQ: INV36-REQ-005, INV36-REQ-006, INV36-REQ-007, INV36-REQ-008, INV36-REQ-009, INV36-REQ-010 | KIND: security"""

    def test_round_trip_both_directions_and_empty_frame(self):
        a, b = pair()
        self.assertEqual(b.open(a.seal(b"lease=42")), b"lease=42")
        self.assertEqual(a.open(b.seal(b"ack")), b"ack")
        self.assertEqual(b.open(a.seal(b"")), b"")
        self.assertEqual(a.frames_sealed, 2)
        self.assertEqual(b.frames_opened, 2)

    def test_ciphertext_does_not_contain_plaintext(self):
        a, b = pair()
        message = b"REVOKE highly-sensitive-lease-42"
        wire = a.seal(message)
        self.assertNotIn(message, wire)
        self.assertEqual(b.open(wire), message)

    def test_tamper_ciphertext_and_sequence_fail_authentication(self):
        a, b = pair()
        wire = bytearray(a.seal(b"grant"))
        wire[-1] ^= 1
        with self.assertRaises(AuthFailure):
            b.open(wire)
        self.assertEqual(b.recv_seq, 0)

        wire = bytearray(a.seal(b"next"))
        # Sequence is the final 8 bytes of the fixed header.  Tampering it must
        # fail AEAD authentication rather than affecting replay state.
        wire[HEADER_SIZE - 1] ^= 1
        with self.assertRaises(AuthFailure):
            b.open(wire)
        self.assertEqual(b.recv_seq, 0)

    def test_wrong_key_session_id_and_reflection_fail(self):
        shared = hashlib.sha256(b"shared").digest()
        a = Session("a", "b", shared, session_id=b"A" * 16)
        wrong_key = Session("b", "a", hashlib.sha256(b"other").digest(), session_id=b"A" * 16)
        wrong_session = Session("b", "a", shared, session_id=b"B" * 16)
        frame = a.seal(b"control")
        with self.assertRaises(AuthFailure):
            wrong_key.open(frame)
        with self.assertRaises(AuthFailure):
            wrong_session.open(frame)
        with self.assertRaises(AuthFailure):
            a.open(frame)

    def test_replay_and_out_of_order_are_refused_without_advancing_state(self):
        a, b = pair()
        f1 = a.seal(b"one")
        f2 = a.seal(b"two")
        with self.assertRaises(OutOfOrder):
            b.open(f2)
        self.assertEqual(b.recv_seq, 0)
        self.assertEqual(b.open(f1), b"one")
        self.assertEqual(b.open(f2), b"two")
        with self.assertRaises(Replay):
            b.open(f1)
        self.assertEqual(b.recv_seq, 2)
        self.assertEqual(b.out_of_order, 1)
        self.assertEqual(b.replays, 1)

    def test_frame_bounds_and_wire_bounds(self):
        a, b = pair()
        payload = b"x" * MAX_FRAME
        frame = a.seal(payload)
        self.assertLessEqual(len(frame), MAX_WIRE_FRAME)
        self.assertEqual(b.open(frame), payload)
        with self.assertRaises(FrameTooLarge):
            a.seal(b"x" * (MAX_FRAME + 1))
        relay = Relay()
        with self.assertRaises(FrameTooLarge):
            relay.forward(b"x" * (MAX_WIRE_FRAME + 1))

    def test_malformed_magic_version_algorithm_zero_sequence_and_short_frame(self):
        a, b = pair()
        with self.assertRaises(FrameFormatError):
            b.open(b"short")

        frame = bytearray(a.seal(b"x"))
        frame[0] ^= 1
        with self.assertRaises(FrameFormatError):
            b.open(frame)

        frame = bytearray(a.seal(b"x"))
        frame[4] = (FRAME_VERSION + 1) & 0xFF
        with self.assertRaises(FrameFormatError):
            b.open(frame)

        frame = bytearray(a.seal(b"x"))
        frame[5] = 0xFF
        with self.assertRaises(FrameFormatError):
            b.open(frame)

        # Struct layout is magic(4), version(1), algorithm(1), sequence(8).
        header = struct.pack(">4sBBQ", b"PKCT", FRAME_VERSION, 1, 0)
        with self.assertRaises(FrameFormatError):
            b.open(header + b"x" * TAG_SIZE)

    def test_sequence_exhaustion_fails_before_nonce_reuse(self):
        a, _ = pair()
        a.send_seq = MAX_SEQUENCE
        with self.assertRaises(SequenceExhausted):
            a.seal(b"never sent")
        self.assertEqual(a.frames_sealed, 0)

    def test_secret_not_exposed_in_repr_and_reference_dropped(self):
        secret = b"Z" * 32
        s = Session("a", "b", secret, session_id=b"S" * 16)
        self.assertNotIn("ZZZZ", repr(s))
        self.assertEqual(s.shared, b"")

    def test_close_is_fail_closed(self):
        a, _ = pair()
        a.close()
        with self.assertRaises(SessionClosed):
            a.seal(b"x")
        with self.assertRaises(SessionClosed):
            a.open(b"x" * (HEADER_SIZE + TAG_SIZE))

    def test_relay_history_is_bounded_and_can_be_disabled(self):
        relay = Relay(max_history=2)
        relay.forward(b"a")
        relay.forward(b"b")
        relay.forward(b"c")
        self.assertEqual(list(relay.seen), [b"b", b"c"])
        blind = Relay(max_history=0)
        blind.forward(b"ciphertext")
        self.assertEqual(list(blind.seen), [])

    def test_concurrent_seal_allocates_unique_monotonic_sequences(self):
        a, b = pair()
        frames = []
        frames_lock = threading.Lock()

        def worker(i):
            frame = a.seal(f"m{i}".encode())
            with frames_lock:
                frames.append(frame)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(64)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(a.send_seq, 64)
        sequences = [int.from_bytes(frame[HEADER_SIZE - 8:HEADER_SIZE], "big") for frame in frames]
        self.assertEqual(sorted(sequences), list(range(1, 65)))
        for frame in sorted(frames, key=lambda f: int.from_bytes(f[HEADER_SIZE - 8:HEADER_SIZE], "big")):
            b.open(frame)
        self.assertEqual(b.recv_seq, 64)

    def test_identity_encoding_is_unambiguous(self):
        shared = hashlib.sha256(b"shared").digest()
        sid = b"I" * 16
        a = Session("a|b", "c", shared, session_id=sid)
        b = Session("c", "a|b", shared, session_id=sid)
        self.assertEqual(b.open(a.seal(b"ok")), b"ok")

    def test_optimized_mode_runs_security_path(self):
        code = (
            "import hashlib,sys; sys.path.insert(0,%r); "
            "from inv36_control_transport import Session; "
            "k=hashlib.sha256(b'k').digest(); sid=b'S'*16; "
            "a=Session('a','b',k,sid); b=Session('b','a',k,sid); "
            "print(b.open(a.seal(b'ok')).decode())"
        ) % str(ROOT)
        proc = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
