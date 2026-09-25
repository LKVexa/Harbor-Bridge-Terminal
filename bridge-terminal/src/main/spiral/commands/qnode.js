'use strict';

/**
 * SPIRAL built-ins — Qnode fleet (`qn` / `qnode` / `qn01`…`qn50`)
 * plus DF container short focus codes (`ns` `nm` `nl` `nx` `nf`)
 * and Harbor focus dispatcher (`__hf__`).
 *
 * Focus: typing a short code with no args enters interactive focus
 * (HARBOR_FOCUS + PS1). While focused, info/run/bell/… route through __hf__.
 */

const path = require('node:path');
const { QnodeLocator, COUNT } = require('../qnodes/locator');
const { runQvm } = require('../qnodes/runner');
const { DFLocator } = require('../dfabric/locator');
const { runCli, PYTHON } = require('../dfabric/runner');
const { fail, padRight } = require('./util');

const DF_FOCUS = {
  ns: { kind: 'df-node', key: 'small', id: 'N_SMALL', label: 'DF_Small' },
  nm: { kind: 'df-node', key: 'medium', id: 'N_MEDIUM', label: 'DF_Medium' },
  nl: { kind: 'df-node', key: 'large', id: 'N_LARGE', label: 'DF_Large' },
  nx: { kind: 'df-node', key: 'xlarge', id: 'N_XLARGE', label: 'DF_Xtra_Large' },
  nf: { kind: 'df-fabric', key: null, id: 'DF_Fabric', label: 'DF_Fabric' }
};

const QN_FOCUS_CMDS = new Set([
  'info', 'capabilities', 'resources', 'run', 'bell', 'selftest',
  'status', 'where', 'help', 'detach', 'validate'
]);
const DF_FOCUS_CMDS = new Set([
  'status', 'build', 'verify', 'run', 'where', 'doctor', 'help', 'detach', 'attest'
]);

function appDir() {
  try { return path.resolve(__dirname, '..', '..', '..', '..'); } catch { return undefined; }
}

function makeQLoc(ctx) {
  return new QnodeLocator({
    envRoot: () => ctx.env.get('QNODE_ROOT'),
    envHarbor: () => ctx.env.get('HARBOR_ROOT'),
    appDir: appDir()
  });
}

function makeDFLoc(ctx) {
  const pol = ctx.host && ctx.host.fabricPolicy;
  if (pol) return new DFLocator({ fixedRoot: pol.root });
  return new DFLocator({
    envRoot: () => ctx.env.get('DF_ROOT'),
    resourcesPath: process.resourcesPath,
    appDir: (() => { try { return path.dirname(process.execPath); } catch { return undefined; } })()
  });
}

function focusPrompt(code) {
  return `\x1b[38;5;208m${code}\x1b[0m \x1b[38;5;44m›\x1b[0m `;
}

function enterFocus(ctx, code, headerLines) {
  if (!ctx.env.get('HARBOR_PS1_SAVE')) {
    ctx.env.set('HARBOR_PS1_SAVE', ctx.env.get('PS1') || '');
  }
  ctx.env.set('HARBOR_FOCUS', code);
  ctx.env.set('PS1', focusPrompt(code));
  for (const line of headerLines) ctx.stdout.write(line + '\n');
  ctx.stdout.write(`\x1b[2mfocused · type a command below, or\x1b[0m \x1b[38;5;75mexit\x1b[0m\x1b[2m/\x1b[0m\x1b[38;5;75mdetach\x1b[0m\x1b[2m to leave\x1b[0m\n`);
  return 0;
}

function leaveFocus(ctx) {
  const code = ctx.env.get('HARBOR_FOCUS');
  const saved = ctx.env.get('HARBOR_PS1_SAVE');
  ctx.env.set('HARBOR_FOCUS', '');
  if (saved !== undefined && saved !== null) ctx.env.set('PS1', saved);
  ctx.env.set('HARBOR_PS1_SAVE', '');
  ctx.stdout.write(`\x1b[38;5;79m✓\x1b[0m left focus${code ? ' ' + code : ''}\n`);
  return 0;
}

async function attachQnode(ctx, code) {
  const loc = makeQLoc(ctx);
  const node = loc.roster().nodes.find((n) => n.code === code);
  if (!node) return fail(ctx, code, `unknown qnode ${code}`);
  const lines = [
    `\x1b[1mQnode ${node.id}\x1b[0m  \x1b[2m(${code})\x1b[0m`,
    `  product   : ${node.product}${node.version ? ' · ' + node.version : ''}`,
    `  backend   : ${node.backend}`,
    `  operable  : ${node.operable ? '\x1b[38;5;114myes\x1b[0m' : '\x1b[31mno\x1b[0m'}${node.product_bound ? '' : ' \x1b[33m(product unbound — run scripts\\\\link-qvm.cmd)\x1b[0m'}`,
    `  path      : ${node.path || '—'}`,
    `  product   : ${loc.productRoot() || '—'}`,
    '',
    `\x1b[2mcommands:\x1b[0m info · capabilities · resources · run <circuit.json> · bell · selftest · status · where · exit`
  ];
  return enterFocus(ctx, code, lines);
}

async function attachDF(ctx, code) {
  const spec = DF_FOCUS[code];
  const loc = makeDFLoc(ctx);
  const root = loc.root();
  let present = false;
  let built = false;
  let p = null;
  if (spec.kind === 'df-fabric') {
    p = loc.fabricDir();
    present = !!p;
  } else {
    const roster = loc.roster();
    const n = roster.find((x) => x.key === spec.key);
    present = !!(n && n.present);
    built = !!(n && n.built);
    p = n && n.path;
  }
  const lines = [
    `\x1b[1mContainer ${spec.id}\x1b[0m  \x1b[2m(${code})\x1b[0m`,
    `  kind      : ${spec.kind}`,
    `  label     : ${spec.label}`,
    `  DF root   : ${root || '\x1b[31mnot bound\x1b[0m'}`,
    `  present   : ${present ? '\x1b[38;5;114myes\x1b[0m' : '\x1b[31mno\x1b[0m'}`,
    `  built     : ${spec.kind === 'df-fabric' ? '—' : (built ? '\x1b[38;5;114myes\x1b[0m' : '\x1b[33mno\x1b[0m')}`,
    `  path      : ${p || '—'}`,
    '',
    `\x1b[2mcommands:\x1b[0m status · build · verify · run · where · doctor · exit`
  ];
  return enterFocus(ctx, code, lines);
}

async function runQnodeSub(ctx, code, sub, rest) {
  const loc = makeQLoc(ctx);
  const dir = loc.nodeDir(code);
  const product = loc.productRoot();
  if (!dir) return fail(ctx, code, `instance directory missing for ${code}`);
  if (!product) return fail(ctx, code, 'QVM product unbound — run scripts\\link-qvm.cmd or set QVM_PRODUCT_ROOT');

  const argv = (() => {
    switch (sub) {
      case 'info': return ['info'];
      case 'capabilities': return ['capabilities'];
      case 'selftest': return ['selftest'];
      case 'validate':
        if (!rest[0]) { fail(ctx, code, 'usage: validate <program.json>'); return null; }
        return ['validate', rest[0]];
      case 'resources':
        if (!rest[0]) { fail(ctx, code, 'usage: resources <program.json>'); return null; }
        return ['resources', ...rest];
      case 'run':
        if (!rest[0]) { fail(ctx, code, 'usage: run <program.json> [--backend …] [--shots N]'); return null; }
        return ['run', ...rest];
      case 'bell': {
        const bell = path.join(product, 'examples', 'bell.json');
        return ['run', bell, '--shots', '1000', '--seed', '42'];
      }
      default:
        return null;
    }
  })();
  if (argv === null && ['validate', 'resources', 'run'].includes(sub)) return 1;
  if (!argv) return fail(ctx, code, `unknown focus command: ${sub}`);

  ctx.stdout.write(`\x1b[2m[${code}] $ python -m qvm.cli ${argv.join(' ')}\x1b[0m\n`);
  const rc = await runQvm({
    productRoot: product,
    instanceDir: dir,
    argv,
    stdout: ctx.stdout,
    stderr: ctx.stderr,
    signal: ctx.signal
  });
  if (sub === 'info' && rc === 0) {
    loc.writeProbe(code, { ok: true, cmd: 'info', version: loc.productVersion() });
  }
  return rc;
}

async function runDFSub(ctx, code, sub, rest) {
  const spec = DF_FOCUS[code];
  const loc = makeDFLoc(ctx);
  const root = loc.root();
  if (!root) return fail(ctx, code, 'no DF root — set DF_ROOT or run START_HARBOR.cmd');

  if (sub === 'where') {
    const p = spec.kind === 'df-fabric' ? loc.fabricDir() : loc.nodeDir(spec.key);
    ctx.stdout.write(`code ${code}  id ${spec.id}\nroot ${root}\npath ${p || '(absent)'}\n`);
    return p ? 0 : 1;
  }
  if (sub === 'status' || sub === 'doctor') {
    if (spec.kind === 'df-fabric') {
      const p = loc.fabricDir();
      ctx.stdout.write(`DF_Fabric ${p ? 'present' : 'ABSENT'}  ${p || ''}\n`);
      return p ? 0 : 1;
    }
    const n = loc.roster().find((x) => x.key === spec.key);
    ctx.stdout.write(`${spec.id} present=${n && n.present ? 'yes' : 'no'} built=${n && n.built ? 'yes' : 'no'}\n`);
    return n && n.present ? 0 : 1;
  }

  const cwd = spec.kind === 'df-fabric' ? loc.fabricDir() : loc.nodeDir(spec.key);
  if (!cwd) return fail(ctx, code, `${spec.label} not found under DF root`);

  const map = spec.kind === 'df-fabric'
    ? { build: 'fabric-build', verify: 'fabric-verify', run: 'fabric-run', attest: 'fabric-attest' }
    : { build: 'node-build', verify: 'node-verify', run: 'node-run', attest: 'node-attest' };
  const cli = map[sub];
  if (!cli) return fail(ctx, code, `unknown focus command: ${sub}`);

  const argv = [cli, ...rest];
  ctx.stdout.write(`\x1b[2m[${code}] $ ${PYTHON} adapter/dfabric/cli.py ${argv.join(' ')}\x1b[0m\n`);
  return runCli({ cwd, argv, stdout: ctx.stdout, stderr: ctx.stderr, signal: ctx.signal });
}

/** Harbor focus dispatcher — invoked by kernel when HARBOR_FOCUS is set. */
const hfCmd = {
  name: '__hf__',
  summary: 'internal harbor focus dispatcher',
  usage: '__hf__ <code> <sub> [...]',
  async run(ctx) {
    const code = (ctx.argv[0] || '').toLowerCase();
    const sub = (ctx.argv[1] || 'help').toLowerCase();
    const rest = ctx.argv.slice(2);

    if (sub === 'detach' || sub === 'exit') return leaveFocus(ctx);

    if (DF_FOCUS[code]) {
      if (sub === 'help') {
        ctx.stdout.write('DF focus: status | build | verify | run | where | doctor | exit\n');
        return 0;
      }
      return runDFSub(ctx, code, sub, rest);
    }

    if (/^qn\d{2}$/.test(code)) {
      if (sub === 'help') {
        ctx.stdout.write('Qnode focus: info | capabilities | resources | run <json> | bell | selftest | status | where | exit\n');
        return 0;
      }
      if (sub === 'status' || sub === 'where') {
        const loc = makeQLoc(ctx);
        const node = loc.roster().nodes.find((n) => n.code === code);
        if (!node) return fail(ctx, code, 'missing');
        ctx.stdout.write([
          `${node.id} (${code})`,
          `  operable : ${node.operable ? 'yes' : 'no'}`,
          `  path     : ${node.path}`,
          `  product  : ${loc.productRoot() || '(unbound)'}`,
          `  version  : ${node.version || '?'}`,
          ''
        ].join('\n'));
        return node.operable ? 0 : 1;
      }
      return runQnodeSub(ctx, code, sub, rest);
    }

    return fail(ctx, '__hf__', `unknown focus target: ${code}`);
  }
};

const qnCmd = {
  name: 'qn',
  aka: ['qnode'],
  summary: 'Qnode fleet: status, list, attach, run QVM',
  usage: 'qn <status|list|info|run|bell|attach|use|where|help> [qnNN|args…]',
  async run(ctx) {
    const loc = makeQLoc(ctx);
    const sub = (ctx.argv[0] || 'help').toLowerCase();

    switch (sub) {
      case 'help':
        ctx.stdout.write([
          '\x1b[1mQnode fleet (50 × QVM 8.1.0-alpha)\x1b[0m',
          '  \x1b[38;5;79mqn status\x1b[0m              fleet operability board',
          '  \x1b[38;5;79mqn list\x1b[0m                codes qn01…qn50',
          '  \x1b[38;5;79mqn where\x1b[0m               QNODE_ROOT + product link',
          '  \x1b[38;5;79mqn attach <qnNN>\x1b[0m       interactive focus (or type qnNN)',
          '  \x1b[38;5;79mqn info <qnNN>\x1b[0m         run qvm.cli info on instance',
          '  \x1b[38;5;79mqn run <qnNN> <json>\x1b[0m   run a circuit on instance',
          '  \x1b[38;5;79mqn bell <qnNN>\x1b[0m         bell-pair demo on instance',
          '  \x1b[38;5;79mqn use <path>\x1b[0m          bind QNODE_ROOT',
          '',
          '  containers: \x1b[38;5;75mns nm nl nx nf\x1b[0m   ·  qnodes: \x1b[38;5;75mqn01\x1b[0m…\x1b[38;5;75mqn50\x1b[0m',
          ''
        ].join('\n'));
        return 0;

      case 'use': {
        if (!ctx.argv[1]) return fail(ctx, 'qn', 'usage: qn use <path-to-qnodes>');
        const resolved = ctx.resolveHost ? ctx.resolveHost(ctx.argv[1]) : path.resolve(ctx.argv[1]);
        ctx.env.set('QNODE_ROOT', resolved);
        ctx.stdout.write(`\x1b[38;5;79m✓\x1b[0m QNODE_ROOT=${resolved}\n`);
        return 0;
      }

      case 'where': {
        const r = loc.root();
        const p = loc.productRoot();
        const h = loc.harborRoot();
        ctx.stdout.write([
          `\x1b[1mHarbor\x1b[0m     : ${h || '\x1b[31m(not found)\x1b[0m'}`,
          `QNODE_ROOT : ${r || '\x1b[31m(not found)\x1b[0m'}`,
          `product    : ${p || '\x1b[31m(unbound — scripts\\\\link-qvm.cmd)\x1b[0m'}`,
          `version    : ${loc.productVersion() || '—'}`,
          ''
        ].join('\n'));
        return r && p ? 0 : 1;
      }

      case 'list': {
        const roster = loc.roster();
        const codes = roster.nodes.map((n) => n.code);
        for (let i = 0; i < codes.length; i += 10) {
          ctx.stdout.write('  ' + codes.slice(i, i + 10).join('  ') + '\n');
        }
        ctx.stdout.write(`\n  \x1b[2m${roster.operable}/${roster.count} operable · type qnNN for interactive focus\x1b[0m\n`);
        return 0;
      }

      case 'status': {
        const roster = loc.roster();
        ctx.stdout.write(`\x1b[1mQnode fleet\x1b[0m  ${loc.summaryLine()}\n`);
        ctx.stdout.write(`  root    : ${roster.root || '\x1b[31munbound\x1b[0m'}\n`);
        ctx.stdout.write(`  product : ${roster.product || '\x1b[31munbound\x1b[0m'}\n\n`);
        for (let row = 0; row < 10; row++) {
          const parts = [];
          for (let col = 0; col < 5; col++) {
            const n = roster.nodes[row + col * 10];
            if (!n) continue;
            const mark = n.operable ? '\x1b[38;5;114mok\x1b[0m' : (n.present ? '\x1b[33m?\x1b[0m' : '\x1b[31m-\x1b[0m');
            parts.push(`${n.code} ${mark}`);
          }
          ctx.stdout.write('  ' + parts.join('   ') + '\n');
        }
        ctx.stdout.write('\n  \x1b[2mfocus: type qn07   containers: ns nm nl nx nf\x1b[0m\n');
        return roster.operable === roster.count ? 0 : 1;
      }

      case 'attach': {
        const code = (ctx.argv[1] || '').toLowerCase();
        if (!/^qn\d{2}$/.test(code)) return fail(ctx, 'qn', 'usage: qn attach qnNN');
        return attachQnode(ctx, code);
      }

      case 'info':
      case 'bell':
      case 'run':
      case 'capabilities':
      case 'selftest': {
        const code = (ctx.argv[1] || '').toLowerCase();
        if (!/^qn\d{2}$/.test(code)) return fail(ctx, 'qn', `usage: qn ${sub} qnNN` + (sub === 'run' ? ' <circuit.json>' : ''));
        const rest = ctx.argv.slice(2);
        return runQnodeSub(ctx, code, sub, rest);
      }

      default:
        // bare `qn qn07` → attach
        if (/^qn\d{2}$/.test(sub)) return attachQnode(ctx, sub);
        return fail(ctx, 'qn', `unknown subcommand: ${sub}`);
    }
  },
  complete(ctx, partial) {
    const base = ['status', 'list', 'info', 'run', 'bell', 'attach', 'use', 'where', 'help', 'capabilities', 'selftest'];
    const codes = [];
    for (let i = 1; i <= COUNT; i++) codes.push('qn' + String(i).padStart(2, '0'));
    return [...base, ...codes].filter((s) => s.startsWith(partial));
  }
};

/** Build qn01…qn50 first-class commands. */
function makeQnShort(code) {
  return {
    name: code,
    summary: `focus Qnode ${code.toUpperCase().replace('QN', 'QN-')}`,
    usage: `${code} [info|run|bell|…|exit]`,
    async run(ctx) {
      if (!ctx.argv.length) return attachQnode(ctx, code);
      const sub = ctx.argv[0].toLowerCase();
      if (sub === 'attach') return attachQnode(ctx, code);
      return runQnodeSub(ctx, code, sub, ctx.argv.slice(1));
    }
  };
}

function makeDfShort(code) {
  const spec = DF_FOCUS[code];
  return {
    name: code,
    summary: `focus container ${spec.id}`,
    usage: `${code} [status|build|verify|run|where|doctor|exit]`,
    async run(ctx) {
      if (!ctx.argv.length) return attachDF(ctx, code);
      const sub = ctx.argv[0].toLowerCase();
      if (sub === 'attach') return attachDF(ctx, code);
      if (sub === 'exit' || sub === 'detach') return leaveFocus(ctx);
      return runDFSub(ctx, code, sub, ctx.argv.slice(1));
    }
  };
}

const shorts = [];
for (let i = 1; i <= COUNT; i++) shorts.push(makeQnShort('qn' + String(i).padStart(2, '0')));
for (const c of Object.keys(DF_FOCUS)) shorts.push(makeDfShort(c));

module.exports = [qnCmd, hfCmd, ...shorts];
module.exports.QN_FOCUS_CMDS = QN_FOCUS_CMDS;
module.exports.DF_FOCUS_CMDS = DF_FOCUS_CMDS;
module.exports.DF_FOCUS = DF_FOCUS;
