"use strict";
/** Deliver / stage a compiled mobile VM node bundle toward a device. Never fakes success. */
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

function parseArgs(argv) {
  const o = {
    manifest: null,
    platform: null,
    device: null,
    waitDevice: false,
    waitTimeoutSec: 120,
    pollMs: 2000,
  };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--manifest") o.manifest = argv[++i];
    else if (argv[i] === "--platform") o.platform = argv[++i];
    else if (argv[i] === "--device") o.device = argv[++i];
    else if (argv[i] === "--wait-device") o.waitDevice = true;
    else if (argv[i] === "--wait-timeout") o.waitTimeoutSec = Number(argv[++i] || 120);
    else if (argv[i] === "--poll-ms") o.pollMs = Number(argv[++i] || 2000);
    else if (argv[i] === "--help" || argv[i] === "-h") o.help = true;
  }
  return o;
}

function usage() {
  return [
    "Usage: node deliver-mobile-vm-node.js --manifest PATH [--platform android|ios]",
    "       [--device SERIAL] [--wait-device] [--wait-timeout SEC] [--poll-ms MS]",
    "",
    "Android: uses adb when present (PATH or common SDK locations).",
    "  --wait-device  poll until an adb device is online, then push.",
    "iOS: detects ideviceinstaller / xcrun / Apple tools if present; otherwise stages.",
    "Never reports success without a real tool exit code.",
  ].join("\n");
}

function which(cmd) {
  const r = spawnSync(process.platform === "win32" ? "where.exe" : "which", [cmd], {
    encoding: "utf8",
    windowsHide: true,
  });
  if (r.status !== 0) return null;
  return (r.stdout || "").split(/\r?\n/).map((s) => s.trim()).filter(Boolean)[0] || null;
}

function findAdb() {
  const onPath = which("adb");
  if (onPath) return onPath;
  const home = process.env.USERPROFILE || process.env.HOME || "";
  const local = process.env.LOCALAPPDATA || "";
  const candidates = [
    path.join(local, "Android", "Sdk", "platform-tools", "adb.exe"),
    path.join(home, "AppData", "Local", "Android", "Sdk", "platform-tools", "adb.exe"),
    path.join(home, "Android", "Sdk", "platform-tools", "adb.exe"),
    "C:\\Android\\platform-tools\\adb.exe",
    "C:\\platform-tools\\adb.exe",
    path.join(home, "scoop", "apps", "adb", "current", "adb.exe"),
  ];
  return candidates.find((p) => fs.existsSync(p)) || null;
}

function findIosTools() {
  const tools = {};
  for (const name of ["ideviceinstaller", "idevice_id", "xcrun", "cfgutil"]) {
    const hit = which(name);
    if (hit) tools[name] = hit;
  }
  return tools;
}

function adbDevices(adb) {
  const r = spawnSync(adb, ["devices"], { encoding: "utf8", windowsHide: true, timeout: 15000 });
  const lines = (r.stdout || "").split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
  const devices = [];
  for (const line of lines) {
    if (/^List of devices/i.test(line)) continue;
    const m = /^(\S+)\s+(\S+)/.exec(line);
    if (m) devices.push({ serial: m[1], state: m[2] });
  }
  return { exit: r.status, devices, raw: (r.stdout || "").slice(0, 1000) };
}

function sleepSync(ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    /* busy-wait acceptable for short CLI polls; Atomics.wait if SharedArrayBuffer available */
    try {
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, Math.min(50, end - Date.now()));
    } catch {
      spawnSync(process.execPath, ["-e", `setTimeout(()=>{},${Math.min(50, Math.max(1, end - Date.now()))})`], {
        windowsHide: true,
        timeout: Math.min(100, Math.max(20, end - Date.now() + 20)),
      });
    }
  }
}

function waitForAdbDevice(adb, preferredSerial, timeoutSec, pollMs) {
  const deadline = Date.now() + timeoutSec * 1000;
  const attempts = [];
  while (Date.now() < deadline) {
    const snap = adbDevices(adb);
    attempts.push({ at: new Date().toISOString(), exit: snap.exit, devices: snap.devices });
    const online = snap.devices.filter((d) => d.state === "device");
    const hit = preferredSerial
      ? online.find((d) => d.serial === preferredSerial)
      : online[0];
    if (hit) return { ok: true, device: hit, attempts };
    sleepSync(pollMs);
  }
  return { ok: false, device: null, attempts };
}

function harborRootFromManifest(manifestPath) {
  let dir = path.dirname(manifestPath);
  for (let i = 0; i < 8; i++) {
    if (fs.existsSync(path.join(dir, "START_HARBOR.cmd"))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return path.resolve(path.dirname(manifestPath), "..", "..", "..", "..");
}

function writeEvidence(harborRoot, record) {
  const dirs = [
    path.join(harborRoot, "docs", "verification", "mobile-delivery"),
    path.join(harborRoot, "mobile-platform", "compiler", "logs"),
  ];
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const name = `delivery-${record.platform || "unknown"}-${stamp}.json`;
  for (const d of dirs) {
    fs.mkdirSync(d, { recursive: true });
    fs.writeFileSync(path.join(d, name), JSON.stringify(record, null, 2) + "\n", "utf8");
  }
  const latest = path.join(dirs[0], `LATEST_${record.platform || "unknown"}.json`);
  fs.writeFileSync(latest, JSON.stringify(record, null, 2) + "\n", "utf8");
  return { evidenceFile: path.join(dirs[0], name), latest };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log(usage());
    process.exit(0);
  }
  if (!args.manifest || !fs.existsSync(args.manifest)) {
    console.error("deliver: --manifest PATH required");
    console.log(usage());
    process.exit(2);
  }
  const manifest = JSON.parse(fs.readFileSync(args.manifest, "utf8"));
  const dir = path.resolve(path.dirname(args.manifest));
  const bundle = path.join(dir, "node-bundle.harbundle");
  const platform = args.platform || manifest.platform;
  let device = args.device || (manifest.trigger && manifest.trigger.device_id) || null;
  const harborRoot = harborRootFromManifest(args.manifest);
  const probedAt = new Date().toISOString();

  let delivery = {
    status: "staged",
    tool: null,
    next_command: null,
    detail: "",
    device_serial: null,
    exit_codes: {},
    wait_device: !!args.waitDevice,
  };

  if (!fs.existsSync(bundle)) {
    delivery.status = "failed";
    delivery.detail = "node-bundle.harbundle missing beside manifest";
    manifest.delivery = delivery;
    fs.writeFileSync(args.manifest, JSON.stringify(manifest, null, 2) + "\n", "utf8");
    writeEvidence(harborRoot, { probedAt, platform, delivery, manifest: args.manifest });
    console.error("[deliver] FAILED: missing bundle");
    process.exit(1);
  }

  if (platform === "android") {
    const adb = findAdb();
    if (!adb) {
      delivery.status = "staged";
      delivery.tool = null;
      delivery.next_command = `adb push "${bundle}" /sdcard/HarborMobileNodes/`;
      delivery.detail =
        "adb not found on PATH or common Android SDK paths. Bundle staged. Install platform-tools, connect device, or re-run with --wait-device once adb exists.";
      console.log("[deliver] staged (no adb): " + delivery.next_command);
    } else {
      let target = device;
      let waitInfo = null;
      const initial = adbDevices(adb);
      delivery.exit_codes.adb_devices_initial = initial.exit;
      const online = initial.devices.filter((d) => d.state === "device");
      if (!target && online.length) target = online[0].serial;

      if ((!target || !online.some((d) => d.serial === target)) && args.waitDevice) {
        console.log(`[deliver] waiting up to ${args.waitTimeoutSec}s for adb device...`);
        waitInfo = waitForAdbDevice(adb, device, args.waitTimeoutSec, args.pollMs);
        if (waitInfo.ok) {
          target = waitInfo.device.serial;
          console.log(`[deliver] device online: ${target}`);
        } else {
          delivery.status = "staged";
          delivery.tool = adb;
          delivery.device_serial = null;
          delivery.next_command = `adb push "${bundle}" /sdcard/HarborMobileNodes/`;
          delivery.detail = `wait-device timed out after ${args.waitTimeoutSec}s; no online adb device. Bundle remains staged.`;
          delivery.wait_attempts = waitInfo.attempts.length;
          console.log("[deliver] wait-device timeout — staged only");
          manifest.delivery = delivery;
          fs.writeFileSync(args.manifest, JSON.stringify(manifest, null, 2) + "\n", "utf8");
          const ev = writeEvidence(harborRoot, {
            probedAt,
            platform,
            adb,
            devices_initial: initial.devices,
            wait: waitInfo,
            delivery,
            bundle,
            manifest: args.manifest,
          });
          console.log(JSON.stringify({ ok: true, delivery, evidence: ev.evidenceFile }));
          process.exit(0);
        }
      }

      if (!target) {
        delivery.status = "staged";
        delivery.tool = adb;
        delivery.next_command = `adb push "${bundle}" /sdcard/HarborMobileNodes/`;
        delivery.detail = `adb present (${adb}) but no online device. devices=${JSON.stringify(initial.devices)}. Re-run with --wait-device or connect a device.`;
        console.log("[deliver] staged (adb, no device): " + delivery.detail);
      } else {
        const serialArgs = ["-s", target];
        const mk = spawnSync(adb, serialArgs.concat(["shell", "mkdir", "-p", "/sdcard/HarborMobileNodes"]), {
          encoding: "utf8",
          windowsHide: true,
          timeout: 30000,
        });
        const push = spawnSync(adb, serialArgs.concat(["push", bundle, "/sdcard/HarborMobileNodes/"]), {
          encoding: "utf8",
          windowsHide: true,
          timeout: 120000,
        });
        delivery.exit_codes.mkdir = mk.status;
        delivery.exit_codes.push = push.status;
        delivery.device_serial = target;
        delivery.tool = adb;
        if (push.status === 0) {
          delivery.status = "sent";
          delivery.detail = ((push.stdout || "") + (push.stderr || "")).slice(0, 500);
          console.log(`[deliver] adb push OK serial=${target}`);
        } else {
          delivery.status = "failed";
          delivery.next_command = `adb -s ${target} push "${bundle}" /sdcard/HarborMobileNodes/`;
          delivery.detail = `adb push failed exit=${push.status}: ${((push.stderr || push.stdout || "")).slice(0, 400)}`;
          console.log("[deliver] adb push FAILED — bundle remains staged");
        }
      }
      if (waitInfo) delivery.wait_attempts = waitInfo.attempts.length;
    }
  } else {
    const iosTools = findIosTools();
    const toolNames = Object.keys(iosTools);
    delivery.status = "staged";
    delivery.tool = toolNames.length ? toolNames.join(",") : null;
    delivery.next_command =
      "Copy node-bundle.harbundle via Xcode Devices / Apple Configurator / MDM (no automatic idevice push in this Harbor release).";
    delivery.detail = toolNames.length
      ? `iOS tools detected (${toolNames.join(", ")}) but Harbor does not auto-install; staged only.`
      : "iOS delivery is staged only (no ideviceinstaller/xcrun/cfgutil on PATH).";
    console.log("[deliver] iOS staged: " + delivery.detail);
  }

  manifest.delivery = delivery;
  fs.writeFileSync(args.manifest, JSON.stringify(manifest, null, 2) + "\n", "utf8");
  const stageDir = path.join(dir, "delivery");
  fs.mkdirSync(stageDir, { recursive: true });
  fs.writeFileSync(path.join(stageDir, "DELIVERY_STATUS.json"), JSON.stringify(delivery, null, 2) + "\n", "utf8");
  const ev = writeEvidence(harborRoot, {
    probedAt,
    platform,
    delivery,
    bundle,
    manifest: args.manifest,
  });
  console.log(JSON.stringify({ ok: delivery.status !== "failed", delivery, evidence: ev.evidenceFile }));
  process.exit(delivery.status === "failed" ? 1 : 0);
}

main();