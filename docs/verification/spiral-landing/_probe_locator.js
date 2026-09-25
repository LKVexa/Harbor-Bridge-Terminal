const path = require('path');
const fs = require('fs');
const harbor = process.env.HARBOR_ROOT || path.resolve(__dirname, '../../..');
const { QnodeLocator } = require(path.join(harbor, 'bridge-terminal/src/main/spiral/qnodes/locator.js'));
const { DFLocator } = require(path.join(harbor, 'bridge-terminal/src/main/spiral/dfabric/locator.js'));
const outDir = path.join(harbor, 'docs', 'verification', 'spiral-landing');
const started = Date.now();
const qLoc = new QnodeLocator({ appDir: path.join(harbor, 'bridge-terminal') });
const q = qLoc.roster();
const dfLoc = new DFLocator({ envRoot: () => process.env.DF_ROOT });
let df = { root: null, roster: [], fabricDir: null, error: null };
try {
  df.root = dfLoc.root();
  df.roster = dfLoc.roster();
  df.fabricDir = dfLoc.fabricDir();
} catch (e) { df.error = e.message; }
const dfCodes = [
  { code: 'ns', kind: 'df-node', id: 'N_SMALL', key: 'small' },
  { code: 'nm', kind: 'df-node', id: 'N_MEDIUM', key: 'medium' },
  { code: 'nl', kind: 'df-node', id: 'N_LARGE', key: 'large' },
  { code: 'nx', kind: 'df-node', id: 'N_XLARGE', key: 'xlarge' },
  { code: 'nf', kind: 'df-fabric', id: 'DF_Fabric', key: null }
];
const board = dfCodes.map(c => {
  let operability, runtime;
  if (!df.root) { operability = 'unbound'; runtime = '-'; }
  else if (c.kind === 'df-fabric') {
    const p = df.fabricDir; operability = p ? 'present' : 'absent'; runtime = p ? 'fabric' : '-';
  } else {
    const n = df.roster.find(x => x.key === c.key);
    if (!n || !n.present) { operability = 'absent'; runtime = '-'; }
    else if (n.built) { operability = 'built'; runtime = 'vm/.build'; }
    else { operability = 'not built'; runtime = 'present'; }
  }
  return { code: c.code, kind: c.kind, id: c.id, operability, runtime };
});
const src = fs.readFileSync(path.join(harbor, 'bridge-terminal/src/main/spiral/commands/qnode.js'), 'utf8');
const expectedQn = Array.from({length:50}, (_,i) => 'qn' + String(i+1).padStart(2,'0'));
const expectedDf = ['ns','nm','nl','nx','nf'];
const focusCheck = {
  all_50_qn_tokens_in_source: expectedQn.every(c => src.includes(c)),
  df_codes_in_source: expectedDf.every(c => src.includes(c)),
  DF_FOCUS_block_present: /DF_FOCUS/.test(src),
  note: 'static source scan of commands/qnode.js for focus code registration (not a live SPIRAL REPL)'
};
const result = {
  generated_pt: new Date().toLocaleString('en-US', { timeZone: 'America/Los_Angeles' }) + ' PT',
  method: 'Same QnodeLocator + DFLocator classes used by SpiralKernel._banner; run outside session with HARBOR_ROOT/QNODE_ROOT/DF_ROOT',
  elapsed_ms: Date.now() - started,
  env: { HARBOR_ROOT: harbor, QNODE_ROOT: process.env.QNODE_ROOT || null, DF_ROOT: process.env.DF_ROOT || null },
  qnodes: {
    root: q.root,
    count: q.count,
    operable: q.operable,
    version: q.version,
    product_bound: q.product_bound,
    nodes_sample: q.nodes.filter((_,i)=>[0,24,49].includes(i)).map(n => ({ code: n.code, id: n.id, operable: n.operable, present: n.present, version: n.version })),
    inoperable_count: q.nodes.filter(n => !n.operable).length,
    inoperable: q.nodes.filter(n => !n.operable).map(n => ({ code: n.code, present: n.present }))
  },
  df_board: board,
  df_meta: { root: df.root, fabricDir: df.fabricDir, roster_count: (df.roster||[]).length, error: df.error },
  focus_command_source_check: focusCheck
};
fs.writeFileSync(path.join(outDir, 'fleet-board-locator.json'), JSON.stringify(result, null, 2));
console.log(JSON.stringify({ operable: q.operable+'/'+q.count, version: q.version, df: board.map(b => b.code+':'+b.operability), focusCheck, elapsed_ms: result.elapsed_ms }, null, 2));


