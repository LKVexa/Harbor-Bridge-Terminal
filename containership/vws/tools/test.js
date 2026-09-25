#!/usr/bin/env node
'use strict';
// Portable file discovery: no cmd.exe glob expansion. A timeout is a failure, never a pass.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawn}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const ui=process.argv.includes('--ui');
const shipOnly=process.argv.includes('--ship');
const files=[];
function walk(p){for(const e of fs.readdirSync(p,{withFileTypes:true})){const q=path.join(p,e.name);if(e.isDirectory())walk(q);else if(e.name.endsWith('.test.js')&&(ui||e.name!=='browser.test.js'))files.push(q);}}
walk(path.join(root,'tests'));files.sort();
if(shipOnly){for(let i=files.length-1;i>=0;i--)if(!files[i].startsWith(path.join(root,'tests','ship')+path.sep))files.splice(i,1);}
const destination=process.env.VWS_TEST_OUTPUT||path.join(root,'..','_runs','vws-tests');fs.mkdirSync(destination,{recursive:true});
const results=[];let next=0;
async function one(file){
 const relative=path.relative(root,file).split(path.sep).join('/');const stem=relative.replace(/[^a-zA-Z0-9.-]/g,'_');const started=Date.now();
 const log=fs.openSync(path.join(destination,stem+'.tap'),'w');
 const child=spawn(process.execPath,['--test','--test-timeout=120000',file],{cwd:root,env:process.env,stdio:['ignore',log,log],windowsHide:true,shell:false,detached:process.platform!=='win32'});fs.closeSync(log);
 let timedOut=false,spawnError=null;
 const timer=setTimeout(()=>{timedOut=true;if(process.platform!=='win32'){try{process.kill(-child.pid,'SIGKILL');}catch{}}else{const k=spawn('taskkill',['/PID',String(child.pid),'/T','/F'],{stdio:'ignore',windowsHide:true});k.on('error',()=>child.kill());}},125000);
 const code=await new Promise(resolve=>{child.once('error',e=>{spawnError=e.code;resolve(69);});child.once('close',code=>resolve(code));});clearTimeout(timer);
 const text=fs.readFileSync(path.join(destination,stem+'.tap'),'utf8');
 const metric=k=>{const match=text.match(new RegExp('^# '+k+' (\\d+)$','m'));return match?Number(match[1]):null;};
 const record={file:relative,status:code===0&&!timedOut&&!spawnError?'PASS':'FAIL',exitCode:code,timedOut,spawnError,durationMs:Date.now()-started,tests:metric('tests'),pass:metric('pass'),fail:metric('fail'),skipped:metric('skipped'),cancelled:metric('cancelled'),log:stem+'.tap'};results.push(record);console.log(JSON.stringify(record));
 fs.writeFileSync(path.join(destination,'results.json'),JSON.stringify({complete:results.length===files.length,expectedFiles:files.length,node:process.version,platform:process.platform,results},null,2)+'\n');
}
async function worker(){while(next<files.length){const file=files[next++];await one(file);}}
// Native execution and read-only ship tests share one workspace; serialize explicit execution runs.
Promise.all(Array.from({length:process.env.UC_EXECUTION_TESTS==='1'?1:3},worker)).then(()=>{process.exitCode=results.every(r=>r.status==='PASS')?0:1;}).catch(e=>{console.error(e);process.exitCode=1;});
