"""M15 - differential validation harness.

Runs the same corpus through this validator and an independent reference
(V8's ``WebAssembly.validate`` via Node.js, when present) and classifies every
disagreement:

* ``FALSE_ACCEPT``  - we accept, reference rejects      -> CRITICAL, blocks release
* ``PROPOSAL_GAP``  - we refuse with UNSUPPORTED_PROPOSAL, reference accepts
                      (expected: V8 enables proposals we do not certify)
* ``LIMIT_GAP``     - we refuse on an M13 ceiling, reference accepts (expected)
* ``FALSE_REJECT``  - any other reject the reference accepts -> investigate
"""
from __future__ import annotations

import base64
import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterable

from .errors import Code, InvalidModule
from .typecheck import validate_module

_NODE_SRC = r"""
const lines = require('fs').readFileSync(0, 'utf8').split('\n').filter(Boolean);
const out = lines.map(l => { try { return WebAssembly.validate(Buffer.from(l, 'base64')) ? 1 : 0; }
                             catch (e) { return -1; } });
process.stdout.write(JSON.stringify(out));
"""


def node_available() -> bool:
    return shutil.which("node") is not None


def reference_verdicts(modules: list[bytes], timeout: float = 120.0) -> list[int]:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node not found: differential reference unavailable")
    inp = "\n".join(base64.b64encode(m).decode() for m in modules) + "\n"
    r = subprocess.run([node, "-e", _NODE_SRC], input=inp, capture_output=True, text=True,
                       timeout=timeout, check=True)
    return json.loads(r.stdout)


@dataclass
class Disagreement:
    name: str
    kind: str
    ours: str
    reference: int


def ours(m: bytes) -> tuple[bool, str]:
    try:
        validate_module(m)
        return True, "OK"
    except InvalidModule as e:
        return False, e.code.value


def run(corpus: Iterable[tuple[str, bytes]]) -> dict:
    items = list(corpus)
    ref: list[int] = []
    for i in range(0, len(items), 1000):
        ref += reference_verdicts([m for _, m in items[i:i + 1000]])
    dis: list[Disagreement] = []
    agree = 0
    for (name, m), rv in zip(items, ref):
        ok, code = ours(m)
        if ok == bool(rv == 1):
            agree += 1
            continue
        if ok:
            kind = "FALSE_ACCEPT"
        elif code == Code.UNSUPPORTED_PROPOSAL.value:
            kind = "PROPOSAL_GAP"
        elif code in (Code.LIMIT_EXCEEDED.value, Code.DEADLINE_EXCEEDED.value):
            kind = "LIMIT_GAP"
        else:
            kind = "FALSE_REJECT"
        dis.append(Disagreement(name, kind, code, rv))
    counts: dict[str, int] = {}
    for d in dis:
        counts[d.kind] = counts.get(d.kind, 0) + 1
    return {"schema": "PK_DIFFERENTIAL_REPORT/1", "reference": "v8/WebAssembly.validate",
            "total": len(items), "agree": agree, "disagreements": counts,
            "critical": counts.get("FALSE_ACCEPT", 0),
            "examples": [d.__dict__ for d in dis[:50]]}
