"use strict";
/**
 * Verify per-cubby brctl serve launch + HTTP APDU proxy into projection.
 */
const fs = require("fs");
const path = require("path");
const http = require("http");
const net = require("net");
const { spawn } = require("child_process");

const harborRoot = path.resolve(__dirname, "..", "..", "..");
process.chdir(harborRoot);
const verDir = path.join(harborRoot, "docs", "verification", "brctl-serve-proxy");
fs.mkdirSync(verDir, { recursive: true });

const serveMgr = require(path.join(harborRoot, "bridge-terminal", "gateway", "brctl-serve-manager.js"));
const reg = require(path.join(harborRoot, "mobile-platform", "compiler", "cubbies", "registry.js"));

const evidence = {
  generated_pt: new Date().toLocaleString("en-US", { timeZone: "America/Los_Angeles" }) + " PT",
  steps: [],
  gaps: [],
};

function step(id, ok, detail) {
  evidence.steps.push({ id, ok: !!ok, detail });
  console.log(ok ? "PASS" : "FAIL", id, typeof detail === "string" ? detail : JSON.stringify(detail).slice(0, 240));
}

function req(port, method, urlPath, headers, body) {
  return new Promise((resolve) => {
    const r = http.request(
      { host: "127.0.0.1", port, path: urlPath, method, headers: headers || {} },
      (res) => {
        let b = "";
        res.on("data", (c) => (b += c));
        res.on("end", () => resolve({ status: res.statusCode, headers: res.headers, body: b }));
      }
    );
    r.on("error", (e) => resolve({ status: 0, error: String(e) }));
    if (body != null) r.end(typeof body === "string" ? body : JSON.stringify(body));
    else r.end();
  });
}

(async () => {
  serveMgr.setHarborRoot(harborRoot);
  const probeId = "MC-SRVPROBE";
  try {
    const info = await serveMgr.ensure(probeId, { harborRoot });
    step("manager_ensure_ready", !!(info && info.ready && info.pid), info);
    const apdu = await serveMgr.apdu(probeId, "010200000000000000000000");
    const rsp = (apdu && (apdu.response || apdu.text)) || "";
    step("manager_apdu_status", /^9000/i.test(String(rsp)), apdu);
    fs.writeFileSync(path.join(verDir, "manager-probe.json"), JSON.stringify({ info, apdu }, null, 2) + "\n");
  } catch (e) {
    step("manager_ensure_ready", false, String(e && e.message || e));
  }

  const tokenFile = path.join(harborRoot, "ACCESS_TOKEN.txt");
  let token = null;
  if (fs.existsSync(tokenFile)) token = fs.readFileSync(tokenFile, "utf8").trim();

  const port = await new Promise((resolve, reject) => {
    const s = net.createServer();
    s.listen(0, "127.0.0.1", () => {
      const p = s.address().port;
      s.close(() => resolve(p));
    });
    s.on("error", reject);
  });

  const principals = path.join(harborRoot, "bridge-terminal", ".vws-local", "principals.json");
  const env = {
    ...process.env,
    PORT: String(port),
    VWS_HOST: "127.0.0.1",
    VWS_SECURE_COOKIES: "0",
    HARBOR_ROOT: harborRoot,
    HARBOR_MOBILE_AUTH_HOOK: "1",
  };
  if (fs.existsSync(principals)) env.VWS_PRINCIPALS_FILE = principals;
  delete env.VWS_SNAPSHOTS;
  delete env.VWS_SNAPSHOT_DIR;

  const gw = spawn(process.execPath, [path.join(harborRoot, "bridge-terminal", "gateway", "server.js")], {
    cwd: path.join(harborRoot, "bridge-terminal"),
    env,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });
  let boot = "";
  gw.stdout.on("data", (d) => { boot += d.toString(); });
  gw.stderr.on("data", (d) => { boot += d.toString(); });

  const waitListen = () => new Promise((resolve, reject) => {
    const deadline = Date.now() + 20000;
    const tryOnce = () => {
      const s = net.connect({ host: "127.0.0.1", port }, () => { s.end(); resolve(); });
      s.on("error", () => {
        if (Date.now() > deadline) reject(new Error("gateway listen timeout: " + boot.slice(-800)));
        else setTimeout(tryOnce, 150);
      });
    };
    tryOnce();
  });

  let cubbyId = null;
  try {
    await waitListen();
    step("gateway_listen", true, { port });

    if (token) {
      const ticket = await req(port, "POST", "/api/ws-ticket", {
        Authorization: "Bearer " + token,
        "Content-Type": "application/json",
        "X-Harbor-Mobile-Platform": "android",
        Origin: `http://127.0.0.1:${port}`,
      }, "{}");
      let tb = {};
      try { tb = JSON.parse(ticket.body); } catch { /* ignore */ }
      cubbyId = tb.cubby_id;
      step("ws_ticket_mc", ticket.status === 200 && !!cubbyId && tb.device_download === false, {
        status: ticket.status,
        cubby_id: cubbyId,
        projection_url: tb.projection_url,
        primary: tb.primary,
      });
      fs.writeFileSync(path.join(verDir, "ws-ticket.json"), JSON.stringify({ status: ticket.status, body: tb }, null, 2) + "\n");
    } else {
      // Fallback: allocate without ticket so HTTP serve paths can still be probed
      const alloc = reg.allocateMobileCubby({
        harborRoot,
        platform: "android",
        sessionId: "verify-brctl-serve-1",
        principal: "local/operator",
        trigger: "verification",
        port: String(port),
      });
      cubbyId = alloc.cubby.id;
      step("ws_ticket_mc", false, "ACCESS_TOKEN.txt missing — used registry allocate fallback " + cubbyId);
      evidence.gaps.push("No ACCESS_TOKEN.txt for live ws-ticket probe; used allocateMobileCubby fallback");
    }

    if (cubbyId) {
      await new Promise((r) => setTimeout(r, 1000));
      const proj = await req(port, "GET", `/cubby/${cubbyId}/projection`);
      const hasServeUi = /brctl serve/i.test(proj.body) && (/APDU/i.test(proj.body) || /hex-APDU/i.test(proj.body));
      step("projection_has_serve_ui", proj.status === 200 && hasServeUi, {
        status: proj.status,
        hasServeUi,
        x_brctl: proj.headers["x-harbor-brctl-serve"],
        snippet: proj.body.slice(0, 240).replace(/\s+/g, " "),
      });
      fs.writeFileSync(path.join(verDir, "projection.html"), proj.body);

      const st = await req(port, "GET", `/cubby/${cubbyId}/serve/status`);
      let sj = {};
      try { sj = JSON.parse(st.body); } catch { /* ignore */ }
      const ready = !!(sj.serve && (sj.serve.ready || sj.serve.pid));
      step("serve_status", st.status === 200 && ready, { status: st.status, serve: sj.serve || sj });
      fs.writeFileSync(path.join(verDir, "serve-status.json"), JSON.stringify(sj, null, 2) + "\n");

      const ap = await req(port, "POST", `/cubby/${cubbyId}/serve/apdu`, {
        "Content-Type": "application/json",
      }, { hex: "010200000000000000000000" });
      let aj = {};
      try { aj = JSON.parse(ap.body); } catch { /* ignore */ }
      const rsp = aj.response || aj.text || "";
      step("serve_apdu_proxy", ap.status === 200 && /^9000/i.test(String(rsp)), {
        status: ap.status, response: rsp, request: aj.request,
      });
      fs.writeFileSync(path.join(verDir, "serve-apdu.json"), JSON.stringify(aj, null, 2) + "\n");
    }

    const blocked = await req(port, "GET", "/cubby/QN-01/projection", {
      "X-Harbor-Mobile-Platform": "android",
      "X-Harbor-Principal": "local/no-cubby-user",
      "User-Agent": "Mozilla/5.0 (Linux; Android 14)",
    });
    step("mobile_qn_gate_still_403", blocked.status === 403, { status: blocked.status });
  } catch (e) {
    step("gateway_probe", false, String(e && e.message || e));
    fs.writeFileSync(path.join(verDir, "gateway-boot.txt"), boot);
  } finally {
    try { await serveMgr.stop(probeId); } catch { /* ignore */ }
    try { await serveMgr.stopAll(); } catch { /* ignore */ }
    try { gw.kill(); } catch { /* ignore */ }
  }

  evidence.gaps.push(
    "brctl serve exposes a hex-APDU REPL over stdio — not a framebuffer. Harbor proxies that REPL honestly."
  );
  evidence.summary = {
    passed: evidence.steps.filter((s) => s.ok).length,
    failed: evidence.steps.filter((s) => !s.ok).length,
    surface: "hex-APDU REPL via brctl serve stdio, proxied by Harbor HTTP/WS",
  };
  fs.writeFileSync(path.join(verDir, "EVIDENCE.json"), JSON.stringify(evidence, null, 2) + "\n");
  console.log("\nSUMMARY", evidence.summary);
  process.exit(evidence.summary.failed ? 1 : 0);
})();
