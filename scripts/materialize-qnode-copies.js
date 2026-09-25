#!/usr/bin/env node
'use strict';
/**
 * Materialize 50 FULL independent QVM copies under Harbor-Bridge-Terminal/qnodes/QN-XX.
 * Seed source: qvm/product junction, PRODUCT_LINK.txt, or DEFAULT_SRC.
 * Does NOT modify the original New folder QVM tree.
 * Runtime does not depend on the junction — each QN-XX is self-contained.
 */
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');

const HARBOR = path.resolve(__dirname, '..');
const QNODES = path.join(HARBOR, 'qnodes');
const FLEET_DIR = path.join(HARBOR, 'fleet');
const COUNT = 50;
const PRODUCT = 'QVM 8.1.0-alpha';
const BACKEND = 'statevector';
const PARALLEL = Math.max(1, Math.min(5, Number(process.env.QNODE_COPY_PARALLEL || 4)));
const DEFAULT_SRC = 'C:\\Users\\russe\\OneDrive\\Desktop\\New folder\\QVM_Quantum_VM_v8.1.0-alpha\\QVM_Quantum_VM_v8.1.0-alpha';

function readLinkSrc() {
  const linkFile = path.join(HARBOR, 'qvm', 'PRODUCT_LINK.txt');
  const junction = path.join(HARBOR, 'qvm', 'product');
  if (fs.existsSync(path.join(junction, 'qvm', 'cli.py'))) return junction;
  try {
    const text = fs.readFileSync(linkFile, 'utf8');
    for (const line of text.split(/\r?\n/)) {
      const m = /^QVM_PRODUCT_ROOT=(.+)$/.exec(line.trim());
      if (m && fs.existsSync(path.join(m[1].trim(), 'qvm', 'cli.py'))) return m[1].trim();
    }
  } catch { /* ignore */ }
  if (fs.existsSync(path.join(DEFAULT_SRC, 'qvm', 'cli.py'))) return DEFAULT_SRC;
  return null;
}

function qnodeCmd(id, code) {
  return [
    '@echo off',
    'setlocal',
    `set QNODE_ID=${id}`,
    `set QNODE_CODE=${code}`,
    'set QNODE_HOME=%~dp0',
    'if "%QNODE_HOME:~-1%"=="\\" set QNODE_HOME=%QNODE_HOME:~0,-1%',
    'set PRODUCT=%QNODE_HOME%',
    'if not exist "%PRODUCT%\\qvm\\cli.py" (',
    '  echo [QNODE] full QVM copy missing — run scripts\\materialize-qnode-copies.cmd',
    '  exit /b 1',
    ')',
    'set PYTHONPATH=%PRODUCT%',
    'cd /d "%PRODUCT%"',
    'if "%~1"=="" (',
    '  where py >nul 2>nul && (py -3 -m qvm.cli info & exit /b %errorlevel%)',
    '  where python >nul 2>nul && (python -m qvm.cli info & exit /b %errorlevel%)',
    '  echo Python 3 not found & exit /b 2',
    ')',
    'where py >nul 2>nul && (py -3 -m qvm.cli %* & exit /b %errorlevel%)',
    'where python >nul 2>nul && (python -m qvm.cli %* & exit /b %errorlevel%)',
    'echo Python 3 not found & exit /b 2',
    ''
  ].join('\r\n');
}

function writeHarborMeta(dir, id, code, index) {
  fs.mkdirSync(path.join(dir, 'runtime'), { recursive: true });
  const identity = {
    id,
    code,
    index,
    product: PRODUCT,
    copy: true,
    product_root: '.',
    backend_default: BACKEND,
    created: new Date().toISOString()
  };
  fs.writeFileSync(path.join(dir, 'IDENTITY.json'), JSON.stringify(identity, null, 2) + '\n');
  fs.writeFileSync(path.join(dir, 'QNODE.cmd'), qnodeCmd(id, code));
  fs.writeFileSync(
    path.join(dir, 'HARBOR_README.md'),
    `# ${id} (${code})\n\n` +
      `Full independent copy of ${PRODUCT}.\n\n` +
      `In Harbor type \`${code}\` then \`info\`, \`bell\`, \`run <circuit.json>\`, \`exit\`.\n\n` +
      `Shell: \`${path.join(dir, 'QNODE.cmd')} info\`\n` +
      `Rematerialize: \`scripts\\materialize-qnode-copies.cmd\`\n`
  );
}

function robocopy(src, dest) {
  return new Promise((resolve) => {
    fs.mkdirSync(dest, { recursive: true });
    const args = [src, dest, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/nc', '/ns', '/np', '/R:1', '/W:1'];
    const child = spawn('robocopy', args, { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] });
    let err = '';
    child.stderr.on('data', (b) => { err += b.toString(); });
    child.on('close', (code) => {
      const ok = code != null && code < 8;
      resolve({ ok, code: code == null ? 1 : code, err });
    });
    child.on('error', (e) => resolve({ ok: false, code: 1, err: e.message }));
  });
}

async function materializeOne(src, i) {
  const idx = String(i).padStart(2, '0');
  const id = `QN-${idx}`;
  const code = `qn${idx}`;
  const dest = path.join(QNODES, id);
  if (fs.existsSync(dest)) {
    try {
      fs.rmSync(dest, { recursive: true, force: true });
    } catch (e) {
      return { id, ok: false, err: 'rm failed: ' + e.message };
    }
  }
  const rc = await robocopy(src, dest);
  if (!rc.ok) return { id, ok: false, err: 'robocopy exit ' + rc.code + ' ' + rc.err };
  if (!fs.existsSync(path.join(dest, 'qvm', 'cli.py'))) {
    return { id, ok: false, err: 'missing qvm/cli.py after copy' };
  }
  writeHarborMeta(dest, id, code, i);
  return { id, ok: true };
}

async function runPool(items, limit, worker) {
  const results = new Array(items.length);
  let next = 0;
  async function workerLoop() {
    while (true) {
      const i = next++;
      if (i >= items.length) return;
      results[i] = await worker(items[i], i);
      process.stdout.write(`  [${i + 1}/${items.length}] ${results[i].id}${results[i].ok ? ' OK' : ' FAIL ' + results[i].err}\n`);
    }
  }
  const runners = [];
  for (let k = 0; k < Math.min(limit, items.length); k++) runners.push(workerLoop());
  await Promise.all(runners);
  return results;
}

async function main() {
  const src = readLinkSrc();
  if (!src) {
    console.error('[materialize] No QVM seed found. Set qvm/PRODUCT_LINK.txt or create qvm/product junction.');
    process.exit(1);
  }
  console.log('[materialize] seed: ' + src);
  console.log('[materialize] dest: ' + QNODES + ' (QN-01..QN-' + String(COUNT).padStart(2, '0') + ')');
  console.log('[materialize] parallel: ' + PARALLEL);

  fs.mkdirSync(QNODES, { recursive: true });
  fs.mkdirSync(FLEET_DIR, { recursive: true });

  const indices = [];
  for (let i = 1; i <= COUNT; i++) indices.push(i);
  const results = await runPool(indices, PARALLEL, (i) => materializeOne(src, i));
  const failed = results.filter((r) => !r.ok);
  const roster = [];
  for (let i = 1; i <= COUNT; i++) {
    const idx = String(i).padStart(2, '0');
    const id = 'QN-' + idx;
    const code = 'qn' + idx;
    roster.push({
      id, code, index: i, dir: id, product: PRODUCT, backend: BACKEND,
      copy: true, operable_hint: 'IDENTITY + local qvm/cli.py + VERSION'
    });
  }

  const fleet = {
    version: 2,
    generated: new Date().toISOString(),
    count: COUNT,
    mode: 'full-copies',
    product: PRODUCT,
    seed_link: 'qvm/PRODUCT_LINK.txt',
    seed_junction: 'qvm/product',
    note: 'Each QN-XX is a complete independent QVM tree. Rematerialize via scripts/materialize-qnode-copies.cmd',
    nodes: roster
  };
  fs.writeFileSync(path.join(QNODES, 'FLEET.json'), JSON.stringify(fleet, null, 2) + '\n');

  const harborFleet = {
    version: 2,
    generated: new Date().toISOString(),
    harbor_root: '.',
    qnode_mode: 'full-copies',
    df_containers: [
      { code: 'ns', kind: 'df-node', id: 'N_SMALL', dir: 'DF_Small', focus: 'ns' },
      { code: 'nm', kind: 'df-node', id: 'N_MEDIUM', dir: 'DF_Medium', focus: 'nm' },
      { code: 'nl', kind: 'df-node', id: 'N_LARGE', dir: 'DF_Large', focus: 'nl' },
      { code: 'nx', kind: 'df-node', id: 'N_XLARGE', dir: 'DF_Xtra_Large', focus: 'nx' },
      { code: 'nf', kind: 'df-fabric', id: 'DF_Fabric', dir: 'DF_Fabric', focus: 'nf' }
    ],
    qnodes: roster.map((n) => ({ code: n.code, kind: 'qnode', id: n.id, product: n.product, copy: true, focus: n.code }))
  };
  fs.writeFileSync(path.join(FLEET_DIR, 'HARBOR_FLEET.json'), JSON.stringify(harborFleet, null, 2) + '\n');

  console.log('[materialize] done. ok=' + (COUNT - failed.length) + ' failed=' + failed.length);
  if (failed.length) {
    for (const f of failed) console.error('  FAIL ' + f.id + ': ' + f.err);
    process.exit(1);
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
