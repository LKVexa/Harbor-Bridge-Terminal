// MC-022 JavaScript binding adapter and fixture component (Node >= 18, no deps).
//
// 64-bit integers are handled with BigInt end to end (never Number), strings
// are validated with a fatal TextDecoder, and f32/f64 travel as bit patterns.
//   node inv12.mjs encode <vectors.json>
//   node inv12.mjs decode <vectors.json> <images.json>
import { readFileSync } from "node:fs";

class AbiError extends Error { constructor(code) { super(code); this.code = code; } }
const fail = (c) => { throw new AbiError(c); };
const U32MAX = 0xffffffffn;
const PRIM = { bool: [1, 1], s8: [1, 1], u8: [1, 1], s16: [2, 2], u16: [2, 2], s32: [4, 4], u32: [4, 4],
  s64: [8, 8], u64: [8, 8], f32: [4, 4], f64: [8, 8], char: [4, 4], string: [8, 4] };
const discSize = (n) => (n <= 256 ? 1 : n <= 65536 ? 2 : 4);
const flagsSize = (n) => (n === 0 ? 0 : n <= 8 ? 1 : n <= 16 ? 2 : 4 * Math.ceil(n / 32));
const utf8 = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true });
const enc = new TextEncoder();

function alignUp(p, a) {
  const r = Math.floor((p + a - 1) / a) * a; // p, a are safe Numbers (< 2**53)
  if (BigInt(r) > U32MAX) fail("PK_INTEROP_MEMORY_OVERFLOW");
  return r;
}
function cases(t) {
  switch (t.k) {
    case "variant": return [t.cases.map((c) => c[0]), t.cases.map((c) => c[1])];
    case "enum": return [t.cases, t.cases.map(() => null)];
    case "option": return [["none", "some"], [null, t.t]];
    case "result": return [["ok", "error"], [t.ok, t.err]];
  }
  return null;
}
function fields(t) {
  if (t.k === "tuple") return [t.ts.map((_, i) => String(i)), t.ts];
  return [t.fields.map((f) => f[0]), t.fields.map((f) => f[1])];
}
function align(t) {
  if (PRIM[t.k]) return PRIM[t.k][1];
  switch (t.k) {
    case "list": case "own": case "borrow": case "future": case "stream": return 4;
    case "record": case "tuple": return Math.max(1, ...fields(t)[1].map(align));
    case "flags": { const n = t.names.length; return n <= 8 ? 1 : n <= 16 ? 2 : 4; }
  }
  const [ns, ps] = cases(t);
  return Math.max(discSize(ns.length), ...ps.filter(Boolean).map(align));
}
const maxCaseAlign = (ps) => Math.max(1, ...ps.filter(Boolean).map(align));
function size(t) {
  if (PRIM[t.k]) return PRIM[t.k][0];
  switch (t.k) {
    case "list": return 8;
    case "own": case "borrow": case "future": case "stream": return 4;
    case "record": case "tuple": {
      let s = 0;
      for (const f of fields(t)[1]) s = alignUp(s, align(f)) + size(f);
      return alignUp(s, align(t));
    }
    case "flags": return flagsSize(t.names.length);
  }
  const [ns, ps] = cases(t);
  const s = alignUp(discSize(ns.length), maxCaseAlign(ps));
  return alignUp(s + Math.max(0, ...ps.filter(Boolean).map(size)), align(t));
}

class Mem {
  constructor(bytes) { this.b = bytes || new Uint8Array(0); this.pos = 0; }
  alloc(a, n) {
    const p = alignUp(this.pos, a);
    if (BigInt(p) + BigInt(n) > U32MAX) fail("PK_INTEROP_MEMORY_OVERFLOW");
    this.pos = p + n;
    if (this.b.length < this.pos) { const nb = new Uint8Array(this.pos); nb.set(this.b); this.b = nb; }
    return p;
  }
  check(p, n, a) {
    const P = BigInt(p), N = BigInt(n);
    if (P > U32MAX || N > U32MAX || P + N > U32MAX) fail("PK_INTEROP_MEMORY_OVERFLOW");
    if (P + N > BigInt(this.b.length)) fail("PK_INTEROP_MEMORY_BOUNDS");
    if (a > 1 && p % a !== 0) fail("PK_INTEROP_MEMORY_ALIGNMENT");
  }
  ld(p, n) {
    this.check(p, n, n);
    let v = 0n;
    for (let i = n - 1; i >= 0; i--) v = (v << 8n) | BigInt(this.b[p + i]);
    return v;
  }
  st(p, n, v) {
    this.check(p, n, n);
    for (let i = 0; i < n; i++) { this.b[p + i] = Number(v & 0xffn); v >>= 8n; }
  }
}

function parseInt_(k, s) {
  const w = BigInt(PRIM[k][0] * 8);
  if (!/^-?[0-9]+$/.test(s)) fail("PK_INTEROP_TYPE_MISMATCH");
  const v = BigInt(s);
  const [lo, hi] = k[0] === "s" ? [-(1n << (w - 1n)), (1n << (w - 1n)) - 1n] : [0n, (1n << w) - 1n];
  if (v < lo || v > hi) fail("PK_INTEROP_OUT_OF_RANGE");
  return BigInt.asUintN(Number(w), v);
}

function store(m, v, t, p) {
  const k = t.k;
  switch (k) {
    case "bool": return m.st(p, 1, v ? 1n : 0n);
    case "s8": case "u8": case "s16": case "u16": case "s32": case "u32": case "s64": case "u64":
      return m.st(p, PRIM[k][0], parseInt_(k, v));
    case "f32": case "f64": return m.st(p, PRIM[k][0], BigInt(v));
    case "char": {
      const c = BigInt(v);
      if ((c >= 0xd800n && c <= 0xdfffn) || c > 0x10ffffn) fail("PK_INTEROP_ENCODING");
      return m.st(p, 4, c);
    }
    case "string": {
      if (!v.isWellFormed()) fail("PK_INTEROP_ENCODING"); // lone UTF-16 surrogates refused
      const bytes = enc.encode(v);
      const q = m.alloc(1, bytes.length);
      m.b.set(bytes, q);
      m.st(p, 4, BigInt(q)); m.st(p + 4, 4, BigInt(bytes.length));
      return;
    }
    case "list": {
      const es = size(t.t);
      const q = m.alloc(align(t.t), v.length * es);
      v.forEach((x, i) => store(m, x, t.t, q + i * es));
      m.st(p, 4, BigInt(q)); m.st(p + 4, 4, BigInt(v.length));
      return;
    }
    case "record": case "tuple": {
      const [ns, ts] = fields(t);
      let off = 0;
      ns.forEach((n, i) => {
        off = alignUp(off, align(ts[i]));
        store(m, k === "tuple" ? v[i] : v[n], ts[i], p + off);
        off += size(ts[i]);
      });
      return;
    }
    case "flags": {
      const set = new Set(v);
      let bits = 0n;
      t.names.forEach((n, i) => { if (set.has(n)) bits |= 1n << BigInt(i); });
      const sz = flagsSize(t.names.length);
      if (sz === 1 || sz === 2) return m.st(p, sz, bits);
      for (let w = 0; w < sz / 4; w++) m.st(p + 4 * w, 4, (bits >> BigInt(32 * w)) & 0xffffffffn);
      return;
    }
    case "own": case "borrow": case "future": case "stream": {
      const h = BigInt(v);
      if (h === 0n || h > U32MAX) fail("PK_INTEROP_HANDLE");
      return m.st(p, 4, h);
    }
  }
  const [ns, ps] = cases(t);
  let cname, payload;
  if (k === "enum") cname = v;
  else if (k === "option") [cname, payload] = v === null ? ["none", null] : ["some", v.some];
  else if (k === "result") [cname, payload] = "ok" in v ? ["ok", v.ok] : ["error", v.error];
  else [cname, payload] = [v.case, v.value];
  const idx = ns.indexOf(cname);
  if (idx < 0) fail("PK_INTEROP_INVALID_DISCRIMINANT");
  m.st(p, discSize(ns.length), BigInt(idx));
  if (ps[idx]) store(m, payload, ps[idx], p + alignUp(discSize(ns.length), maxCaseAlign(ps)));
}

const hex = (b, w) => "0x" + b.toString(16).padStart(w, "0");

function load(m, p, t) {
  const k = t.k;
  switch (k) {
    case "bool": return m.ld(p, 1) !== 0n;
    case "u8": case "u16": case "u32": case "u64": return m.ld(p, PRIM[k][0]).toString();
    case "s8": case "s16": case "s32": case "s64": {
      const w = PRIM[k][0] * 8;
      return BigInt.asIntN(w, m.ld(p, PRIM[k][0])).toString();
    }
    case "f32": {
      let b = m.ld(p, 4);
      if (((b >> 23n) & 0xffn) === 0xffn && (b & 0x7fffffn) !== 0n) b = 0x7fc00000n;
      return hex(b, 8);
    }
    case "f64": {
      let b = m.ld(p, 8);
      if (((b >> 52n) & 0x7ffn) === 0x7ffn && (b & 0xfffffffffffffn) !== 0n) b = 0x7ff8000000000000n;
      return hex(b, 16);
    }
    case "char": {
      const c = m.ld(p, 4);
      if ((c >= 0xd800n && c <= 0xdfffn) || c > 0x10ffffn) fail("PK_INTEROP_ENCODING");
      return c.toString();
    }
    case "string": {
      const q = Number(m.ld(p, 4)), n = Number(m.ld(p + 4, 4));
      m.check(q, n, 1);
      try { return utf8.decode(m.b.subarray(q, q + n)); } catch { fail("PK_INTEROP_ENCODING"); }
    }
    case "list": {
      const q = Number(m.ld(p, 4)), n = Number(m.ld(p + 4, 4));
      const es = size(t.t);
      if (BigInt(n) * BigInt(es) > U32MAX) fail("PK_INTEROP_MEMORY_OVERFLOW");
      m.check(q, n * es, align(t.t));
      if (es === 0 && n > 1000000) fail("PK_INTEROP_LIMIT");
      const out = [];
      for (let i = 0; i < n; i++) out.push(load(m, q + i * es, t.t));
      return out;
    }
    case "record": case "tuple": {
      const [ns, ts] = fields(t);
      let off = 0;
      const rec = {}, arr = [];
      ns.forEach((n, i) => {
        off = alignUp(off, align(ts[i]));
        const x = load(m, p + off, ts[i]);
        rec[n] = x; arr.push(x);
        off += size(ts[i]);
      });
      return k === "tuple" ? arr : rec;
    }
    case "flags": {
      const n = t.names.length, sz = flagsSize(n);
      if (sz === 0) return [];
      let bits = 0n;
      if (sz === 1 || sz === 2) bits = m.ld(p, sz);
      else for (let w = 0; w < sz / 4; w++) bits |= m.ld(p + 4 * w, 4) << BigInt(32 * w);
      if (bits >> BigInt(n)) fail("PK_INTEROP_INVALID_FLAGS");
      return t.names.filter((_, i) => (bits >> BigInt(i)) & 1n);
    }
    case "own": case "borrow": case "future": case "stream": {
      const h = m.ld(p, 4);
      if (h === 0n) fail("PK_INTEROP_HANDLE");
      return h.toString();
    }
  }
  const [ns, ps] = cases(t);
  const idx = Number(m.ld(p, discSize(ns.length)));
  if (idx >= ns.length) fail("PK_INTEROP_INVALID_DISCRIMINANT");
  const payload = ps[idx] ? load(m, p + alignUp(discSize(ns.length), maxCaseAlign(ps)), ps[idx]) : null;
  const c = ns[idx];
  if (k === "enum") return c;
  if (k === "option") return c === "none" ? null : { some: payload };
  if (k === "result") return { [c]: payload };
  return ps[idx] ? { case: c, value: payload } : { case: c };
}

function guard(fn) {
  try { return fn(); } catch (e) {
    if (e instanceof AbiError) return { err: e.code };
    return { err: "PANIC:" + e.message };
  }
}

export function encodeValue(v, t) {
  return guard(() => {
    const m = new Mem();
    const root = m.alloc(align(t), size(t));
    store(m, v, t, root);
    return { image: Buffer.from(m.b).toString("hex"), root };
  });
}
export function decodeImage(imgHex, root, t) {
  return guard(() => ({ ok: load(new Mem(new Uint8Array(Buffer.from(imgHex, "hex"))), root, t) }));
}

// ---- real-guest adapter (MC-011/MC-019): operate directly on WebAssembly.Memory
class GuestMem extends Mem {
  constructor(memory, realloc) { super(new Uint8Array(memory.buffer)); this.memory = memory; this.realloc = realloc; this.live = []; }
  alloc(a, n) {
    const p = this.realloc(0, 0, a, n) >>> 0;
    this.b = new Uint8Array(this.memory.buffer); // buffer may be replaced on memory.grow
    if (p % a !== 0) fail("PK_INTEROP_REALLOC");
    try { this.check(p, n, 1); } catch { fail("PK_INTEROP_REALLOC"); }
    for (const [q, m] of this.live) if (n && m && p < q + m && q < p + n) fail("PK_INTEROP_REALLOC");
    this.live.push([p, n]);
    return p;
  }
}
export function liftFromMemory(memory, root, t) {
  return guard(() => ({ ok: load(new Mem(new Uint8Array(memory.buffer).slice()), root >>> 0, t) }));
}
export function lowerIntoGuest(memory, realloc, v, t) {
  return guard(() => {
    const m = new GuestMem(memory, realloc);
    const root = m.alloc(align(t), size(t));
    store(m, v, t, root);
    return { root, allocations: m.live.length };
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const [mode, vpath, ipath] = process.argv.slice(2);
  const vec = JSON.parse(readFileSync(vpath, "utf8"));
  const out = {};
  if (mode === "encode") {
    for (const v of vec.valid) out[v.id] = encodeValue(v.value, v.descriptor);
  } else if (mode === "decode") {
    const imgs = JSON.parse(readFileSync(ipath, "utf8"));
    for (const v of [...vec.valid, ...vec.invalid]) {
      const src = imgs[v.id];
      if (!src) continue;
      out[v.id] = src.err ? { err: "PRODUCER_FAILED" } : decodeImage(src.image, src.root, v.descriptor);
    }
  } else { console.error("usage"); process.exit(2); }
  process.stdout.write(JSON.stringify(out) + "\n");
}
