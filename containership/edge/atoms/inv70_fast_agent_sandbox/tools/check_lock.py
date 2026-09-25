"""CI lockfile / runtime-integrity check (C031, C045). Exit 1 on any violation."""
import pathlib
import re
import sys

LOCK = pathlib.Path(__file__).resolve().parents[1] / "requirements" / "wasm.lock"


def problems(text: str) -> list[str]:
    out = []
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    if not lines:
        return ["lock is empty"]
    for l in lines:
        if not re.match(r"^[A-Za-z0-9_.-]+==\d+(\.\d+)*\s+--hash=sha256:[0-9a-f]{64}$", l):
            out.append(f"not an exact, hashed pin: {l}")
    return out


if __name__ == "__main__":
    p = problems(LOCK.read_text())
    for x in p:
        print("LOCK:", x)
    sys.exit(1 if p else 0)
