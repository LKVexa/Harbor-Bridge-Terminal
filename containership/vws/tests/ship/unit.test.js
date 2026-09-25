'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { vetArgv } = require('../../ship/policy');
const { ShipBroker, childEnv } = require('../../ship/broker');
const { load } = require('../../gateway/config');
const { parse, resolvePython, noLinks } = require('../../tools/start-ship');
const { createIdentity } = require('../../gateway/auth');
const logger = { info(){}, warn(){}, error(){} };
const python = resolvePython();
const id = () => crypto.randomBytes(12).toString('hex');
const wait = n => new Promise(r => setTimeout(r,n));
function fixture(body, over={}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(),'ucvws-'));
  fs.writeFileSync(path.join(root,'uc.py'), body);
  const b = new ShipBroker({shipRoot:root,python,shipControl:false,shipOutputBytes:8192,shipReadMs:3000,shipControlMs:3000,...over},logger);
  return {root,b,async close(){await b.close();fs.rmSync(root,{recursive:true,force:true});}};
}
test('read command vocabulary is canonical and does not authorize mutation',()=>{
  for(const argv of [['status'],['berths'],['capabilities'],['doctor'],['lifecycle'],['lifecycle','vm_small'],['fabric','status','vm_small'],['workflow','status'],['vws-workflow','status'],['onebit-workflow','status'],['master-workflow','status'],['platform','status'],['platform','kernel'],['onebit','status'],['recover','list']]) assert.equal(vetArgv(argv).mutation,false);
  assert.throws(()=>vetArgv(['verify']));
  assert.throws(()=>vetArgv(['run','vm_small','--sealed','--generation','1']));
});
test('control is allowlisted; executions require positive generation and capped ticks',()=>{
  assert.deepEqual(vetArgv(['verify','vm_small'],{control:true}).argv,['verify','vm_small','--quick']);
  assert.equal(vetArgv(['run','vm_small','--sealed','--generation','2'],{control:true}).mutation,true);
  assert.throws(()=>vetArgv(['verify'],{control:true}),/one berth/);
  assert.deepEqual(vetArgv(['run','vm_small','--ticks','1','--generation','2'],{control:true}).argv,['run','vm_small','--ticks','1','--generation','2','--no-view']);
  for(const a of [['run','vm_small','--sealed'],['run','vm_small','--ticks','11','--generation','2'],['run','vm_small','--sealed','--generation','0'],['run','vm_small','--sealed','--generation','9007199254740992'],['build'],['load','vm_small'],['seal'],['recover','apply']]) assert.throws(()=>vetArgv(a,{control:true}));
});
test('injection, paths, extra flags, and malformed argv are refused',()=>{
  for(const a of [[],null,['status;whoami'],['status','&&'],['lifecycle','../vm_small'],['lifecycle','C:\\x'],['lifecycle','$(id)'],['status','--root'],['status','\n'],['run',42],Array(9).fill('a')]) assert.throws(()=>vetArgv(a,{control:true}));
});
test('Python child environment excludes credentials and preload variables',()=>{
  const env=childEnv({PATH:'/bin',SystemRoot:'X',VWS_TOKEN:'secret',NODE_OPTIONS:'evil',PYTHONPATH:'evil',HOME:'secret'});
  assert.equal(env.PATH,'/bin'); for(const k of ['VWS_TOKEN','NODE_OPTIONS','PYTHONPATH','HOME']) assert.equal(env[k],undefined);
  assert.equal(env.UC_VWS_CHILD,'1');
});
test('launcher arguments validate ports, explicit modes and unknown options',()=>{
  assert.equal(parse([]).control,false);assert.equal(parse(['--control','--port','12345','--no-browser']).control,true);
  for(const a of [['--port','0'],['--port','65536'],['--port'],['--root','/tmp'],['--unknown']]) assert.throws(()=>parse(a));
});
test('integrated config refuses public bind, dev auth, relative Python, legacy bridge and snapshots',()=>{
  const env={VWS_SHIP_ROOT:path.resolve(__dirname,'../../..'),PYTHON:python,VWS_HOST:'127.0.0.1',VWS_AUTH:'static-file',VWS_PRINCIPALS_FILE:'/not/needed'};
  assert.equal(load(env).shipControl,false);
  for(const over of [{VWS_HOST:'0.0.0.0'},{VWS_AUTH:'none-loopback-dev'},{PYTHON:'python'},{VWS_FABRIC:'1'},{VWS_SNAPSHOTS:'1'},{VWS_PROFILE:'PERSISTENT'}]) assert.throws(()=>load({...env,...over}));
});
test('exact credential revocation is not rescued by a second credential for same identity',()=>{
  const d=fs.mkdtempSync(path.join(os.tmpdir(),'uc-auth-')), f=path.join(d,'p.json');
  const one='a'.repeat(40),two='b'.repeat(40),hash=t=>crypto.createHash('sha256').update(t).digest('hex');
  const entries=[one,two].map(token=>({sub:'alice',tenant:'acme',tokenSha256:hash(token),capabilities:['terminal','ship.read']}));
  fs.writeFileSync(f,JSON.stringify(entries)); const identity=createIdentity({auth:'static-file',principalsFile:f},logger); const p=identity.authenticate(one);assert.ok(p);
  entries[0].revoked=true;fs.writeFileSync(f,JSON.stringify(entries));fs.utimesSync(f,new Date(),new Date(Date.now()+2000));
  assert.equal(identity.stillValid(p),false);assert.ok(identity.authenticate(two));fs.rmSync(d,{recursive:true,force:true});
});
test('broker executes canonical isolated Python and captures bounded output',async()=>{
  const x=fixture('import sys,os,json\nprint(json.dumps({"argv":sys.argv[1:],"isolated":sys.flags.isolated,"child":os.environ.get("UC_VWS_CHILD")}))');
  try {const r=await x.b.run('s',id(),['status']);assert.equal(r.code,0);const j=JSON.parse(r.stdout);assert.deepEqual(j.argv,['status']);assert.equal(j.isolated,1);assert.equal(j.child,'1');assert.equal(x.b.telemetry().active,0);}finally{await x.close();}
});
test('broker denies control at the gateway even if worker asks for it',async()=>{
  const x=fixture('print("should not run")');try{assert.throws(()=>x.b.run('s',id(),['verify'],{control:true}));assert.equal(x.b.stats.started,0);}finally{await x.close();}
});
test('broker output overflow terminates without exceeding combined capture cap',async()=>{
  const x=fixture('import sys,time\nsys.stdout.write("x"*50000);sys.stdout.flush();time.sleep(4)');
  try{const r=await x.b.run('s',id(),['status']);assert.equal(r.outcome,'OUTPUT_LIMIT');assert.equal(r.code,125);assert.ok(r.stdout.length+r.stderr.length<=8192);}finally{await x.close();}
});
test('broker deadline kills a stalled operation',async()=>{
  const x=fixture('import time\ntime.sleep(30)',{shipReadMs:100});
  try{const r=await x.b.run('s',id(),['status']);assert.equal(r.outcome,'DEADLINE');assert.equal(r.code,124);}finally{await x.close();}
});
test('broker concurrency refuses rather than queues; ownership restricts cancellation',async()=>{
  const x=fixture('import time\ntime.sleep(30)');
  try{const op=id(),job=x.b.run('alice',op,['status']);assert.throws(()=>x.b.run('bob',id(),['status']),/busy/);x.b.cancel('bob',op);assert.equal(x.b.telemetry().active,1);x.b.cancelOwner('alice');const r=await job;assert.equal(r.outcome,'CANCELLED');assert.equal(r.code,130);}finally{await x.close();}
});
test('broker shutdown cancels active job and rejects future work',async()=>{
  const x=fixture('import time\ntime.sleep(30)');const job=x.b.run('s',id(),['status']);await x.b.close();assert.equal((await job).outcome,'CANCELLED');assert.throws(()=>x.b.run('s',id(),['status']));await x.close();
});
test('launcher link traversal is refused before credential writes',{skip:process.platform==='win32'?'native Windows symlink privileges not assumed':false},()=>{
  const d=fs.mkdtempSync(path.join(os.tmpdir(),'uc-link-'));fs.symlinkSync(os.tmpdir(),path.join(d,'link'));assert.throws(()=>noLinks(path.join(d,'link','p.json')));fs.rmSync(d,{recursive:true,force:true});
});
test('ship bridge schema validates arrays and rejects oversized or untyped arguments',()=>{
 const {validateRecord,encodeRecord,FrameDecoder}=require('../../protocol/bridge');
 const valid={t:'ship.request',id:'a'.repeat(24),argv:['run','vm_small','--sealed','--generation','1']};
 assert.deepEqual(validateRecord(valid,'worker_to_gateway'),valid);
 for(const argv of [[],Array(9).fill('a'),['x'.repeat(129)],[42],{},'status'])assert.throws(()=>validateRecord({...valid,argv},'worker_to_gateway'));
 assert.throws(()=>validateRecord({...valid,root:'/tmp'},'worker_to_gateway'));
 let got;const f=new FrameDecoder({direction:'worker_to_gateway',onRecord:r=>{got=r;},onError:e=>{throw e;}});f.push(encodeRecord(valid,'worker_to_gateway'));assert.deepEqual(got,valid);assert.equal(f.end(),'clean');
});

test('pixel inspection is read-only and exact; pixel writes never cross the bridge',()=>{
 for(const a of [['pixels','status'],['pixels','inspect','vm_small','DF_Small'],['pixels','cell','vm_small','DF_Small','3','57'],['tiff-workflow','status'],['onebit-workflow','status'],['master-workflow','status'],['platform','status'],['platform','kernel'],['onebit','status'],['onebit','tiff-read','vm_small','DF_Small','3']]) assert.equal(vetArgv(a).mutation,false);
 for(const a of [['pixels','cell','vm_small','DF_Small','4','0'],['pixels','cell','vm_small','DF_Small','0','58'],['pixels','inspect','vm_small','OTHER'],['pixels','paint','vm_small','DF_Small','0','0','4'],['pixels','checkpoint','vm_small','DF_Small'],['pixels','export-gif','vm_small','DF_Small'],['onebit','tiff-put','vm_small','DF_Small','0','packet.bin']]) assert.throws(()=>vetArgv(a,{control:true}));
});
