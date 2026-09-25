"use strict";
/**
 * Harbor cubby materializer (reproducible Bottle Rocket VM image prep).
 *
 * Architecture:
 *   Bottle Rocket 3.0 = VM substrate
 *   iOS735_LCTL / LinearAndroid_LCTL = application nodes (Bottle Rocket VMs)
 *   RODEO = sidecar to Linear Android (Gradle substitute) - not a peer app node
 *   Mobile login -> allocate mobile cubby (MC-NNN) -> VM runs in cubby -> project to browser local 127
 *
 * Role: prepare/assemble the VM image for the cubby (brctl assemble). This does NOT
 * mean "download VM to phone storage." Optional --deliver is advanced sideload only.
 *
 * Honest limits: does not flash phones. Uses real trees (junctions). If brctl/adb
 * are absent, packages + manifests and prints next-command handoff.
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawnSync } = require("child_process");

const COMPILER_NAME = "harbor-mobile-vm-node-compiler";
const COMPILER_VERSION = "0.2.0";
const SCHEMA_VERSION = 1;

function harborRootFrom(here) {
  // scripts/ or mobile-platform/compiler/
  const cand = [
    path.resolve(here, "..", ".."),
    path.resolve(here, ".."),
    process.env.HARBOR_ROOT ? path.resolve(process.env.HARBOR_ROOT) : null,
  ].filter(Boolean);
  for (const c of cand) {
    if (fs.existsSync(path.join(c, "START_HARBOR.cmd")) && fs.existsSync(path.join(c, "mobile-platform"))) {
      return c;
    }
  }
  return path.resolve(here, "..", "..");
}

function sha256File(p) {
  const h = crypto.createHash("sha256");
  h.update(fs.readFileSync(p));
  return h.digest("hex");
}

function sha256Buf(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function readLinkRoot(productLinkFile, keys) {
  if (!fs.existsSync(productLinkFile)) return null;
  const text = fs.readFileSync(productLinkFile, "utf8");
  for (const key of keys) {
    const re = new RegExp("^" + key + "=(.*)$", "im");
    const m = text.match(re);
    if (m) return m[1].trim();
  }
  return null;
}

function pin(role, filePath, pins) {
  if (!fs.existsSync(filePath)) {
    pins.push({ role, path: filePath, sha256: null, bytes: 0, missing: true });
    return null;
  }
  const st = fs.statSync(filePath);
  if (st.isDirectory()) {
    pins.push({ role, path: filePath, sha256: null, bytes: 0, is_dir: true });
    return filePath;
  }
  const digest = sha256File(filePath);
  pins.push({ role, path: filePath, sha256: digest, bytes: st.size });
  return digest;
}

function ensureDir(d) {
  fs.mkdirSync(d, { recursive: true });
}

function writeJson(p, obj) {
  ensureDir(path.dirname(p));
  // Stable JSON: sorted keys at top level only is not enough; use deterministic stringify
  fs.writeFileSync(p, stableStringify(obj) + "\n", "utf8");
}

function stableStringify(value) {
  return JSON.stringify(sortKeys(value), null, 2);
}

function sortKeys(v) {
  if (Array.isArray(v)) return v.map(sortKeys);
  if (v && typeof v === "object" && !(v instanceof Date)) {
    const out = {};
    for (const k of Object.keys(v).sort()) out[k] = sortKeys(v[k]);
    return out;
  }
  return v;
}

function copyFile(src, dst) {
  ensureDir(path.dirname(dst));
  fs.copyFileSync(src, dst);
}

function parseArgs(argv) {
  const out = {
    platform: null,
    sessionId: null,
    deviceId: null,
    authPrincipal: null,
    deliver: false,
    cubbyId: null,
    dryRun: false,
    trigger: "manual",
    outRoot: null,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--platform") out.platform = String(argv[++i] || "").toLowerCase();
    else if (a === "--session") out.sessionId = argv[++i];
    else if (a === "--device") out.deviceId = argv[++i];
    else if (a === "--principal") out.authPrincipal = argv[++i];
    else if (a === "--trigger") out.trigger = argv[++i] || "manual";
    else if (a === "--deliver") out.deliver = true;
    else if (a === "--cubby") out.cubbyId = argv[++i];
    else if (a === "--dry-run") out.dryRun = true;
    else if (a === "--out") out.outRoot = argv[++i];
    else if (a === "--help" || a === "-h") out.help = true;
  }
  return out;
}

function usage() {
  return [
    "Usage: node compile-mobile-vm-node.js --platform android|ios [options]",
    "",
    "Options:",
    "  --session ID       auth/enter-Harbor session id",
    "  --device ID        target mobile device id",
    "  --principal NAME   auth principal label (never a secret/token)",
    "  --trigger EVENT    e.g. mobile-auth, manual, dry-run (default manual)",
    "  --cubby ID         mobile cubby id (MC-NNN) this image materializes for",
    "  --deliver          OPTIONAL sideload (adb); demoted - not enter-Harbor",
    "  --dry-run          same as compile; forces deterministic SOURCE_DATE_EPOCH=0 if unset",
    "  --out DIR          override output root (default mobile-platform/compiler/out)",
    "",
    "Reproducibility: output dir is content-addressed from pinned input hashes.",
    "Same pins => same content_hash => same bundle_sha256 (ZIP mtime normalized).",
  ].join("\n");
}

function zipDir(srcDir, zipPath, epochSec) {
  // Prefer PowerShell Compress-Archive with fixed timestamps via a staging copy note:
  // Node without deps: use PowerShell on Windows for zip, then hash the zip.
  // For reproducibility, write a tar-like deterministic file list bundle instead if zip varies.
  // We produce BOTH:
  //   files under outDir (deterministic)
  //   node-bundle.zip via PowerShell (may vary) â€” primary checksum is of MANIFEST + file list hash
  // Actually: build a deterministic .tar via pure JS (ustar-lite) for reproducibility proof.
  const entries = [];
  function walk(rel) {
    const abs = path.join(srcDir, rel);
    const st = fs.statSync(abs);
    if (st.isDirectory()) {
      for (const name of fs.readdirSync(abs).sort()) {
        if (name === "node-bundle.zip" || name === "node-bundle.harbundle" || name === "COMPILE_MANIFEST.json" || name === "AUTH_CONTEXT.json" || name === "LATEST_android.json" || name === "LATEST_ios.json" || name === "delivery") continue;
        walk(rel ? path.join(rel, name) : name);
      }
    } else {
      entries.push({ rel: rel.replace(/\\/g, "/"), buf: fs.readFileSync(abs) });
    }
  }
  walk("");
  // Deterministic archive format: HARBOR_BUNDLE_V1\n then for each file: length|path\n + bytes
  const parts = [Buffer.from("HARBOR_BUNDLE_V1\n", "utf8")];
  for (const e of entries) {
    const header = Buffer.from(`${e.buf.length}|${e.rel}\n`, "utf8");
    parts.push(header, e.buf);
  }
  const blob = Buffer.concat(parts);
  fs.writeFileSync(zipPath, blob);
  return { bytes: blob.length, sha256: sha256Buf(blob), entryCount: entries.length };
}

function runRodeoDoctor(rodeoRoot, steps) {
  const cmd = path.join(rodeoRoot, "rodeo.cmd");
  if (!fs.existsSync(cmd)) {
    steps.push({ id: "rodeo-doctor", status: "skipped", detail: "rodeo.cmd missing" });
    return;
  }
  const r = spawnSync(cmd, ["doctor"], {
    cwd: rodeoRoot,
    encoding: "utf8",
    timeout: 120000,
    shell: true,
    env: process.env,
  });
  if (r.error) {
    steps.push({ id: "rodeo-doctor", status: "skipped", detail: String(r.error.message || r.error) });
    return;
  }
  const ok = r.status === 0;
  steps.push({
    id: "rodeo-doctor",
    status: ok ? "ok" : "failed",
    detail: `exit=${r.status}; ${(r.stdout || r.stderr || "").slice(0, 400)}`,
  });
}

function findBrctl(brRoot, harborRoot) {
  const candidates = [
    path.join(harborRoot, "mobile-platform", "compiler", "bin", "brctl.exe"),
    path.join(harborRoot, "mobile-platform", "compiler", "bin", "brctl"),
    path.join(brRoot, ".build", "brctl.exe"),
    path.join(brRoot, ".build", "brctl"),
    path.join(brRoot, "build", "brctl.exe"),
    path.join(brRoot, "build", "brctl"),
  ];
  return candidates.find((p) => fs.existsSync(p)) || null;
}

function runBrctlAssemble(brRoot, harborRoot, steps, payloadOut) {
  const hit = findBrctl(brRoot || "", harborRoot);
  if (!hit) {
    steps.push({
      id: "brctl-assemble",
      status: "skipped",
      detail: "brctl not built. Run scripts\\build-brctl.cmd (MSYS2 UCRT64 gcc+openssl). Node package still includes substrate pin + app LCTL pins.",
    });
    return null;
  }
  const boot = path.join(brRoot, "examples", "boot.mssl");
  if (!fs.existsSync(boot)) {
    steps.push({ id: "brctl-assemble", status: "skipped", detail: `brctl found at ${hit} but examples/boot.mssl missing` });
    return hit;
  }
  ensureDir(payloadOut);
  const imageOut = path.join(payloadOut, "boot.brimg");
  const r = spawnSync(hit, ["assemble", boot, imageOut], {
    cwd: brRoot,
    encoding: "utf8",
    timeout: 60000,
    windowsHide: true,
  });
  const detailTail = ((r.stdout || "") + (r.stderr || "")).trim().slice(0, 400);
  if (r.status === 0 && fs.existsSync(imageOut)) {
    const st = fs.statSync(imageOut);
    steps.push({
      id: "brctl-assemble",
      status: "ok",
      detail: `assembled ${imageOut} (${st.size} bytes) via ${hit}; ${detailTail || "PASS"}`,
    });
    return hit;
  }
  steps.push({
    id: "brctl-assemble",
    status: "failed",
    detail: `brctl assemble exit=${r.status}: ${detailTail || String(r.error || "unknown")}`,
  });
  return hit;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || !args.platform) {
    console.log(usage());
    process.exit(args.help ? 0 : 2);
  }
  if (!["android", "ios"].includes(args.platform)) {
    console.error("platform must be android|ios");
    process.exit(2);
  }

  const here = __dirname;
  const harborRoot = harborRootFrom(here);
  const mp = path.join(harborRoot, "mobile-platform");
  const outRoot = args.outRoot
    ? path.resolve(args.outRoot)
    : path.join(mp, "compiler", "out");

  const epoch = process.env.SOURCE_DATE_EPOCH
    ? String(process.env.SOURCE_DATE_EPOCH)
    : args.dryRun || args.trigger === "dry-run"
      ? "0"
      : "0"; // always 0 for content-addressed reproducibility unless overridden
  process.env.SOURCE_DATE_EPOCH = epoch;

  const pins = [];
  const steps = [];

  const brMeta = path.join(mp, "bottle-rocket");
  const brLink = path.join(brMeta, "PRODUCT_LINK.txt");
  const brVer = path.join(brMeta, "VERSION");
  pin("bottle-rocket.PRODUCT_LINK", brLink, pins);
  pin("bottle-rocket.VERSION", brVer, pins);

  let brProduct = null;
  const brJunction = path.join(brMeta, "product");
  if (fs.existsSync(path.join(brJunction, "MANIFEST.json"))) brProduct = brJunction;
  else brProduct = readLinkRoot(brLink, ["BOTTLE_ROCKET_PRODUCT_ROOT"]);
  if (brProduct && fs.existsSync(path.join(brProduct, "MANIFEST.json"))) {
    pin("bottle-rocket.MANIFEST.json", path.join(brProduct, "MANIFEST.json"), pins);
    pin("bottle-rocket.README.md", path.join(brProduct, "README.md"), pins);
  } else {
    steps.push({ id: "resolve-substrate", status: "failed", detail: "Bottle Rocket product not linked/found" });
  }

  let appMeta;
  let appIdFile;
  let nodeId;
  let sidecarMeta = null;

  if (args.platform === "android") {
    appMeta = path.join(mp, "nodes", "android-lctl");
    appIdFile = path.join(appMeta, "IDENTITY.json");
    nodeId = "BR-VM-LINEARANDROID-LCTL";
    sidecarMeta = path.join(appMeta, "sidecar-rodeo");
  } else {
    appMeta = path.join(mp, "nodes", "ios-lctl");
    appIdFile = path.join(appMeta, "IDENTITY.json");
    nodeId = "BR-VM-IOS735-LCTL";
  }

  pin("app.IDENTITY.json", appIdFile, pins);
  pin("app.VERSION", path.join(appMeta, "VERSION"), pins);
  pin("app.PRODUCT_LINK.txt", path.join(appMeta, "PRODUCT_LINK.txt"), pins);

  let appProduct = fs.existsSync(path.join(appMeta, "product"))
    ? path.join(appMeta, "product")
    : readLinkRoot(path.join(appMeta, "PRODUCT_LINK.txt"), ["PRODUCT_ROOT"]);

  if (args.platform === "android") {
    if (appProduct) {
      pin("android.TRANSLATION_REPORT.md", path.join(appProduct, "TRANSLATION_REPORT.md"), pins);
      const unitsDir = path.join(appProduct, "units");
      if (fs.existsSync(unitsDir)) {
        const unitFiles = fs.readdirSync(unitsDir).filter((f) => f.endsWith(".lctlc")).sort();
        for (const f of unitFiles) pin(`android.units.${f}`, path.join(unitsDir, f), pins);
      }
    }
    if (sidecarMeta) {
      pin("rodeo.IDENTITY.json", path.join(sidecarMeta, "IDENTITY.json"), pins);
      pin("rodeo.VERSION", path.join(sidecarMeta, "VERSION"), pins);
      pin("rodeo.PRODUCT_LINK.txt", path.join(sidecarMeta, "PRODUCT_LINK.txt"), pins);
      const rodeoProduct = fs.existsSync(path.join(sidecarMeta, "product", "rodeo.cmd"))
        ? path.join(sidecarMeta, "product")
        : readLinkRoot(path.join(sidecarMeta, "PRODUCT_LINK.txt"), ["PRODUCT_ROOT"]);
      if (rodeoProduct) {
        pin("rodeo.rodeo.cmd", path.join(rodeoProduct, "rodeo.cmd"), pins);
        pin("rodeo.bootstrap.json", path.join(rodeoProduct, "rodeo.bootstrap.json"), pins);
        runRodeoDoctor(rodeoProduct, steps);
      } else {
        steps.push({ id: "rodeo-doctor", status: "skipped", detail: "RODEO product not linked" });
      }
    }
  } else if (appProduct) {
    pin("ios.README.md", path.join(appProduct, "README.md"), pins);
    const ev = path.join(appProduct, "evidence", "VERIFY.json");
    if (fs.existsSync(ev)) pin("ios.evidence.VERIFY.json", ev, pins);
    const appUnit = path.join(appProduct, "source", "IOS735_APP.lctlc");
    if (fs.existsSync(appUnit)) pin("ios.source.IOS735_APP.lctlc", appUnit, pins);
    const map = path.join(appProduct, "map", "TRANSLATION_MAP.json");
    if (fs.existsSync(map)) pin("ios.map.TRANSLATION_MAP.json", map, pins);
  }

  // brctl assemble runs after payloadOut is created (see below)

  // Content hash from pins that have sha256
  const pinMaterial = pins
    .filter((p) => p.sha256)
    .map((p) => `${p.role}:${p.sha256}`)
    .sort()
    .join("\n");
  const contentHash = sha256Buf(Buffer.from(pinMaterial + `\nplatform=${args.platform}\nnode=${nodeId}\n`, "utf8"));
  const short = contentHash.slice(0, 12);
  const detPath = path.join(outRoot, "nodes", `${args.platform}-${short}`);

  ensureDir(detPath);
  const identityOut = path.join(detPath, "identity");
  const substrateOut = path.join(detPath, "substrate-pin");
  const appOut = path.join(detPath, "app-node");
  const payloadOut = path.join(detPath, "payload");
  ensureDir(identityOut);
  ensureDir(substrateOut);
  ensureDir(appOut);
  ensureDir(payloadOut);
  if (brProduct) runBrctlAssemble(brProduct, harborRoot, steps, payloadOut);

  // Copy small metadata into package (not bulk LCTL trees)
  for (const f of ["PRODUCT_LINK.txt", "VERSION", "README.md"]) {
    const s = path.join(brMeta, f);
    if (fs.existsSync(s)) copyFile(s, path.join(substrateOut, f));
  }
  if (brProduct && fs.existsSync(path.join(brProduct, "MANIFEST.json"))) {
    copyFile(path.join(brProduct, "MANIFEST.json"), path.join(substrateOut, "MANIFEST.json"));
  }

  for (const f of ["PRODUCT_LINK.txt", "VERSION", "README.md", "IDENTITY.json"]) {
    const s = path.join(appMeta, f);
    if (fs.existsSync(s)) copyFile(s, path.join(appOut, f));
  }

  if (args.platform === "android" && sidecarMeta) {
    const scOut = path.join(appOut, "sidecar-rodeo");
    ensureDir(scOut);
    for (const f of ["PRODUCT_LINK.txt", "VERSION", "README.md", "IDENTITY.json"]) {
      const s = path.join(sidecarMeta, f);
      if (fs.existsSync(s)) copyFile(s, path.join(scOut, f));
    }
  }

  const nodeIdentity = {
    schema_version: 1,
    node_id: `${nodeId}@${short}`,
    base_node_id: nodeId,
    kind: "bottle-rocket-vm-app-node",
    platform: args.platform,
    vm_substrate: "BOTTLE_ROCKET_3.0.0_MODEL_OPERATIONAL_110K",
    content_hash: contentHash,
    android_sidecar: args.platform === "android" ? "RODEO-GRADLE-SUBSTITUTE" : null,
    compiled_by: { name: COMPILER_NAME, version: COMPILER_VERSION },
  };
  writeJson(path.join(identityOut, "NODE_IDENTITY.json"), nodeIdentity);

  const handoff = [
    "# Mobile VM node delivery handoff",
    "",
    `platform: ${args.platform}`,
    `node: ${nodeIdentity.node_id}`,
    `content_hash: ${contentHash}`,
    "",
    "This package is a **Bottle Rocket VM application node** artifact for Harbor.",
    "It does not claim an automatic phone flash.",
    "",
    "## Android deliver (when device + adb present)",
    "  adb push <bundle> /sdcard/HarborMobileNodes/",
    "  adb shell mkdir -p /sdcard/HarborMobileNodes",
    "",
    "## iOS deliver",
    "  Use Apple Configurator / Xcode Devices / your MDM to copy the staged bundle.",
    "  No ideviceinstaller automation is assumed by Harbor.",
    "",
    "## RODEO (Android sidecar)",
    "  RODEO is the Gradle substitute sidecar for Linear Android â€” run builds via rodeo.cmd against the linked product.",
    "",
  ].join("\n");
  fs.writeFileSync(path.join(payloadOut, "DELIVER.md"), handoff, "utf8");

  // Pin list snapshot inside package
  writeJson(path.join(detPath, "INPUT_PINS.json"), { pins });

  const bundlePath = path.join(detPath, "node-bundle.harbundle");
  const bundleInfo = zipDir(detPath, bundlePath, Number(epoch) || 0);

  const created = new Date().toISOString();
  const manifest = {
    schema_version: SCHEMA_VERSION,
    compiler: {
      name: COMPILER_NAME,
      version: COMPILER_VERSION,
      entrypoint: "mobile-platform/compiler/compile-mobile-vm-node.js",
    },
    trigger: {
      event: args.trigger || (args.dryRun ? "dry-run" : "manual"),
      session_id: args.sessionId,
      cubby_id: args.cubbyId || null,
      device_id: args.deviceId || null,
      auth_principal: args.authPrincipal || null,
    },
    platform: args.platform,
    node_id: nodeIdentity.node_id,
    architecture: {
      vm_substrate: "mobile-platform/bottle-rocket",
      app_node_kind: "bottle-rocket-vm-app-node",
      android_sidecar: args.platform === "android" ? "mobile-platform/nodes/android-lctl/sidecar-rodeo" : null,
      rules: [
        "Each mobile platform application node is a Bottle Rocket VM.",
        "RODEO is a sidecar to Linear Android because RODEO is a Gradle substitute.",
      ],
    },
    reproducibility: {
      content_hash: contentHash,
      source_date_epoch: epoch,
      deterministic_path: path.relative(harborRoot, detPath).replace(/\\/g, "/"),
      notes:
        "Output directory name is platform + first 12 hex of content_hash over sorted role:sha256 pins. Bundle is HARBOR_BUNDLE_V1 deterministic concat (not ZIP).",
    },
    inputs: { pins },
    build_steps: steps,
    output: {
      dir: path.relative(harborRoot, detPath).replace(/\\/g, "/"),
      bundle: path.relative(harborRoot, bundlePath).replace(/\\/g, "/"),
      bundle_sha256: bundleInfo.bundle_sha256 || bundleInfo.sha256,
      delivery_staged: path.relative(harborRoot, path.join(payloadOut, "DELIVER.md")).replace(/\\/g, "/"),
    },
    delivery: {
      status: "not_attempted",
      tool: null,
      next_command: null,
      detail: "Pass --deliver to attempt adb/stage handoff.",
    },
    created,
  };

  // Fix bundle sha field
  manifest.output.bundle_sha256 = bundleInfo.sha256;

  writeJson(path.join(detPath, "COMPILE_MANIFEST.json"), manifest);
  writeJson(path.join(detPath, "AUTH_CONTEXT.json"), { session_id: args.sessionId || null, device_id: args.deviceId || null, auth_principal: args.authPrincipal || null, trigger: args.trigger || null, content_hash: contentHash });
  // Also latest pointer
  ensureDir(outRoot);
  writeJson(path.join(outRoot, `LATEST_${args.platform}.json`), {
    node_id: nodeIdentity.node_id,
    content_hash: contentHash,
    dir: manifest.output.dir,
    bundle_sha256: manifest.output.bundle_sha256,
    created,
  });

  console.log(`[compile-mobile-vm-node] platform=${args.platform}`);
  console.log(`[compile-mobile-vm-node] content_hash=${contentHash}`);
  console.log(`[compile-mobile-vm-node] out=${detPath}`);
  console.log(`[compile-mobile-vm-node] bundle_sha256=${bundleInfo.sha256}`);

  let delivery = manifest.delivery;
  if (args.deliver) {
    const deliverJs = path.join(here, "deliver-mobile-vm-node.js");
    const dr = spawnSync(process.execPath, [deliverJs, "--manifest", path.join(detPath, "COMPILE_MANIFEST.json"), "--platform", args.platform], {
      encoding: "utf8",
      shell: false,
    });
    console.log(dr.stdout || "");
    if (dr.stderr) console.error(dr.stderr);
    if (fs.existsSync(path.join(detPath, "COMPILE_MANIFEST.json"))) {
      const updated = JSON.parse(fs.readFileSync(path.join(detPath, "COMPILE_MANIFEST.json"), "utf8"));
      delivery = updated.delivery || delivery;
    }
  }

  // Print machine-readable summary line for hooks
  console.log(
    JSON.stringify({
      ok: true,
      platform: args.platform,
      content_hash: contentHash,
      bundle_sha256: bundleInfo.sha256,
      dir: manifest.output.dir,
      delivery_status: delivery.status,
    })
  );
}

main();
