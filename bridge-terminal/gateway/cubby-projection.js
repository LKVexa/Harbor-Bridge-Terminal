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
 *
 * Desktop: QVM + containership cubbies project directly on local 127.
 * Mobile: BR mobile cubby first; then proxy/attach to QN/CS via that cubby.
 * Never a device VM download.
 */
const fs = require("node:fs");
const path = require("node:path");
const gate = require("./cubby-access-gate");

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

function principalFromReq(req) {
  const hdr = req.headers["x-harbor-principal"];
  if (typeof hdr === "string" && hdr.trim()) return hdr.trim();
  return null;
}

function projectionHtml(cubby, session, port, gateResult) {
  const id = (cubby && cubby.id) || (session && session.cubby_id) || "unknown";
  const status = (session && session.status) || (cubby && cubby.status) || "unknown";
  const platform = (cubby && cubby.platform) || (session && session.platform) || "";
  const sid = (session && session.session_id) || (cubby && cubby.session_id) || "";
  const url = (session && session.projection_url) || (cubby && cubby.projection && cubby.projection.url) || "";
  const pathNote = (gateResult && gateResult.path) || "direct";
  const brVia = gateResult && gateResult.br_cubby_id ? gateResult.br_cubby_id : "";
  const esc = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Harbor cubby ${esc(id)} — projection</title>
<style>
  :root { color-scheme: dark; font-family: ui-sans-serif, system-ui, sans-serif; }
  body { margin: 0; background: #0b1220; color: #e8eefc; }
  main { max-width: 42rem; margin: 2rem auto; padding: 1.5rem; border: 1px solid #243049; border-radius: 12px; background: #121a2b; }
  h1 { font-size: 1.25rem; margin: 0 0 0.5rem; }
  .tag { display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px; background: #1d4ed8; font-size: 0.75rem; margin-right: 0.35rem; }
  .ok { background: #15803d; }
  dl { display: grid; grid-template-columns: 9rem 1fr; gap: 0.35rem 0.75rem; margin: 1.25rem 0; font-size: 0.95rem; }
  dt { color: #93a4c3; } dd { margin: 0; word-break: break-all; }
  .banner { margin-top: 1rem; padding: 0.85rem 1rem; border-radius: 8px; background: #052e1a; border: 1px solid #166534; line-height: 1.45; }
  .warn { background: #2a1a05; border-color: #854d0e; }
  code { font-family: ui-monospace, Consolas, monospace; font-size: 0.85em; }
</style>
</head>
<body>
<main>
  <span class="tag ${status === "live" || status === "registered" || !session ? "ok" : ""}">${esc(status === "live" ? "operable · live" : status)}</span>
  <span class="tag">${esc(pathNote)}</span>
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
  <div class="banner warn" style="margin-top:0.75rem">
    Full Bottle Rocket host UI in-browser is optional. This page proves cubby id + session + projection contract.
    <code>brctl serve</code> remains available for advanced host-state serving.
  </div>
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
        json(res, 200, { cubby, session, device_download: false });
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
        json(res, 200, session);
        return true;
      }
    } catch (e) {
      json(res, 500, { error: "cubby registry", reason: String(e && e.message) });
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

    // Static QN/CS cubbies are projectable without a session file (desktop or gated mobile)
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
    const html = projectionHtml(cubby, session, port, gateResult);
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
    });
    if (req.method !== "HEAD") res.end(buf);
    else res.end();
    return true;
  }

  return false;
}

module.exports = { handle, matchCubbyApi, matchProjection, projectionHtml };
