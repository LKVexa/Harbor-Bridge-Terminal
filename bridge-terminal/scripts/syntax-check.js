'use strict';

/**
 * Lightweight syntax gate: parse-checks every .js in the project with
 * `node --check`. Run with `npm run check`. Exits non-zero on the first error.
 */

const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');
const SKIP = new Set(['node_modules', 'dist', '.git']);

function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    if (SKIP.has(name)) continue;
    const full = path.join(dir, name);
    const st = fs.statSync(full);
    if (st.isDirectory()) walk(full, out);
    else if (name.endsWith('.js')) out.push(full);
  }
  return out;
}

let ok = 0, bad = 0;
for (const file of walk(ROOT)) {
  try {
    execFileSync(process.execPath, ['--check', file], { stdio: 'pipe' });
    ok++;
  } catch (err) {
    bad++;
    console.error('✗ ' + path.relative(ROOT, file));
    console.error(String(err.stderr || err.message).trim());
  }
}

console.log(`\nsyntax-check: ${ok} ok, ${bad} failed`);
process.exit(bad ? 1 : 0);
