// Standalone, non-Python fixture validator (M23). Usage: node fixtures/validate.mjs
// Implements the same JSON-Schema subset as fabric/wire.py and also executes the
// add.wasm fixture through the engine. Exit 0 only if every expectation holds.
import fs from 'node:fs'; import path from 'node:path'; import crypto from 'node:crypto'; import url from 'node:url';
const here = path.dirname(url.fileURLToPath(import.meta.url));
const schemas = path.join(here, '..', 'schemas');
const T = {object: v => v && typeof v === 'object' && !Array.isArray(v), array: Array.isArray, string: v => typeof v === 'string',
  integer: v => Number.isInteger(v), number: v => typeof v === 'number', boolean: v => typeof v === 'boolean'};
function validate(inst, s, p = '$') {
  const e = [];
  if (s.type && !T[s.type](inst)) return [`${p}: expected ${s.type}`];
  if (s.enum && !s.enum.some(x => JSON.stringify(x) === JSON.stringify(inst))) e.push(`${p}: not in enum`);
  if (typeof inst === 'string') {
    if (s.pattern && !new RegExp(s.pattern, 'u').test(inst)) e.push(`${p}: pattern`);
    if (inst.length < (s.minLength ?? 0)) e.push(`${p}: short`);
    if (s.maxLength !== undefined && inst.length > s.maxLength) e.push(`${p}: long`);
  }
  if (typeof inst === 'number') {
    if (s.minimum !== undefined && inst < s.minimum) e.push(`${p}: min`);
    if (s.maximum !== undefined && inst > s.maximum) e.push(`${p}: max`);
  }
  if (Array.isArray(inst)) {
    if (inst.length < (s.minItems ?? 0)) e.push(`${p}: few`);
    if (s.maxItems !== undefined && inst.length > s.maxItems) e.push(`${p}: many`);
    if (s.items) inst.forEach((v, i) => e.push(...validate(v, s.items, `${p}[${i}]`)));
  }
  if (T.object(inst)) {
    for (const r of s.required ?? []) if (!(r in inst)) e.push(`${p}: missing ${r}`);
    const props = s.properties ?? {};
    for (const [k, v] of Object.entries(inst)) {
      if (k in props) e.push(...validate(v, props[k], `${p}.${k}`));
      else if (s.additionalProperties === false) e.push(`${p}: unknown ${k}`);
    }
  }
  return e;
}
const index = JSON.parse(fs.readFileSync(path.join(here, 'INDEX.json')));
let bad = 0, n = 0;
for (const [name, sha] of Object.entries(index.files)) {
  const buf = fs.readFileSync(path.join(here, name));
  if (crypto.createHash('sha256').update(buf).digest('hex') !== sha) { console.log('HASH MISMATCH', name); bad++; continue; }
  if (!name.endsWith('.json')) continue;
  const fx = JSON.parse(buf); n++;
  const sch = JSON.parse(fs.readFileSync(path.join(schemas, fx.schema + '.schema.json')));
  const ok = validate(fx.instance, sch).length === 0;
  if (ok !== fx.expect_valid) { console.log('MISMATCH', name); bad++; }
}
const wasm = fs.readFileSync(path.join(here, 'add.wasm'));
const inst = await WebAssembly.instantiate(wasm, {});
if (inst.instance.exports.run(20, 22) !== 42) { console.log('WASM MISMATCH'); bad++; }
console.log(JSON.stringify({consumer: 'node ' + process.version, fixtures: n, wasm: 'add.wasm run(20,22)=42', failures: bad}));
process.exit(bad ? 1 : 0);
