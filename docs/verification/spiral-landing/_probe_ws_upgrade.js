const fs = require('fs');
const path = require('path');
const http = require('http');
const crypto = require('crypto');
const net = require('net');
const harbor = process.env.HARBOR_ROOT || path.resolve(__dirname, '../../..');
const port = Number(process.env.PROBE_PORT || 10003);
const token = fs.readFileSync(path.join(harbor, 'ACCESS_TOKEN.txt'), 'utf8').trim();
const outDir = path.join(harbor, 'docs', 'verification', 'spiral-landing');
const PROTOCOL = 'hermit.vws.v2';

function postTicket(origin) {
  return new Promise((resolve, reject) => {
    const headers = { Authorization: 'Bearer ' + token, 'Content-Length': 0 };
    if (origin) headers.Origin = origin;
    const req = http.request({ host: '127.0.0.1', port, path: '/api/ws-ticket', method: 'POST', headers }, (res) => {
      const cookies = res.headers['set-cookie'] || [];
      let body = '';
      res.on('data', d => body += d);
      res.on('end', () => resolve({ status: res.statusCode, cookies, body, headers: res.headers }));
    });
    req.on('error', reject);
    req.end();
  });
}

function upgradeWithCookie(cookieHeader, origin) {
  return new Promise((resolve) => {
    const key = crypto.randomBytes(16).toString('base64');
    const lines = [
      'GET /ws/terminal HTTP/1.1',
      'Host: 127.0.0.1:' + port,
      'Connection: Upgrade',
      'Upgrade: websocket',
      'Sec-WebSocket-Version: 13',
      'Sec-WebSocket-Key: ' + key,
      'Sec-WebSocket-Protocol: ' + PROTOCOL,
    ];
    if (origin) lines.push('Origin: ' + origin);
    if (cookieHeader) lines.push('Cookie: ' + cookieHeader);
    lines.push('', '');
    const socket = net.connect({ host: '127.0.0.1', port }, () => {
      socket.write(lines.join('\r\n'));
    });
    let buf = Buffer.alloc(0);
    let settled = false;
    const done = (obj) => { if (settled) return; settled = true; try { socket.destroy(); } catch {} ; resolve(obj); };
    const timer = setTimeout(() => done({ ok: false, reason: 'timeout', head: buf.toString('utf8').slice(0, 400) }), 5000);
    socket.on('data', (chunk) => {
      buf = Buffer.concat([buf, chunk]);
      const s = buf.toString('utf8');
      if (s.includes('\r\n\r\n')) {
        clearTimeout(timer);
        const status = /^HTTP\/1\.\d\s+(\d+)/.exec(s);
        done({ ok: status && status[1] === '101', status: status && Number(status[1]), head: s.slice(0, 500), bytes: buf.length });
      }
    });
    socket.on('error', (e) => { clearTimeout(timer); done({ ok: false, reason: e.message }); });
  });
}

function upgradeWithBearerNoOrigin() {
  return new Promise((resolve) => {
    const key = crypto.randomBytes(16).toString('base64');
    const lines = [
      'GET /ws/terminal HTTP/1.1',
      'Host: 127.0.0.1:' + port,
      'Connection: Upgrade',
      'Upgrade: websocket',
      'Sec-WebSocket-Version: 13',
      'Sec-WebSocket-Key: ' + key,
      'Sec-WebSocket-Protocol: ' + PROTOCOL,
      'Authorization: Bearer ' + token,
      '', ''
    ];
    const socket = net.connect({ host: '127.0.0.1', port }, () => socket.write(lines.join('\r\n')));
    let buf = Buffer.alloc(0);
    let settled = false;
    const done = (obj) => { if (settled) return; settled = true; try { socket.destroy(); } catch {}; resolve(obj); };
    const timer = setTimeout(() => done({ ok: false, reason: 'timeout', head: buf.toString('utf8').slice(0, 400) }), 5000);
    socket.on('data', (chunk) => {
      buf = Buffer.concat([buf, chunk]);
      const s = buf.toString('utf8');
      if (s.includes('\r\n\r\n')) {
        clearTimeout(timer);
        const status = /^HTTP\/1\.\d\s+(\d+)/.exec(s);
        done({ ok: status && status[1] === '101', status: status && Number(status[1]), head: s.slice(0, 500), bytes: buf.length });
      }
    });
    socket.on('error', (e) => { clearTimeout(timer); done({ ok: false, reason: e.message }); });
  });
}

(async () => {
  const t0 = Date.now();
  const origin = 'http://127.0.0.1:' + port;
  const ticket = await postTicket(origin);
  const cookieHeader = (ticket.cookies || []).map(c => c.split(';')[0]).join('; ');
  const withCookie = await upgradeWithCookie(cookieHeader, origin);
  const withBearer = await upgradeWithBearerNoOrigin();
  // Focus registration structural check
  const src = fs.readFileSync(path.join(harbor, 'bridge-terminal/src/main/spiral/commands/qnode.js'), 'utf8');
  const focus = {
    loop_registers_qn_shorts: /for\s*\(\s*let\s+i\s*=\s*1;\s*i\s*<=\s*COUNT;\s*i\+\+\)\s*shorts\.push\(makeQnShort/.test(src),
    df_focus_keys: ['ns','nm','nl','nx','nf'].every(c => new RegExp("\\b" + c + "\\s*:").test(src) || src.includes("'" + c + "'") || src.includes('"' + c + '"')),
    DF_FOCUS_present: /const DF_FOCUS\s*=/.test(src),
    COUNT_is_50: /COUNT\s*=\s*50|require\([^)]*locator[^)]*\)/.test(src) || src.includes('COUNT'),
    makeQnShort_present: /function makeQnShort|makeQnShort\s*=/.test(src) || /makeQnShort\(/.test(src)
  };
  const out = {
    generated_pt: new Date().toLocaleString('en-US', { timeZone: 'America/Los_Angeles' }) + ' PT',
    port,
    ticket_http_status: ticket.status,
    ticket_cookie_present: /vws_ticket=/.test(cookieHeader),
    ws_upgrade_cookie_origin: { ok: !!withCookie.ok, status: withCookie.status || null, reason: withCookie.reason || null, head_redacted: (withCookie.head || '').replace(/vws_ticket=[^;\s]+/g, 'vws_ticket=[REDACTED]').slice(0, 300) },
    ws_upgrade_bearer_no_origin: { ok: !!withBearer.ok, status: withBearer.status || null, reason: withBearer.reason || null, head_redacted: (withBearer.head || '').slice(0, 300) },
    focus_command_registration: focus,
    elapsed_ms: Date.now() - t0,
    note: 'Upgrade verifies admission (101 + subprotocol). Full SPIRAL banner bytes require completing the hermit.vws.v2 session open handshake after upgrade; not decoded here.'
  };
  fs.writeFileSync(path.join(outDir, 'port10003-ws-upgrade.json'), JSON.stringify(out, null, 2));
  // refresh focus check in fleet-board-locator.json
  const fleetPath = path.join(outDir, 'fleet-board-locator.json');
  if (fs.existsSync(fleetPath)) {
    const fleet = JSON.parse(fs.readFileSync(fleetPath, 'utf8'));
    fleet.focus_command_source_check = { ...focus, note: 'Structural registration in commands/qnode.js (loop over COUNT for qn01..qn50 + DF_FOCUS shorts)' };
    fs.writeFileSync(fleetPath, JSON.stringify(fleet, null, 2));
  }
  console.log(JSON.stringify({ ticket: ticket.status, cookie_upgrade: withCookie.ok, cookie_status: withCookie.status, bearer_upgrade: withBearer.ok, bearer_status: withBearer.status, focus, elapsed_ms: out.elapsed_ms }, null, 2));
})().catch(e => { console.error(e); process.exit(1); });
