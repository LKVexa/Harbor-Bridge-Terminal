#!/usr/bin/env node
'use strict';
/**
 * Local quick start (loopback only). Creates an operator principal on first run, prints its access token ONCE,
 * finds the DF containers (DF_ROOT, or a folder beside/above this one holding DF_Fabric), binds Qnode fleet
 * roots, and starts the gateway.
 *   node tools/start-local.js [--port 10000] [--no-fabric]
 *
 * Note: gateway profile is LOCAL_VOLATILE — do not set VWS_SNAPSHOTS / VWS_SNAPSHOT_DIR (ConfigError).
 */
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const harborRoot = process.env.HARBOR_ROOT || path.resolve(root, '..');
const args = process.argv.slice(2);
const dataDir = path.join(root, '.vws-local');
fs.mkdirSync(dataDir, { recursive: true });
const pf = path.join(dataDir, 'principals.json');
if (!fs.existsSync(pf)) {
  const token = crypto.randomBytes(32).toString('base64url');
  fs.writeFileSync(pf, JSON.stringify([{ sub: 'operator', tenant: 'local', tokenSha256: crypto.createHash('sha256').update(token).digest('hex'), capabilities: ['terminal', 'fabric'] }], null, 2), { mode: 0o600 });
  console.log('\n  Access token (shown once; paste it into the sign-in box):\n\n    ' + token + '\n\n  Lost it? Delete .vws-local/principals.json and start again.\n');
}

function hasFabric(dir) {
  return dir && fs.existsSync(path.join(dir, 'DF_Fabric', 'adapter', 'dfabric', 'cli.py'));
}

function portFree(port) {
  return new Promise((resolve) => {
    const s = net.createServer();
    s.once('error', () => resolve(false));
    s.once('listening', () => s.close(() => resolve(true)));
    s.listen(port, '127.0.0.1');
  });
}

async function pickPort(preferred) {
  const start = Number(preferred) || 10000;
  for (let p = start; p < start + 20; p++) {
    if (await portFree(p)) return String(p);
  }
  throw new Error('no free loopback port in range ' + start + '-' + (start + 19));
}

(async () => {
  let preferred = args.includes('--port') ? args[args.indexOf('--port') + 1] : (process.env.PORT || '10000');
  const port = await pickPort(preferred);
  if (port !== String(preferred)) {
    console.log(`  note: port ${preferred} is in use — using ${port} instead\n`);
  }

  let df = process.env.DF_ROOT || null;
  if (!df && !args.includes('--no-fabric')) {
    const candidates = [
      path.join(root, 'df'),
      path.dirname(root),
      path.dirname(path.dirname(root)),
      path.join(path.dirname(root), 'New folder'),
      path.join(path.dirname(path.dirname(root)), 'New folder'),
      path.join(process.env.USERPROFILE || '', 'OneDrive', 'Desktop', 'New folder')
    ];
    for (const c of candidates) {
      if (hasFabric(c)) { df = c; break; }
    }
  }

  let qnodeRoot = process.env.QNODE_ROOT || null;
  if (!qnodeRoot) {
    const q = path.join(harborRoot, 'qnodes');
    if (fs.existsSync(path.join(q, 'FLEET.json')) || fs.existsSync(path.join(q, 'QN-01'))) qnodeRoot = q;
  }

  const env = {
    ...process.env,
    PORT: port,
    VWS_HOST: '127.0.0.1',
    VWS_PRINCIPALS_FILE: pf,
    VWS_SECURE_COOKIES: '0',
    VWS_FABRIC: df ? '1' : '0',
    HARBOR_ROOT: harborRoot
  };
  delete env.VWS_SNAPSHOTS;
  delete env.VWS_SNAPSHOT_DIR;
  if (df) env.DF_ROOT = df;
  if (qnodeRoot) env.QNODE_ROOT = qnodeRoot;

  console.log(`  HERMIT virtual WebSocket  ->  http://127.0.0.1:${port}/`);
  console.log(`  fabric : ${df ? 'ON  (DF_ROOT=' + df + ')' : 'off (no DF_Fabric folder found; set DF_ROOT)'}`);
  console.log(`  qnodes : ${qnodeRoot ? 'ON  (QNODE_ROOT=' + qnodeRoot + ')' : 'off (qnodes/ not found; set QNODE_ROOT)'}`);
  console.log(`  focus  : qn01..qn50   containers: ns nm nl nx nf`);
  console.log(`  Ctrl+C drains sessions and stops.\n`);

  const child = spawn(process.execPath, [path.join(root, 'gateway', 'server.js')], { env, stdio: 'inherit' });
  process.on('SIGINT', () => child.kill('SIGINT'));
  process.on('SIGTERM', () => child.kill('SIGTERM'));
  child.on('exit', (c) => process.exit(c === null ? 1 : c));
})().catch((e) => {
  console.error('  start-local failed:', e.message || e);
  process.exit(1);
});