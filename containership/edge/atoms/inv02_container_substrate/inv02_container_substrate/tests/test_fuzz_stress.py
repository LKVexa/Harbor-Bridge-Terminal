"""MC61 fuzzing harnesses, MC63 race/concurrency stress, MC64 fault injection.

Deterministic seeded fuzzing (stdlib ``random``) so failures reproduce; set
``INV02_FUZZ_ITERS`` to raise iteration counts for long campaigns (CI nightly).
"""
import json
import os
import random
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from inv02_container_substrate import oci, rootfs, store
from inv02_container_substrate.registry import IntegrityError, LimitExceeded, Registry, RegistryError, ValidationError, parse_reference
from inv02_container_substrate.tests.fixtures import make_image, make_tar

ITERS = int(os.environ.get("INV02_FUZZ_ITERS", "300"))
EXPECTED = (oci.OCIError, IntegrityError, ValidationError, LimitExceeded, RegistryError)


def mutate(rng: random.Random, data: bytes) -> bytes:
    b = bytearray(data)
    for _ in range(rng.randint(1, 8)):
        op = rng.randint(0, 3)
        if op == 0 and b:
            b[rng.randrange(len(b))] = rng.randrange(256)
        elif op == 1 and b:
            del b[rng.randrange(len(b))]
        elif op == 2:
            b.insert(rng.randrange(len(b) + 1), rng.randrange(256))
        elif b:
            i = rng.randrange(len(b))
            b[i:i] = b[i:i + rng.randint(1, 32)]
    return bytes(b)


class FuzzTests(unittest.TestCase):
    def test_manifest_parser_never_crashes_unexpectedly(self):
        rng = random.Random(1234)
        seeds = [make_image([[("a", "file", b"x")]])["manifest"], make_image([[("a", "file", b"y")]])["config"]]
        for i in range(ITERS):
            data = mutate(rng, rng.choice(seeds))
            try:
                oci.parse_manifest(data)
            except EXPECTED:
                pass
            try:
                oci.ImageConfig.parse(data)
            except EXPECTED:
                pass

    def test_reference_parser(self):
        rng = random.Random(99)
        alphabet = "abc:/@._-0123456789sha256ABC \t\x00é"
        for _ in range(ITERS * 3):
            s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 80)))
            try:
                p = parse_reference(s)
                self.assertIn(p.kind, ("tag", "digest"))
            except ValidationError:
                pass

    def test_layer_unpack_never_escapes(self):
        rng = random.Random(7)
        seed, _ = make_tar([("d/", "dir"), ("d/f", "file", b"hello" * 50), ("l", "sym", "d/f")])
        with tempfile.TemporaryDirectory() as tmp:
            sentinel = Path(tmp) / "sentinel"
            sentinel.mkdir()
            for i in range(ITERS // 3):
                try:
                    rootfs.apply_layer(Path(tmp) / f"r{i}", mutate(rng, seed),
                                       policy=rootfs.UnpackPolicy(max_uncompressed_bytes=1 << 20, max_entries=100))
                except EXPECTED:
                    pass
            self.assertEqual(list(sentinel.iterdir()), [])

    def test_legacy_registry_pull_fuzz(self):
        rng = random.Random(5)
        reg = Registry()
        d = reg.push("app", "1", [b"a", b"b"])
        good = reg.blobs[d]
        for _ in range(ITERS):
            reg.blobs[d] = mutate(rng, good)
            try:
                reg.pull(d)
            except EXPECTED:
                pass


class StressTests(unittest.TestCase):
    def test_concurrent_writers_readers_and_gc(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = store.ContentStore(tmp)
            errors: list[BaseException] = []
            digests: list[str] = []
            lock = threading.Lock()

            def writer(n):
                try:
                    for i in range(25):
                        d = s.put(f"{n}-{i}".encode())
                        s.set_tag(f"r.test/w{n}:t{i % 3}", d)
                        with lock:
                            digests.append(d)
                except BaseException as e:
                    errors.append(e)

            def reader():
                try:
                    for _ in range(50):
                        with lock:
                            ds = list(digests[-5:])
                        for d in ds:
                            s.get(d)
                except BaseException as e:
                    errors.append(e)

            def collector():
                try:
                    for _ in range(5):
                        s.gc(grace_s=3600)
                except BaseException as e:
                    errors.append(e)

            ts = [threading.Thread(target=writer, args=(n,)) for n in range(6)] + \
                 [threading.Thread(target=reader) for _ in range(3)] + [threading.Thread(target=collector)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(errors, [])
            self.assertTrue(s.fsck()["ok"])
            self.assertEqual(len(s.snapshot_meta()["tags"]), 18)

    def test_multiprocess_cas(self):
        import multiprocessing as mp
        with tempfile.TemporaryDirectory() as tmp:
            s = store.ContentStore(tmp)
            base = s.put(b"base")
            s.set_tag("r.test/x:1", base)
            cands = [s.put(f"p{i}".encode()) for i in range(6)]
            ctx = mp.get_context("fork")
            q = ctx.Queue()
            ps = [ctx.Process(target=_cas_worker, args=(tmp, base, d, q)) for d in cands]
            [p.start() for p in ps]
            [p.join(30) for p in ps]
            results = [q.get(timeout=5) for _ in ps]
            self.assertEqual(results.count("win"), 1)


def _cas_worker(root, base, d, q):
    try:
        store.ContentStore(root).set_tag("r.test/x:1", d, expected=base)
        q.put("win")
    except store.ConflictError:
        q.put("lose")


class FaultInjectionTests(unittest.TestCase):
    def test_crash_during_atomic_write_leaves_previous_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = store.ContentStore(tmp)
            a = s.put(b"a")
            s.set_tag("r.test/x:1", a)
            b = s.put(b"b")
            with mock.patch("os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    s.set_tag("r.test/x:1", b)
            self.assertEqual(store.ContentStore(tmp).get_tag("r.test/x:1"), a)
            self.assertEqual([p for p in Path(tmp).iterdir() if p.name.endswith(".tmp")], [])

    def test_fsync_failure_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = store.ContentStore(tmp)
            with mock.patch("os.fsync", side_effect=OSError("EIO")):
                with self.assertRaises(OSError):
                    s.put(b"z")
            self.assertEqual(s.digests(), [])

    def test_corrupt_metadata_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store.ContentStore(tmp)
            Path(tmp, "meta.json").write_text("{not json")
            with self.assertRaises(IntegrityError):
                store.ContentStore(tmp)

    def test_lock_timeout(self):
        import fcntl
        with tempfile.TemporaryDirectory() as tmp:
            s = store.ContentStore(tmp, limits=store.StoreLimits(lock_timeout_s=0.2))
            fd = os.open(Path(tmp, "LOCK"), os.O_RDWR)
            fcntl.flock(fd, fcntl.LOCK_EX)
            import multiprocessing as mp
            ctx = mp.get_context("fork")
            q = ctx.Queue()
            p = ctx.Process(target=_lock_worker, args=(tmp, q))
            p.start()
            p.join(10)
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            self.assertEqual(q.get(timeout=5), "timeout")


def _lock_worker(root, q):
    try:
        store.ContentStore(root, limits=store.StoreLimits(lock_timeout_s=0.2)).put(b"x")
        q.put("acquired")
    except store.LockTimeout:
        q.put("timeout")


if __name__ == "__main__":
    unittest.main()
