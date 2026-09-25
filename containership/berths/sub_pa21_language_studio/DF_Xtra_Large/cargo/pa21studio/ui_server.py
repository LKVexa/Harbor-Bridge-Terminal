"""The bridge the window talks to.

A local HTTP server on the loopback interface, serving one HTML file and a
small JSON API that calls the same `Studio` methods the CLI calls. There is no
second implementation of install behind the window -- the window is a view.

Three properties matter more than the API surface:

  * It binds 127.0.0.1 only, on an ephemeral port, and prints the URL. Nothing
    is reachable from another machine.
  * Every request must carry the session token minted at startup and handed to
    the page in its URL, so another local process cannot drive an install by
    guessing the port.
  * Long operations stream their progress as newline-delimited JSON, so the
    window can show what is happening rather than a spinner that means nothing.
"""

from __future__ import annotations

import json
import os
import queue
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

from .core import Studio, StudioError, VERSION, default_root
from . import container as containers
from . import ledger as pa21_ledger
from . import lctlc

UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")


class _State:
    token: str = ""
    root: Optional[str] = None
    vm_default: str = ""
    pa21_default: str = ""
    busy: bool = False
    last: Dict[str, object] = {}


STATE = _State()


def _guess_vm() -> str:
    """A predictive affordance, not a decision: the likeliest package nearby."""
    if STATE.vm_default and os.path.exists(STATE.vm_default):
        return STATE.vm_default
    here = os.getcwd()
    home = os.path.expanduser("~")
    cands = []
    for base in (here, os.path.dirname(here), os.path.join(home, "Desktop"),
                 os.path.join(home, "Desktop", "VMs"), home):
        try:
            for name in os.listdir(base):
                p = os.path.join(base, name)
                if name.lower().endswith(".zip") and os.path.isfile(p):
                    cands.append(p)
                elif os.path.isdir(p) and os.path.isfile(
                        os.path.join(p, "src", "brvm.c")):
                    cands.append(p)
        except OSError:
            continue
    for c in cands:
        if "BOTTLE" in os.path.basename(c).upper():
            return c
    return cands[0] if cands else ""


def _guess_pa21() -> str:
    if STATE.pa21_default and os.path.isdir(STATE.pa21_default):
        return STATE.pa21_default
    home = os.path.expanduser("~")
    for base in (os.getcwd(), os.path.dirname(os.getcwd()),
                 os.path.join(home, "Desktop"), home):
        try:
            for name in sorted(os.listdir(base)):
                p = os.path.join(base, name)
                if os.path.isdir(p) and pa21_ledger.find_packages(p):
                    return p
        except OSError:
            continue
    return ""


class Handler(BaseHTTPRequestHandler):
    server_version = "PA21StudioUI/" + VERSION

    # -- plumbing -------------------------------------------------------
    def log_message(self, fmt, *args):                       # noqa: A003
        pass                                                  # the window is the log

    def _authorised(self, q: Dict[str, list]) -> bool:
        tok = (q.get("token") or [""])[0]
        return secrets.compare_digest(tok, STATE.token)

    def _json(self, obj, code: int = 200):
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, path: str):
        with open(path, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    # -- routes ---------------------------------------------------------
    def do_GET(self):                                        # noqa: N802
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            return self._html(os.path.join(UI_DIR, "index.html"))
        if not self._authorised(q):
            return self._json({"error": "unauthorised"}, 403)
        s = Studio(STATE.root)
        if u.path == "/api/state":
            try:
                st = s.status()
            except StudioError as e:
                st = {"installed": False, "error": str(e)}
            return self._json({
                "studio_version": VERSION,
                "status": st,
                "defaults": {"vm": _guess_vm(), "pa21": _guess_pa21(),
                             "root": s.root, "default_root": default_root()},
                "templates": lctlc.template_list(),
                "busy": STATE.busy,
            })
        if u.path == "/api/plan":
            vm = (q.get("vm") or [""])[0]
            pa21 = (q.get("pa21") or [""])[0]
            mode = (q.get("mode") or ["install"])[0]
            try:
                if mode == "uninstall":
                    return self._json(s.plan_uninstall(
                        purge=(q.get("purge") or ["0"])[0] == "1"))
                return self._json(s.plan_install(vm, pa21 or None))
            except StudioError as e:
                return self._json({"error": str(e), "detail": e.detail}, 400)
        if u.path == "/api/inspect":
            path = (q.get("path") or [""])[0]
            return self._json(_inspect(path))
        if u.path == "/api/apps":
            try:
                return self._json(s.list_apps())
            except StudioError as e:
                return self._json({"error": str(e)}, 400)
        if u.path == "/api/containers":
            try:
                out = s.list_containers(
                    verify=(q.get("verify") or ["1"])[0] == "1")
                out["templates"] = lctlc.template_list()
                return self._json(out)
            except StudioError as e:
                return self._json({"error": str(e)}, 400)
        return self._json({"error": "no such route"}, 404)

    def do_POST(self):                                       # noqa: N802
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if not self._authorised(q):
            return self._json({"error": "unauthorised"}, 403)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self._json({"error": "malformed request body"}, 400)
        if u.path == "/api/install":
            return self._stream("install", payload)
        if u.path == "/api/uninstall":
            return self._stream("uninstall", payload)
        if u.path == "/api/container/new":
            s = Studio(STATE.root)
            try:
                return self._json(s.new_app(
                    str(payload.get("name", "")),
                    template=str(payload.get("template", "hello")),
                    requires_operational=[int(x) for x in
                                          payload.get("requires", [])],
                    version=str(payload.get("version", "0.1.0"))))
            except StudioError as e:
                return self._json({"error": str(e), "detail": e.detail}, 400)
        if u.path == "/api/container/build":
            s = Studio(STATE.root)
            try:
                return self._json(s.build_app(str(payload.get("name", ""))))
            except (StudioError, lctlc.ToolchainError) as e:
                return self._json({"error": str(e),
                                   "detail": getattr(e, "detail", {})}, 400)
        if u.path == "/api/container/run":
            s = Studio(STATE.root)
            try:
                return self._json(s.run_app(str(payload.get("name", ""))))
            except (StudioError, lctlc.ToolchainError) as e:
                return self._json({"error": str(e),
                                   "detail": getattr(e, "detail", {})}, 400)
        if u.path == "/api/container/remove":
            s = Studio(STATE.root)
            try:
                return self._json(s.remove_container(
                    str(payload.get("name", ""))))
            except StudioError as e:
                return self._json({"error": str(e), "detail": e.detail}, 400)
        if u.path == "/api/container/pack":
            s = Studio(STATE.root)
            try:
                return self._json(s.pack_container(
                    str(payload.get("name", ""))))
            except StudioError as e:
                return self._json({"error": str(e), "detail": e.detail}, 400)
        if u.path == "/api/selftest":
            s = Studio(STATE.root)
            try:
                return self._json(s.selftest())
            except StudioError as e:
                return self._json({"error": str(e), "detail": e.detail}, 400)
        return self._json({"error": "no such route"}, 404)

    # -- streaming ------------------------------------------------------
    def _stream(self, action: str, payload: Dict[str, object]):
        if STATE.busy:
            return self._json({"error": "another operation is running"}, 409)
        STATE.busy = True
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        events: "queue.Queue[Optional[Dict[str, object]]]" = queue.Queue()

        def on_event(ev):
            events.put(dict(ev))

        result: Dict[str, object] = {}

        def work():
            nonlocal result
            s = Studio(payload.get("root") or STATE.root)
            try:
                if action == "install":
                    result = s.install(
                        vm_source=payload.get("vm", ""),
                        pa21_root=payload.get("pa21") or None,
                        build=bool(payload.get("build", True)),
                        force=bool(payload.get("force", False)),
                        on_event=on_event)
                else:
                    result = s.uninstall(purge=bool(payload.get("purge", False)),
                                         on_event=on_event)
            except StudioError as e:
                result = {"ok": False, "error": str(e), "detail": e.detail}
            except Exception as e:                           # noqa: BLE001
                result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            finally:
                events.put(None)

        t = threading.Thread(target=work, daemon=True)
        t.start()
        try:
            while True:
                ev = events.get()
                if ev is None:
                    break
                self.wfile.write((json.dumps(ev, default=str) + "\n")
                                 .encode("utf-8"))
                self.wfile.flush()
            t.join(timeout=5)
            STATE.last = result
            self.wfile.write((json.dumps({"phase": "result", "result": result},
                                         default=str) + "\n").encode("utf-8"))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            STATE.busy = False


def _inspect(path: str) -> Dict[str, object]:
    """What a path is, so the window can say so before anything is pressed."""
    p = os.path.abspath(os.path.expanduser(path)) if path else ""
    if not p or not os.path.exists(p):
        return {"path": p, "exists": False,
                "kind": "missing",
                "detail": "nothing at this path"}
    if os.path.isdir(p):
        if os.path.isfile(os.path.join(p, "src", "brvm.c")):
            return {"path": p, "exists": True, "kind": "runtime_directory",
                    "detail": "a BOTTLE ROCKET package"}
        pkgs = pa21_ledger.find_packages(p)
        if pkgs:
            sur = pa21_ledger.survey(p)
            return {"path": p, "exists": True, "kind": "pa21_delivery",
                    "detail": f"{sur.get('package_count')} package(s), ledger "
                              f"{sur.get('round', 'unknown')}, "
                              f"{sur.get('operational', 0)}/"
                              f"{sur.get('items', 0)} operational",
                    "survey": sur}
        return {"path": p, "exists": True, "kind": "directory",
                "detail": "a directory, but not a runtime or a PA21 delivery"}
    size = os.path.getsize(p)
    if p.lower().endswith(".zip"):
        try:
            import zipfile
            with zipfile.ZipFile(p) as zf:
                names = zf.namelist()
            top = sorted({n.split("/")[0] for n in names if n.strip()})
            looks = any(n.endswith("src/brvm.c") for n in names)
            return {"path": p, "exists": True,
                    "kind": "runtime_archive" if looks else "archive",
                    "detail": (f"{len(names)} entries, "
                               f"{size / 1024:.0f} KiB"
                               + (f", package {top[0]}" if len(top) == 1 else
                                  f", {len(top)} top-level entries")),
                    "contains_runtime": looks}
        except Exception as e:                               # noqa: BLE001
            return {"path": p, "exists": True, "kind": "archive",
                    "detail": f"unreadable archive: {e}"}
    return {"path": p, "exists": True, "kind": "file",
            "detail": f"{size} bytes"}


def serve(root: Optional[str] = None, port: int = 0, open_browser: bool = True,
          vm_default: str = "", pa21_default: str = "") -> int:
    STATE.token = secrets.token_urlsafe(24)
    STATE.root = root
    STATE.vm_default = vm_default or ""
    STATE.pa21_default = pa21_default or ""
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    host, bound = httpd.server_address[0], httpd.server_address[1]
    url = f"http://{host}:{bound}/?token={STATE.token}"
    # flushed explicitly: when this is launched with its output redirected --
    # from a shortcut, a service wrapper, or a script -- Python block-buffers
    # stdout, and the URL a caller needs in order to open the window at all
    # would sit in the buffer until the process exits.
    print("PA21 Language Studio — install window", flush=True)
    print(f"  {url}", flush=True)
    print("  close this window's tab and press Ctrl-C here when finished",
          flush=True)
    if open_browser:
        threading.Thread(target=lambda: (time.sleep(0.4),
                                         webbrowser.open(url)),
                         daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nclosed")
    finally:
        httpd.server_close()
    return 0
