"use strict";
/**
 * SPIRAL / Harbor gateway hook: successful auth (ws-ticket mint) → mobile cubby spawn + projection.
 *
 * Primary story (browser setting on local 127):
 *   1. Infer mobile platform (header / query / UA / default)
 *   2. Allocate mobile cubby id (MC-NNN) in fleet/CUBBIES.json
 *   3. Bind Bottle Rocket VM session in that cubby (Harbor gateway side)
 *   4. Expose projection URL on 127.0.0.1 for the device browser to open/embed
 *
 * The device does NOT download the VM. adb/idevice sideload is optional/advanced
 * (HARBOR_MOBILE_AUTH_DELIVER=1) and is not the enter-Harbor path.
 *
 * Enabled when HARBOR_MOBILE_AUTH_HOOK is unset or "1"/"true"/"on".
 * Disabled with HARBOR_MOBILE_AUTH_HOOK=0|false|off|no.
 *
 * Mode:
 *   HARBOR_MOBILE_AUTH_HOOK_MODE=queue (default) — write auth-queue JSON (watcher may materialize image)
 *   HARBOR_MOBILE_AUTH_HOOK_MODE=compile — also spawn on-mobile-auth.js (cubby materializer)
 *
 * Never logs bearer tokens or ticket values.
 */
const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");
const serveMgr = require("./brctl-serve-manager");

function enabled() {
  const v = String(process.env.HARBOR_MOBILE_AUTH_HOOK ?? "1").toLowerCase();
  return !(v === "0" || v === "false" || v === "off" || v === "no");
}

function harborRootFrom(cfgRoot) {
  if (process.env.HARBOR_ROOT) return path.resolve(process.env.HARBOR_ROOT);
  const cand = path.resolve(cfgRoot, "..");
  if (fs.existsSync(path.join(cand, "START_HARBOR.cmd"))) return cand;
  return cand;
}

function loadCubbyRegistry(harborRoot) {
  return require(path.join(harborRoot, "mobile-platform", "compiler", "cubbies", "registry.js"));
}

function inferPlatform(req) {
  const hdr = req.headers["x-harbor-mobile-platform"] || req.headers["x-mobile-platform"];
  if (typeof hdr === "string") {
    const p = hdr.trim().toLowerCase();
    if (p === "android" || p === "ios") return { platform: p, source: "header" };
  }
  try {
    const u = new URL(req.url || "/", "http://127.0.0.1");
    const q = (u.searchParams.get("mobile_platform") || u.searchParams.get("platform") || "").toLowerCase();
    if (q === "android" || q === "ios") return { platform: q, source: "query" };
  } catch { /* ignore */ }
  const ua = String(req.headers["user-agent"] || "");
  if (/Android/i.test(ua)) return { platform: "android", source: "user-agent" };
  if (/iPhone|iPad|iPod|iOS/i.test(ua)) return { platform: "ios", source: "user-agent" };
  const def = String(process.env.HARBOR_MOBILE_AUTH_DEFAULT_PLATFORM || "android").toLowerCase();
  return { platform: def === "ios" ? "ios" : "android", source: "config-default" };
}

function ensureDirs(harborRoot) {
  const queue = path.join(harborRoot, "mobile-platform", "compiler", "auth-queue");
  const logs = path.join(harborRoot, "mobile-platform", "compiler", "logs");
  const ver = path.join(harborRoot, "docs", "verification", "mobile-auth-hook");
  const cubbyVer = path.join(harborRoot, "docs", "verification", "mobile-cubby");
  fs.mkdirSync(queue, { recursive: true });
  fs.mkdirSync(logs, { recursive: true });
  fs.mkdirSync(ver, { recursive: true });
  fs.mkdirSync(cubbyVer, { recursive: true });
  return { queue, logs, ver, cubbyVer };
}

/**
 * Fire after a successful /api/ws-ticket mint (principal authenticated, ticket issued).
 * Must not throw into the HTTP handler; must not block on materialize/compile.
 * Returns evidence including cubby_id + projection_url for optional ticket body enrichment.
 */
function onTicketIssued({ cfg, log, req, principal, ticketMeta }) {
  if (!enabled()) return { skipped: true, reason: "disabled" };
  try {
    const harborRoot = harborRootFrom(cfg.root);
    const { queue, logs, ver, cubbyVer } = ensureDirs(harborRoot);
    const inferred = inferPlatform(req);
    const sessionId = `ws-ticket-${Date.now().toString(36)}-${(principal && principal.sub) || "anon"}`;
    const port = (cfg && cfg.port) || process.env.PORT || null;

    // --- Primary: allocate mobile cubby + projection on local 127 ---
    const reg = loadCubbyRegistry(harborRoot);
    const brHint = reg.tryBindBrServe(harborRoot, "pending", null);
    const alloc = reg.allocateMobileCubby({
      harborRoot,
      platform: inferred.platform,
      sessionId,
      principal: principal ? `${principal.tenant}/${principal.sub}` : null,
      deviceId: req.headers["x-harbor-device-id"] || null,
      trigger: "spiral-ws-ticket",
      port,
      brServe: brHint,
    });
    const cubbyId = alloc.cubby.id;
    // Launch per-cubby brctl serve (hex-APDU REPL). Fire-and-forget so ticket path stays non-blocking.
    try {
      serveMgr.setHarborRoot(harborRoot);
      Promise.resolve(serveMgr.ensure(cubbyId, { harborRoot }))
        .then((serveInfo) => {
          try {
            const sessPath = path.join(harborRoot, "mobile-platform", "compiler", "cubbies", "sessions", cubbyId + ".json");
            let s = {};
            if (fs.existsSync(sessPath)) s = JSON.parse(fs.readFileSync(sessPath, "utf8"));
            s.br_serve = serveInfo;
            s.updated_at = new Date().toISOString();
            fs.writeFileSync(sessPath, JSON.stringify(s, null, 2) + "\n", { encoding: "utf8", mode: 0o600 });
          } catch { /* best-effort */ }
          try { if (log && log.info) log.info("mobile.brctl_serve_ready", { cubby_id: cubbyId, pid: serveInfo && serveInfo.pid }); } catch { /* noop */ }
        })
        .catch((serveErr) => {
          try { if (log && log.warn) log.warn("mobile.brctl_serve_start_failed", { cubby_id: cubbyId, reason: serveErr && serveErr.message }); } catch { /* noop */ }
        });
    } catch (serveErr) {
      try { if (log && log.warn) log.warn("mobile.brctl_serve_start_failed", { cubby_id: cubbyId, reason: serveErr && serveErr.message }); } catch { /* noop */ }
    }

    const projectionUrl = alloc.session.projection_url;
    // Refresh projection URL with known port if cfg.port arrived late
    if (port && alloc.cubby.projection) {
      alloc.cubby.projection.url = reg.projectionUrl(cubbyId, port);
      alloc.session.projection_url = alloc.cubby.projection.url;
    }

    const sideload = process.env.HARBOR_MOBILE_AUTH_DELIVER === "1";
    const job = {
      platform: inferred.platform,
      session_id: sessionId,
      cubby_id: cubbyId,
      projection_url: projectionUrl,
      device_id: req.headers["x-harbor-device-id"] || null,
      principal: principal ? `${principal.tenant}/${principal.sub}` : null,
      deliver: sideload,
      primary: "cubby-projection",
      device_download: false,
      trigger: "spiral-ws-ticket",
      platform_source: inferred.source,
      issued_at: new Date().toISOString(),
      expires_in_ms: ticketMeta && ticketMeta.expiresInMs != null ? ticketMeta.expiresInMs : null,
    };
    const fname = `${Date.now()}-${inferred.platform}-${cubbyId}-${(principal && principal.sub) || "anon"}.json`;
    const jobPath = path.join(queue, fname);
    fs.writeFileSync(jobPath, JSON.stringify(job, null, 2) + "\n", { encoding: "utf8", mode: 0o600 });

    const line = `[mobile-auth-hook] cubby=${cubbyId} platform=${job.platform} source=${inferred.source} principal=${job.principal} projection=${projectionUrl}`;
    if (log && typeof log.info === "function") {
      log.info("mobile.cubby_spawn", {
        cubby_id: cubbyId,
        platform: job.platform,
        source: inferred.source,
        principal: job.principal,
        projection_url: projectionUrl,
        device_download: false,
      });
    } else console.log(line);

    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const evidence = {
      fired: true,
      at: job.issued_at,
      primary: "cubby-projection",
      device_download: false,
      cubby_id: cubbyId,
      projection_url: projectionUrl,
      projection_path: `/cubby/${cubbyId}/projection`,
      platform: job.platform,
      platform_source: inferred.source,
      principal: job.principal,
      session_id: sessionId,
      queue_file: path.relative(harborRoot, jobPath).replace(/\\/g, "/"),
      registry: "fleet/CUBBIES.json",
      session_file: alloc.session_path,
      sideload_requested: sideload,
      mode: String(process.env.HARBOR_MOBILE_AUTH_HOOK_MODE || "queue"),
      message: "Projected from Harbor cubby — VM not downloaded to device",
    };
    fs.writeFileSync(path.join(logs, `mobile-auth-hook-${stamp}.json`), JSON.stringify(evidence, null, 2) + "\n");
    fs.writeFileSync(path.join(ver, "LATEST.json"), JSON.stringify(evidence, null, 2) + "\n");
    fs.appendFileSync(path.join(ver, "HOOK_FIRE.log"), `${job.issued_at} ${line}\n`);
    fs.writeFileSync(path.join(cubbyVer, "LATEST_ALLOC.json"), JSON.stringify(evidence, null, 2) + "\n");

    const mode = String(process.env.HARBOR_MOBILE_AUTH_HOOK_MODE || "queue").toLowerCase();
    if (mode === "compile" || mode === "sync-compile" || mode === "materialize") {
      const hookJs = path.join(harborRoot, "mobile-platform", "compiler", "hooks", "on-mobile-auth.js");
      if (fs.existsSync(hookJs)) {
        const args = [hookJs, "--platform", job.platform, "--session", sessionId, "--cubby", cubbyId];
        if (job.device_id) args.push("--device", String(job.device_id));
        if (job.principal) args.push("--principal", String(job.principal));
        if (sideload) args.push("--deliver");
        const child = spawn(process.execPath, args, {
          cwd: harborRoot,
          detached: true,
          stdio: "ignore",
          windowsHide: true,
          env: { ...process.env, HARBOR_ROOT: harborRoot },
        });
        child.unref();
        evidence.materializer_spawned = true;
        fs.writeFileSync(path.join(ver, "LATEST.json"), JSON.stringify(evidence, null, 2) + "\n");
        fs.writeFileSync(path.join(cubbyVer, "LATEST_ALLOC.json"), JSON.stringify(evidence, null, 2) + "\n");
      }
    }
    return evidence;
  } catch (e) {
    try {
      if (log && typeof log.error === "function") log.error("mobile.auth_hook_error", { reason: e && e.message });
      else console.error("[mobile-auth-hook] error:", e && e.message);
    } catch { /* noop */ }
    return { skipped: true, reason: String(e && e.message) };
  }
}

module.exports = { onTicketIssued, enabled, inferPlatform };
