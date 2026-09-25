#!/usr/bin/env node
'use strict';
/**
 * Generate 50 thin Qnode instance directories under Harbor-Bridge-Terminal/qnodes.
 * Does NOT copy the QVM product — instances point at ../qvm/product (junction).
 */
const fs = require('node:fs');
const path = require('node:path');

const HARBOR = path.resolve(__dirname, '..');
const QNODES = path.join(HARBOR, 'qnodes');
const FLEET_DIR = path.join(HARBOR, 'fleet');
const COUNT = 50;
const PRODUCT = 'QVM 8.1.0-alpha';
const BACKEND = 'statevector';

fs.mkdirSync(QNODES, { recursive: true });
fs.mkdirSync(FLEET_DIR, { recursive: true });

const roster = [];
for (let i = 1; i <= COUNT; i++) {
  const idx = String(i).padStart(2, '0');
  const id = `QN-${idx}`;
  const code = `qn${idx}`;
  const dir = path.join(QNODES, id);
  fs.mkdirSync(path.join(dir, 'runtime'), { recursive: true });

  const identity = {
    id,
    code,
    index: i,
    product: PRODUCT,
    product_root: '../qvm/product',
    product_root_abs_hint: 'resolved via QNODE_ROOT/../qvm/product or PRODUCT_LINK.txt',
    backend_default: BACKEND,
    created: new Date().toISOString()
  };
  fs.writeFileSync(path.join(dir, 'IDENTITY.json'), JSON.stringify(identity, null, 2) + '\n');
  fs.writeFileSync(path.join(dir, 'README.md'),
    `# ${id} (${code})\n\nThin Qnode instance for ${PRODUCT}.\n\n` +
    `In the Harbor terminal type \`${code}\` to enter interactive focus, then ` +
    `\`info\`, \`capabilities\`, \`bell\`, \`run <circuit.json>\`, \`selftest\`, \`exit\`.\n\n` +
    `Or from a shell: \`${path.join(dir, 'QNODE.cmd')} info\`\n`
  );

  const qnodeCmd = [
    '@echo off',
    'setlocal',
    `set QNODE_ID=${id}`,
    `set QNODE_CODE=${code}`,
    'set QNODE_HOME=%~dp0',
    'if "%QNODE_HOME:~-1%"=="\\" set QNODE_HOME=%QNODE_HOME:~0,-1%',
    'set HARBOR_ROOT=%QNODE_HOME%\\..\\..',
    'call "%HARBOR_ROOT%\\scripts\\link-qvm.cmd" >nul 2>&1',
    'set PRODUCT=%HARBOR_ROOT%\\qvm\\product',
    'if not exist "%PRODUCT%\\qvm\\cli.py" (',
    '  echo [QNODE] product missing — run scripts\\link-qvm.cmd',
    '  exit /b 1',
    ')',
    'set PYTHONPATH=%PRODUCT%',
    'cd /d "%QNODE_HOME%\\runtime"',
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
  fs.writeFileSync(path.join(dir, 'QNODE.cmd'), qnodeCmd);

  roster.push({
    id, code, index: i, dir: id, product: PRODUCT, backend: BACKEND,
    operable_hint: 'IDENTITY + linked qvm/product'
  });
}

const fleet = {
  version: 1,
  generated: new Date().toISOString(),
  count: COUNT,
  product: PRODUCT,
  product_link: 'qvm/PRODUCT_LINK.txt',
  product_junction: 'qvm/product',
  nodes: roster
};
fs.writeFileSync(path.join(QNODES, 'FLEET.json'), JSON.stringify(fleet, null, 2) + '\n');

const harborFleet = {
  version: 1,
  generated: new Date().toISOString(),
  harbor_root: '.',
  df_containers: [
    { code: 'ns', kind: 'df-node', id: 'N_SMALL', dir: 'DF_Small', focus: 'ns' },
    { code: 'nm', kind: 'df-node', id: 'N_MEDIUM', dir: 'DF_Medium', focus: 'nm' },
    { code: 'nl', kind: 'df-node', id: 'N_LARGE', dir: 'DF_Large', focus: 'nl' },
    { code: 'nx', kind: 'df-node', id: 'N_XLARGE', dir: 'DF_Xtra_Large', focus: 'nx' },
    { code: 'nf', kind: 'df-fabric', id: 'DF_Fabric', dir: 'DF_Fabric', focus: 'nf' }
  ],
  qnodes: roster.map((n) => ({ code: n.code, kind: 'qnode', id: n.id, product: n.product, focus: n.code }))
};
fs.writeFileSync(path.join(FLEET_DIR, 'HARBOR_FLEET.json'), JSON.stringify(harborFleet, null, 2) + '\n');

console.log(`generated ${COUNT} qnodes under ${QNODES}`);
