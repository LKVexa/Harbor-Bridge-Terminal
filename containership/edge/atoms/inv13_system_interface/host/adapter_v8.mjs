// MC-002 -- INV-13 runtime adapter for the V8 WebAssembly engine (Node >= 18).
// Reads one JSON request on stdin: {module_b64, grant:{capabilities:[...], clock_resolution_ns,
// stdout_limit, random_limit}, entry, fuel_ms}. Policy is decided in Python; this file only
// (1) re-checks the engine's own view of the imports against the grant and (2) binds
// exactly the granted host functions. Nothing ambient is registered.
import { webcrypto } from 'node:crypto';
import { hrtime } from 'node:process';

const MAP = {
  'inv13:clocks@4.3.0': { 'monotonic-now': 'monotonic-clock', 'wall-now': 'wall-clock' },
  'inv13:random@4.3.0': { 'get-random-bytes': 'random' },
  'inv13:stdio@4.3.0': { 'stdout-write': 'stdio', 'stderr-write': 'stdio' },
};
const chunks = [];
for await (const c of process.stdin) chunks.push(c);
const req = JSON.parse(Buffer.concat(chunks).toString('utf8'));
const out = { ok: false, stdout: '', error: null, engine: `v8 ${process.versions.v8}`, imports: [] };
try {
  const bytes = Buffer.from(req.module_b64, 'base64');
  if (!WebAssembly.validate(bytes)) throw { code: 'E2008', msg: 'engine validation failed' };
  const mod = new WebAssembly.Module(bytes);
  const granted = new Set(req.grant.capabilities);
  const imports = WebAssembly.Module.imports(mod);
  out.imports = imports.map(i => [i.module, i.name, i.kind]);
  for (const i of imports) {
    const cap = (MAP[i.module] || {})[i.name];
    if (!cap || i.kind !== 'function' || !granted.has(cap)) throw { code: 'E1001', msg: `import ${i.module}.${i.name} not granted` };
  }
  let memory = null; let stdout = Buffer.alloc(0); let randBudget = req.grant.random_limit ?? 65536;
  const res = BigInt(req.grant.clock_resolution_ns ?? 1000000);
  const mem = () => new Uint8Array(memory.buffer);
  const table = {
    'inv13:clocks@4.3.0': {
      'monotonic-now': () => (hrtime.bigint() / res) * res,
      'wall-now': () => (BigInt(Date.now()) * 1000000n / res) * res,
    },
    'inv13:random@4.3.0': {
      'get-random-bytes': (ptr, len) => {
        if (len < 0 || len > randBudget || ptr < 0 || ptr + len > memory.buffer.byteLength) return -1;
        randBudget -= len; webcrypto.getRandomValues(mem().subarray(ptr, ptr + len)); return len;
      },
    },
    'inv13:stdio@4.3.0': {
      'stdout-write': (ptr, len) => {
        if (len < 0 || ptr < 0 || ptr + len > memory.buffer.byteLength) return -1;
        const room = (req.grant.stdout_limit ?? 65536) - stdout.length; if (room <= 0) return -2;
        const n = Math.min(room, len); stdout = Buffer.concat([stdout, Buffer.from(mem().subarray(ptr, ptr + n))]); return n;
      },
      'stderr-write': (ptr, len) => len,
    },
  };
  const importObject = {};
  for (const i of imports) { (importObject[i.module] ??= {})[i.name] = table[i.module][i.name]; }
  const inst = new WebAssembly.Instance(mod, importObject);
  memory = inst.exports.memory;
  if (!(memory instanceof WebAssembly.Memory)) throw { code: 'E2008', msg: 'module must export memory' };
  const entry = inst.exports[req.entry || 'run'];
  if (typeof entry !== 'function') throw { code: 'E6001', msg: 'entry not exported' };
  out.result = String(entry());
  out.stdout = stdout.toString('base64');
  out.ok = true;
} catch (e) {
  if (e && e.code && e.msg) out.error = { code: e.code, message: e.msg };
  else if (e instanceof WebAssembly.RuntimeError) out.error = { code: 'E9001', message: 'guest trap' };
  else out.error = { code: 'E9001', message: 'internal error' };  // no host detail crosses
}
process.stdout.write(JSON.stringify(out));
