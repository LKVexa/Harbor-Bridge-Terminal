#!/usr/bin/env node
'use strict';
/**
 * Local quick start (loopback only). Creates an operator principal on first run, prints its access token ONCE,
 * finds the DF containers (DF_ROOT, or a folder beside/above this one holding DF_Fabric) and starts the gateway.
 *   node tools/start-local.js [--port 10000] [--no-fabric]
 */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const port = args.includes('--port') ? args[args.indexOf('--port') + 1] : '10000';
const dataDir = path.join(root, '.vws-local');
fs.mkdirSync(dataDir, { recursive: true });
const pf = path.join(dataDir, 'principals.json');
if (!fs.existsSync(pf)) {
  const token = crypto.randomBytes(32).toString('base64url');
  fs.writeFileSync(pf, JSON.stringify([{ sub: 'operator', tenant: 'local', tokenSha256: crypto.createHash('sha256').update(token).digest('hex'), capabilities: ['terminal', 'fabric'] }], null, 2), { mode: 0o600 });
  console.log('\n  Access token (shown once; paste it into the sign-in box):\n\n    ' + token + '\n\n  Lost it? Delete .vws-local/principals.json and start again.\n');
}
let df = process.env.DF_ROOT || null;
if (!df && !args.includes('--no-fabric')) for (const c of [path.join(root, 'df'), path.dirname(root), path.dirname(path.dirname(root))]) if (fs.existsSync(path.join(c, 'DF_Fabric', 'adapter', 'dfabric', 'cli.py'))) { df = c; break; }
const env = { ...process.env, PORT: port, VWS_HOST: '127.0.0.1', VWS_PRINCIPALS_FILE: pf, VWS_SECURE_COOKIES: '0', VWS_FABRIC: df ? '1' : '0' };
if (df) env.DF_ROOT = df;
console.log(`  HERMIT virtual WebSocket  ->  http://127.0.0.1:${port}/\n  fabric: ${df ? 'ON  (DF_ROOT=' + df + ')' : 'off (no DF_Fabric folder found; set DF_ROOT)'}\n  Ctrl+C drains sessions and stops.\n`);
const child = spawn(process.execPath, [path.join(root, 'gateway', 'server.js')], { env, stdio: 'inherit' });
process.on('SIGINT', () => child.kill('SIGINT'));
process.on('SIGTERM', () => child.kill('SIGTERM'));
child.on('exit', (c) => process.exit(c === null ? 1 : c));
