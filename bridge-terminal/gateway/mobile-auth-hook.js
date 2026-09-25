"use strict";
/**
 * SPIRAL / Harbor gateway hook: successful auth (ws-ticket mint) → mobile-auth path.
 *
 * Enabled when HARBOR_MOBILE_AUTH_HOOK is unset or "1"/"true"/"on".
 * Disabled with HARBOR_MOBILE_AUTH_HOOK=0|false|off|no.
 *
 * Platform selection (first hit wins):
 *   1. Header X-Harbor-Mobile-Platform: android|ios
 *   2. Query ?mobile_platform= / ?platform=
 *   3. User-Agent heuristics (Android / iPhone|iPad|iOS)
 *   4. HARBOR_MOBILE_AUTH_DEFAULT_PLATFORM (default: android)
 *
 * Mode:
 *   HARBOR_MOBILE_AUTH_HOOK_MODE=queue (default) — write auth-queue JSON (watcher drains)
 *   HARBOR_MOBILE_AUTH_HOOK_MODE=compile — also spawn on-mobile-auth.js (fire-and-forget)
 *
 * Never logs bearer tokens or ticket values.
 */
const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");

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
  fs.mkdirSync(queue, { recursive: true });
  fs.mkdirSync(logs, { recursive: true });
  fs.mkdirSync(ver, { recursive: true });
  return { queue, logs, ver };
}

/**
 * Fire after a successful /api/ws-ticket mint (principal authenticated, ticket issued).
 * Must not throw into the HTTP handler; must not block on compile.
 */
function onTicketIssued({ cfg, log, req, principal, ticketMeta }) {
  if (!enabled()) return { skipped: true, reason: "disabled" };
  try {
    const harborRoot = harborRootFrom(cfg.root);
    const { queue, logs, ver } = ensureDirs(harborRoot);
    const inferred = inferPlatform(req);
    const sessionId = `ws-ticket-${Date.now().toString(36)}-${(principal && principal.sub) || "anon"}`;
    const job = {
      platform: inferred.platform,
      session_id: sessionId,
      device_id: req.headers["x-harbor-device-id"] || null,
      principal: principal ? `${principal.tenant}/${principal.sub}` : null,
      deliver: process.env.HARBOR_MOBILE_AUTH_DELIVER === "1",
      trigger: "spiral-ws-ticket",
      platform_source: inferred.source,
      issued_at: new Date().toISOString(),
      expires_in_ms: ticketMeta && ticketMeta.expiresInMs != null ? ticketMeta.expiresInMs : null,
    };
    const fname = `${Date.now()}-${inferred.platform}-${(principal && principal.sub) || "anon"}.json`;
    const jobPath = path.join(queue, fname);
    fs.writeFileSync(jobPath, JSON.stringify(job, null, 2) + "\n", { encoding: "utf8", mode: 0o600 });

    const line = `[mobile-auth-hook] fired platform=${job.platform} source=${inferred.source} principal=${job.principal} queue=${fname}`;
    if (log && typeof log.info === "function") log.info("mobile.auth_hook", { platform: job.platform, source: inferred.source, principal: job.principal, queue: fname });
    else console.log(line);

    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const evidence = {
      fired: true,
      at: job.issued_at,
      platform: job.platform,
      platform_source: inferred.source,
      principal: job.principal,
      session_id: sessionId,
      queue_file: path.relative(harborRoot, jobPath).replace(/\\/g, "/"),
      mode: String(process.env.HARBOR_MOBILE_AUTH_HOOK_MODE || "queue"),
    };
    fs.writeFileSync(path.join(logs, `mobile-auth-hook-${stamp}.json`), JSON.stringify(evidence, null, 2) + "\n");
    fs.writeFileSync(path.join(ver, "LATEST.json"), JSON.stringify(evidence, null, 2) + "\n");
    fs.appendFileSync(path.join(ver, "HOOK_FIRE.log"), `${job.issued_at} ${line}\n`);

    const mode = String(process.env.HARBOR_MOBILE_AUTH_HOOK_MODE || "queue").toLowerCase();
    if (mode === "compile" || mode === "sync-compile") {
      const hookJs = path.join(harborRoot, "mobile-platform", "compiler", "hooks", "on-mobile-auth.js");
      if (fs.existsSync(hookJs)) {
        const args = [hookJs, "--platform", job.platform, "--session", sessionId];
        if (job.device_id) args.push("--device", String(job.device_id));
        if (job.principal) args.push("--principal", String(job.principal));
        if (job.deliver) args.push("--deliver");
        const child = spawn(process.execPath, args, {
          cwd: harborRoot,
          detached: true,
          stdio: "ignore",
          windowsHide: true,
          env: { ...process.env, HARBOR_ROOT: harborRoot },
        });
        child.unref();
        evidence.compile_spawned = true;
        fs.writeFileSync(path.join(ver, "LATEST.json"), JSON.stringify(evidence, null, 2) + "\n");
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