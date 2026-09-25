"""Differential check of wasm_verify.parse_module against V8 WebAssembly.validate.

Declared lane NODE_WASM. Mutates the test fixtures with a fixed seed and
reports the agreement table; the result is evidence, not a pass/fail gate:
parse_module is a structural validator and is EXPECTED to accept some modules
whose instruction sequences V8 rejects. It must never accept fewer valid
modules than policy explains (the only intended refusals of V8-valid modules
are shared/memory64 limits and multiple memories).

    python tools/differential_v8.py [--n 4000] [--seed 7] [--out evidence/DIFFERENTIAL_V8.json]
"""
from __future__ import annotations

import argparse
import base64
import collections
import importlib
import json
import pathlib
import random
import shutil
import subprocess
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG_DIR.parent))
sys.path.insert(0, str(PKG_DIR / "tests"))
wv = importlib.import_module(f"{PKG_DIR.name}.wasm_verify")
import wasm_fixtures as fx  # noqa: E402

POLICY_REFUSALS = ("memory64/shared", "multiple memories")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=str(PKG_DIR / "evidence" / "DIFFERENTIAL_V8.json"))
    a = ap.parse_args(argv)
    if shutil.which("node") is None:
        print("NOT RUN: lane NODE_WASM unavailable (node not on PATH)")
        return 3
    rng = random.Random(a.seed)
    seeds = [fx.module(), fx.module(imports=(("env", "a"),)), fx.module(mem=None)]
    samples = []
    for _ in range(a.n):
        d = bytearray(rng.choice(seeds))
        for _ in range(rng.randint(1, 3)):
            d[rng.randrange(len(d))] = rng.randrange(256)
        samples.append(bytes(d))
    ours, reasons = [], []
    for d in samples:
        try:
            wv.parse_module(d); ours.append(True); reasons.append(None)
        except wv.MalformedModule as exc:
            ours.append(False); reasons.append(str(exc))
    js = ("const l=require('fs').readFileSync(0,'utf8').trim().split('\\n');"
          "console.log(JSON.stringify(l.map(x=>WebAssembly.validate(Buffer.from(x,'base64')))))")
    v8 = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True,
                                   input="\n".join(base64.b64encode(s).decode() for s in samples)).stdout)
    table = collections.Counter(f"ours={'accept' if o else 'refuse'}/v8={'valid' if v else 'invalid'}"
                                for o, v in zip(ours, v8))
    over_strict = [reasons[i] for i in range(len(samples)) if not ours[i] and v8[i]]
    unexplained = [r for r in over_strict if not any(p in r for p in POLICY_REFUSALS)]
    result = {"schema": "INV44_DIFFERENTIAL/1", "label": "MEASURED", "seed": a.seed, "n": a.n,
              "table": dict(sorted(table.items())),
              "refused_but_v8_valid": {"policy": len(over_strict) - len(unexplained),
                                       "unexplained": len(unexplained), "examples": unexplained[:5]},
              "accepted_but_v8_invalid_rate": round(table["ours=accept/v8=invalid"] / a.n, 4)}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if unexplained else 0


if __name__ == "__main__":
    raise SystemExit(main())
