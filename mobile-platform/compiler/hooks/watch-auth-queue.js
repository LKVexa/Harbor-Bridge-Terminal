"use strict";
/**
 * Optional queue watcher: drop JSON files into mobile-platform/compiler/auth-queue/
 * { "platform":"android", "session_id":"...", "device_id":"...", "principal":"..." }
 * to trigger on-mobile-auth. No secrets in queue files.
 */
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const queue = path.join(__dirname, "..", "auth-queue");
const processed = path.join(queue, "processed");
fs.mkdirSync(processed, { recursive: true });

function handle(file) {
  const abs = path.join(queue, file);
  let data;
  try {
    data = JSON.parse(fs.readFileSync(abs, "utf8"));
  } catch (e) {
    console.error("skip bad json", file, e.message);
    return;
  }
  if (!data.platform) return;
  const hook = path.join(__dirname, "on-mobile-auth.js");
  const args = [hook, "--platform", String(data.platform).toLowerCase()];
  if (data.session_id) args.push("--session", String(data.session_id));
  if (data.device_id) args.push("--device", String(data.device_id));
  if (data.principal) args.push("--principal", String(data.principal));
  if (data.deliver) args.push("--deliver");
  console.log("[auth-queue] processing", file);
  spawnSync(process.execPath, args, { stdio: "inherit" });
  fs.renameSync(abs, path.join(processed, `${Date.now()}-${file}`));
}

console.log("[auth-queue] watching", queue);
setInterval(() => {
  for (const f of fs.readdirSync(queue)) {
    if (!f.endsWith(".json")) continue;
    handle(f);
  }
}, 2000);
