"""Reference producer / consumer (C029).  Executed by tests/test_wire.py so it cannot drift.

Run from the directory containing the package:
    python inv18_completion_primitive/examples/producer_consumer.py
"""
import pathlib
import sys
import threading

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
PKG = pathlib.Path(__file__).resolve().parents[1].name
pkg = __import__(PKG)
runtime = __import__(PKG + ".runtime", fromlist=["Runtime"])


def main() -> list:
    rt = runtime.Runtime({"environment": "dev"})
    out = []

    # 1. value: producer thread resolves, consumer waits with its own deadline
    writer, reader = rt.create(int, tenant="example")
    threading.Thread(target=lambda: rt.resolve(writer, 42)).start()
    out.append(rt.take_wait(reader, timeout=5.0))                  # ('ok', 42)

    # 2. error: an error is a normal, tagged outcome
    writer2, reader2 = rt.create(str, tenant="example")
    rt.resolve_error(writer2, "DEPENDENCY_UNAVAILABLE: upstream refused")
    out.append(rt.take(reader2))                                   # ('error', '...')

    # 3. abandonment: the producer drops its capability without resolving
    writer3, reader3 = rt.create(str, tenant="example")
    del writer3
    try:
        rt.take(reader3)
    except pkg.Abandoned as exc:
        out.append(("abandoned", exc.code))                        # ('abandoned', 'FUTURE_ABANDONED')
    return out


if __name__ == "__main__":
    for line in main():
        print(line)
