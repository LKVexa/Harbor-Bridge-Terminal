#!/usr/bin/env node
'use strict';
/** Create a principal entry for VWS_PRINCIPALS_FILE. The token is printed ONCE; only its SHA-256 is stored. */
const crypto = require('node:crypto');
const fs = require('node:fs');
const [file, sub, tenant, caps] = process.argv.slice(2);
if (!file || !sub || !tenant) { console.error('usage: node tools/mkprincipal.js <principals.json> <sub> <tenant> [terminal,fabric]'); process.exit(2); }
const token = crypto.randomBytes(32).toString('base64url');
let list = []; try { list = JSON.parse(fs.readFileSync(file, 'utf8')); } catch { /* new file */ }
list = list.filter((p) => !(p.sub === sub && p.tenant === tenant));
list.push({ sub, tenant, tokenSha256: crypto.createHash('sha256').update(token).digest('hex'), capabilities: (caps || 'terminal').split(',') });
fs.writeFileSync(file, JSON.stringify(list, null, 2) + '\n', { mode: 0o600 });
console.log(token);
