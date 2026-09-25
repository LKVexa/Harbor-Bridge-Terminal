'use strict';

/**
 * SPIRAL — QVM CLI runner for a single Qnode full copy.
 * Spawns `python -m qvm.cli …` with PYTHONPATH = that copy's root and
 * cwd = the copy root (QN-XX). Each QN-XX is an independent QVM tree.
 */

const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');

function resolvePython() {
  if (process.env.PYTHON) return process.env.PYTHON;
  return process.platform === 'win32' ? 'py' : 'python3';
}

/**
 * @param {object} o
 * @param {string} o.productRoot   QN-XX copy root (contains qvm/cli.py)
 * @param {string} o.instanceDir   QN-XX directory (same as productRoot for full copies)
 * @param {string[]} o.argv        args after `qvm.cli`
 * @param {{write:(s:string)=>void}} o.stdout
 * @param {{write:(s:string)=>void}} o.stderr
 * @param {AbortSignal} [o.signal]
 * @param {object} [o.env]
 * @returns {Promise<number>}
 */
function runQvm(o) {
  return new Promise((resolve) => {
    const productRoot = o.productRoot || o.instanceDir;
    const cli = path.join(productRoot, 'qvm', 'cli.py');
    if (!fs.existsSync(cli)) {
      o.stderr.write(`\x1b[31mqnode: QVM copy CLI missing at ${cli}\x1b[0m\n`);
      return resolve(127);
    }
    const cwd = o.instanceDir || productRoot;
    try { fs.mkdirSync(path.join(cwd, 'runtime'), { recursive: true }); } catch { /* ignore */ }

    const py = resolvePython();
    const usePyLauncher = py === 'py' || /[/\\]py(\.exe)?$/i.test(py);
    const args = usePyLauncher
      ? ['-3', '-m', 'qvm.cli', ...o.argv]
      : ['-m', 'qvm.cli', ...o.argv];

    const env = {
      ...(o.env || process.env),
      PYTHONPATH: productRoot + (process.env.PYTHONPATH ? path.delimiter + process.env.PYTHONPATH : ''),
      QNODE_HOME: o.instanceDir || productRoot,
      QNODE_ID: path.basename(o.instanceDir || productRoot)
    };

    let child;
    try {
      child = spawn(py, args, {
        cwd,
        env,
        shell: false,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe']
      });
    } catch (err) {
      if (usePyLauncher) {
        try {
          child = spawn(process.env.PYTHON || 'python', ['-m', 'qvm.cli', ...o.argv], {
            cwd, env, shell: false, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe']
          });
        } catch (err2) {
          o.stderr.write(`\x1b[31mqnode: cannot start Python: ${err2.message}\x1b[0m\n`);
          return resolve(127);
        }
      } else {
        o.stderr.write(`\x1b[31mqnode: cannot start ${py}: ${err.message}\x1b[0m\n`);
        return resolve(127);
      }
    }

    const onAbort = () => { try { child.kill('SIGINT'); } catch { /* noop */ } };
    if (o.signal) {
      if (o.signal.aborted) onAbort();
      else o.signal.addEventListener('abort', onAbort, { once: true });
    }

    const { StringDecoder } = require('node:string_decoder');
    const pump = (stream, sink) => {
      const dec = new StringDecoder('utf8');
      stream.on('data', (b) => sink.write(dec.write(b)));
      stream.on('end', () => { const t = dec.end(); if (t) sink.write(t); });
    };
    pump(child.stdout, o.stdout);
    pump(child.stderr, o.stderr);

    child.on('error', (err) => {
      o.stderr.write(`\x1b[31mqnode: ${err.message}\x1b[0m\n`);
      resolve(127);
    });
    child.on('close', (code) => resolve(code == null ? 1 : code));
  });
}

module.exports = { runQvm, resolvePython };
