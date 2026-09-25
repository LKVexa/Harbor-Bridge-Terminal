'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {startGateway,sleep}=require('../helpers');const {resolvePython}=require('../../tools/start-ship');
let chromium;try{({chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright'));}catch{}
test('Chromium: sign in, real ship capabilities, virtual Unicode shell, credential-free URL and storage', {skip:chromium?false:'playwright not installed',timeout:60000}, async()=>{
 const root=path.resolve(__dirname,'../../..');const h=await startGateway({},{VWS_SHIP_ROOT:root,PYTHON:resolvePython(),VWS_HOST:'127.0.0.1'});
 h.principals[0].capabilities.push('ship.read');fs.writeFileSync(h.pf,JSON.stringify(h.principals));fs.utimesSync(h.pf,new Date(),new Date(Date.now()+1000));
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,args:process.platform==='linux'?['--no-sandbox']:[]});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:960}});const faults=[];page.on('pageerror',e=>faults.push(e.message));const urls=[];page.on('websocket',w=>urls.push(w.url()));
  const response=await page.goto(h.http+'/');assert.match(response.headers()['content-security-policy'],/frame-ancestors 'none'/);
  await page.waitForSelector('#signin:not([hidden])');await page.fill('#signin-token',h.tokens.alice);await page.click('#signin button');
  await page.waitForFunction(()=>document.getElementById('st-conn').textContent==='active');await page.click('#screen');
  await page.keyboard.type('ship capabilities');await page.keyboard.press('Enter');
  await page.waitForFunction(()=>document.getElementById('a11y-screen').textContent.includes('UC-2.4.0'));
  const text=await page.locator('#a11y-screen').textContent();assert.match(text,/"bootable_guest": false/);assert.match(text,/"arbitrary_host_shell": false/);
  await page.keyboard.type('echo connected-✓');await page.keyboard.press('Enter');await page.waitForFunction(()=>/\nconnected-✓/.test(document.getElementById('a11y-screen').textContent));
  assert.ok(urls.length===1&&!urls[0].includes('?'));assert.equal(await page.evaluate(()=>document.cookie),'');
  assert.equal(await page.evaluate(token=>document.documentElement.outerHTML.includes(token)||JSON.stringify(localStorage).includes(token)||JSON.stringify(sessionStorage).includes(token),h.tokens.alice),false);
  assert.deepEqual(faults,[]);
  const dir=process.env.VWS_TEST_OUTPUT||path.join(root,'_runs','vws-tests');fs.mkdirSync(dir,{recursive:true});await page.screenshot({path:path.join(dir,'uc240-terminal.png')});
 }finally{await browser.close();await h.stop();}
});
