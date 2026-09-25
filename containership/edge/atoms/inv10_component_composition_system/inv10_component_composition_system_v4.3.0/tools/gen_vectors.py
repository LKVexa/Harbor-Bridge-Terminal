"""MC-41: generate cross-implementation conformance vectors for PK_COMPOSITION_ID/2.

Each vector: input units + externals, and either the expected full result or the expected error code.
Other implementations must reproduce `expected.composition` byte-for-byte from the spec.
"""
import json
import _path  # noqa: F401
from _path import ROOT
from inv10_component_composition_system.composition import Unit, compose, CompositionError

CASES = [
    ("empty", [], []),
    ("single-export", [("a", [], ["i"])], []),
    ("chain", [("store", [], ["wasi:kv/store"]), ("api", ["wasi:kv/store"], ["wasi:http/handler"])], []),
    ("external-used", [("api", ["wasi:http/outgoing"], [])], ["wasi:http/outgoing"]),
    ("external-unused-ignored", [("a", [], ["i"])], ["unused:x/y"]),
    ("diamond", [("d", [], ["x"]), ("b", ["x"], ["y"]), ("c", ["x"], ["z"]), ("a", ["y", "z"], [])], []),
    ("unicode-nfc", [("café", [], ["naïve:ü/ß"]), ("z", ["naïve:ü/ß"], [])], []),
    ("versioned", [("p", [], ["acme:kv/store@1.2.0"]), ("c", ["acme:kv/store@1.2.0"], [])], []),
    ("self-cycle", [("s", ["x"], ["x"])], []),
    ("cycle", [("a", ["i-b"], ["i-a"]), ("b", ["i-a"], ["i-b"])], []),
    ("unsatisfied", [("a", ["missing"], [])], []),
    ("ambiguous", [("a", [], ["i"]), ("b", [], ["i"])], []),
    ("whitespace-id", [(" a", [], [])], []),
]


def build():
    out = []
    for name, units, ext in CASES:
        us = [Unit(n, frozenset(i), frozenset(e)) for n, i, e in units]
        vec = {"name": name, "input": {"units": [{"name": n, "imports": i, "exports": e} for n, i, e in units],
                                        "external": ext}}
        try:
            vec["expected"] = compose(us, external=frozenset(ext))
        except CompositionError as exc:
            vec["expected_error"] = exc.code
        out.append(vec)
    return {"profile": "PK_COMPOSITION_ID/2", "schema": "PK_COMPOSITION/1", "vectors": out}


if __name__ == "__main__":
    p = ROOT / "conformance" / "vectors.json"
    p.write_text(json.dumps(build(), indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {p}")
