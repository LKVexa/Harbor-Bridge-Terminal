"use strict";
/** Deliver / stage a compiled mobile VM node bundle toward a device. Never fakes success. */
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

function parseArgs(argv) {
  const o = { manifest: null, platform: null, device: null };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--manifest") o.manifest = argv[++i];
    else if (argv[i] === "--platform") o.platform = argv[++i];
    else if (argv[i] === "--device") o.device = argv[++i];
  }
  return o;
}

function which(cmd) {
  const r = spawnSync(process.platform === "win32" ? "where.exe" : "which", [cmd], { encoding: "utf8" });
  if (r.status !== 0) return null;
  return (r.stdout || "").split(/\r?\n/).map((s) => s.trim()).filter(Boolean)[0] || null;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.manifest || !fs.existsSync(args.manifest)) {
    console.error("deliver: --manifest PATH required");
    process.exit(2);
  }
  const manifest = JSON.parse(fs.readFileSync(args.manifest, "utf8"));
  const dir = path.resolve(path.dirname(args.manifest));
  const bundle = path.join(dir, "node-bundle.harbundle");
  const platform = args.platform || manifest.platform;
  const device = args.device || (manifest.trigger && manifest.trigger.device_id);

  let delivery = {
    status: "staged",
    tool: null,
    next_command: null,
    detail: "",
  };

  if (platform === "android") {
    const adb = which("adb");
    if (!adb) {
      delivery.status = "staged";
      delivery.tool = null;
      delivery.next_command = `adb push "${bundle}" /sdcard/HarborMobileNodes/`;
      delivery.detail = "adb not on PATH. Bundle staged. Connect device, enable debugging, then run next_command (mkdir on device first if needed).";
      console.log("[deliver] staged (no adb): " + delivery.next_command);
    } else {
      const serialArgs = device ? ["-s", device] : [];
      const mk = spawnSync(adb, serialArgs.concat(["shell", "mkdir", "-p", "/sdcard/HarborMobileNodes"]), { encoding: "utf8" });
      const push = spawnSync(adb, serialArgs.concat(["push", bundle, "/sdcard/HarborMobileNodes/"]), { encoding: "utf8" });
      if (push.status === 0) {
        delivery.status = "sent";
        delivery.tool = adb;
        delivery.detail = (push.stdout || "").slice(0, 500);
        console.log("[deliver] adb push OK");
      } else {
        delivery.status = "failed";
        delivery.tool = adb;
        delivery.next_command = `adb push "${bundle}" /sdcard/HarborMobileNodes/`;
        delivery.detail = `adb push failed exit=${push.status}: ${(push.stderr || push.stdout || "").slice(0, 400)}`;
        console.log("[deliver] adb push FAILED — bundle remains staged");
      }
    }
  } else {
    delivery.status = "staged";
    delivery.tool = null;
    delivery.next_command = "Copy node-bundle.harbundle via Xcode Devices / Apple Configurator / MDM (no automatic idevice push).";
    delivery.detail = "iOS delivery is staged only in this Harbor release.";
    console.log("[deliver] iOS staged: " + delivery.next_command);
  }

  manifest.delivery = delivery;
  fs.writeFileSync(args.manifest, JSON.stringify(manifest, null, 2) + "\n", "utf8");
  const stageDir = path.join(dir, "delivery");
  fs.mkdirSync(stageDir, { recursive: true });
  fs.writeFileSync(path.join(stageDir, "DELIVERY_STATUS.json"), JSON.stringify(delivery, null, 2) + "\n", "utf8");
  console.log(JSON.stringify({ ok: delivery.status !== "failed", delivery }));
  process.exit(delivery.status === "failed" ? 1 : 0);
}

main();
