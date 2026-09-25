"""C065-C066: copy / scheduler-transition / serialization profile of the element path.

* copies: identity check that write->read hands over the SAME object (zero-copy in-instance)
* serialization: bytes produced per element only at the INV-12 seam (CanonicalCodec)
* lock transitions: acquisitions per element (write=1, read=1) via an instrumented lock
* cProfile top functions for a 50k-element loop
Writes benchmarks/results/profile.json."""
import cProfile, io, json, pstats
from _tools_pkg import ROOT, mod

S = mod("stream"); A = mod("adapters")


class CountingLock:
    def __init__(self, inner): self.inner, self.n = inner, 0
    def __enter__(self): self.n += 1; return self.inner.__enter__()
    def __exit__(self, *a): return self.inner.__exit__(*a)
    def acquire(self, *a, **k): self.n += 1; return self.inner.acquire(*a, **k)
    def release(self): return self.inner.release()
    def _is_owned(self): return self.inner._is_owned()
    def _release_save(self): return self.inner._release_save()
    def _acquire_restore(self, x): return self.inner._acquire_restore(x)


def main():
    s = S.Stream(bytes, config=S.StreamConfig(max_credit=10, max_buffer=10)); s.grant(1)
    payload = b"x" * 4096
    s.write(payload); same = s.read() is payload
    s2 = S.Stream(int, config=S.StreamConfig(max_credit=1000, max_buffer=1000)); lock = CountingLock(s2._lock); s2._lock = lock
    s2.grant(1000); base = lock.n
    for i in range(1000): s2.write(i); s2.read()
    per_elem = (lock.n - base) / 1000
    codec = A.CanonicalCodec()
    ser = {t: len(codec.lower(v)) for t, v in (("int", 7), ("bytes4k", payload), ("str", "hello"))}
    pr = cProfile.Profile(); s3 = S.Stream(int, config=S.StreamConfig(max_credit=50000, max_buffer=50000)); s3.grant(50000)
    pr.enable()
    for i in range(50000): s3.write(i); s3.read()
    pr.disable()
    buf = io.StringIO(); pstats.Stats(pr, stream=buf).sort_stats("tottime").print_stats(8)
    out = {"zero_copy_in_instance": same, "lock_acquisitions_per_element": per_elem,
           "serialized_bytes_at_inv12_seam": ser, "copies_per_element_in_instance": 0 if same else None,
           "cprofile_top": [l for l in buf.getvalue().splitlines() if l.strip()][:20],
           "notes": "INV-17 never serializes inside an instance; the only encoding is the INV-12 seam."}
    (ROOT / "benchmarks" / "results").mkdir(parents=True, exist_ok=True)
    (ROOT / "benchmarks" / "results" / "profile.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("zero_copy_in_instance", "lock_acquisitions_per_element", "serialized_bytes_at_inv12_seam")}))


if __name__ == "__main__":
    main()
