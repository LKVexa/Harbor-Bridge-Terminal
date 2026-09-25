"use strict";
/**
 * Per-cubby `brctl serve --state` process manager.
 *
 * Bottle Rocket `serve` is NOT an HTTP server: it is a stdin/stdout hex-APDU REPL
 * that prints "READY hex-APDU per line; EOF stops", then answers one hex line per
 * APDU. Harbor owns lifecycle and proxies that REPL into the browser projection
 * page (HTTP POST + optional WS), keeping Harbor ticket/session gates on the gateway.
 */
const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { EventEmitter } = require("node:events");

const REL_STATES = path.join("mobile-platform", "compiler", "cubbies", "serve-states");
const REL_SESSIONS = path.join("mobile-platform", "compiler", "cubbies", "sessions");
const REL_BRCTL_WIN = path.join("mobile-platform", "compiler", "bin", "brctl.exe");
const REL_BRCTL = path.join("mobile-platform", "compiler", "bin", "brctl");

/** @type {Map<string, CubbyServe>} */
const instances = new Map();
let harborRootHint = null;
let logFn = null;

function setLog(fn) { logFn = typeof fn === "function" ? fn : null; }
function log(level, msg, extra) {
  if (logFn) try { logFn(level, msg, extra); } catch { /* noop */ }
  else if (level === "error") console.error("[brctl-serve]", msg, extra || "");
}

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
  if (harborRootHint) return harborRootHint;
  return path.resolve(__dirname, "..", "..");
}

function setHarborRoot(root) { harborRootHint = path.resolve(root); }

function resolveBrctl(root) {
  const a = path.join(root, REL_BRCTL_WIN);
  const b = path.join(root, REL_BRCTL);
  if (fs.existsSync(a)) return a;
  if (fs.existsSync(b)) return b;
  return null;
}

function statePrefix(root, cubbyId) {
  const d = path.join(root, REL_STATES, cubbyId);
  fs.mkdirSync(d, { recursive: true });
  return path.join(d, "br");
}

function normalizeHex(hex) {
  const s = String(hex || "").replace(/\s+/g, "").toLowerCase();
  if (!s) return { ok: false, error: "empty hex" };
  if (!/^[0-9a-f]+$/.test(s)) return { ok: false, error: "non-hex" };
  if (s.length % 2 !== 0) return { ok: false, error: "odd length" };
  if (s.length > 8192) return { ok: false, error: "too long" };
  return { ok: true, hex: s };
}

class CubbyServe extends EventEmitter {
  constructor(cubbyId, root) {
    super();
    this.cubbyId = cubbyId;
    this.root = root;
    this.brctl = resolveBrctl(root);
    this.statePrefix = statePrefix(root, cubbyId);
    this.child = null;
    this.pid = null;
    this.ready = false;
    this.startedAt = null;
    this.lastError = null;
    this.stdoutBuf = "";
    this.queue = [];
    this.busy = false;
    this.exited = false;
    this.exitCode = null;
  }

  info() {
    return {
      cubby_id: this.cubbyId,
      pid: this.pid,
      ready: this.ready && !this.exited,
      alive: !!(this.child && this.child.exitCode === null && !this.exited),
      started_at: this.startedAt,
      state_prefix: this.statePrefix,
      state_rel: path.relative(this.root, this.statePrefix).replace(/\\/g, "/"),
      brctl: this.brctl,
      serve_args: ["serve", "--state", this.statePrefix],
      last_error: this.lastError,
      exit_code: this.exitCode,
      queued: this.queue.length,
      bind: "stdio (Harbor proxies; no native HTTP from brctl)",
      surface: "hex-APDU REPL (not a framebuffer)",
      device_download: false,
    };
  }

  start() {
    if (this.child && this.child.exitCode === null && !this.exited) {
      return Promise.resolve(this.info());
    }
    if (!this.brctl) {
      this.lastError = "brctl missing";
      return Promise.reject(new Error("brctl missing"));
    }
    this.exited = false;
    this.ready = false;
    this.stdoutBuf = "";
    this.exitCode = null;
    this.lastError = null;

    const args = ["serve", "--state", this.statePrefix];
    const child = spawn(this.brctl, args, {
      cwd: this.root,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
      env: { ...process.env },
    });
    this.child = child;
    this.pid = child.pid;
    this.startedAt = new Date().toISOString();
    log("info", "brctl.serve.start", { cubby_id: this.cubbyId, pid: this.pid, state: this.statePrefix });

    return new Promise((resolve, reject) => {
      let settled = false;
      const failTimer = setTimeout(() => {
        if (settled) return;
        settled = true;
        this.lastError = "READY timeout";
        reject(new Error("brctl serve READY timeout"));
      }, 8000);

      const onReady = () => {
        if (settled) return;
        settled = true;
        clearTimeout(failTimer);
        this.ready = true;
        this.persistSessionMeta();
        this.emit("ready", this.info());
        resolve(this.info());
      };

      child.stdout.setEncoding("utf8");
      child.stderr.setEncoding("utf8");
      child.stdout.on("data", (chunk) => this._onStdout(chunk, onReady));
      child.stderr.on("data", (chunk) => {
        const t = String(chunk).trim();
        if (t) log("warn", "brctl.serve.stderr", { cubby_id: this.cubbyId, text: t.slice(0, 400) });
      });
      child.on("error", (e) => {
        this.lastError = String(e && e.message || e);
        this.exited = true;
        if (!settled) { settled = true; clearTimeout(failTimer); reject(e); }
        this._failAll(this.lastError);
        this.emit("exit", { code: null, error: this.lastError });
      });
      child.on("exit", (code) => {
        this.exited = true;
        this.ready = false;
        this.exitCode = code;
        this.pid = null;
        this._failAll("process exited");
        this.persistSessionMeta();
        this.emit("exit", { code });
        log("info", "brctl.serve.exit", { cubby_id: this.cubbyId, code });
        if (!settled) { settled = true; clearTimeout(failTimer); reject(new Error("exited before READY")); }
      });
    });
  }

  _onStdout(chunk, onReady) {
    this.stdoutBuf += chunk;
    let idx;
    while ((idx = this.stdoutBuf.indexOf("\n")) >= 0) {
      let line = this.stdoutBuf.slice(0, idx);
      this.stdoutBuf = this.stdoutBuf.slice(idx + 1);
      if (line.endsWith("\r")) line = line.slice(0, -1);
      if (!this.ready && /^READY\b/i.test(line)) {
        onReady();
        this.emit("line", { type: "ready", text: line });
        continue;
      }
      if (!this.ready) continue;
      if (this.busy && this.queue[0] && this.queue[0].waiting) {
        const job = this.queue.shift();
        this.busy = false;
        job.waiting = false;
        clearTimeout(job.timer);
        job.resolve({ ok: true, response: line.toLowerCase(), request: job.hex });
        this.emit("line", { type: "response", text: line, request: job.hex });
        this._pump();
      } else {
        this.emit("line", { type: "stdout", text: line });
      }
    }
  }

  _failAll(reason) {
    const q = this.queue.splice(0);
    this.busy = false;
    for (const job of q) {
      clearTimeout(job.timer);
      job.reject(new Error(reason));
    }
  }

  _pump() {
    if (this.busy || !this.ready || this.exited) return;
    const job = this.queue[0];
    if (!job) return;
    this.busy = true;
    job.waiting = true;
    try {
      this.child.stdin.write(job.hex + "\n");
    } catch (e) {
      this.queue.shift();
      this.busy = false;
      job.reject(e);
      this._pump();
    }
  }

  apdu(hex) {
    const n = normalizeHex(hex);
    if (!n.ok) return Promise.reject(new Error(n.error));
    if (!this.ready || this.exited || !this.child) {
      return Promise.reject(new Error("serve not ready"));
    }
    return new Promise((resolve, reject) => {
      const job = {
        hex: n.hex,
        resolve,
        reject,
        waiting: false,
        timer: setTimeout(() => {
          const i = this.queue.indexOf(job);
          if (i >= 0) this.queue.splice(i, 1);
          if (job.waiting) this.busy = false;
          reject(new Error("APDU timeout"));
          this._pump();
        }, 10000),
      };
      this.queue.push(job);
      this._pump();
    });
  }

  stop() {
    return new Promise((resolve) => {
      if (!this.child || this.exited) {
        instances.delete(this.cubbyId);
        this.persistSessionMeta(true);
        return resolve({ stopped: true, cubby_id: this.cubbyId });
      }
      const child = this.child;
      let finished = false;
      const done = () => {
        if (finished) return;
        finished = true;
        instances.delete(this.cubbyId);
        this.persistSessionMeta(true);
        resolve({ stopped: true, cubby_id: this.cubbyId, exit_code: this.exitCode });
      };
      child.once("exit", done);
      try { child.stdin.end(); } catch { /* noop */ }
      const t = setTimeout(() => {
        try { child.kill(); } catch { /* noop */ }
        setTimeout(done, 1500);
      }, 800);
      child.once("exit", () => clearTimeout(t));
    });
  }

  persistSessionMeta(stopped) {
    try {
      const p = path.join(this.root, REL_SESSIONS, this.cubbyId + ".json");
      let session = {};
      if (fs.existsSync(p)) {
        try { session = JSON.parse(fs.readFileSync(p, "utf8")); } catch { session = {}; }
      }
      session.br_serve = {
        ...(session.br_serve || {}),
        ...this.info(),
        stopped: !!stopped,
        updated_at: new Date().toISOString(),
        proxy: {
          http_status: "/cubby/" + this.cubbyId + "/serve/status",
          http_apdu: "/cubby/" + this.cubbyId + "/serve/apdu",
          ws: "/cubby/" + this.cubbyId + "/serve/ws",
        },
      };
      session.updated_at = new Date().toISOString();
      fs.mkdirSync(path.dirname(p), { recursive: true });
      fs.writeFileSync(p, JSON.stringify(session, null, 2) + "\n", { encoding: "utf8", mode: 0o600 });
    } catch (e) {
      log("warn", "brctl.serve.persist_fail", { cubby_id: this.cubbyId, reason: String(e && e.message) });
    }
  }
}

async function ensure(cubbyId, opts) {
  const id = String(cubbyId || "").trim();
  if (!/^[A-Za-z0-9._-]+$/.test(id)) throw new Error("invalid cubby id");
  const root = harborRootFrom(opts && opts.harborRoot);
  setHarborRoot(root);
  let inst = instances.get(id);
  if (inst && inst.ready && !inst.exited) return inst.info();
  if (inst && (!inst.ready || inst.exited)) {
    try { await inst.stop(); } catch { /* noop */ }
    instances.delete(id);
  }
  inst = new CubbyServe(id, root);
  instances.set(id, inst);
  return inst.start();
}

function get(cubbyId) { return instances.get(String(cubbyId)) || null; }
function list() { return [...instances.values()].map((i) => i.info()); }

async function apdu(cubbyId, hex) {
  let inst = get(cubbyId);
  if (!inst || !inst.ready || inst.exited) {
    await ensure(cubbyId);
    inst = get(cubbyId);
  }
  return inst.apdu(hex);
}

async function stop(cubbyId) {
  const inst = get(cubbyId);
  if (!inst) return { stopped: true, cubby_id: cubbyId, missing: true };
  return inst.stop();
}

async function stopAll() {
  const ids = [...instances.keys()];
  const results = [];
  for (const id of ids) {
    try { results.push(await stop(id)); }
    catch (e) { results.push({ cubby_id: id, error: String(e && e.message) }); }
  }
  return results;
}

function attachWs(cubbyId, wsSend, wsClose) {
  const inst = get(cubbyId);
  if (!inst) return () => {};
  const onLine = (ev) => { try { wsSend(JSON.stringify(ev)); } catch { /* noop */ } };
  const onExit = (ev) => {
    try { wsSend(JSON.stringify({ type: "exit", ...ev })); } catch { /* noop */ }
    try { wsClose(); } catch { /* noop */ }
  };
  inst.on("line", onLine);
  inst.on("exit", onExit);
  if (inst.ready) {
    try {
      wsSend(JSON.stringify({
        type: "ready",
        text: "READY hex-APDU per line; EOF stops",
        info: inst.info(),
      }));
    } catch { /* noop */ }
  }
  return () => { inst.off("line", onLine); inst.off("exit", onExit); };
}

module.exports = {
  ensure,
  get,
  list,
  apdu,
  stop,
  stopAll,
  attachWs,
  setHarborRoot,
  setLog,
  normalizeHex,
  resolveBrctl,
  statePrefix,
  harborRootFrom,
};
