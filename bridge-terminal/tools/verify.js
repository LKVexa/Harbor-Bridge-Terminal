#!/usr/bin/env node
'use strict';
/** Verify every file listed in release/manifest.json by SHA-256 and report files that are present but unlisted. Offline; installs nothing. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const mf = path.join(root, 'release', 'manifest.json');
if (!fs.existsSync(mf)) { console.error('release/manifest.json not found'); process.exit(2); }
const manifest = JSON.parse(fs.readFileSync(mf, 'utf8'));
let bad = 0;
for (const f of manifest.files) {
  const p = path.join(root, f.path);
  if (!fs.existsSync(p)) { console.error('MISSING  ' + f.path); bad++; continue; }
  const h = crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
  if (h !== f.sha256) { console.error('MISMATCH ' + f.path); bad++; }
}
const listed = new Set(manifest.files.map((f) => f.path));
const extra = [];
(function walk(d) { for (const n of fs.readdirSync(d)) { const p = path.join(d, n); const rel = path.relative(root, p).split(path.sep).join('/'); if (rel === 'release/manifest.json' || /^(\.vws-local|node_modules|dist|\.git)(\/|$)/.test(rel)) continue; if (fs.statSync(p).isDirectory()) walk(p); else if (!listed.has(rel)) extra.push(rel); } })(root);
console.log(JSON.stringify({ candidate: manifest.candidate, files: manifest.files.length, failed: bad, unlisted: extra.length, status: bad ? 'FAIL' : 'PASS' }, null, 2));
if (extra.length) console.error('unlisted files:\n  ' + extra.slice(0, 20).join('\n  '));
process.exit(bad ? 1 : 0);
