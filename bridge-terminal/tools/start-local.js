#!/usr/bin/env node
'use strict';
/**
 * Local quick start (loopback only). Creates an operator principal on first run, prints its access token ONCE,
 * finds the DF containers (DF_ROOT, or a folder beside/above this one holding DF_Fabric), binds Qnode fleet
 * roots, and starts the gateway. After the gateway listens on 127.0.0.1, launches VB-JA21 Portable Optical
 * Desktop with JA21_START_URL pointing at the Harbor URL (omni-bin / start navigation) — never the Windows
 * default browser.
 *   node tools/start-local.js [--port 10000] [--no-fabric] [--no-browser]
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
  try {
    const tokenFile = path.join(harborRoot, 'ACCESS_TOKEN.txt');
    fs.writeFileSync(tokenFile, token + '\n', { mode: 0o600 });
    console.log('\n  Access token (shown once; paste it into the sign-in box):\n\n    ' + token + '\n\n  Also saved to: ' + tokenFile + '\n  Lost it? Delete bridge-terminal/.vws-local/principals.json and ACCESS_TOKEN.txt, then start again.\n');
  } catch (e) {
    console.log('\n  Access token (shown once; paste it into the sign-in box):\n\n    ' + token + '\n\n  Lost it? Delete .vws-local/principals.json and start again.\n');
  }
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

function portOpen(port) {
  return new Promise((resolve) => {
    const s = net.connect({ host: '127.0.0.1', port: Number(port) }, () => {
      s.end();
      resolve(true);
    });
    s.on('error', () => resolve(false));
  });
}

async function pickPort(preferred) {
  const start = Number(preferred) || 10000;
  for (let p = start; p < start + 20; p++) {
    if (await portFree(p)) return String(p);
  }
  throw new Error('no free loopback port in range ' + start + '-' + (start + 19));
}

function waitForListen(port, timeoutMs) {
  const deadline = Date.now() + (timeoutMs || 20000);
  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      const s = net.connect({ host: '127.0.0.1', port: Number(port) }, () => {
        s.end();
        resolve();
      });
      s.on('error', () => {
        if (Date.now() > deadline) reject(new Error('gateway did not listen on 127.0.0.1:' + port));
        else setTimeout(tryOnce, 200);
      });
    };
    tryOnce();
  });
}

function resolveJa21Portable() {
  const portable = path.join(harborRoot, 'optical-desktop', 'portable');
  const startCmd = path.join(portable, 'Start JA21 Portable Desktop.cmd');
  const ps1 = path.join(portable, 'host', 'Start-JA21Browser.ps1');
  if (fs.existsSync(startCmd) && fs.existsSync(ps1)) {
    return { portable, startCmd, ps1 };
  }
  const linkFile = path.join(harborRoot, 'optical-desktop', 'PRODUCT_LINK.txt');
  if (fs.existsSync(linkFile)) {
    const text = fs.readFileSync(linkFile, 'utf8');
    const m = text.match(/^JA21_PORTABLE_ROOT=(.+)$/m);
    if (m) {
      const src = m[1].trim();
      const srcCmd = path.join(src, 'Start JA21 Portable Desktop.cmd');
      const srcPs1 = path.join(src, 'host', 'Start-JA21Browser.ps1');
      if (fs.existsSync(srcCmd) && fs.existsSync(srcPs1)) {
        return { portable: src, startCmd: srcCmd, ps1: srcPs1 };
      }
    }
  }
  return null;
}

function launchJa21OpticalDesktop(harborUrl) {
  const ja21 = resolveJa21Portable();
  if (!ja21) {
    console.log('  optical: JA21 Portable Desktop not linked — run scripts\\link-optical-desktop.cmd');
    console.log('           (Harbor will NOT open the system default browser.)');
    return null;
  }
  const env = {
    ...process.env,
    JA21_START_URL: harborUrl,
    // Harbor is loopback-only; JA21 denies private/loopback hosts unless this is set.
    JA21_ALLOW_PRIVATE_HOSTS: '1',
    HARBOR_ROOT: harborRoot
  };
  // Launch via PowerShell with -StartUrl so the omni/start navigation is explicit.
  // Detached: gateway keeps running; JA21 is its own WPF/WebView2 window.
  const child = spawn(
    'powershell.exe',
    [
      '-NoLogo', '-NoProfile', '-STA', '-ExecutionPolicy', 'Bypass',
      '-File', ja21.ps1,
      '-Root', ja21.portable,
      '-StartUrl', harborUrl
    ],
    {
      env,
      cwd: ja21.portable,
      detached: true,
      stdio: 'ignore',
      windowsHide: false
    }
  );
  child.unref();
  console.log(`  optical: VB-JA21 Portable Desktop 9.8.7  <-  ${harborUrl}`);
  console.log(`           (omni-bin start URL via JA21_START_URL / -StartUrl; not the system browser)`);
  console.log(`           root: ${ja21.portable}`);
  return child;
}

(async () => {
  const noBrowser = args.includes('--no-browser') || process.env.HARBOR_NO_BROWSER === '1';
  let preferred = args.includes('--port') ? args[args.indexOf('--port') + 1] : (process.env.PORT || '10000');

  // If preferred port is already serving (e.g. prior Harbor on 10001), reuse it for JA21 only when --reuse.
  const reuse = args.includes('--reuse') || process.env.HARBOR_REUSE === '1';
  let port;
  let startedGateway = false;
  if (reuse && !(await portFree(preferred)) && (await portOpen(preferred))) {
    port = String(preferred);
    console.log(`  note: reusing existing listener on 127.0.0.1:${port}\n`);
  } else {
    port = await pickPort(preferred);
    if (port !== String(preferred)) {
      console.log(`  note: port ${preferred} is in use — using ${port} instead\n`);
    }
    startedGateway = true;
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

  const harborUrl = `http://127.0.0.1:${port}/`;

  console.log(`  HERMIT virtual WebSocket  ->  ${harborUrl}`);
  console.log(`  fabric : ${df ? 'ON  (DF_ROOT=' + df + ')' : 'off (no DF_Fabric folder found; set DF_ROOT)'}`);
  console.log(`  qnodes : ${qnodeRoot ? 'ON  (QNODE_ROOT=' + qnodeRoot + ')' : 'off (qnodes/ not found; set QNODE_ROOT)'}`);
  console.log(`  focus  : qn01..qn50   containers: ns nm nl nx nf`);
  console.log(`  browser: ${noBrowser ? 'skipped (--no-browser)' : 'VB-JA21 optical desktop (omni-bin)'}`);
  console.log(`  Ctrl+C drains sessions and stops.\n`);

  if (!startedGateway) {
    if (!noBrowser) launchJa21OpticalDesktop(harborUrl);
    // Keep process alive so START_HARBOR.cmd doesn't exit immediately; user Ctrl+C to leave.
    await new Promise(() => {});
    return;
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

  const child = spawn(process.execPath, [path.join(root, 'gateway', 'server.js')], { env, stdio: 'inherit' });
  process.on('SIGINT', () => child.kill('SIGINT'));
  process.on('SIGTERM', () => child.kill('SIGTERM'));
  child.on('exit', (c) => process.exit(c === null ? 1 : c));

  waitForListen(port, 25000)
    .then(() => {
      if (!noBrowser) launchJa21OpticalDesktop(harborUrl);
    })
    .catch((e) => {
      console.error('  optical: could not confirm gateway listen:', e.message || e);
      console.error('           (Harbor will NOT open the system default browser.)');
    });
})().catch((e) => {
  console.error('  start-local failed:', e.message || e);
  process.exit(1);
});