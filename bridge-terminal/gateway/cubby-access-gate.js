"use strict";
/**
 * Cubby access gate — desktop vs mobile entry rules.
 *
 * Desktop (no mobile platform signal):
 *   May attach/project Qnode (QN-*) and containership (CS-*) cubbies directly
 *   via Harbor local 127. No Bottle Rocket mobile cubby required.
 *
 * Mobile (X-Harbor-Mobile-Platform / UA / mobile_platform query / existing MC session):
 *   MUST have a live Bottle Rocket mobile cubby (MC-*) for this principal first.
 *   That BR cubby offloads/projects for lower-capability devices. Only then may
 *   the mobile session attach to or request QVM / containership cubbies
 *   (proxied via the BR mobile cubby).
 *
 * Creating a QVM/containership cubby from mobile also requires the BR gate.
 */
const path = require("node:path");

function loadRegistry(harborRoot) {
  return require(path.join(harborRoot, "mobile-platform", "compiler", "cubbies", "registry.js"));
}

function isMobileClient(req) {
  const hdr = req.headers["x-harbor-mobile-platform"] || req.headers["x-mobile-platform"];
  if (typeof hdr === "string" && hdr.trim()) return { mobile: true, source: "header", platform: hdr.trim().toLowerCase() };
  try {
    const u = new URL(req.url || "/", "http://127.0.0.1");
    const q = (u.searchParams.get("mobile_platform") || u.searchParams.get("platform") || "").toLowerCase();
    if (q === "android" || q === "ios") return { mobile: true, source: "query", platform: q };
    if (u.searchParams.get("client") === "mobile") return { mobile: true, source: "query-client", platform: null };
  } catch { /* ignore */ }
  const ua = String(req.headers["user-agent"] || "");
  if (/Android/i.test(ua)) return { mobile: true, source: "user-agent", platform: "android" };
  if (/iPhone|iPad|iPod|iOS/i.test(ua)) return { mobile: true, source: "user-agent", platform: "ios" };
  return { mobile: false, source: "desktop", platform: null };
}

function principalKey(principal) {
  if (!principal) return null;
  if (typeof principal === "string") return principal;
  if (principal.tenant && principal.sub) return `${principal.tenant}/${principal.sub}`;
  return null;
}

function findLiveMobileBrCubby(harborRoot, principal) {
  const reg = loadRegistry(harborRoot);
  const doc = reg.readRegistry(harborRoot);
  const key = principalKey(principal);
  const list = doc.mobile_cubbies || [];
  const live = list.filter((c) => c.status === "live" && c.operable !== false);
  if (!key) return live[live.length - 1] || null;
  const mine = live.filter((c) => c.principal === key);
  return mine[mine.length - 1] || null;
}

function cubbyKind(id) {
  if (!id) return null;
  if (/^MC-/i.test(id)) return "mobile-cubby";
  if (/^QN-/i.test(id)) return "qnode-cubby";
  if (/^CS-/i.test(id)) return "containership-cubby";
  return "unknown";
}

/**
 * Gate an attach/projection/create request for a target cubby.
 * Returns { ok, path, status?, error?, ... }.
 */
function checkAccess({ harborRoot, req, principal, targetCubbyId, action }) {
  const client = isMobileClient(req);
  const kind = cubbyKind(targetCubbyId);
  const act = action || "attach";

  // Desktop: direct local-127 projection for any cubby family (no BR mobile required)
  if (!client.mobile) {
    return {
      ok: true,
      path: "desktop-direct",
      client: "desktop",
      action: act,
      target: targetCubbyId,
      target_kind: kind,
      device_download: false,
      note: "Desktop local-127 cubby projection — no mobile BR cubby required",
    };
  }

  // Mobile targeting its own BR cubby family: always allowed (create/project MC-*)
  if (kind === "mobile-cubby" || act === "create-mobile-br" || !targetCubbyId) {
    return {
      ok: true,
      path: "mobile-br-cubby",
      client: "mobile",
      platform: client.platform,
      action: act,
      target: targetCubbyId,
      target_kind: kind,
      device_download: false,
      note: "Mobile Bottle Rocket cubby path (prerequisite / primary)",
    };
  }

  // Mobile wanting QVM or containership: require live BR mobile cubby first
  if (kind === "qnode-cubby" || kind === "containership-cubby") {
    const br = findLiveMobileBrCubby(harborRoot, principal);
    if (!br) {
      return {
        ok: false,
        status: 403,
        error: "mobile_br_cubby_required",
        client: "mobile",
        platform: client.platform,
        action: act,
        target: targetCubbyId,
        target_kind: kind,
        device_download: false,
        message:
          "Mobile device must create a live Bottle Rocket mobile cubby (MC-*) before attaching to QVM or containership cubbies. The BR cubby offloads/projects for the device.",
        remediation: {
          step1: "POST /api/ws-ticket with X-Harbor-Mobile-Platform: android|ios (spawns MC-NNN)",
          step2: "Open projection_url on local 127",
          step3: "Retry attach with X-Harbor-Mobile-Cubby: MC-NNN (or same principal live cubby)",
        },
      };
    }
    return {
      ok: true,
      path: "mobile-via-br-cubby",
      client: "mobile",
      platform: client.platform,
      action: act,
      target: targetCubbyId,
      target_kind: kind,
      br_cubby_id: br.id,
      br_session_id: br.session_id,
      br_projection_url: br.projection && br.projection.url,
      device_download: false,
      note: "Mobile session proxied via live Bottle Rocket cubby to QVM/containership cubby",
    };
  }

  return {
    ok: true,
    path: "mobile-other",
    client: "mobile",
    action: act,
    target: targetCubbyId,
    target_kind: kind,
    device_download: false,
  };
}

module.exports = {
  isMobileClient,
  findLiveMobileBrCubby,
  cubbyKind,
  checkAccess,
  principalKey,
};
