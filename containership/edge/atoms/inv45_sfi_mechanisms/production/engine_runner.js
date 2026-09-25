// INV-45 trusted execution runner for the node-v8 engine adapter.
// Runs under the Node permission model (no fs writes, no child processes, no workers),
// with an empty environment. Reads one JSON job on stdin, writes one JSON result on stdout.
// Only allowlisted host functions exist; everything else is absent (deny by default).
'use strict';
const crypto = require('crypto');

const HOST = {
  // hostcall allowlist: "module.name" -> factory(ctx) returning the JS function
  'env.trace_i32': (ctx) => (v) => { if (ctx.trace.length < 1024) ctx.trace.push(v | 0); },
};

function toArg(a) {
  if (a.t === 'i64') return BigInt(a.v);
  return Number(a.v);
}
function fromResult(v) {
  if (typeof v === 'bigint') return { t: 'i64', v: v.toString() };
  if (v === undefined) return null;
  return { t: 'num', v: Number.isNaN(v) ? 'NaN' : v };
}

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => { input += d; if (input.length > 64 * 1024 * 1024) process.exit(3); });
process.stdin.on('end', () => {
  const job = JSON.parse(input);
  const out = { schema: 'PK_SFI_ENGINE_RESULT/1', engine: 'node-v8', node: process.version, calls: [], regions: [] };
  const memory = job.memory_pages ? new WebAssembly.Memory({ initial: job.memory_pages }) : null;
  if (memory && job.canary) new Uint8Array(memory.buffer).fill(job.canary);
  const instances = {};
  const ctx = { trace: [] };
  for (const m of job.modules) {
    const mod = new WebAssembly.Module(Buffer.from(m.b64, 'base64'));
    const imports = {};
    for (const imp of WebAssembly.Module.imports(mod)) {
      const key = imp.module + '.' + imp.name;
      imports[imp.module] = imports[imp.module] || {};
      if (imp.kind === 'memory' && key === 'env.memory' && memory) imports.env.memory = memory;
      else if (imp.kind === 'function' && HOST[key] && (m.allow || []).includes(key)) imports[imp.module][imp.name] = HOST[key](ctx);
      else { out.error = 'import not provided: ' + key; process.stdout.write(JSON.stringify(out)); return; }
    }
    instances[m.name] = new WebAssembly.Instance(mod, imports);
  }
  for (const c of job.calls) {
    const inst = instances[c.module];
    const fn = inst && inst.exports[c.export];
    if (typeof fn !== 'function') { out.calls.push({ ok: false, trap: 'no such export' }); continue; }
    const t0 = process.hrtime.bigint();
    try {
      const r = fn(...(c.args || []).map(toArg));
      out.calls.push({ ok: true, result: fromResult(r), ns: Number(process.hrtime.bigint() - t0) });
    } catch (e) {
      out.calls.push({ ok: false, trap: String(e && e.message || e).slice(0, 200), ns: Number(process.hrtime.bigint() - t0) });
    }
  }
  if (memory) {
    const u8 = new Uint8Array(memory.buffer);
    for (const [a, b] of (job.regions || [])) {
      const slice = u8.subarray(a, b);
      let untouched = true;
      if (job.canary !== undefined) for (let i = 0; i < slice.length; i++) if (slice[i] !== job.canary) { untouched = false; break; }
      out.regions.push({ start: a, end: b, sha256: crypto.createHash('sha256').update(slice).digest('hex'), untouched });
    }
  }
  out.trace = ctx.trace;
  process.stdout.write(JSON.stringify(out));
});
