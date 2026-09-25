'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),net=require('node:net');
const {spawn}=require('node:child_process');const {Client,sleep}=require('../helpers');const {resolvePython}=require('../../tools/start-ship');
async function freePort(){const s=net.createServer();await new Promise(r=>s.listen(0,'127.0.0.1',r));const p=s.address().port;await new Promise(r=>s.close(r));return p;}
test('real launcher issues hashed credential, authenticates local socket, and busy-port rotation leaves credential unchanged',{timeout:30000},async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'uc-launch-'));const source=path.resolve(__dirname,'../..');fs.cpSync(source,path.join(dir,'vws'),{recursive:true,filter:p=>!p.includes('node_modules')&&!p.includes('.vws-local')});fs.writeFileSync(path.join(dir,'uc.py'),'print("fixture-ship-ready")');
 const port=await freePort();const script=path.join(dir,'vws/tools/start-ship.js');const env={...process.env,UC_PYTHON:resolvePython(),VWS_LOG:'silent'};
 let child,c,stdout='',stderr='';
 try{
  child=spawn(process.execPath,[script,'--port',String(port),'--no-browser'],{env,stdio:['ignore','pipe','pipe'],windowsHide:true});child.stdout.on('data',b=>{stdout+=b;});child.stderr.on('data',b=>{stderr+=b;});
  let token;for(let n=0;n<200;n++){token=stdout.match(/\n([A-Za-z0-9_-]{43})\n/)?.[1];if(token)break;if(child.exitCode!==null)throw new Error('launcher exited before ready: '+stderr);await sleep(25);}assert.ok(token,'one-time credential issued');
  const pf=path.join(dir,'_runs/vws/principals.json');const before=fs.readFileSync(pf);const principals=JSON.parse(before);assert.equal(principals[0].tokenSha256,crypto.createHash('sha256').update(token).digest('hex'));assert.ok(!before.includes(Buffer.from(token)));
  const origin=`http://127.0.0.1:${port}`;
  const ticket=await fetch(origin+'/api/ws-ticket',{method:'POST',headers:{Authorization:`Bearer ${token}`,Origin:origin}});
  assert.equal(ticket.status,200,'browser exchanges bearer for a single-use cookie');
  const setCookie=ticket.headers.get('set-cookie');assert.match(setCookie,/HttpOnly/);assert.match(setCookie,/SameSite=Strict/);
  const cookie=setCookie.split(';')[0];
  c=await new Client(`ws://127.0.0.1:${port}/ws/terminal`,null,{headers:{Origin:origin,Cookie:cookie}}).open();const out=await c.run('ship status; echo LAUNCH-DONE','LAUNCH-DONE\r\n');assert.match(out,/fixture-ship-ready/);assert.equal(c.type('hello')[0].payload.capabilities.shipControl,false);
  // async child: keep the first gateway responsive while the second probes its own runtime.
  const second=spawn(process.execPath,[script,'--port',String(port),'--new-token','--no-browser'],{env,stdio:'ignore',windowsHide:true});const rc=await new Promise(r=>second.once('close',r));assert.notEqual(rc,0);assert.deepEqual(fs.readFileSync(pf),before,'busy port must not revoke existing token');
 }finally{if(c)c.close();if(child&&child.exitCode===null){child.kill('SIGTERM');await Promise.race([new Promise(r=>child.once('close',r)),sleep(6000)]);if(child.exitCode===null)child.kill('SIGKILL');}fs.rmSync(dir,{recursive:true,force:true});}
});
