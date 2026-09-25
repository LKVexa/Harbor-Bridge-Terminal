'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawnSync}=require('node:child_process');const {startGateway,Client}=require('../helpers');const {resolvePython}=require('../../tools/start-ship');
const root=path.resolve(__dirname,'../../..'),python=resolvePython();
const options={skip:process.env.UC_EXECUTION_TESTS==='1'?false:'explicit UC_EXECUTION_TESTS=1 and locally built engines required; test mutates the selected candidate',timeout:240000};
function generation(){const p=spawnSync(python,['-I','-B',path.join(root,'uc.py'),'lifecycle','vm_small'],{encoding:'utf8',timeout:20000});assert.equal(p.status,0,p.stderr);return JSON.parse(p.stdout).workloads[0]?.generation||1;}
test('actual control WebSocket: stale generation refused, sealed witness agrees, one TIFF tick succeeds',options,async()=>{
 const h=await startGateway({},{VWS_SHIP_ROOT:root,VWS_SHIP_CONTROL:'1',PYTHON:python,VWS_HOST:'127.0.0.1'});h.principals[0].capabilities.push('ship.read','ship.control');fs.writeFileSync(h.pf,JSON.stringify(h.principals));fs.utimesSync(h.pf,new Date(),new Date(Date.now()+1000));let c;
 try{
  c=await new Client(h.url,h.tokens.alice).open(160,50);assert.equal(c.type('hello')[0].payload.capabilities.shipControl,true);
  const g=generation();let out=await c.run(`ship run vm_small --sealed --generation ${g+1}; echo STALE-DONE`,'STALE-DONE\r\n',30000);assert.match(out,/stale generation refused before mutation/);assert.equal(generation(),g);
  out=await c.run(`ship run vm_small --sealed --generation ${g}; echo SEALED-DONE`,'SEALED-DONE\r\n',180000);assert.match(out,/CROSS_NODE_DIFFERENTIAL_AGREEMENT/);assert.match(out,/"matches_pinned": true/);
  const g2=generation();out=await c.run(`ship run vm_small --ticks 1 --generation ${g2}; echo TICK-DONE`,'TICK-DONE\r\n',180000);assert.match(out,/TICK_OK/);assert.match(out,/unanimous=true|"unanimous": true/i);
  const dir=process.env.VWS_TEST_OUTPUT||path.join(root,'_runs','vws-tests');fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,'ship-execution-observation.json'),JSON.stringify({schema:'UC/VWS_EXECUTION/1',staleRefused:true,sealedWitnessAgreement:true,pinnedWitnessMatched:true,oneTick:'TICK_OK',generationBefore:g,generationAfter:generation(),childMemoryLimit:'NOT_ENFORCED'},null,2)+'\n');
 }finally{if(c)c.close();await h.stop();}
});
