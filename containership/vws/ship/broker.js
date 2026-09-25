'use strict';
/** Gateway-owned UC processes; session workers NEVER receive a root or interpreter. */
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { vetArgv, Refusal } = require('./policy');
function childEnv(source = process.env) {
  const env = {};
  for (const k of ['PATH','SystemRoot','SYSTEMROOT','PATHEXT','COMSPEC','LANG','LC_ALL','TEMP','TMP','TMPDIR']) if (source[k] !== undefined) env[k] = source[k];
  Object.assign(env, { PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', PYTHONDONTWRITEBYTECODE: '1', UC_VWS_CHILD: '1' });
  return env;
}
function realFile(p) { return typeof p === 'string' && path.isAbsolute(p) && fs.statSync(p).isFile(); }
class ShipBroker {
  constructor(cfg, log) {
    this.cfg = cfg; this.log = log; this.jobs = new Map(); this.closed = false;
    this.stats = { started: 0, completed: 0, refused: 0, cancelled: 0, timeouts: 0, outputLimits: 0 };
    this.root = fs.realpathSync(cfg.shipRoot);
    if (!realFile(cfg.python) || !realFile(path.join(this.root, 'uc.py'))) throw new Refusal('ship root and absolute Python executable are required');
  }
  run(owner, id, argv, { control = false } = {}) {
    if (this.closed || this.jobs.size >= 1) { this.stats.refused++; throw new Refusal('ship is busy or draining; command was not started'); }
    if (!/^[a-f0-9]{24}$/.test(id)) throw new Refusal('invalid operation ID');
    const spec = vetArgv(argv, { control: this.cfg.shipControl && control });
    const key = owner + ':' + id; const cfg = this.cfg;
    // Fixed-capacity buffers, bounded combined output. No terminal data file is created here.
    const stdout = Buffer.alloc(cfg.shipOutputBytes), stderr = Buffer.alloc(cfg.shipOutputBytes);
    let outN = 0, errN = 0, total = 0, outcome = 'COMPLETED', reason = '', settled = false, timer;
    let child;
    try { child = spawn(cfg.python, ['-I', '-X', 'utf8', '-B', path.join(this.root, 'uc.py'), ...spec.argv], {
      cwd: this.root, env: childEnv(), shell: false, windowsHide: true, detached: process.platform !== 'win32', stdio: ['ignore', 'pipe', 'pipe']
    }); } catch (e) { throw new Refusal('Python could not be started: ' + e.code); }
    const kill = () => {
      if (!child.pid) return;
      if (process.platform !== 'win32') { try { process.kill(-child.pid, 'SIGKILL'); } catch (e) { if (e.code !== 'ESRCH') this.log.warn('ship.kill_failed', { code: e.code }); } }
      else {
        // Best-effort Windows tree cleanup; native Job Object containment is not claimed.
        const exe = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'taskkill.exe');
        const k = spawn(exe, ['/PID', String(child.pid), '/T', '/F'], { shell: false, windowsHide: true, stdio: 'ignore' });
        k.once('error', () => { try { child.kill(); } catch {} });
        const t = setTimeout(() => { try { child.kill(); k.kill(); } catch {} }, 1500); t.unref(); k.once('close', () => clearTimeout(t));
      }
    };
    const cancel = (why = 'CANCELLED') => { if (settled || outcome !== 'COMPLETED') return; outcome = why; reason = why === 'DEADLINE' ? 'deadline exceeded' : why === 'OUTPUT_LIMIT' ? 'combined output exceeded the configured cap' : 'command cancelled; inspect lifecycle before retrying a mutation'; kill(); };
    this.jobs.set(key, { owner, id, cancel, pid: child.pid, mutation: spec.mutation }); this.stats.started++;
    const promise = new Promise(resolve => {
      const done = (code) => {
        if (settled) return; settled = true; clearTimeout(timer); this.jobs.delete(key);
        if (outcome === 'COMPLETED') this.stats.completed++; else if (outcome === 'DEADLINE') this.stats.timeouts++; else if (outcome === 'OUTPUT_LIMIT') this.stats.outputLimits++; else this.stats.cancelled++;
        this.log.info('ship.finished', { id, owner, operation: spec.argv[0], code, outcome, bytes: total });
        resolve({ code: Number.isInteger(code) && code >= 0 && code <= 255 ? code : 70, outcome, reason, stdout: stdout.subarray(0, outN), stderr: stderr.subarray(0, errN), mutation: spec.mutation });
      };
      const take = (which, b) => {
        const room = Math.max(0, cfg.shipOutputBytes - total), n = Math.min(room, b.length);
        if (which === 'out') { b.copy(stdout, outN, 0, n); outN += n; } else { b.copy(stderr, errN, 0, n); errN += n; }
        total += n; if (n < b.length) cancel('OUTPUT_LIMIT');
      };
      child.stdout.on('data', b => take('out', b)); child.stderr.on('data', b => take('err', b));
      child.once('error', e => { outcome = 'REFUSED'; reason = 'Python spawn failed: ' + e.code; done(69); });
      // Kill any group member holding stdout after the direct process exits, then await close.
      child.once('exit', () => { if (process.platform !== 'win32') kill(); });
      child.once('close', code => done(outcome === 'DEADLINE' ? 124 : outcome === 'OUTPUT_LIMIT' ? 125 : outcome === 'CANCELLED' ? 130 : code));
      timer = setTimeout(() => cancel('DEADLINE'), spec.mutation ? cfg.shipControlMs : cfg.shipReadMs); timer.unref();
    });
    this.jobs.get(key).promise = promise;
    return promise;
  }
  cancel(owner, id) { const j = this.jobs.get(owner + ':' + id); if (j) j.cancel(); }
  cancelOwner(owner) { for (const j of this.jobs.values()) if (j.owner === owner) j.cancel(); }
  async close() { this.closed = true; const jobs = [...this.jobs.values()]; for (const j of jobs) j.cancel(); await Promise.all(jobs.map(j => j.promise)); }
  telemetry() { return { active: this.jobs.size, concurrency: 1, controlEnabled: this.cfg.shipControl, outputBytes: this.cfg.shipOutputBytes, childMemoryLimit: 'NOT_ENFORCED', ...this.stats }; }
}
module.exports = { ShipBroker, childEnv };
