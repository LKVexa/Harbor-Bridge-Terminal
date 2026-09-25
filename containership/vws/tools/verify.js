#!/usr/bin/env node
'use strict';
/** Fail-closed local integrity: exact delivered inventory, bounded safe paths, no symlinks. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');const errors=[];let manifest;
try{manifest=JSON.parse(fs.readFileSync(path.join(root,'release','manifest.json'),'utf8'));}catch(e){console.error('Manifest unreadable: '+e.message);process.exit(2);}
const seen=new Set();
for(const f of manifest.files||[]){
 if(typeof f.path!=='string'||f.path.includes('\\')||f.path.startsWith('/')||f.path.split('/').some(x=>!x||x==='.'||x==='..')||seen.has(f.path)){errors.push('invalid/duplicate path');continue;}seen.add(f.path);
 let p=root;let invalid=false;for(const part of f.path.split('/')){p=path.join(p,part);try{if(fs.lstatSync(p).isSymbolicLink()){invalid=true;break;}}catch{invalid=true;break;}}
 if(invalid||!fs.statSync(p).isFile()){errors.push('missing/link '+f.path);continue;}
 const b=fs.readFileSync(p);if(b.length!==f.bytes||crypto.createHash('sha256').update(b).digest('hex')!==f.sha256)errors.push('mismatch '+f.path);
}
const extra=[];
(function walk(d){for(const n of fs.readdirSync(d)){const p=path.join(d,n),rel=path.relative(root,p).split(path.sep).join('/');if(rel==='release/manifest.json'||/^(\.vws-local|node_modules|dist|\.git)(\/|$)/.test(rel))continue;const st=fs.lstatSync(p);if(st.isSymbolicLink()){errors.push('link '+rel);continue;}if(st.isDirectory())walk(p);else if(!seen.has(rel))extra.push(rel);}})(root);
console.log(JSON.stringify({candidate:manifest.candidate,files:seen.size,failed:errors.length,unlisted:extra.length,status:errors.length||extra.length?'FAIL':'PASS',errors:errors.slice(0,20),extra:extra.slice(0,20)},null,2));process.exit(errors.length||extra.length?1:0);
