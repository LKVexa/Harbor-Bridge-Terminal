'use strict';
/** Terminal words never become shell text. This is the sole UC command grammar. */
const READ = new Set(['status', 'berths', 'capabilities', 'doctor']);
class Refusal extends Error { constructor(message) { super(message); this.code = 'SHIP_REFUSED'; } }
function vetArgv(argv, { control = false } = {}) {
  if (!Array.isArray(argv) || argv.length < 1 || argv.length > 8 || argv.some(x => typeof x !== 'string' || x.length > 128 || /[\x00-\x20\x7f;&|<>`$\\/]/.test(x))) throw new Refusal('invalid ship argument vector');
  const name = x => { if (typeof x !== 'string' || !/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(x)) throw new Refusal('invalid berth name'); return x; };
  const gen = x => { if (!/^[1-9][0-9]{0,14}$/.test(x || '') || !Number.isSafeInteger(Number(x))) throw new Refusal('positive generation required'); return x; };
  const a = [...argv];
  if (READ.has(a[0]) && a.length === 1) return { argv: a, mutation: false };
  if (a[0] === 'lifecycle' && (a.length === 1 || a.length === 2)) { if (a.length === 2) name(a[1]); return { argv: a, mutation: false }; }
  if (a[0] === 'fabric' && a[1] === 'status' && a.length === 3) { name(a[2]); return { argv: a, mutation: false }; }
  if (['workflow', 'vws-workflow', 'tiff-workflow', 'onebit-workflow', 'master-workflow'].includes(a[0]) && a[1] === 'status' && a.length === 2) return { argv: a, mutation: false };
  if (a[0] === 'platform' && ['status','health','hardware','kernel','compatibility','audit-check'].includes(a[1]) && a.length === 2) return { argv: a, mutation: false };
  if (a[0] === 'recover' && a[1] === 'list' && a.length === 2) return { argv: a, mutation: false };
  if (a[0] === 'pixels' && a[1] === 'status' && a.length === 2) return { argv: a, mutation: false };
  if (a[0] === 'onebit' && a[1] === 'status' && a.length === 2) return { argv: a, mutation: false };
  if (a[0] === 'onebit' && a[1] === 'tiff-read' && a.length === 5) {
    name(a[2]);
    if (!['DF_Small','DF_Medium','DF_Large','DF_Xtra_Large','DF_Fabric'].includes(a[3])) throw new Refusal('invalid onebit TIFF slot');
    if (!/^[0-3]$/.test(a[4])) throw new Refusal('invalid onebit TIFF tile');
    return { argv: a, mutation: false };
  }
  if (a[0] === 'pixels' && ['inspect', 'cell'].includes(a[1])) {
    if (a.length !== (a[1] === 'cell' ? 6 : 4)) throw new Refusal('invalid pixel arguments');
    name(a[2]);
    if (!['DF_Small','DF_Medium','DF_Large','DF_Xtra_Large','DF_Fabric'].includes(a[3])) throw new Refusal('invalid pixel slot');
    if (a[1] === 'cell' && (!/^[0-3]$/.test(a[4]) || !/^(?:[0-9]|[1-4][0-9]|5[0-7])$/.test(a[5]))) throw new Refusal('invalid pixel cell');
    return { argv: a, mutation: false };
  }
  if (!control) throw new Refusal('read-only session: launch TERMINAL.cmd --control for allowlisted execution');
  if (a[0] === 'verify' && a.length === 2) { name(a[1]); return { argv: [...a, '--quick'], mutation: true }; }
  if (a[0] === 'verify') throw new Refusal('ship verify requires one berth name; all-berth verification remains a local CLI operation');
  if (a[0] === 'run' && a.length === 5 && a[2] === '--sealed' && a[3] === '--generation') { name(a[1]); gen(a[4]); return { argv: a, mutation: true }; }
  if (a[0] === 'run' && a.length === 6 && a[2] === '--ticks' && a[4] === '--generation' && /^[1-9]$|^10$/.test(a[3])) {
    name(a[1]); gen(a[5]); return { argv: [...a, '--no-view'], mutation: true };
  }
  throw new Refusal('command is not in the ship allowlist; load, unload, arbitrary paths, build, seal and recovery writes remain local CLI operations');
}
module.exports = { vetArgv, Refusal };
