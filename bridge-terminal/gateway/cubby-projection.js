"use strict";
/**
 * Gateway HTTP surface for Harbor cubbies + local-127 projection.
 *
 * Routes:
 *   GET  /api/cubbies
 *   GET  /api/cubbies/:id
 *   GET  /api/cubbies/:id/session
 *   GET|POST /api/cubbies/:id/attach   — access-gated (mobile needs BR cubby for QN/CS)
 *   GET  /api/cubbies/access-check?target=QN-01  — dry-run gate
 *   GET  /cubby/:id/projection         — HTML projected view (gated for mobile→QN/CS)
 *   GET  /cubby/:id/serve/status       — brctl serve process status (MC-* live)
 *   POST /cubby/:id/serve/apdu         — proxy one hex-APDU to brctl serve stdin/stdout
 *   WS   /cubby/:id/serve/ws           — stream READY/responses (optional)
 *
 * Honest surface: `brctl serve` is a hex-APDU REPL (not an HTTP framebuffer). Harbor
 * launches it per mobile cubby and proxies that REPL into the projection page.
 *
 * Desktop: QVM + containership cubbies project directly on local 127.
 * Mobile: BR mobile cubby first; then proxy/attach to QN/CS via that cubby.
 * Never a device VM download.
 */
const path = require("node:path");
const crypto = require("node:crypto");
const gate = require("./cubby-access-gate");
const serveMgr = require("./brctl-serve-manager");

function loadRegistry() {
  try {
    return require(path.join(__dirname, "..", "..", "mobile-platform", "compiler", "cubbies", "registry.js"));
  } catch {
    const alt = path.join(process.env.HARBOR_ROOT || path.join(__dirname, "..", ".."), "mobile-platform", "compiler", "cubbies", "registry.js");
    return require(alt);
  }
}

function harborRoot(cfg) {
  const reg = loadRegistry();
  return reg.harborRootFrom(cfg && cfg.root);
}

function matchCubbyApi(p) {
  if (p === "/api/cubbies") return { kind: "list" };
  if (p === "/api/cubbies/access-check") return { kind: "access-check" };
  let m = p.match(/^\/api\/cubbies\/([A-Za-z0-9._-]+)\/session$/);
  if (m) return { kind: "session", id: m[1] };
  m = p.match(/^\/api\/cubbies\/([A-Za-z0-9._-]+)\/attach$/);
  if (m) return { kind: "attach", id: m[1] };
  m = p.match(/^\/api\/cubbies\/([A-Za-z0-9._-]+)$/);
  if (m) return { kind: "one", id: m[1] };
  return null;
}

function matchProjection(p) {
  const m = p.match(/^\/cubby\/([A-Za-z0-9._-]+)\/projection$/);
  return m ? { id: m[1] } : null;
}

function matchServe(p) {
  let m = p.match(/^\/cubby\/([A-Za-z0-9._-]+)\/serve\/status$/);
  if (m) return { id: m[1], kind: "status" };
  m = p.match(/^\/cubby\/([A-Za-z0-9._-]+)\/serve\/apdu$/);
  if (m) return { id: m[1], kind: "apdu" };
  m = p.match(/^\/cubby\/([A-Za-z0-9._-]+)\/serve\/ws$/);
  if (m) return { id: m[1], kind: "ws" };
  return null;
}

function principalFromReq(req) {
  const hdr = req.headers["x-harbor-principal"];
  if (typeof hdr === "string" && hdr.trim()) return hdr.trim();
  return null;
}

function isMobileCubbyId(id) {
  return /^MC-/i.test(String(id || ""));
}

function readBody(req, limit) {
  return new Promise((resolve, reject) => {
    const max = limit || 65536;
    const chunks = [];
    let n = 0;
    req.on("data", (c) => {
      n += c.length;
      if (n > max) {
        reject(new Error("body too large"));
        try { req.destroy(); } catch { /* noop */ }
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

async function ensureServeForCubby(root, cubbyId) {
  if (!isMobileCubbyId(cubbyId)) return null;
  serveMgr.setHarborRoot(root);
  try {
    return await serveMgr.ensure(cubbyId, { harborRoot: root });
  } catch (e) {
    return {
      ready: false,
      error: String(e && e.message || e),
      cubby_id: cubbyId,
      surface: "hex-APDU REPL (not a framebuffer)",
      device_download: false,
    };
  }
}

function projectionHtml(cubby, session, port, gateResult, serveInfo) {
  const id = (cubby && cubby.id) || (session && session.cubby_id) || "unknown";
  const status = (session && session.status) || (cubby && cubby.status) || "unknown";
  const platform = (cubby && cubby.platform) || (session && session.platform) || "";
  const sid = (session && session.session_id) || (cubby && cubby.session_id) || "";
  const url = (session && session.projection_url) || (cubby && cubby.projection && cubby.projection.url) || "";
  const pathNote = (gateResult && gateResult.path) || "direct";
  const brVia = gateResult && gateResult.br_cubby_id ? gateResult.br_cubby_id : "";
  const mobile = isMobileCubbyId(id);
  const serveReady = !!(serveInfo && serveInfo.ready);
  const servePid = (serveInfo && serveInfo.pid) || "";
  const serveState = (serveInfo && (serveInfo.state_rel || serveInfo.state_prefix)) || "";
  const esc = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const seedInfo = {
    ready: serveReady,
    pid: servePid,
    state_rel: serveState,
    surface: (serveInfo && serveInfo.surface) || "hex-APDU REPL (not a framebuffer)",
  };
  const serveBlock = !mobile ? `
  <div class="banner note" style="margin-top:0.75rem">
    QN/CS cubbies use Harbor fabric projection. Live <code>brctl serve</code> APDU proxy is attached to mobile <code>MC-*</code> cubbies.
  </div>` : `
  <h2 style="font-size:1rem;margin:1.25rem 0 0.5rem;color:#c7d2fe">Bottle Rocket <code>brctl serve</code> (proxied)</h2>
  <div class="banner note">
    Upstream <code>brctl serve --state …</code> is a <strong>hex-APDU REPL over stdio</strong>
    (banner: <code>READY hex-APDU per line; EOF stops</code>) — not an HTTP framebuffer.
    Harbor launches one process per mobile cubby and proxies APDUs here via
    <code>POST /cubby/${esc(id)}/serve/apdu</code> (optional WS <code>/cubby/${esc(id)}/serve/ws</code>).
  </div>
  <dl>
    <dt>serve pid</dt><dd><code>${esc(servePid || "—")}</code></dd>
    <dt>serve state</dt><dd><code>${esc(serveState || "—")}</code></dd>
    <dt>serve ready</dt><dd><code>${esc(String(serveReady))}</code></dd>
    <dt>surface</dt><dd>hex-APDU REPL (not a framebuffer)</dd>
  </dl>
  <div class="row">
    <button type="button" id="btn-hello" class="secondary">HELLO 010c</button>
    <button type="button" id="btn-status" class="secondary">STATUS 0102…</button>
    <button type="button" id="btn-caps" class="secondary">CAPS 010b…</button>
    <button type="button" id="btn-refresh" class="secondary">Refresh status</button>
  </div>
  <div class="row">
    <input id="apdu" type="text" spellcheck="false" placeholder="hex APDU e.g. 010200000000000000000000" value="010200000000000000000000"/>
    <button type="button" id="btn-send">Send APDU</button>
  </div>
  <div id="log" class="console" aria-live="polite"></div>
  <script>
  (function () {
    var cubbyId = ${JSON.stringify(id)};
    var logEl = document.getElementById("log");
    function line(cls, text) {
      var d = document.createElement("div");
      if (cls) d.className = cls;
      d.textContent = text;
      logEl.appendChild(d);
      logEl.scrollTop = logEl.scrollHeight;
    }
    function showServe(info) {
      line("okline", "serve ready=" + !!(info && info.ready) + " pid=" + ((info && info.pid) || "?") +
        " state=" + ((info && (info.state_rel || info.state_prefix)) || "?"));
      if (info && info.surface) line("", "surface: " + info.surface);
    }
    async function refresh() {
      try {
        var r = await fetch("/cubby/" + encodeURIComponent(cubbyId) + "/serve/status", { cache: "no-store" });
        var j = await r.json();
        if (!r.ok) { line("err", "status HTTP " + r.status + " " + JSON.stringify(j)); return; }
        showServe(j.serve || j);
      } catch (e) { line("err", String(e)); }
    }
    async function sendHex(hex) {
      line("", "> " + hex);
      try {
        var r = await fetch("/cubby/" + encodeURIComponent(cubbyId) + "/serve/apdu", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ hex: hex })
        });
        var j = await r.json();
        if (!r.ok) { line("err", "APDU HTTP " + r.status + " " + JSON.stringify(j)); return; }
        line("okline", "< " + (j.response || JSON.stringify(j)));
      } catch (e) { line("err", String(e)); }
    }
    document.getElementById("btn-send").onclick = function () {
      sendHex(document.getElementById("apdu").value);
    };
    document.getElementById("btn-hello").onclick = function () { sendHex("010c"); };
    document.getElementById("btn-status").onclick = function () { sendHex("010200000000000000000000"); };
    document.getElementById("btn-caps").onclick = function () { sendHex("010b00000000000000000000"); };
    document.getElementById("btn-refresh").onclick = refresh;
    line("", "Harbor ↔ brctl serve proxy for " + cubbyId);
    ${serveReady
      ? "showServe(" + JSON.stringify(seedInfo) + ");"
      : "line('', 'Starting serve…'); refresh();"}
  })();
  </script>`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Harbor cubby ${esc(id)} — projection</title>
<style>
  :root { color-scheme: dark; font-family: ui-sans-serif, system-ui, sans-serif; }
  body { margin: 0; background: #0b1220; color: #e8eefc; }
  main { max-width: 52rem; margin: 1.5rem auto; padding: 1.25rem; border: 1px solid #243049; border-radius: 12px; background: #121a2b; }
  h1 { font-size: 1.25rem; margin: 0 0 0.5rem; }
  .tag { display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px; background: #1d4ed8; font-size: 0.75rem; margin-right: 0.35rem; }
  .ok { background: #15803d; }
  .warn-tag { background: #a16207; }
  dl { display: grid; grid-template-columns: 9rem 1fr; gap: 0.35rem 0.75rem; margin: 1rem 0; font-size: 0.95rem; }
  dt { color: #93a4c3; } dd { margin: 0; word-break: break-all; }
  .banner { margin-top: 1rem; padding: 0.85rem 1rem; border-radius: 8px; background: #052e1a; border: 1px solid #166534; line-height: 1.45; }
  .note { background: #1a2336; border-color: #334155; }
  code { font-family: ui-monospace, Consolas, monospace; font-size: 0.85em; }
  .console { background: #060b14; border: 1px solid #243049; border-radius: 8px; padding: 0.75rem; min-height: 12rem; max-height: 22rem; overflow: auto; white-space: pre-wrap; font-family: ui-monospace, Consolas, monospace; font-size: 0.8rem; line-height: 1.4; }
  .row { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.75rem 0; }
  input[type=text] { flex: 1; min-width: 12rem; background: #0b1220; color: #e8eefc; border: 1px solid #334155; border-radius: 6px; padding: 0.45rem 0.6rem; font-family: ui-monospace, Consolas, monospace; }
  button { background: #1d4ed8; color: white; border: 0; border-radius: 6px; padding: 0.45rem 0.75rem; cursor: pointer; font-size: 0.85rem; }
  button.secondary { background: #334155; }
  .err { color: #fca5a5; }
  .okline { color: #86efac; }
</style>
</head>
<body>
<main>
  <span class="tag ${status === "live" || status === "registered" || !session ? "ok" : ""}">${esc(status === "live" ? "operable · live" : status)}</span>
  <span class="tag">${esc(pathNote)}</span>
  ${serveReady ? '<span class="tag ok">brctl serve · ready</span>' : (mobile ? '<span class="tag warn-tag">brctl serve · starting</span>' : '')}
  <h1>Cubby ${esc(id)}</h1>
  <p>VM / fabric session projected to this browser on <code>127.0.0.1</code> — not downloaded.</p>
  <dl>
    <dt>Cubby id</dt><dd><code>${esc(id)}</code></dd>
    <dt>Session</dt><dd><code>${esc(sid || "—")}</code></dd>
    <dt>Platform</dt><dd>${esc(platform || "—")}</dd>
    <dt>Entry path</dt><dd><code>${esc(pathNote)}</code></dd>
    <dt>Via BR cubby</dt><dd><code>${esc(brVia || "n/a (desktop direct or MC self)")}</code></dd>
    <dt>Bind</dt><dd><code>127.0.0.1${port ? ":" + esc(port) : ""}</code></dd>
    <dt>Projection URL</dt><dd><code>${esc(url || "/cubby/" + id + "/projection")}</code></dd>
    <dt>VM location</dt><dd>Harbor cubby (gateway side)</dd>
  </dl>
  <div class="banner">
    <strong>Projected from Harbor cubby — not downloaded.</strong>
    QVM nodes, containership slots, and mobile Bottle Rocket sessions are all cubbies.
    Desktop opens them on local 127 directly. Mobile must hold a live BR mobile cubby before QVM/containership attach.
  </div>
  ${serveBlock}
</main>
</body>
</html>`;
}

function forbidHtml(gateResult) {
  const esc = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>403 — mobile BR cubby required</title>
<style>body{font-family:system-ui;background:#0b1220;color:#e8eefc;padding:2rem}code{background:#1a2336;padding:0.1rem 0.35rem;border-radius:4px}.box{max-width:40rem;margin:auto;border:1px solid #854d0e;background:#2a1a05;padding:1.25rem;border-radius:12px}</style></head>
<body><div class="box"><h1>403 mobile_br_cubby_required</h1>
<p>${esc(gateResult.message)}</p>
<ol>
<li>Authenticate with <code>X-Harbor-Mobile-Platform</code> to spawn an <code>MC-*</code> Bottle Rocket cubby</li>
<li>Open its <code>projection_url</code> on local 127</li>
<li>Retry this QVM/containership projection</li>
</ol>
<pre>${esc(JSON.stringify(gateResult.remediation || {}, null, 2))}</pre>
</div></body></html>`;
}

function handle(req, res, { cfg, json }) {
  const p = (() => {
    try { return new URL(req.url || "/", "http://127.0.0.1").pathname; }
    catch { return (req.url || "").split("?")[0]; }
  })();

  const root = harborRoot(cfg);
  const principal = principalFromReq(req);
  serveMgr.setHarborRoot(root);

  const api = matchCubbyApi(p);
  if (api) {
    if (api.kind === "attach") {
      if (req.method !== "GET" && req.method !== "POST" && req.method !== "HEAD") {
        json(res, 405, { error: "method" }, { Allow: "GET, POST, HEAD" });
        return true;
      }
      const result = gate.checkAccess({ harborRoot: root, req, principal, targetCubbyId: api.id, action: "attach" });
      if (!result.ok) {
        json(res, result.status || 403, result);
        return true;
      }
      const reg = loadRegistry();
      const cubby = reg.getCubby(root, api.id);
      json(res, 200, {
        attached: true,
        gate: result,
        cubby,
        projection_path: `/cubby/${api.id}/projection`,
        device_download: false,
      });
      return true;
    }

    if (api.kind === "access-check") {
      if (req.method !== "GET" && req.method !== "HEAD") {
        json(res, 405, { error: "method" }, { Allow: "GET, HEAD" });
        return true;
      }
      let target = null;
      try {
        target = new URL(req.url || "/", "http://127.0.0.1").searchParams.get("target");
      } catch { /* ignore */ }
      const result = gate.checkAccess({ harborRoot: root, req, principal, targetCubbyId: target, action: "access-check" });
      json(res, result.ok ? 200 : (result.status || 403), result);
      return true;
    }

    if (req.method !== "GET" && req.method !== "HEAD") {
      json(res, 405, { error: "method" }, { Allow: "GET, HEAD" });
      return true;
    }
    const reg = loadRegistry();
    try {
      if (api.kind === "list") {
        const body = reg.listCubbies(root);
        body.primary_story = "cubby spawn + browser projection on local 127";
        body.device_download = false;
        body.entry = {
          desktop: "QVM and containership cubbies project directly on local 127 (no BR mobile cubby)",
          mobile: "Must create live Bottle Rocket mobile cubby (MC-*) first; then attach to QN/CS via that cubby",
        };
        body.brctl_serve = {
          manager: "bridge-terminal/gateway/brctl-serve-manager.js",
          processes: serveMgr.list(),
          note: "Per-MC brctl serve stdio REPL proxied at /cubby/:id/serve/*",
        };
        json(res, 200, body);
        return true;
      }
      if (api.kind === "one") {
        const cubby = reg.getCubby(root, api.id);
        if (!cubby) {
          json(res, 404, { error: "cubby not found", id: api.id });
          return true;
        }
        const session = reg.readSession(root, api.id);
        const live = serveMgr.get(api.id);
        json(res, 200, {
          cubby,
          session,
          device_download: false,
          br_serve: live ? live.info() : (session && (session.br_serve || session.br_serve)) || null,
        });
        return true;
      }
      if (api.kind === "session") {
        const session = reg.readSession(root, api.id);
        if (!session) {
          const cubby = reg.getCubby(root, api.id);
          if (!cubby) {
            json(res, 404, { error: "session not found", id: api.id });
            return true;
          }
          json(res, 200, {
            cubby_id: cubby.id,
            status: cubby.status || "registered",
            operable: cubby.operable !== false,
            projection_url: cubby.projection && cubby.projection.url,
            device_download: false,
            note: "static cubby (no live mobile projection session file)",
          });
          return true;
        }
        const live = serveMgr.get(api.id);
        if (live) session.br_serve_live = live.info();
        json(res, 200, session);
        return true;
      }
    } catch (e) {
      json(res, 500, { error: "cubby registry", reason: String(e && e.message) });
      return true;
    }
  }

  const serveRoute = matchServe(p);
  if (serveRoute) {
    if (serveRoute.kind === "ws") {
      json(res, 426, { error: "upgrade required", path: p });
      return true;
    }
    const gateResult = gate.checkAccess({
      harborRoot: root,
      req,
      principal,
      targetCubbyId: serveRoute.id,
      action: "project",
    });
    if (!gateResult.ok) {
      json(res, gateResult.status || 403, gateResult);
      return true;
    }
    if (!isMobileCubbyId(serveRoute.id)) {
      json(res, 400, {
        error: "brctl_serve_mobile_only",
        message: "brctl serve proxy is attached to mobile MC-* cubbies",
        device_download: false,
      });
      return true;
    }
    if (serveRoute.kind === "status") {
      if (req.method !== "GET" && req.method !== "HEAD") {
        json(res, 405, { error: "method" }, { Allow: "GET, HEAD" });
        return true;
      }
      Promise.resolve()
        .then(() => ensureServeForCubby(root, serveRoute.id))
        .then((info) => {
          json(res, 200, {
            cubby_id: serveRoute.id,
            serve: info,
            device_download: false,
            surface: "hex-APDU REPL proxied from brctl serve stdio",
          });
        })
        .catch((e) => json(res, 503, { error: "serve_unavailable", reason: String(e && e.message) }));
      return true;
    }
    if (serveRoute.kind === "apdu") {
      if (req.method !== "POST") {
        json(res, 405, { error: "method" }, { Allow: "POST" });
        return true;
      }
      readBody(req)
        .then(async (raw) => {
          let body = {};
          try { body = JSON.parse(raw || "{}"); } catch { body = {}; }
          const hex = body.hex || body.apdu || raw;
          await ensureServeForCubby(root, serveRoute.id);
          const out = await serveMgr.apdu(serveRoute.id, hex);
          json(res, 200, {
            cubby_id: serveRoute.id,
            request: out.request,
            response: out.response,
            device_download: false,
          });
        })
        .catch((e) => json(res, 400, { error: "apdu_failed", reason: String(e && e.message) }));
      return true;
    }
  }

  const proj = matchProjection(p);
  if (proj) {
    if (req.method !== "GET" && req.method !== "HEAD") {
      json(res, 405, { error: "method" }, { Allow: "GET, HEAD" });
      return true;
    }
    const gateResult = gate.checkAccess({
      harborRoot: root,
      req,
      principal,
      targetCubbyId: proj.id,
      action: "project",
    });
    if (!gateResult.ok) {
      const html = forbidHtml(gateResult);
      const buf = Buffer.from(html, "utf8");
      res.writeHead(403, {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Length": buf.length,
        "Cache-Control": "no-store",
        "X-Harbor-Gate": "mobile_br_cubby_required",
        "X-Harbor-Device-Download": "false",
      });
      if (req.method !== "HEAD") res.end(buf);
      else res.end();
      return true;
    }

    const reg = loadRegistry();
    let cubby = null;
    let session = null;
    try {
      cubby = reg.getCubby(root, proj.id);
      session = reg.readSession(root, proj.id);
    } catch { /* ignore */ }

    if (!cubby && !session) {
      json(res, 404, { error: "cubby not found", id: proj.id });
      return true;
    }
    if (!cubby) {
      cubby = { id: proj.id, kind: "unknown", status: "registered" };
    }
    if (!cubby.projection) {
      cubby = {
        ...cubby,
        projection: {
          url: `http://127.0.0.1:${(cfg && cfg.port) || process.env.PORT || "10000"}/cubby/${proj.id}/projection`,
          path: `/cubby/${proj.id}/projection`,
          bind: "127.0.0.1",
          note: "Projected from Harbor cubby — not downloaded",
        },
        status: cubby.status || "registered",
      };
    }

    const port = (cfg && cfg.port) || process.env.PORT || "";
    const finish = (serveInfo) => {
      const html = projectionHtml(cubby, session, port, gateResult, serveInfo);
      const buf = Buffer.from(html, "utf8");
      res.writeHead(200, {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Length": buf.length,
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Harbor-Cubby": proj.id,
        "X-Harbor-Projection": "cubby-local-127",
        "X-Harbor-Entry-Path": gateResult.path || "unknown",
        "X-Harbor-Device-Download": "false",
        "X-Harbor-Brctl-Serve": serveInfo && serveInfo.ready ? "ready" : (isMobileCubbyId(proj.id) ? "pending" : "n/a"),
      });
      if (req.method !== "HEAD") res.end(buf);
      else res.end();
    };
    if (isMobileCubbyId(proj.id)) {
      ensureServeForCubby(root, proj.id).then(finish).catch((e) => finish({ ready: false, error: String(e && e.message) }));
    } else {
      finish(null);
    }
    return true;
  }

  return false;
}

/**
 * Optional WS upgrade for /cubby/:id/serve/ws — returns true if handled.
 * Bare RFC6455 accept (no hermit.vws subprotocol).
 */
function handleServeUpgrade(req, socket, head, { cfg }) {
  const p = (() => {
    try { return new URL(req.url || "/", "http://127.0.0.1").pathname; }
    catch { return (req.url || "").split("?")[0]; }
  })();
  const m = matchServe(p);
  if (!m || m.kind !== "ws") return false;
  if (head && head.length) {
    try { socket.write("HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n"); } catch { /* noop */ }
    try { socket.destroy(); } catch { /* noop */ }
    return true;
  }
  const root = harborRoot(cfg);
  const principal = principalFromReq(req);
  const gateResult = gate.checkAccess({
    harborRoot: root,
    req,
    principal,
    targetCubbyId: m.id,
    action: "project",
  });
  if (!gateResult.ok || !isMobileCubbyId(m.id)) {
    try { socket.write("HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n"); } catch { /* noop */ }
    try { socket.destroy(); } catch { /* noop */ }
    return true;
  }
  const key = req.headers["sec-websocket-key"];
  if (typeof key !== "string") {
    try { socket.write("HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n"); } catch { /* noop */ }
    try { socket.destroy(); } catch { /* noop */ }
    return true;
  }

  // Prefer gateway WsConnection if available
  let WsConnection = null;
  try { WsConnection = require("./ws").WsConnection; } catch { /* optional */ }

  Promise.resolve()
    .then(() => ensureServeForCubby(root, m.id))
    .then(() => {
      const accept = crypto.createHash("sha1")
        .update(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
        .digest("base64");
      socket.write(
        "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n" +
        `Sec-WebSocket-Accept: ${accept}\r\n\r\n`
      );
      if (!WsConnection) {
        // Minimal text-frame reader is not implemented without ws.js — close politely.
        try { socket.end(); } catch { /* noop */ }
        return;
      }
      const ws = new WsConnection(socket, { maxMessageBytes: 65536, sendQueueBytes: 262144 });
      const send = (text) => { try { ws.sendText(Buffer.from(String(text), "utf8")); } catch { /* noop */ } };
      const unsub = serveMgr.attachWs(m.id, send, () => { try { ws.terminate(1000, "serve exit"); } catch { /* noop */ } });
      ws.on("text", (buf) => {
        let msg = buf.toString("utf8").trim();
        let hex = msg;
        try {
          const j = JSON.parse(msg);
          if (j && (j.hex || j.apdu)) hex = j.hex || j.apdu;
        } catch { /* plain hex */ }
        serveMgr.apdu(m.id, hex).then((out) => {
          send(JSON.stringify({ type: "response", request: out.request, text: out.response }));
        }).catch((e) => {
          send(JSON.stringify({ type: "error", reason: String(e && e.message) }));
        });
      });
      ws.on("close", () => { try { unsub(); } catch { /* noop */ } });
    })
    .catch(() => {
      try { socket.write("HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\n\r\n"); } catch { /* noop */ }
      try { socket.destroy(); } catch { /* noop */ }
    });
  return true;
}

module.exports = {
  handle,
  handleServeUpgrade,
  matchCubbyApi,
  matchProjection,
  matchServe,
  projectionHtml,
  ensureServeForCubby,
};
