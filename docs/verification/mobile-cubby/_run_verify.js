const fs = require("fs");
const path = require("path");
const http = require("http");
const net = require("net");
const { spawn } = require("child_process");

const harborRoot = path.resolve(__dirname, "..", "..", "..");
process.chdir(harborRoot);
const verDir = path.join(harborRoot, "docs", "verification", "mobile-cubby");
fs.mkdirSync(verDir, { recursive: true });

const reg = require(path.join(harborRoot, "mobile-platform", "compiler", "cubbies", "registry.js"));
const gate = require(path.join(harborRoot, "bridge-terminal", "gateway", "cubby-access-gate.js"));

const evidence = {
  generated_pt: new Date().toLocaleString("en-US", { timeZone: "America/Los_Angeles" }) + " PT",
  steps: [],
  gaps: [],
};

function step(id, ok, detail) {
  evidence.steps.push({ id, ok, detail });
  console.log((ok ? "PASS" : "FAIL"), id, typeof detail === "string" ? detail : JSON.stringify(detail).slice(0, 220));
}

const alloc = reg.allocateMobileCubby({
  harborRoot,
  platform: "android",
  sessionId: "verify-mobile-cubby-1",
  principal: "local/operator",
  trigger: "verification",
  port: "10000",
});
step("allocate_mobile_cubby", !!alloc.cubby.id, {
  cubby_id: alloc.cubby.id,
  projection_url: alloc.session.projection_url,
  device_download: alloc.cubby.device_download,
});
fs.writeFileSync(path.join(verDir, "ALLOC.json"), JSON.stringify(alloc, null, 2) + "\n");

const listed = reg.listCubbies(harborRoot);
const found = (listed.mobile_cubbies || []).some((c) => c.id === alloc.cubby.id);
step("registry_contains_mc", found, { mobile_count: listed.counts.mobile_cubbies, total: listed.counts.total });

const desk = gate.checkAccess({
  harborRoot,
  req: { headers: { "user-agent": "HarborDesktop/1.0" }, url: "/cubby/QN-01/projection" },
  principal: "local/operator",
  targetCubbyId: "QN-01",
  action: "project",
});
step("desktop_qn_direct", desk.ok && desk.path === "desktop-direct", desk);

const mobileNoBr = gate.checkAccess({
  harborRoot,
  req: {
    headers: { "user-agent": "Mozilla/5.0 (Linux; Android 14)", "x-harbor-mobile-platform": "android" },
    url: "/cubby/QN-01/projection",
  },
  principal: "local/no-cubby-user",
  targetCubbyId: "QN-01",
  action: "project",
});
step("mobile_qn_blocked_without_br", !mobileNoBr.ok && mobileNoBr.error === "mobile_br_cubby_required", {
  status: mobileNoBr.status,
  error: mobileNoBr.error,
});

const mobileWithBr = gate.checkAccess({
  harborRoot,
  req: {
    headers: { "user-agent": "Mozilla/5.0 (Linux; Android 14)", "x-harbor-mobile-platform": "android" },
    url: "/api/cubbies/QN-01/attach",
  },
  principal: "local/operator",
  targetCubbyId: "QN-01",
  action: "attach",
});
step("mobile_qn_allowed_via_br", mobileWithBr.ok && mobileWithBr.path === "mobile-via-br-cubby" && mobileWithBr.br_cubby_id === alloc.cubby.id, mobileWithBr);

const readmeOk = /does \*\*not\*\* download the vm|does not download the vm/i.test(fs.readFileSync(path.join(harborRoot, "README.md"), "utf8"));
const mp = JSON.parse(fs.readFileSync(path.join(harborRoot, "fleet", "MOBILE_PLATFORM.json"), "utf8"));
const mpOk = mp.architecture && mp.architecture.device_download === false;
step("docs_no_primary_download", readmeOk && mpOk, { readmeOk, mpOk });

(async () => {
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
    const deadline = Date.now() + 15000;
    const tryOnce = () => {
      const s = net.connect({ host: "127.0.0.1", port }, () => { s.end(); resolve(); });
      s.on("error", () => {
        if (Date.now() > deadline) reject(new Error("gateway listen timeout: " + boot.slice(-800)));
        else setTimeout(tryOnce, 150);
      });
    };
    tryOnce();
  });

  function req(method, urlPath, headers) {
    return new Promise((resolve) => {
      const r = http.request(
        { host: "127.0.0.1", port, path: urlPath, method, headers: headers || {} },
        (res) => {
          let body = "";
          res.on("data", (c) => (body += c));
          res.on("end", () => resolve({ status: res.statusCode, headers: res.headers, body }));
        }
      );
      r.on("error", (e) => resolve({ status: 0, error: String(e) }));
      if (method === "POST") r.end("{}");
      else r.end();
    });
  }

  try {
    await waitListen();
    const proj = await req("GET", `/cubby/${alloc.cubby.id}/projection`);
    step("projection_http_200", proj.status === 200 && /Projected from Harbor cubby/i.test(proj.body) && /not downloaded/i.test(proj.body), {
      status: proj.status,
      x_cubby: proj.headers["x-harbor-cubby"],
      snippet: proj.body.slice(0, 180).replace(/\s+/g, " "),
    });
    fs.writeFileSync(path.join(verDir, "projection.html"), proj.body);

    const blocked = await req("GET", "/cubby/QN-01/projection", {
      "X-Harbor-Mobile-Platform": "android",
      "X-Harbor-Principal": "local/no-cubby-user",
      "User-Agent": "Mozilla/5.0 (Linux; Android 14)",
    });
    step("http_gate_403_without_br", blocked.status === 403 && /mobile_br_cubby_required/i.test(blocked.body), {
      status: blocked.status,
    });
    fs.writeFileSync(path.join(verDir, "gate-403.html"), blocked.body);

    const deskProj = await req("GET", "/cubby/QN-01/projection", {
      "User-Agent": "HarborDesktop/1.0",
    });
    step("http_desktop_qn_200", deskProj.status === 200, { status: deskProj.status, path: deskProj.headers["x-harbor-entry-path"] });

    const allowed = await req("GET", "/api/cubbies/QN-01/attach", {
      "X-Harbor-Mobile-Platform": "android",
      "X-Harbor-Principal": "local/operator",
      "User-Agent": "Mozilla/5.0 (Linux; Android 14)",
    });
    let attachBody = {};
    try { attachBody = JSON.parse(allowed.body); } catch {}
    step("http_mobile_attach_via_br", allowed.status === 200 && attachBody.gate && attachBody.gate.br_cubby_id === alloc.cubby.id, {
      status: allowed.status,
      gate: attachBody.gate,
    });
    fs.writeFileSync(path.join(verDir, "attach-via-br.json"), JSON.stringify(attachBody, null, 2) + "\n");

    if (token) {
      const ticket = await req("POST", "/api/ws-ticket", {
        Authorization: "Bearer " + token,
        "Content-Type": "application/json",
        "X-Harbor-Mobile-Platform": "android",
        Origin: `http://127.0.0.1:${port}`,
      });
      let tb = {};
      try { tb = JSON.parse(ticket.body); } catch {}
      step("ws_ticket_returns_cubby", ticket.status === 200 && !!tb.cubby_id && tb.device_download === false, {
        status: ticket.status,
        cubby_id: tb.cubby_id,
        projection_url: tb.projection_url,
        primary: tb.primary,
      });
      fs.writeFileSync(path.join(verDir, "ws-ticket-mobile.json"), JSON.stringify({ status: ticket.status, body: tb }, null, 2) + "\n");
    } else {
      step("ws_ticket_returns_cubby", false, "ACCESS_TOKEN.txt missing");
      evidence.gaps.push("No ACCESS_TOKEN.txt for live ws-ticket probe");
    }

    const apiList = await req("GET", "/api/cubbies");
    let lb = {};
    try { lb = JSON.parse(apiList.body); } catch {}
    step("api_cubbies_lists_mobile", apiList.status === 200 && (lb.mobile_cubbies || []).length >= 1, {
      status: apiList.status,
      counts: lb.counts,
    });
  } catch (e) {
    step("gateway_probe", false, String(e && e.message || e));
    fs.writeFileSync(path.join(verDir, "gateway-boot.txt"), boot);
  } finally {
    try { gw.kill(); } catch {}
  }

  evidence.gaps.push("Full Bottle Rocket host UI in browser projection page is a stub (contract page), not a complete BR framebuffer.");
  evidence.summary = {
    passed: evidence.steps.filter((s) => s.ok).length,
    failed: evidence.steps.filter((s) => !s.ok).length,
    cubby_id: alloc.cubby.id,
    projection_url_pattern: "http://127.0.0.1:{port}/cubby/{MC-id}/projection",
  };
  fs.writeFileSync(path.join(verDir, "EVIDENCE.json"), JSON.stringify(evidence, null, 2) + "\n");
  fs.writeFileSync(path.join(verDir, "LATEST_ALLOC.json"), JSON.stringify({
    cubby_id: alloc.cubby.id,
    projection_url: alloc.session.projection_url,
    device_download: false,
    primary: "cubby-projection",
  }, null, 2) + "\n");
  console.log("\nSUMMARY", evidence.summary);
  process.exit(evidence.summary.failed ? 1 : 0);
})();
