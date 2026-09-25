"use strict";
/**
 * Harbor cubby registry — Qnode + containership + mobile cubbies.
 * Mobile cubbies (MC-NNN) are allocated on SPIRAL/ws-ticket mobile login.
 * VM stays in the cubby; browser gets a projection on local 127.
 */
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const REGISTRY_REL = path.join("fleet", "CUBBIES.json");
const SESSIONS_REL = path.join("mobile-platform", "compiler", "cubbies", "sessions");

function harborRootFrom(hint) {
  if (process.env.HARBOR_ROOT) return path.resolve(process.env.HARBOR_ROOT);
  if (hint) {
    const c = path.resolve(hint);
    if (fs.existsSync(path.join(c, "START_HARBOR.cmd"))) return c;
    const up = path.resolve(c, "..");
    if (fs.existsSync(path.join(up, "START_HARBOR.cmd"))) return up;
    const up2 = path.resolve(c, "..", "..");
    if (fs.existsSync(path.join(up2, "START_HARBOR.cmd"))) return up2;
  }
  return path.resolve(__dirname, "..", "..", "..");
}

function registryPath(harborRoot) {
  return path.join(harborRoot, REGISTRY_REL);
}

function sessionsDir(harborRoot) {
  const d = path.join(harborRoot, SESSIONS_REL);
  fs.mkdirSync(d, { recursive: true });
  return d;
}

function readRegistry(harborRoot) {
  const p = registryPath(harborRoot);
  if (!fs.existsSync(p)) throw new Error("missing " + REGISTRY_REL);
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function writeRegistry(harborRoot, doc) {
  const mobile = Array.isArray(doc.mobile_cubbies) ? doc.mobile_cubbies : [];
  doc.counts = {
    qnode_cubbies: (doc.qnode_cubbies || []).length,
    containership_cubbies: (doc.containership_cubbies || []).length,
    mobile_cubbies: mobile.length,
    total: (doc.qnode_cubbies || []).length + (doc.containership_cubbies || []).length + mobile.length,
  };
  if (!doc.growth) doc.growth = {};
  doc.growth.next_mobile_seq = nextSeqFrom(mobile);
  doc.generated = new Date().toISOString();
  fs.writeFileSync(registryPath(harborRoot), JSON.stringify(doc, null, 2) + "\n", "utf8");
  return doc;
}

function nextSeqFrom(mobile) {
  let max = 0;
  for (const m of mobile || []) {
    const match = String(m.id || "").match(/^MC-(\d+)$/i);
    if (match) max = Math.max(max, parseInt(match[1], 10));
  }
  return max + 1;
}

function formatMobileId(seq) {
  return "MC-" + String(seq).padStart(3, "0");
}

function projectionUrl(cubbyId, port) {
  const p = port || process.env.PORT || "10000";
  return `http://127.0.0.1:${p}/cubby/${encodeURIComponent(cubbyId)}/projection`;
}

/**
 * Allocate a new mobile cubby and bind a projection session.
 * Does NOT download a VM to the device.
 */
function allocateMobileCubby(opts) {
  const harborRoot = harborRootFrom(opts && opts.harborRoot);
  const doc = readRegistry(harborRoot);
  if (!Array.isArray(doc.mobile_cubbies)) doc.mobile_cubbies = [];
  const seq = (doc.growth && doc.growth.next_mobile_seq) || nextSeqFrom(doc.mobile_cubbies);
  const id = formatMobileId(seq);
  const sessionId =
    (opts && opts.sessionId) ||
    `br-proj-${Date.now().toString(36)}-${crypto.randomBytes(4).toString("hex")}`;
  const platform = (opts && opts.platform) || "android";
  const port = (opts && opts.port) || process.env.PORT || null;
  const now = new Date().toISOString();
  const projUrl = projectionUrl(id, port);

  const cubby = {
    id,
    kind: "mobile-cubby",
    family: "cubby",
    platform,
    session_id: sessionId,
    principal: (opts && opts.principal) || null,
    device_id: (opts && opts.deviceId) || null,
    trigger: (opts && opts.trigger) || "spiral-ws-ticket",
    created_at: now,
    status: "live",
    operable: true,
    operable_when: "projection session live",
    vm_location: "harbor-cubby",
    device_download: false,
    projection: {
      url: projUrl,
      path: `/cubby/${id}/projection`,
      bind: "127.0.0.1",
      note: "VM runs in Harbor cubby; browser receives projected view — not a downloaded VM",
    },
    materializer: {
      role: "cubby-materializer",
      brctl: "assemble (image prep for cubby, not phone storage)",
    },
    br_serve: (opts && opts.brServe) || null,
  };

  doc.mobile_cubbies.push(cubby);
  if (!doc.growth) doc.growth = {};
  doc.growth.next_mobile_seq = seq + 1;
  writeRegistry(harborRoot, doc);

  const session = {
    cubby_id: id,
    session_id: sessionId,
    platform,
    status: "live",
    operable: true,
    created_at: now,
    updated_at: now,
    projection_url: projUrl,
    projection_path: `/cubby/${id}/projection`,
    bind: "127.0.0.1",
    device_download: false,
    message: "Projected from Harbor cubby — VM not downloaded to device",
    principal: cubby.principal,
    br_serve: cubby.br_serve,
  };
  const sessPath = path.join(sessionsDir(harborRoot), `${id}.json`);
  fs.writeFileSync(sessPath, JSON.stringify(session, null, 2) + "\n", { encoding: "utf8", mode: 0o600 });

  return { cubby, session, registry_path: REGISTRY_REL.replace(/\\/g, "/"), session_path: path.relative(harborRoot, sessPath).replace(/\\/g, "/") };
}

function getCubby(harborRoot, id) {
  const doc = readRegistry(harborRootFrom(harborRoot));
  const all = [
    ...(doc.qnode_cubbies || []),
    ...(doc.containership_cubbies || []),
    ...(doc.mobile_cubbies || []),
  ];
  return all.find((c) => c.id === id) || null;
}

function listCubbies(harborRoot) {
  const root = harborRootFrom(harborRoot);
  const doc = readRegistry(root);
  return {
    vocabulary: doc.vocabulary,
    naming: doc.naming,
    growth: doc.growth,
    projection: doc.projection,
    counts: doc.counts,
    qnode_cubbies: doc.qnode_cubbies || [],
    containership_cubbies: doc.containership_cubbies || [],
    mobile_cubbies: doc.mobile_cubbies || [],
  };
}

function readSession(harborRoot, cubbyId) {
  const p = path.join(sessionsDir(harborRootFrom(harborRoot)), `${cubbyId}.json`);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function tryBindBrServe(harborRoot, cubbyId, statePath) {
  // Record brctl serve bind hint. Harbor gateway brctl-serve-manager.js launches
  // `brctl serve --state <prefix>` per MC cubby and proxies the hex-APDU REPL into
  // /cubby/:id/projection (stdio — not a native HTTP framebuffer).
  const brctl = path.join(harborRoot, "mobile-platform", "compiler", "bin", "brctl.exe");
  const alt = path.join(harborRoot, "mobile-platform", "compiler", "bin", "brctl");
  const hit = fs.existsSync(brctl) ? brctl : fs.existsSync(alt) ? alt : null;
  if (!hit) return { attempted: false, reason: "brctl missing" };
  const prefix = statePath || path.join(
    harborRoot, "mobile-platform", "compiler", "cubbies", "serve-states", String(cubbyId), "br"
  );
  return {
    attempted: true,
    brctl: hit,
    state_prefix: prefix,
    serve_args: ["serve", "--state", prefix],
    proxy: {
      http_status: `/cubby/${cubbyId}/serve/status`,
      http_apdu: `/cubby/${cubbyId}/serve/apdu`,
      ws: `/cubby/${cubbyId}/serve/ws`,
    },
    surface: "hex-APDU REPL (not a framebuffer)",
    note: "Gateway brctl-serve-manager launches serve per cubby; projection page proxies APDUs.",
  };
}

module.exports = {
  harborRootFrom,
  readRegistry,
  writeRegistry,
  allocateMobileCubby,
  getCubby,
  listCubbies,
  readSession,
  projectionUrl,
  tryBindBrServe,
  formatMobileId,
  REGISTRY_REL,
  SESSIONS_REL,
};
