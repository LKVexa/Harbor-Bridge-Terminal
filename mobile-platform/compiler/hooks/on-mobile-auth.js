"use strict";
/**
 * Hook: mobile platform authenticating / entering Harbor.
 * Compiles a Bottle Rocket VM application node for the platform and optionally delivers.
 *
 * Invoked by:
 *   scripts\on-mobile-auth.cmd --platform android|ios [--session S] [--device D]
 *   or a future SPIRAL/mobile bridge when a device enters Harbor.
 *
 * Does NOT fire on ordinary operator ACCESS_TOKEN sign-in unless you wire it explicitly.
 */
const path = require("path");
const { spawnSync } = require("child_process");

function parseArgs(argv) {
  const o = { platform: null, session: null, device: null, principal: null, deliver: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--platform") o.platform = String(argv[++i] || "").toLowerCase();
    else if (argv[i] === "--session") o.session = argv[++i];
    else if (argv[i] === "--device") o.device = argv[++i];
    else if (argv[i] === "--principal") o.principal = argv[++i];
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
  const a = ["--platform", args.platform, "--trigger", "mobile-auth"];
  if (args.session) a.push("--session", args.session);
  if (args.device) a.push("--device", args.device);
  if (args.principal) a.push("--principal", args.principal);
  if (args.deliver || process.env.HARBOR_MOBILE_AUTH_DELIVER === "1") a.push("--deliver");

  console.log(`[on-mobile-auth] compiling Bottle Rocket VM node for ${args.platform} (enter-Harbor)`);
  const r = spawnSync(process.execPath, [compiler, ...a], { encoding: "utf8", stdio: "inherit" });
  process.exit(r.status == null ? 1 : r.status);
}

main();
