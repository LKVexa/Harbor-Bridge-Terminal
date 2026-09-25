"use strict";
/**
 * Hook: mobile platform authenticating / entering Harbor via cubby projection.
 *
 * Primary path: cubby already allocated by gateway mobile-auth-hook (MC-NNN) with
 * projection on local 127. This script is the **cubby materializer** — it prepares
 * / assembles the Bottle Rocket VM image for the cubby (brctl assemble). It does
 * NOT mean "download VM to phone storage."
 *
 * Optional --deliver runs advanced adb/idevice sideload (demoted; not enter-Harbor).
 *
 * Invoked by:
 *   scripts\on-mobile-auth.cmd --platform android|ios [--session S] [--cubby MC-001] [--device D]
 *   auth-queue watcher after SPIRAL ws-ticket
 */
const path = require("path");
const { spawnSync } = require("child_process");

function parseArgs(argv) {
  const o = { platform: null, session: null, device: null, principal: null, cubby: null, deliver: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--platform") o.platform = String(argv[++i] || "").toLowerCase();
    else if (argv[i] === "--session") o.session = argv[++i];
    else if (argv[i] === "--device") o.device = argv[++i];
    else if (argv[i] === "--principal") o.principal = argv[++i];
    else if (argv[i] === "--cubby") o.cubby = argv[++i];
    else if (argv[i] === "--deliver") o.deliver = true;
  }
  return o;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.platform || !["android", "ios"].includes(args.platform)) {
    console.error("on-mobile-auth: --platform android|ios required");
    process.exit(2);
  }
  const compiler = path.join(__dirname, "..", "compile-mobile-vm-node.js");
  const a = ["--platform", args.platform, "--trigger", "mobile-auth-cubby-materializer"];
  if (args.session) a.push("--session", args.session);
  if (args.device) a.push("--device", args.device);
  if (args.principal) a.push("--principal", args.principal);
  if (args.cubby) a.push("--cubby", args.cubby);
  if (args.deliver || process.env.HARBOR_MOBILE_AUTH_DELIVER === "1") a.push("--deliver");

  console.log(`[on-mobile-auth] cubby materializer for ${args.platform}` + (args.cubby ? ` cubby=${args.cubby}` : "") + " (VM stays in cubby; not a device download)");
  const r = spawnSync(process.execPath, [compiler, ...a], { encoding: "utf8", stdio: "inherit" });
  process.exit(r.status == null ? 1 : r.status);
}

main();
