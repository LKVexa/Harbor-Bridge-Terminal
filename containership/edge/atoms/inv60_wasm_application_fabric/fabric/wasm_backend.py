"""M25 (partial) - execution backends.

``NodeWasmBackend`` executes real WebAssembly modules in a separate Node.js
process using V8's WebAssembly engine: bytes are validated/compiled by the
engine, run with a wall-clock timeout (process kill), a declared-memory ceiling
and no imports (no ambient authority). It is a real Wasm execution tier and a
non-Python consumer, but it is **not** wasmCloud: no NATS lattice, no wadm, no
WIT component-model linking. ``WasmCloudBackend`` is the adapter seam for that
and fails closed with BACKEND_NOT_CONFIGURED until a pinned wasmCloud/NATS
environment is supplied (see WAIVERS.json W-M25).
"""
from __future__ import annotations

import base64
import json
import shutil
import subprocess

from .errors import FabricError

_RUNNER = r"""
const chunks=[];process.stdin.on('data',c=>chunks.push(c));process.stdin.on('end',async()=>{
 try{const req=JSON.parse(Buffer.concat(chunks).toString());
  const bytes=Buffer.from(req.module,'base64');
  if(!WebAssembly.validate(bytes)){console.log(JSON.stringify({ok:false,code:'INVALID_ARGUMENT',msg:'invalid wasm'}));return;}
  const mod=await WebAssembly.compile(bytes);
  const imports=WebAssembly.Module.imports(mod);
  if(imports.length){console.log(JSON.stringify({ok:false,code:'PERMISSION_DENIED',msg:'module imports ambient capabilities: '+imports.map(i=>i.module+'.'+i.name).join(',')}));return;}
  const inst=await WebAssembly.instantiate(mod,{});
  const mem=Object.values(inst.exports).find(e=>e instanceof WebAssembly.Memory);
  if(mem && mem.buffer.byteLength>req.max_memory_bytes){console.log(JSON.stringify({ok:false,code:'QUOTA_EXCEEDED',msg:'memory over ceiling'}));return;}
  const fn=inst.exports[req.export];
  if(typeof fn!=='function'){console.log(JSON.stringify({ok:false,code:'NOT_FOUND',msg:'no export '+req.export}));return;}
  const out=fn(...req.args);
  console.log(JSON.stringify({ok:true,value:out,engine:'v8 '+process.versions.v8}));
 }catch(e){console.log(JSON.stringify({ok:false,code:'PROVIDER_ERROR',msg:String(e&&e.message||e).slice(0,200)}));}
});
"""


class ExecutionBackend:
    name = "abstract"

    def invoke(self, module: bytes, export: str, args: list, *, timeout_s: float) -> object:  # pragma: no cover
        raise NotImplementedError


class NodeWasmBackend(ExecutionBackend):
    name = "node-v8-webassembly"

    def __init__(self, node: str | None = None, max_memory_bytes: int = 16 * 65536):
        self.node = node or shutil.which("node")
        self.max_memory_bytes = max_memory_bytes

    @property
    def available(self) -> bool:
        return bool(self.node)

    def invoke(self, module: bytes, export: str, args: list, *, timeout_s: float = 2.0):
        if not self.node:
            raise FabricError("BACKEND_NOT_CONFIGURED", "node not found for WebAssembly execution")
        if any(not isinstance(a, int) or isinstance(a, bool) or not (-2**31 <= a < 2**31) for a in args):
            raise FabricError("INVALID_ARGUMENT", "reference ABI accepts i32 arguments only")
        req = json.dumps({"module": base64.b64encode(bytes(module)).decode(), "export": export,
                          "args": list(args), "max_memory_bytes": self.max_memory_bytes})
        try:
            p = subprocess.run([self.node, "--no-warnings", "-e", _RUNNER], input=req, capture_output=True,
                               text=True, timeout=max(0.05, timeout_s))
        except subprocess.TimeoutExpired:
            raise FabricError("DEADLINE_EXCEEDED", "wasm execution exceeded its time budget (process killed)")
        try:
            out = json.loads(p.stdout.strip().splitlines()[-1])
        except Exception:
            raise FabricError("PROVIDER_ERROR", "wasm runner produced no result") from None
        if not out.get("ok"):
            raise FabricError(out.get("code", "PROVIDER_ERROR"), out.get("msg", ""))
        return out["value"]


class WasmCloudBackend(ExecutionBackend):
    name = "wasmcloud"

    def __init__(self, ctl_url: str | None = None, creds_ref: str | None = None):
        self.ctl_url, self.creds_ref = ctl_url, creds_ref

    def invoke(self, module, export, args, *, timeout_s=2.0):
        raise FabricError("BACKEND_NOT_CONFIGURED",
                          "wasmCloud/NATS/wadm adapter requires a pinned lattice (see SUPPORT_MATRIX.json); not present")


# -- tiny module builder (used by tests, fixtures and the bench) --------------
def _leb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _sec(i: int, payload: bytes) -> bytes:
    return bytes([i]) + _leb(len(payload)) + payload


def build_module(kind: str = "add", *, memory_pages: int | None = None, with_import: bool = False) -> bytes:
    """kind: 'add' (i32,i32)->i32, 'spin' ()->i32 infinite loop, 'trap' ()->i32 unreachable."""
    if kind == "add":
        typ = b"\x60\x02\x7f\x7f\x01\x7f"
        body = b"\x00\x20\x00\x20\x01\x6a\x0b"
    elif kind == "spin":
        typ = b"\x60\x00\x01\x7f"
        body = b"\x00\x03\x40\x0c\x00\x0b\x41\x00\x0b"
    elif kind == "trap":
        typ = b"\x60\x00\x01\x7f"
        body = b"\x00\x00\x0b"
    else:
        raise ValueError(kind)
    out = b"\x00asm\x01\x00\x00\x00" + _sec(1, b"\x01" + typ)
    if with_import:
        out += _sec(2, b"\x01" + _leb(3) + b"env" + _leb(4) + b"host" + b"\x00\x00")
    out += _sec(3, b"\x01\x00")
    exports = [b"\x03run\x00" + _leb(1 if with_import else 0)]
    if memory_pages is not None:
        out += _sec(5, b"\x01\x00" + _leb(memory_pages))
        exports.append(b"\x03mem\x02\x00")
    out += _sec(7, _leb(len(exports)) + b"".join(exports))
    out += _sec(10, b"\x01" + _leb(len(body)) + body)
    return out
