'use strict';

/**
 * SPIRAL — Qnode fleet locator
 * ---------------------------------------------------------------------------
 * Finds the Harbor Qnode roster (QN-01..QN-50 FULL independent QVM copies)
 * under qnodes/. Each operable node has its own qvm/ package + VERSION;
 * runtime does not depend on the shared qvm/product junction (that junction
 * remains only as an optional seed for rematerializing copies).
 *
 * Resolution order for QNODE_ROOT (directory holding QN-01..QN-50):
 *   1. session/host env QNODE_ROOT
 *   2. process.env.QNODE_ROOT
 *   3. HARBOR_ROOT/qnodes (session or process)
 *   4. <appDir>/../qnodes beside bridge-terminal
 *   5. cwd/qnodes
 *
 * Status probes are cached (TTL) — IDENTITY + local VERSION / last_probe only.
 * Never spawn 50 QVM processes on a status poll.
 */

const fs = require('node:fs');
const path = require('node:path');

const COUNT = 50;
const PRODUCT_NAME = 'QVM 8.1.0-alpha';
const CACHE_TTL_MS = 30_000;

function readJSON(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}
function isDir(p) { try { return fs.statSync(p).isDirectory(); } catch { return false; } }
function exists(p) { try { fs.accessSync(p); return true; } catch { return false; } }
function readText(p) {
  try { return fs.readFileSync(p, 'utf8').trim(); } catch { return null; }
}

class QnodeLocator {
  /**
   * @param {object} opts
   * @param {()=>string|undefined} [opts.envRoot]
   * @param {()=>string|undefined} [opts.envHarbor]
   * @param {string} [opts.appDir]  bridge-terminal root (dirname of tools or package)
   */
  constructor(opts = {}) {
    this.opts = opts;
    this._cache = null;
    this._cacheAt = 0;
  }

  harborRoot() {
    const env = this.opts.envHarbor && this.opts.envHarbor();
    if (env && isDir(env)) return path.resolve(env);
    if (process.env.HARBOR_ROOT && isDir(process.env.HARBOR_ROOT)) return path.resolve(process.env.HARBOR_ROOT);
    if (this.opts.appDir) {
      const beside = path.resolve(this.opts.appDir, '..');
      if (isDir(path.join(beside, 'qnodes'))) return beside;
    }
    const cwd = process.cwd();
    if (isDir(path.join(cwd, 'qnodes'))) return cwd;
    if (path.basename(cwd) === 'bridge-terminal' && isDir(path.join(cwd, '..', 'qnodes'))) {
      return path.resolve(cwd, '..');
    }
    return null;
  }

  root() {
    const candidates = [];
    const env = this.opts.envRoot && this.opts.envRoot();
    if (env) candidates.push(env);
    if (process.env.QNODE_ROOT) candidates.push(process.env.QNODE_ROOT);
    const h = this.harborRoot();
    if (h) candidates.push(path.join(h, 'qnodes'));
    if (this.opts.appDir) candidates.push(path.join(this.opts.appDir, '..', 'qnodes'));
    candidates.push(path.join(process.cwd(), 'qnodes'));

    for (const c of candidates) {
      if (!c) continue;
      const r = path.resolve(c);
      if (isDir(path.join(r, 'QN-01')) || exists(path.join(r, 'FLEET.json'))) return r;
    }
    return null;
  }

  /**
   * Optional seed source for rematerializing copies (junction / PRODUCT_LINK).
   * Runtime operability does NOT require this.
   */
  seedProductRoot() {
    const h = this.harborRoot();
    const candidates = [];
    if (h) {
      candidates.push(path.join(h, 'qvm', 'product'));
      const link = readText(path.join(h, 'qvm', 'PRODUCT_LINK.txt'));
      if (link) {
        for (const line of link.split(/\r?\n/)) {
          const m = /^QVM_PRODUCT_ROOT=(.+)$/.exec(line.trim());
          if (m) candidates.push(m[1].trim());
        }
      }
    }
    if (process.env.QVM_PRODUCT_ROOT) candidates.push(process.env.QVM_PRODUCT_ROOT);
    for (const c of candidates) {
      if (c && exists(path.join(c, 'qvm', 'cli.py'))) return path.resolve(c);
    }
    return null;
  }

  /** @deprecated alias — prefer seedProductRoot(); kept for older call sites */
  productRoot() {
    return this.seedProductRoot();
  }

  /** Per-node product root = the QN-XX copy itself when it contains qvm/cli.py. */
  nodeProductRoot(codeOrId) {
    const d = this.nodeDir(codeOrId);
    if (!d) return null;
    if (exists(path.join(d, 'qvm', 'cli.py'))) return d;
    return null;
  }

  isFullCopy(dir) {
    if (!dir) return false;
    return exists(path.join(dir, 'qvm', 'cli.py')) && exists(path.join(dir, 'VERSION'));
  }

  productVersion() {
    const r = this.root();
    if (r) {
      for (let i = 1; i <= COUNT; i++) {
        const d = path.join(r, 'QN-' + String(i).padStart(2, '0'));
        const v = readText(path.join(d, 'VERSION'));
        if (v) return v;
      }
    }
    const seed = this.seedProductRoot();
    if (seed) return readText(path.join(seed, 'VERSION')) || PRODUCT_NAME.replace(/^QVM\s+/, '');
    return null;
  }

  nodeDir(codeOrId) {
    const r = this.root();
    if (!r) return null;
    const key = String(codeOrId || '').toLowerCase();
    let id = null;
    const m = /^qn0*([1-9]\d?|50)$/.exec(key);
    if (m) id = 'QN-' + String(Number(m[1])).padStart(2, '0');
    else if (/^qn-\d{2}$/i.test(key)) id = key.toUpperCase();
    else if (/^qn-\d{2}$/i.test(codeOrId)) id = String(codeOrId).toUpperCase();
    else if (/^\d{1,2}$/.test(key)) {
      const n = Number(key);
      if (n >= 1 && n <= COUNT) id = 'QN-' + String(n).padStart(2, '0');
    }
    if (!id) return null;
    const d = path.join(r, id);
    return isDir(d) ? d : null;
  }

  identity(codeOrId) {
    const d = this.nodeDir(codeOrId);
    if (!d) return null;
    return readJSON(path.join(d, 'IDENTITY.json'));
  }

  /** Full roster with presence / operability. Cached briefly. */
  roster({ force = false } = {}) {
    const now = Date.now();
    if (!force && this._cache && (now - this._cacheAt) < CACHE_TTL_MS) return this._cache;

    const r = this.root();
    const seed = this.seedProductRoot();
    const version = this.productVersion();
    const nodes = [];

    for (let i = 1; i <= COUNT; i++) {
      const idx = String(i).padStart(2, '0');
      const id = 'QN-' + idx;
      const code = 'qn' + idx;
      const dir = r ? path.join(r, id) : null;
      const present = dir ? isDir(dir) : false;
      const ident = present ? readJSON(path.join(dir, 'IDENTITY.json')) : null;
      const lastProbe = present ? readJSON(path.join(dir, 'runtime', 'last_probe.json')) : null;
      const copyOk = present && this.isFullCopy(dir);
      const operable = !!(present && ident && copyOk);
      const nodeVer = present ? readText(path.join(dir, 'VERSION')) : null;
      nodes.push({
        id,
        code,
        index: i,
        present,
        operable,
        copy: copyOk,
        product: (ident && ident.product) || PRODUCT_NAME,
        version: nodeVer || version || null,
        backend: (ident && ident.backend_default) || 'statevector',
        path: dir,
        product_root: copyOk ? dir : null,
        last_probe: lastProbe,
        product_bound: copyOk
      });
    }

    const operableCount = nodes.filter((n) => n.operable).length;
    this._cache = {
      root: r,
      product: seed,
      seed,
      version,
      product_bound: operableCount > 0,
      copies_complete: operableCount === COUNT,
      mode: 'full-copies',
      count: COUNT,
      operable: operableCount,
      present: nodes.filter((n) => n.present).length,
      nodes
    };
    this._cacheAt = now;
    return this._cache;
  }

  summaryLine() {
    const r = this.roster();
    const ver = r.version || '?';
    const state = r.copies_complete
      ? `${r.operable}/${r.count} operable (full copies)`
      : (r.operable > 0
        ? `${r.operable}/${r.count} operable · rematerialize remaining`
        : `${r.present}/${r.count} present · run scripts\\materialize-qnode-copies.cmd`);
    return `Qnodes ${state}  QVM ${ver}  statevector`;
  }

  /** Persist a lightweight probe cache under the instance runtime/. */
  writeProbe(codeOrId, data) {
    const d = this.nodeDir(codeOrId);
    if (!d) return false;
    const runtime = path.join(d, 'runtime');
    try {
      fs.mkdirSync(runtime, { recursive: true });
      fs.writeFileSync(path.join(runtime, 'last_probe.json'), JSON.stringify({
        at: new Date().toISOString(),
        ...data
      }, null, 2) + '\n');
      this._cache = null;
      return true;
    } catch {
      return false;
    }
  }
}

module.exports = { QnodeLocator, COUNT, PRODUCT_NAME };
