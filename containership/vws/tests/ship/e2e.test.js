'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {startGateway,Client,sleep}=require('../helpers');
const {resolvePython}=require('../../tools/start-ship');
const python=resolvePython(),root=path.resolve(__dirname,'../../..');
async function gateway(backend,over={}){
 const h=await startGateway({workerBackend:backend,...over},{VWS_HOST:'127.0.0.1',VWS_SHIP_ROOT:over.shipRoot||root,PYTHON:python,VWS_SHIP_CONTROL:over.shipControl?'1':'0'});
 h.principals[0].capabilities.push('ship.read','ship.control');h.principals[1].capabilities.push('ship.read');
 fs.writeFileSync(h.pf,JSON.stringify(h.principals));fs.utimesSync(h.pf,new Date(),new Date(Date.now()+2000));return h;
}
for(const backend of ['thread','process']){
 test(`actual containership read commands over ${backend} WebSocket`,{timeout:30000},async()=>{
  const h=await gateway(backend);let c;
  try{
   c=await new Client(h.url,h.tokens.alice).open();assert.equal(c.type('hello')[0].payload.capabilities.ship,true);assert.equal(c.type('hello')[0].payload.capabilities.shipControl,false);
   const out=await c.run('ship capabilities; echo READ-DONE','READ-DONE\r\n');assert.match(out,/"uc_release": "UC-2\.7\.0"/);assert.match(out,/"bootable_guest": false/);
   const berths=await c.run('ship berths; echo BERTHS-DONE','BERTHS-DONE\r\n');assert.match(berths,/vm_small/);assert.match(berths,/vm_xtra_large/);
   const pixels=await c.run('ship pixels inspect vm_small DF_Small; echo PIXELS-DONE','PIXELS-DONE\r\n');assert.match(pixels,/UC\/PIXEL_INSPECT\/1/);assert.match(pixels,/blob_sha256/);
   const onebit=await c.run('ship onebit status; echo ONEBIT-DONE','ONEBIT-DONE\r\n');assert.match(onebit,/UC\/1BIT_CAPABILITIES\/1/);assert.match(onebit,/1-bit communication, not 1-bit cognition/);
   const flow=await c.run('ship onebit-workflow status; echo FLOW-DONE','FLOW-DONE\r\n');assert.match(flow,/275000/);assert.match(flow,/"phase_gates_closed": 0/);
   const master=await c.run('ship master-workflow status; echo MASTER-DONE','MASTER-DONE\r\n');assert.match(master,/375000/);assert.match(master,/source_tasks_promoted_pass/);
   const platform=await c.run('ship platform kernel; echo PLATFORM-DONE','PLATFORM-DONE\r\n');assert.match(platform,/UC\/KERNEL_CAPABILITIES\/1/);assert.match(platform,/UC\/PIXEL_KERNEL_ABI\/1/);
   const deny=await c.run('ship run vm_small --sealed --generation 1; echo DENY-DONE','DENY-DONE\r\n');assert.match(deny,/control|read.only|disabled/i);
   assert.ok(!h.logs.some(x=>String(x).includes(h.tokens.alice)),'credential must not be logged');
  }finally{if(c)c.close();await h.stop();}
 });
 test(`principal without ship.read has no ship command (${backend})`,{timeout:20000},async()=>{
  const h=await gateway(backend);let c;
  try{c=await new Client(h.url,h.tokens.nofab).open();assert.equal(c.type('hello')[0].payload.capabilities.ship,false);const out=await c.run('ship status; echo NO-SHIP-DONE','NO-SHIP-DONE\r\n');assert.match(out,/ship: command not found/);}finally{if(c)c.close();await h.stop();}
 });
}
test('control-enabled gateway still denies read-only principal', {timeout:20000},async()=>{
 const h=await gateway('thread',{shipControl:true});let c;
 try{c=await new Client(h.url,h.tokens.bob).open();assert.equal(c.type('hello')[0].payload.capabilities.shipControl,false);const out=await c.run('ship verify; echo LIMITED-DONE','LIMITED-DONE\r\n');assert.match(out,/control|disabled|read.only/i);const live=await (await fetch(h.http+'/live')).json();assert.equal(live.ship.started,0);}finally{if(c)c.close();await h.stop();}
});
test('Ctrl-C cancels gateway-owned Python job and returns terminal exit 130', {timeout:25000},async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'ucvws-cancel-'));fs.writeFileSync(path.join(temp,'uc.py'),'import time\ntime.sleep(60)');
 const h=await gateway('thread',{shipRoot:temp});let c;
 try{c=await new Client(h.url,h.tokens.alice).open();c.input('ship status\r');await c.until(async()=>false,1).catch(()=>{});
  for(let n=0;n<100;n++){const j=await (await fetch(h.http+'/live')).json();if(j.ship.active===1)break;await sleep(25);if(n===99)throw new Error('broker not started');}
  c.ctl('terminal.signal',{signal:'SIGINT'});const out=await c.run('echo RC-$?; echo CANCEL-DONE','CANCEL-DONE\r\n');assert.match(out,/RC-130/);
  const live=await (await fetch(h.http+'/live')).json();assert.equal(live.ship.active,0);assert.equal(live.ship.cancelled,1);
 }finally{if(c)c.close();await h.stop();fs.rmSync(temp,{recursive:true,force:true});}
});
test('disconnect cancels gateway job rather than orphaning it', {timeout:25000},async()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'ucvws-disconnect-'));fs.writeFileSync(path.join(temp,'uc.py'),'import time\ntime.sleep(60)');
 const h=await gateway('process',{shipRoot:temp});let c;
 try{c=await new Client(h.url,h.tokens.alice).open();c.input('ship status\r');let active=false;for(let n=0;n<100;n++){const j=await (await fetch(h.http+'/live')).json();if(j.ship.active===1){active=true;break;}await sleep(25);}assert.ok(active);c.close();
  let live;for(let n=0;n<100;n++){live=await (await fetch(h.http+'/live')).json();if(live.ship.active===0)break;await sleep(25);}assert.equal(live.ship.active,0);assert.equal(live.ship.cancelled,1);
 }finally{if(c)c.close();await h.stop();fs.rmSync(temp,{recursive:true,force:true});}
});
