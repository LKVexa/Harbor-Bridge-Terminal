"""Generate the canonical conformance fixtures (C029).

Deterministic: no timestamps, no random ids.  Re-running must produce byte-identical
files; ``tests/contract/test_fixtures.py`` asserts that (drift check).

Layout::

    fixtures/MANIFEST.json            one entry per case: file, digest, stage, expectation
    fixtures/wasm/<case>.wasm         exact input bytes
    fixtures/golden/<case>.proof.json golden PK_SFI_PROOF/1 for VERIFIED cases
    fixtures/golden/<case>.rewritten.wasm  rewriter output (for rewrite-stage cases)
    fixtures/golden/error_envelope.json    example PK_SFI_ERROR/1

A third-party implementation is conformant when, for every case, verifying
``wasm/<case>.wasm`` (stage ``verify``) or rewriting then verifying it (stage
``rewrite+verify``) under ``profile`` yields exactly ``expect`` (``VERIFIED`` with a
byte-identical canonical proof, or the listed error code).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from inv45_sfi_mechanisms.production import builder, config, sfi  # noqa: E402
from inv45_sfi_mechanisms.production.builder import F64, I32, I64, Func, ModuleBuilder  # noqa: E402
from inv45_sfi_mechanisms.production.errors import SfiError  # noqa: E402

PROFILE = config.profile(config.validate(dict(config.DEFAULTS)))
IMPORT_PROFILE = sfi.Profile(region_base=65536, region_log2=16, function_import_allowlist=("env.trace_i32",),
                             require_imported_memory=True)


def _raw(sections: bytes) -> bytes:
    return b"\x00asm\x01\x00\x00\x00" + sections


def cases() -> list[tuple[str, bytes, str, sfi.Profile, str]]:
    """(name, bytes, stage, profile, expect)"""
    out = []
    rw = builder.rw_module(memory_pages=4)
    out.append(("typical_rw_module", rw, "rewrite+verify", PROFILE, "VERIFIED"))
    out.append(("minimum_empty_module", _raw(b""), "verify", PROFILE, "VERIFIED"))
    b = ModuleBuilder(memory=None)
    b.add(Func((I32, I32), (I32,), [(0x20, 0), (0x20, 1), (0x6A, None), (0x0B, None)], export="add"))
    out.append(("no_memory_pure_function", b.build(), "verify", PROFILE, "VERIFIED"))
    # boundary: partition at the top of the 32-bit space (needs 65536 pages -> 4 GiB declared min)
    top = sfi.Profile(region_base=(1 << 32) - (1 << 12) - 8, region_log2=12)
    b = ModuleBuilder(memory=(65536, None))
    b.add(Func((I32,), (I32,), [(0x20, 0), (0x28, (2, 0)), (0x0B, None)], export="load"))
    out.append(("boundary_top_of_address_space", b.build(), "rewrite+verify", top, "VERIFIED"))
    # table + call_indirect: permitted targets reported
    b = ModuleBuilder(memory=None, table=(2, 2), elements=[(0, [0, 1])])
    b.add(Func((), (I32,), [(0x41, 7), (0x0B, None)]))
    b.add(Func((), (I32,), [(0x41, 9), (0x0B, None)]))
    b.add(Func((I32,), (I32,), [(0x20, 0), (0x11, 1), (0x0B, None)], export="dispatch"))
    # type index for [] -> [i32] is 0 (first func), (i32)->(i32) is 1; call_indirect uses type 0
    b.funcs[2].body = [(0x20, 0), (0x11, 0), (0x0B, None)]
    out.append(("table_call_indirect", b.build(), "rewrite+verify", PROFILE, "VERIFIED"))
    # allowlisted host import + imported shared memory
    b = ModuleBuilder(memory=(4, None), import_memory=("env", "memory"),
                      func_imports=[("env", "trace_i32", (I32,), ())])
    b.add(Func((I32,), (), [(0x20, 0), (0x28, (2, 0)), (0x10, 0), (0x0B, None)], export="t"))
    out.append(("allowlisted_import_shared_memory", b.build(), "rewrite+verify", IMPORT_PROFILE, "VERIFIED"))
    b = ModuleBuilder(memory=(4, None))
    b.add(Func((), (I32,), [(0x41, -5), (0x28, (2, 0xFFFFFF)), (0x0B, None)], export="k"))
    out.append(("constant_address_folded", b.build(), "rewrite+verify", PROFILE, "VERIFIED"))
    b = ModuleBuilder(memory=(4, None))
    b.add(Func((), (I32,), [(0x41, 65536 * 2), (0x28, (2, 0)), (0x0B, None)], export="k"))
    out.append(("constant_address_outside_partition", b.build(), "verify", PROFILE, "SFI_UNMASKED_ACCESS"))
    # ---- invalid ------------------------------------------------------------------------
    out.append(("unmasked_access_unrewritten", rw, "verify", PROFILE, "SFI_UNMASKED_ACCESS"))
    good = sfi.rewrite(rw, PROFILE).artifact
    wrong_mask = sfi.rewrite(rw, sfi.Profile(region_base=65536, region_log2=17)).artifact
    out.append(("mask_constant_for_other_profile", wrong_mask, "verify", PROFILE, "SFI_UNMASKED_ACCESS"))
    b = ModuleBuilder(memory=(4, None))
    b.add(Func((I32,), (I32,), [(0x20, 0), (0x41, 65535), (0x71, None), (0x41, 65536), (0x6A, None),
                                (0x28, (2, 4)), (0x0B, None)], export="load"))
    out.append(("masked_but_nonzero_offset", b.build(), "verify", PROFILE, "SFI_UNMASKED_ACCESS"))
    out.append(("bad_magic", b"\x00asn\x01\x00\x00\x00", "verify", PROFILE, "SFI_MALFORMED_ARTIFACT"))
    out.append(("unsupported_binary_version", b"\x00asm\x02\x00\x00\x00", "verify", PROFILE, "SFI_UNSUPPORTED_VERSION"))
    out.append(("truncated_module", good[:-3], "verify", PROFILE, "SFI_MALFORMED_ARTIFACT"))
    b = ModuleBuilder(memory=(4, None))
    b.add(Func((I32,), (I32,), [(0x20, 0), (0x0B, None)], export="f"))
    simd = bytearray(b.build())
    simd[-2:-1] = b"\xfd"  # replace local.get immediate area -> 0xFD prefix inside body
    out.append(("simd_prefix_opcode", bytes(simd), "verify", PROFILE, "SFI_MALFORMED_ARTIFACT"))
    out.append(("shared_memory_threads", _raw(b"\x05\x04\x01\x03\x04\x04"), "verify", PROFILE,
                "SFI_UNSUPPORTED_FEATURE"))
    b = ModuleBuilder(memory=(4, None))
    b.add(Func((I32,), (I32,), [(0x20, 0), (0x40, None), (0x0B, None)], export="grow"))
    out.append(("memory_grow_forbidden", b.build(), "verify", PROFILE, "SFI_POLICY_REJECTED"))
    b = ModuleBuilder(memory=(4, None), data=[(0, b"escape")])
    out.append(("data_segment_outside_partition", b.build(), "verify", PROFILE, "SFI_POLICY_REJECTED"))
    b = ModuleBuilder(memory=(1, None))
    out.append(("memory_smaller_than_partition", b.build(), "verify", PROFILE, "SFI_POLICY_REJECTED"))
    b = ModuleBuilder(memory=(4, None), func_imports=[("wasi_snapshot_preview1", "fd_write", (I32,), (I32,))])
    out.append(("import_not_allowlisted", b.build(), "verify", PROFILE, "SFI_POLICY_REJECTED"))
    b = ModuleBuilder(memory=(4, None), export_memory="memory")
    out.append(("memory_export_forbidden", b.build(), "verify", PROFILE, "SFI_POLICY_REJECTED"))
    b = ModuleBuilder(memory=None, table=(1, None), elements=[(0, [0])])
    b.add(Func((), (), [(0x0B, None)]))
    out.append(("growable_table", b.build(), "verify", PROFILE, "SFI_POLICY_REJECTED"))
    b = ModuleBuilder(memory=(4, None))
    b.add(Func((I32,), (I64,), [(0x20, 0), (0x0B, None)], export="bad"))
    out.append(("type_mismatch", b.build(), "verify", PROFILE, "SFI_INVALID_MODULE"))
    out.append(("unknown_section_id", _raw(b"\x0d\x00"), "verify", PROFILE, "SFI_MALFORMED_ARTIFACT"))
    out.append(("section_out_of_order", _raw(b"\x03\x01\x00\x01\x01\x00"), "verify", PROFILE,
                "SFI_MALFORMED_ARTIFACT"))
    b = ModuleBuilder(memory=(4, None))
    b.add(Func((I32, F64), (), [(0x20, 0), (0x41, 65535), (0x71, None), (0x41, 65536), (0x6A, None),
                                (0x20, 0), (0x39, (3, 0)), (0x0B, None)], export="s"))
    out.append(("store_value_local_wrong_type", b.build(), "verify", PROFILE, "SFI_INVALID_MODULE"))
    return out


def main() -> int:
    fx = ROOT / "fixtures"
    (fx / "wasm").mkdir(parents=True, exist_ok=True)
    (fx / "golden").mkdir(parents=True, exist_ok=True)
    manifest = {"schema": "PK_SFI_FIXTURES/1", "profile_id": sfi.PROFILE_ID, "cases": []}
    for name, data, stage, prof, expect in cases():
        (fx / "wasm" / f"{name}.wasm").write_bytes(data)
        entry = {"name": name, "file": f"wasm/{name}.wasm", "input_sha256": sfi.sha256_hex(data), "stage": stage,
                 "profile": prof.as_dict(), "expect": expect}
        try:
            target = data
            if stage == "rewrite+verify":
                res = sfi.rewrite(data, prof)
                target = res.artifact
                (fx / "golden" / f"{name}.rewritten.wasm").write_bytes(target)
                entry["rewritten_sha256"] = res.output_sha256
            proof = sfi.verify(target, prof)
            observed = "VERIFIED"
            (fx / "golden" / f"{name}.proof.json").write_text(json.dumps(proof, indent=1, sort_keys=True) + "\n")
            entry["proof_sha256"] = sfi.proof_digest(proof)
        except SfiError as e:
            observed = e.code
        if observed != expect:
            print(f"FIXTURE EXPECTATION MISMATCH {name}: expected {expect} observed {observed}")
            return 1
        manifest["cases"].append(entry)
    env = SfiError("SFI_UNMASKED_ACCESS", "2 memory access(es) not confined", unmasked_count=2,
                   sample_offsets=[41, 57]).as_dict()
    (fx / "golden" / "error_envelope.json").write_text(json.dumps(env, indent=1, sort_keys=True) + "\n")
    (fx / "MANIFEST.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"{len(manifest['cases'])} fixtures written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
