#!/usr/bin/env node
'use strict';
/** Loopback-only containership launcher. Uses installed Node/Python; installs nothing. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn, spawnSync } = require('node:child_process');
const { load } = require('../gateway/config');
const { createGateway } = require('../gateway/server');
function parse(argv) {
  const out = { port: '10000', control: false, newToken: false, browser: true, check: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--port' && i + 1 < argv.length) { out.port = argv[++i]; if (!/^[1-9][0-9]{0,4}$/.test(out.port) || Number(out.port) > 65535) throw new Error('port must be 1..65535'); }
    else if (a === '--control') out.control = true;
    else if (a === '--new-token') out.newToken = true;
    else if (a === '--no-browser') out.browser = false;
    else if (a === '--check') out.check = true;
    else throw new Error('unknown or incomplete launcher option: ' + a);
  }
  return out;
}
function noLinks(p) {
  const absolute = path.resolve(p); const parts = absolute.slice(path.parse(absolute).root.length).split(path.sep); let q = path.parse(absolute).root;
  for (const part of parts) { q = path.join(q, part); if (fs.existsSync(q) && fs.lstatSync(q).isSymbolicLink()) throw new Error('launcher state cannot traverse a link: ' + q); }
}
function resolvePython(env = process.env) {
  const candidates = env.UC_PYTHON || env.PYTHON ? [[env.UC_PYTHON || env.PYTHON]] : process.platform === 'win32' ? [['py','-3'],['python'],['python3']] : [['python3'],['python']];
  for (const [exe, ...prefix] of candidates) {
    const p = spawnSync(exe, [...prefix, '-I','-c','import sys; assert sys.version_info >= (3,10); print(sys.executable)'], { timeout: 10000, encoding: 'utf8', windowsHide: true, shell: false, maxBuffer: 16384 });
    const value = (p.stdout || '').trim(); if (p.status === 0 && path.isAbsolute(value) && fs.existsSync(value)) return value;
  }
  throw new Error('No usable Python 3.10+ runtime found. Set PYTHON to its full executable path. Nothing was installed.');
}
async function main(argv = process.argv.slice(2)) {
  const opts = parse(argv);
  if (Number(process.versions.node.split('.')[0]) < 22) throw new Error('Node.js 22+ is required by this integrated launcher. Nothing was installed.');
  const root = path.resolve(__dirname, '../..');
  if (!fs.existsSync(path.join(root, 'uc.py'))) throw new Error('start-ship.js must remain in UC240/vws/tools');
  const python = resolvePython();
  const dataDir = path.join(root, '_runs', 'vws'); const pf = path.join(dataDir, 'principals.json');
  noLinks(pf);
  const env = { ...process.env, PORT: opts.port, VWS_HOST: '127.0.0.1', VWS_ALLOWED_ORIGINS: `http://127.0.0.1:${opts.port}`, VWS_ALLOW_QUERY_TICKET: '0', VWS_ALLOW_NO_ORIGIN: '0', VWS_AUTH: 'static-file', VWS_SECURE_COOKIES: '0', VWS_PRINCIPALS_FILE: pf, VWS_FABRIC: '0', VWS_SHIP_ROOT: root, VWS_SHIP_CONTROL: opts.control ? '1' : '0', PYTHON: python };
  // Conflicting storage profiles are rejected by load, not silently downgraded.
  const cfg = load(env);
  if (opts.check) { console.log(JSON.stringify({ release: 'UC-2.4.0', node: process.version, python, root, profile: cfg.profile, control: opts.control, host: cfg.host, port: cfg.port, installs: false }, null, 2)); return; }
  fs.mkdirSync(dataDir, { recursive: true, mode: 0o700 });
  let token = null;
  const gw = createGateway(cfg); let stopping = false;
  const stop = async () => { if (stopping) return; stopping = true; try { const result = await gw.shutdown(); process.exitCode = result.forced ? 1 : 0; } catch { process.exitCode = 1; } };
  process.once('SIGINT', stop); process.once('SIGTERM', stop);
  let addr;
  try { addr = await gw.listen(); } catch (e) { await gw.shutdown(); throw e; }
  // Publish a new credential only after the port is successfully owned.
  // An address-in-use failure must not revoke another running launcher's token.
  try {

  if (!fs.existsSync(pf) || opts.newToken) {
    token = crypto.randomBytes(32).toString('base64url');
    const text = JSON.stringify([{ sub: 'operator', tenant: 'local', tokenSha256: crypto.createHash('sha256').update(token).digest('hex'), capabilities: ['terminal','ship.read','ship.control'] }], null, 2) + '\n';
    const temp = path.join(dataDir, 'principal-' + crypto.randomBytes(8).toString('hex') + '.tmp');
    fs.writeFileSync(temp, text, { mode: 0o600, flag: 'wx' });
    fs.renameSync(temp, pf);
  }
  } catch (e) { await gw.shutdown(); throw e; }
  const url = `http://127.0.0.1:${addr.port}/`;
  console.log(`\nUnikernel Containership UC-2.7.0 / HERMIT RAMWS\n${url}\nMode: ${opts.control ? 'CONTROL — allowlisted commands only' : 'READ ONLY'}\nPython: ${python}\nSession storage: RAM only. Ship TIFF/lifecycle files remain on disk.\n`);
  if (token) console.log(`Access token (shown once; paste into Sign in):\n\n${token}\n`);
  else console.log('Use your existing token. Lost it? Stop this service, then run TERMINAL.cmd --new-token.');
  console.log('Type ship help in the terminal. Ctrl+C here drains sessions and cancels ship jobs.\n');
  if (opts.browser) {
    const child = spawn(python, ['-I','-c','import sys,webbrowser; webbrowser.open(sys.argv[1])', url], { shell: false, windowsHide: true, stdio: 'ignore', env: require('../ship/broker').childEnv() });
    child.once('error', () => console.log('Open the printed local URL in your browser.')); child.unref();
  }
  return gw;
}
if (require.main === module) main().catch(e => { console.error('TERMINAL REFUSED: ' + e.message); process.exitCode = 78; });
module.exports = { main, parse, resolvePython, noLinks };
