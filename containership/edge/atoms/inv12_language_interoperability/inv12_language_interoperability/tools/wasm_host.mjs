// MC-019 / MC-011 / MC-012 real-Wasm-guest integration harness.
// Runs a Go-compiled wasip1 guest in Node's WebAssembly engine (V8) and moves
// canonical values across the host/guest boundary through the bounds-checked
// adapter. Prints a JSON report; exit code 0 only if every check passes.
import { readFileSync } from "node:fs";
import { WASI } from "node:wasi";
import { liftFromMemory, lowerIntoGuest } from "../fixtures/js/inv12.mjs";

const wasmPath = process.argv[2];
const T = { k: "record", fields: [["id", { k: "u32" }], ["name", { k: "string" }], ["tags", { k: "list", t: { k: "string" } }]] };
const wasi = new WASI({ version: "preview1", args: [], env: {} });
const { instance } = await WebAssembly.instantiate(readFileSync(wasmPath), wasi.getImportObject());
wasi.initialize(instance);
const x = instance.exports;
const checks = [];
const check = (name, ok, detail) => checks.push({ name, ok: !!ok, detail });

// 1. guest -> host lift from real linear memory
const r1 = liftFromMemory(x.memory, x.produce(), T);
check("lift guest-produced record", r1.ok && r1.ok.id === "42" && r1.ok.name === "guést-\u{1F980}" &&
  JSON.stringify(r1.ok.tags) === '["wasm","go"]', r1);
x.post_return();
check("post_return reset guest arena", x.live_allocs() === 0 && x.post_returns() === 1);

// 2. host -> guest lower via guest cabi_realloc, guest reads it back
const val = { id: "7", name: "hôst", tags: ["a", "\u{1F600}"] };
const low = lowerIntoGuest(x.memory, x.cabi_realloc, val, T);
const expect = 7 * 1000 + new TextEncoder().encode("hôst").length + 1 + 4;
const got = low.root !== undefined ? x.consume(low.root) : -1;
check("lower into guest via cabi_realloc", got === expect, { low, got, expect });
check("allocations accounted", x.live_allocs() === low.allocations, { guest: x.live_allocs(), host: low.allocations });
x.post_return();
check("allocations released exactly once", x.live_allocs() === 0 && x.post_returns() === 2);

// 3. malicious guest pointer is refused by the host adapter
const bad = liftFromMemory(x.memory, x.produce_bad(), T);
check("hostile guest pointer refused", bad.err === "PK_INTEROP_MEMORY_OVERFLOW" || bad.err === "PK_INTEROP_MEMORY_BOUNDS", bad);
x.post_return();

// 4. hostile realloc (returns out-of-range pointer when arena is exhausted) is refused
const huge = { id: "1", name: "x".repeat(70000), tags: [] };
const hr = lowerIntoGuest(x.memory, x.cabi_realloc, huge, T);
check("hostile/exhausted realloc refused", hr.err === "PK_INTEROP_REALLOC", hr);
x.post_return();

// 5. out-of-range root offset refused
const oob = liftFromMemory(x.memory, x.memory.buffer.byteLength - 4, T);
check("root beyond memory refused", oob.err === "PK_INTEROP_MEMORY_BOUNDS", oob);

const ok = checks.every((c) => c.ok);
console.log(JSON.stringify({ engine: `node ${process.version} (V8 WebAssembly)`, guest: "go wasip1/wasm c-shared",
  memory_bytes: x.memory.buffer.byteLength, checks, verdict: ok ? "PASS" : "FAIL" }, null, 1));
process.exit(ok ? 0 : 1);
