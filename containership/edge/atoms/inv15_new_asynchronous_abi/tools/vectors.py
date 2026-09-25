"""Generate (or --check) conformance/vectors.json: known-good and known-bad
encodings for every message type (component 8). Deterministic: fixed tokens."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from inv15_new_asynchronous_abi import handles as H  # noqa: E402
from inv15_new_asynchronous_abi.errors import CancelAck, CancelReason, ErrorCode  # noqa: E402
from inv15_new_asynchronous_abi.wire import codec  # noqa: E402

OUT = ROOT / "conformance" / "vectors.json"


def hx(b):
    return bytes(b).hex()


def build():
    h1 = H.Handle(1, 0, 0, bytes(range(16)))
    h2 = H.Handle(1, 7, 3, bytes(range(16, 32)))
    hmax = H.Handle(H.U32, H.U32, H.U32, b"\xff" * 16)
    good, bad = [], []
    good += [
        {"id": "call.value.empty", "type": "call", "hex": hx(codec.encode_call_result("value", b"")), "decoded": ["value", ""]},
        {"id": "call.value.bytes", "type": "call", "hex": hx(codec.encode_call_result("value", b"\x00\x01ok")), "decoded": ["value", "00016f6b"]},
        {"id": "call.subtask", "type": "call", "hex": hx(codec.encode_call_result("subtask", h2)), "decoded": ["subtask", [1, 7, 3, hx(h2.token)]]},
        {"id": "call.subtask.max", "type": "call", "hex": hx(codec.encode_call_result("subtask", hmax)), "decoded": ["subtask", [H.U32, H.U32, H.U32, "ff" * 16]]},
    ]
    for ec in ErrorCode:
        if ec is ErrorCode.OK:
            continue
        env = {"code": int(ec), "retryable": ec.name in ("NOT_READY", "BUDGET_EXHAUSTED"), "detail": ec.name.lower()}
        good.append({"id": f"call.error.{ec.name}", "type": "call", "hex": hx(codec.encode_call_result("error", env)),
                     "decoded": ["error", [int(ec), env["retryable"], env["detail"]]]})
    good += [
        {"id": "wait.empty", "type": "wait", "hex": hx(codec.encode_wait([])), "decoded": []},
        {"id": "wait.two.canonical", "type": "wait", "hex": hx(codec.encode_wait([h2, h1, h2])), "decoded": [[1, 0, 0, hx(h1.token)], [1, 7, 3, hx(h2.token)]]},
    ]
    for r in CancelReason:
        good.append({"id": f"cancel.{r.name}", "type": "cancel", "hex": hx(codec.encode_cancel(h1, r)), "decoded": [[1, 0, 0, hx(h1.token)], int(r)]})
    for a in CancelAck:
        good.append({"id": f"ack.{a.name}", "type": "ack", "hex": hx(codec.encode_ack(a)), "decoded": int(a)})
    sub = codec.encode_call_result("subtask", h1)
    w2 = codec.encode_wait([h1, h2])
    raw1, raw2 = H.encode(h1), H.encode(h2)
    bad += [
        {"id": "empty", "type": "call", "hex": "", "error": "MALFORMED"},
        {"id": "major2", "type": "call", "hex": "0200" + sub[2:].hex(), "error": "UNSUPPORTED_VERSION"},
        {"id": "unknown.tag", "type": "call", "hex": "010103", "error": "MALFORMED"},
        {"id": "value.truncated", "type": "call", "hex": "01010000000005414243", "error": "MALFORMED"},
        {"id": "value.trailing", "type": "call", "hex": hx(codec.encode_call_result("value", b"a")) + "00", "error": "MALFORMED"},
        {"id": "subtask.truncated", "type": "call", "hex": sub[:-1].hex(), "error": "MALFORMED"},
        {"id": "subtask.trailing", "type": "call", "hex": sub.hex() + "00", "error": "MALFORMED"},
        {"id": "handle.version0", "type": "call", "hex": sub[:3].hex() + "00" + sub[4:].hex(), "error": "UNSUPPORTED_VERSION"},
        {"id": "handle.version2", "type": "call", "hex": sub[:3].hex() + "02" + sub[4:].hex(), "error": "UNSUPPORTED_VERSION"},
        {"id": "handle.feature.bit1", "type": "call", "hex": sub[:4].hex() + "02" + sub[5:].hex(), "error": "UNSUPPORTED_FEATURE"},
        {"id": "handle.advisory.bit4", "type": "call", "hex": sub[:4].hex() + "10" + sub[5:].hex(), "ok_decoded": ["subtask", [1, 0, 0, hx(h1.token)]]},
        {"id": "error.code0", "type": "call", "hex": "0101020000000000", "error": "MALFORMED"},
        {"id": "error.code999", "type": "call", "hex": "01010203e7000000", "error": "MALFORMED"},
        {"id": "error.flags", "type": "call", "hex": "0101020001020000", "error": "MALFORMED"},
        {"id": "error.badutf8", "type": "call", "hex": "01010200010000" + "01ff", "error": "MALFORMED"},
        {"id": "wait.duplicate", "type": "wait", "hex": "01010002" + raw1.hex() + raw1.hex(), "error": "MALFORMED"},
        {"id": "wait.unsorted", "type": "wait", "hex": "01010002" + (raw2.hex() + raw1.hex() if raw2 > raw1 else raw1.hex() + raw2.hex()), "error": "MALFORMED"},
        {"id": "wait.count.overstated", "type": "wait", "hex": "01010003" + w2[4:].hex(), "error": "MALFORMED"},
        {"id": "cancel.reason.unknown", "type": "cancel", "hex": "0101" + raw1.hex() + "c8", "error": "MALFORMED"},
        {"id": "ack.zero", "type": "ack", "hex": "010100", "error": "MALFORMED"},
        {"id": "ack.long", "type": "ack", "hex": "01010101", "error": "MALFORMED"},
    ]
    return {"format": "INV-15-conformance/1", "interface": "pk:async@1.1.0", "good": good, "bad": bad}


def main():
    text = json.dumps(build(), indent=1, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        ok = OUT.exists() and OUT.read_text() == text
        print("VECTORS_REPRODUCIBLE" if ok else "VECTORS_DRIFT")
        return 0 if ok else 1
    OUT.write_text(text)
    d = json.loads(text)
    print(f"wrote {len(d['good'])} good + {len(d['bad'])} bad vectors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
