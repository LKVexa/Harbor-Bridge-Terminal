#!/usr/bin/env node
'use strict';
/**
 * Audit all 50 Harbor Qnodes for inventory, independence, and load-carrying ability.
 * Usage: node scripts/audit-qnode-load.js
 * Optional: QNODE_AUDIT_PARALLEL=5  (default 5)
 */
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');

const HARBOR = path.resolve(__dirname, '..');
const QNODES = path.join(HARBOR, 'qnodes');
const FLEET_JSON = path.join(HARBOR, 'fleet', 'HARBOR_FLEET.json');
const OUT_MD = path.join(HARBOR, 'fleet', 'QNODE_LOAD_AUDIT.md');
const OUT_JSON = path.join(HARBOR, 'fleet', 'QNODE_LOAD_AUDIT.json');
const COUNT = 50;
const PARALLEL = Math.max(1, Math.min(10, Number(process.env.QNODE_AUDIT_PARALLEL || 5)));
const KEY_FILES = [
  'qvm/cli.py',
  'VERSION',
  'IDENTITY.json',
  'QNODE.cmd',
  'examples/bell.json',
  'RUN_QVM.cmd'
];

function nowPtLabel() {
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Los_Angeles',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false, timeZoneName: 'short'
  });
  return fmt.format(new Date());
}

function idFor(i) {
  const idx = String(i).padStart(2, '0');
  return { i, idx, id: `QN-${idx}`, code: `qn${idx}`, dir: path.join(QNODES, `QN-${idx}`) };
}

function isReparsePoint(p) {
  try {
    const st = fs.lstatSync(p);
    // Windows: reparse point bit often exposed via stats; also check if symlink
    if (st.isSymbolicLink && st.isSymbolicLink()) return true;
    // Node on Windows: check mode / readlink
    try {
      fs.readlinkSync(p);
      return true;
    } catch { /* not a link */ }
    return false;
  } catch {
    return false;
  }
}

function countTree(dir) {
  let files = 0;
  let bytes = 0;
  function walk(d) {
    let entries;
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      const full = path.join(d, e.name);
      if (e.isDirectory()) walk(full);
      else if (e.isFile()) {
        files += 1;
        try { bytes += fs.statSync(full).size; } catch { /* ignore */ }
      }
    }
  }
  walk(dir);
  return { files, bytes };
}

function inventory(node) {
  const exists = fs.existsSync(node.dir);
  const keys = {};
  for (const rel of KEY_FILES) {
    keys[rel] = exists && fs.existsSync(path.join(node.dir, rel));
  }
  const reparse = exists ? isReparsePoint(node.dir) : false;
  const qvmReparse = exists && fs.existsSync(path.join(node.dir, 'qvm'))
    ? isReparsePoint(path.join(node.dir, 'qvm'))
    : false;
  let identity = null;
  let version = null;
  if (keys['IDENTITY.json']) {
    try { identity = JSON.parse(fs.readFileSync(path.join(node.dir, 'IDENTITY.json'), 'utf8')); } catch { identity = { parse_error: true }; }
  }
  if (keys['VERSION']) {
    try { version = fs.readFileSync(path.join(node.dir, 'VERSION'), 'utf8').trim(); } catch { version = null; }
  }
  const tree = exists ? countTree(node.dir) : { files: 0, bytes: 0 };
  const missingKeys = KEY_FILES.filter((k) => !keys[k]);
  const ok = exists && missingKeys.length === 0 && !reparse && !qvmReparse
    && identity && identity.id === node.id && identity.code === node.code
    && version === '8.1.0-alpha';
  return {
    exists, keys, missingKeys, reparse, qvmReparse, identity, version,
    files: tree.files, bytes: tree.bytes, ok
  };
}

function runCmd(cwd, cmd, args, timeoutMs) {
  return new Promise((resolve) => {
    const started = Date.now();
    const child = spawn(cmd, args, {
      cwd,
      windowsHide: true,
      shell: false,
      env: { ...process.env, PYTHONPATH: cwd }
    });
    let stdout = '';
    let stderr = '';
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      try { child.kill(); } catch { /* ignore */ }
      resolve({
        ok: false, exit: null, ms: Date.now() - started,
        stdout: stdout.slice(0, 4000), stderr: (stderr + '\n[timeout]').slice(0, 4000)
      });
    }, timeoutMs);
    child.stdout.on('data', (b) => { stdout += b.toString(); });
    child.stderr.on('data', (b) => { stderr += b.toString(); });
    child.on('error', (e) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({ ok: false, exit: 1, ms: Date.now() - started, stdout: stdout.slice(0, 4000), stderr: String(e.message).slice(0, 4000) });
    });
    child.on('close', (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve({
        ok: code === 0,
        exit: code == null ? 1 : code,
        ms: Date.now() - started,
        stdout: stdout.slice(0, 4000),
        stderr: stderr.slice(0, 4000)
      });
    });
  });
}

async function findPython() {
  const tries = [
    ['py', ['-3', '-c', 'print(1)']],
    ['python', ['-c', 'print(1)']]
  ];
  for (const [cmd, args] of tries) {
    const r = await runCmd(HARBOR, cmd, args, 10000);
    if (r.ok) return { cmd, prefix: cmd === 'py' ? ['-3'] : [] };
  }
  return null;
}

async function loadProbe(node, py) {
  const probes = {};
  // info
  probes.info = await runCmd(node.dir, py.cmd, [...py.prefix, '-m', 'qvm.cli', 'info'], 30000);
  // selftest (CLI builtin — real workload)
  probes.selftest = await runCmd(node.dir, py.cmd, [...py.prefix, '-m', 'qvm.cli', 'selftest'], 120000);
  // run bell circuit
  probes.bell = await runCmd(node.dir, py.cmd, [...py.prefix, '-m', 'qvm.cli', 'run', 'examples/bell.json'], 60000);
  const ok = probes.info.ok && probes.selftest.ok && probes.bell.ok;
  return { ok, probes };
}

async function mapPool(items, limit, fn) {
  const out = new Array(items.length);
  let next = 0;
  async function worker() {
    while (true) {
      const i = next++;
      if (i >= items.length) return;
      out[i] = await fn(items[i], i);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, () => worker()));
  return out;
}

function independenceCheck() {
  const a = path.join(QNODES, 'QN-01', 'runtime');
  const b = path.join(QNODES, 'QN-02', 'runtime');
  fs.mkdirSync(a, { recursive: true });
  fs.mkdirSync(b, { recursive: true });
  const markerName = `_audit_marker_${Date.now()}.txt`;
  const markerA = path.join(a, markerName);
  const markerB = path.join(b, markerName);
  const payload = `audit-independence ${new Date().toISOString()}`;
  fs.writeFileSync(markerA, payload);
  const leaked = fs.existsSync(markerB);
  let contentB = null;
  if (leaked) {
    try { contentB = fs.readFileSync(markerB, 'utf8'); } catch { contentB = null; }
  }
  // cleanup
  try { fs.unlinkSync(markerA); } catch { /* ignore */ }
  if (leaked) {
    try { fs.unlinkSync(markerB); } catch { /* ignore */ }
  }
  const ok = !leaked && contentB !== payload;
  return {
    ok,
    detail: ok
      ? 'Marker written under QN-01/runtime did not appear under QN-02/runtime (independent trees).'
      : 'Marker written under QN-01/runtime also appeared under QN-02/runtime — trees may be shared/junctioned.'
  };
}

function fleetAlign() {
  let fleet;
  try {
    fleet = JSON.parse(fs.readFileSync(FLEET_JSON, 'utf8'));
  } catch (e) {
    return { ok: false, detail: 'Failed to parse HARBOR_FLEET.json: ' + e.message, expected: [], found: [] };
  }
  const qnodes = Array.isArray(fleet.qnodes) ? fleet.qnodes : [];
  const expected = [];
  for (let i = 1; i <= COUNT; i++) {
    const idx = String(i).padStart(2, '0');
    expected.push({ id: `QN-${idx}`, code: `qn${idx}`, focus: `qn${idx}` });
  }
  const missing = [];
  const mismatches = [];
  for (const exp of expected) {
    const hit = qnodes.find((q) => q.id === exp.id);
    if (!hit) missing.push(exp.id);
    else {
      if (hit.code !== exp.code || hit.focus !== exp.focus || hit.copy !== true) {
        mismatches.push({ id: exp.id, got: hit });
      }
    }
  }
  const extra = qnodes.filter((q) => !expected.some((e) => e.id === q.id)).map((q) => q.id);
  const mode = fleet.qnode_mode;
  const ok = missing.length === 0 && mismatches.length === 0 && extra.length === 0
    && mode === 'full-copies' && qnodes.length === COUNT;
  return {
    ok, mode, count: qnodes.length, missing, mismatches, extra,
    detail: ok
      ? `HARBOR_FLEET.json lists all ${COUNT} qnodes (qn01…qn50), qnode_mode=full-copies.`
      : `Fleet alignment issues: missing=${missing.join(',') || 'none'} mismatches=${mismatches.length} extra=${extra.join(',') || 'none'} mode=${mode}`
  };
}

function fmtBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function buildMarkdown(report) {
  const lines = [];
  lines.push('# Qnode load audit');
  lines.push('');
  lines.push(`- **Date (America/Los_Angeles):** ${report.date_pt}`);
  lines.push(`- **Harbor root:** \`${report.harbor_root}\``);
  lines.push(`- **Scope:** QN-01 … QN-50 (full QVM 8.1.0-alpha copies)`);
  lines.push(`- **Parallelism:** ${report.parallel}`);
  lines.push(`- **Python:** \`${report.python}\``);
  lines.push('');
  lines.push('## Method');
  lines.push('');
  lines.push('1. **Fleet inventory** — confirm each `qnodes/QN-XX` exists with key entrypoints (`qvm/cli.py`, `VERSION`, `IDENTITY.json`, `QNODE.cmd`, `examples/bell.json`, `RUN_QVM.cmd`); count files/bytes; detect directory reparse/junction.');
  lines.push('2. **Independence** — write a unique marker under `QN-01/runtime/` and verify it does **not** appear under `QN-02/runtime/`.');
  lines.push('3. **Load probe** (per node, cwd = that copy, `PYTHONPATH` = that copy):');
  lines.push('   - `py -3 -m qvm.cli info`');
  lines.push('   - `py -3 -m qvm.cli selftest` (built-in CLI selftest / unit suite)');
  lines.push('   - `py -3 -m qvm.cli run examples/bell.json` (statevector Bell circuit, 1024 shots)');
  lines.push('4. **Harbor integration** — align `fleet/HARBOR_FLEET.json` focus codes `qn01`…`qn50` with on-disk nodes (`qnode_mode=full-copies`).');
  lines.push('');
  lines.push('## Summary');
  lines.push('');
  lines.push(`| Check | Result |`);
  lines.push(`|-------|--------|`);
  lines.push(`| Nodes inventoried | ${report.nodes.length} / ${COUNT} |`);
  lines.push(`| Inventory pass | ${report.counts.inventory_pass} / ${COUNT} |`);
  lines.push(`| Load probe pass | ${report.counts.load_pass} / ${COUNT} |`);
  lines.push(`| Overall carry-load pass | **${report.counts.overall_pass} / ${COUNT}** |`);
  lines.push(`| Independence | ${report.independence.ok ? 'PASS' : 'FAIL'} — ${report.independence.detail} |`);
  lines.push(`| Fleet alignment | ${report.fleet.ok ? 'PASS' : 'FAIL'} — ${report.fleet.detail} |`);
  lines.push(`| Failures | ${report.failures.length === 0 ? 'none' : report.failures.join(', ')} |`);
  lines.push('');
  if (report.failures.length === 0) {
    lines.push('**Verdict:** all 50 Qnodes can carry a load (inventory + info + selftest + bell run).');
  } else {
    lines.push('**Verdict:** NOT all nodes passed. See failures below.');
  }
  lines.push('');
  lines.push('## Per-node results');
  lines.push('');
  lines.push('| Node | Code | Files | Size | Inv | Info | Selftest | Bell | Overall | Notes |');
  lines.push('|------|------|------:|-----:|:---:|:----:|:--------:|:----:|:-------:|-------|');
  for (const n of report.nodes) {
    const notes = [];
    if (n.inventory.missingKeys.length) notes.push('missing:' + n.inventory.missingKeys.join(';'));
    if (n.inventory.reparse) notes.push('dir-reparse');
    if (n.inventory.qvmReparse) notes.push('qvm-reparse');
    if (!n.load.probes.info.ok) notes.push('info-exit=' + n.load.probes.info.exit);
    if (!n.load.probes.selftest.ok) notes.push('selftest-exit=' + n.load.probes.selftest.exit);
    if (!n.load.probes.bell.ok) notes.push('bell-exit=' + n.load.probes.bell.exit);
    const row = [
      n.id,
      n.code,
      String(n.inventory.files),
      fmtBytes(n.inventory.bytes),
      n.inventory.ok ? 'PASS' : 'FAIL',
      n.load.probes.info.ok ? `PASS (${n.load.probes.info.ms}ms)` : `FAIL (${n.load.probes.info.ms}ms)`,
      n.load.probes.selftest.ok ? `PASS (${n.load.probes.selftest.ms}ms)` : `FAIL (${n.load.probes.selftest.ms}ms)`,
      n.load.probes.bell.ok ? `PASS (${n.load.probes.bell.ms}ms)` : `FAIL (${n.load.probes.bell.ms}ms)`,
      n.overall_ok ? 'PASS' : 'FAIL',
      notes.join(' ') || '—'
    ];
    lines.push('| ' + row.join(' | ') + ' |');
  }
  lines.push('');
  lines.push('## Failure details');
  lines.push('');
  const failedNodes = report.nodes.filter((n) => !n.overall_ok);
  if (failedNodes.length === 0) {
    lines.push('None.');
  } else {
    for (const n of failedNodes) {
      lines.push(`### ${n.id}`);
      lines.push('');
      lines.push('```');
      lines.push(JSON.stringify({
        inventory: n.inventory,
        info_stderr: n.load.probes.info.stderr,
        selftest_stderr: n.load.probes.selftest.stderr,
        bell_stderr: n.load.probes.bell.stderr
      }, null, 2));
      lines.push('```');
      lines.push('');
    }
  }
  lines.push('## Re-run');
  lines.push('');
  lines.push('```bat');
  lines.push('scripts\\audit-qnode-load.cmd');
  lines.push('```');
  lines.push('');
  lines.push('Or: `node scripts\\audit-qnode-load.js` (optional `set QNODE_AUDIT_PARALLEL=5`).');
  lines.push('');
  lines.push('If inventory fails (missing `qvm\\cli.py`), rematerialize first:');
  lines.push('');
  lines.push('```bat');
  lines.push('scripts\\materialize-qnode-copies.cmd');
  lines.push('```');
  lines.push('');
  lines.push('Machine-local artifact also written: `fleet/QNODE_LOAD_AUDIT.json`.');
  lines.push('');
  return lines.join('\n');
}

async function main() {
  console.log(`[audit] Harbor=${HARBOR}`);
  console.log(`[audit] parallel=${PARALLEL} date=${nowPtLabel()}`);
  const py = await findPython();
  if (!py) {
    console.error('[audit] Python 3 not found (py -3 / python)');
    process.exit(2);
  }
  console.log(`[audit] python=${py.cmd} ${py.prefix.join(' ')}`);

  const fleet = fleetAlign();
  console.log(`[audit] fleet: ${fleet.ok ? 'PASS' : 'FAIL'} — ${fleet.detail}`);
  const independence = independenceCheck();
  console.log(`[audit] independence: ${independence.ok ? 'PASS' : 'FAIL'} — ${independence.detail}`);

  const nodesMeta = [];
  for (let i = 1; i <= COUNT; i++) nodesMeta.push(idFor(i));

  console.log('[audit] inventory + load probes…');
  const nodes = await mapPool(nodesMeta, PARALLEL, async (node) => {
    const inv = inventory(node);
    let load = {
      ok: false,
      probes: {
        info: { ok: false, exit: null, ms: 0, stdout: '', stderr: 'skipped' },
        selftest: { ok: false, exit: null, ms: 0, stdout: '', stderr: 'skipped' },
        bell: { ok: false, exit: null, ms: 0, stdout: '', stderr: 'skipped' }
      }
    };
    if (inv.keys['qvm/cli.py']) {
      load = await loadProbe(node, py);
    } else {
      load.probes.info.stderr = 'missing qvm/cli.py';
      load.probes.selftest.stderr = 'missing qvm/cli.py';
      load.probes.bell.stderr = 'missing qvm/cli.py';
    }
    const overall_ok = inv.ok && load.ok;
    console.log(`[audit] ${node.id} inv=${inv.ok ? 'PASS' : 'FAIL'} load=${load.ok ? 'PASS' : 'FAIL'} files=${inv.files}`);
    return {
      id: node.id,
      code: node.code,
      inventory: inv,
      load,
      overall_ok
    };
  });

  const failures = nodes.filter((n) => !n.overall_ok).map((n) => n.id);
  const report = {
    date_pt: nowPtLabel(),
    date_iso: new Date().toISOString(),
    harbor_root: HARBOR,
    parallel: PARALLEL,
    python: `${py.cmd} ${py.prefix.join(' ')}`.trim(),
    independence,
    fleet,
    counts: {
      inventory_pass: nodes.filter((n) => n.inventory.ok).length,
      load_pass: nodes.filter((n) => n.load.ok).length,
      overall_pass: nodes.filter((n) => n.overall_ok).length
    },
    failures,
    nodes
  };

  fs.mkdirSync(path.dirname(OUT_MD), { recursive: true });
  fs.writeFileSync(OUT_JSON, JSON.stringify(report, null, 2) + '\n');
  fs.writeFileSync(OUT_MD, buildMarkdown(report));
  console.log(`[audit] wrote ${OUT_MD}`);
  console.log(`[audit] wrote ${OUT_JSON}`);
  console.log(`[audit] overall ${report.counts.overall_pass}/${COUNT} pass; failures=${failures.join(',') || 'none'}`);
  process.exit(failures.length === 0 && independence.ok && fleet.ok ? 0 : 1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
