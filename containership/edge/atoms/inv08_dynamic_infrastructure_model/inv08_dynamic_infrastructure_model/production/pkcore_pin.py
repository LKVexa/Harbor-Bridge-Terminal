"""Component 01 - reproducible ``pk_core`` dependency pin (contract PK_DYN_LOCK/1).

Contract
--------
* ``parse_version`` / ``parse_requirement`` implement a documented PEP 440 subset:
  release ``N(.N)*``, optional pre ``aN|bN|rcN``, ``.postN``, ``.devN`` and a
  ``+local`` label; specifier operators ``== != <= >= < > ~= ===``.  Anything
  else is rejected with ``INV08.PIN.INVALID`` (no silent best-effort parsing).
* The lock file ``production/packaging/pk_core.lock.json`` records package,
  requirement, exact version, wheel filename, sha256 and source.  While the
  pk_core source/wheel is absent from this world its ``state`` is ``UNRESOLVED``
  and every hash is ``null``; consumers MUST fail closed on that state.
* ``resolve_wheelhouse`` only accepts a local directory (no URLs), requires a
  RESOLVED lock, finds exactly the locked wheel and verifies its sha256.
* ``api_surface`` statically (``ast``, no import) lists every ``pk_core`` symbol
  INV-08 uses; ``check_compat`` imports a candidate ``pk_core`` and reports the
  missing symbols.

BLOCKED input: the pk_core source location / wheel and its digest.
"""
from __future__ import annotations

import ast
import hashlib
import importlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .core import Inv08Error, Outcome

LOCK_SCHEMA = "PK_DYN_LOCK/1"
PKG_DIR = Path(__file__).resolve().parent.parent
LOCK_PATH = Path(__file__).resolve().parent / "packaging" / "pk_core.lock.json"
LOCK_STATES = {"UNRESOLVED", "RESOLVED"}
_MAX_READ = 64 * 1024 * 1024

_VER_RE = re.compile(
    r"^(?P<release>\d+(?:\.\d+)*)"
    r"(?:(?P<pre_l>a|b|rc)(?P<pre_n>\d+))?"
    r"(?:\.post(?P<post>\d+))?"
    r"(?:\.dev(?P<dev>\d+))?"
    r"(?:\+(?P<local>[a-z0-9]+(?:\.[a-z0-9]+)*))?$")
_NAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
_OPS = ("===", "~=", "==", "!=", "<=", ">=", "<", ">")


def _err(name: str, msg: str, **details) -> Inv08Error:
    return Inv08Error(code=f"INV08.PIN.{name}", message=msg, outcome=Outcome.BLOCKED
                      if name in {"UNRESOLVED", "NO_WHEEL", "PK_CORE_ABSENT"} else Outcome.TERMINAL_FAILURE,
                      remediation="provide the pk_core wheel and record its sha256 in the lock",
                      details=details)


@dataclass(frozen=True, order=False)
class Version:
    text: str
    release: tuple
    pre: tuple | None
    post: int | None
    dev: int | None
    local: str | None

    def key(self) -> tuple:
        rel = list(self.release)
        while len(rel) > 1 and rel[-1] == 0:
            rel.pop()
        # dev-only < pre < final < post (PEP 440 ordering)
        if self.pre is None and self.post is None and self.dev is not None:
            pre = (-1, 0)
        elif self.pre is None:
            pre = (9, 0)
        else:
            pre = ({"a": 0, "b": 1, "rc": 2}[self.pre[0]], self.pre[1])
        post = -1 if self.post is None else self.post
        dev = float("inf") if self.dev is None else self.dev
        return (tuple(rel), pre, post, dev)

    def public(self) -> "Version":
        return parse_version(self.text.split("+", 1)[0])


def parse_version(text: str) -> Version:
    if not isinstance(text, str) or len(text) > 128:
        raise _err("INVALID", f"version must be a short string, got {text!r}")
    m = _VER_RE.match(text.strip().lower())
    if not m:
        raise _err("INVALID", f"not a supported PEP 440 version: {text!r}")
    pre = (m["pre_l"], int(m["pre_n"])) if m["pre_l"] else None
    return Version(text.strip().lower(), tuple(int(x) for x in m["release"].split(".")), pre,
                   int(m["post"]) if m["post"] else None, int(m["dev"]) if m["dev"] else None,
                   m["local"])


@dataclass(frozen=True)
class Requirement:
    name: str
    specifiers: tuple  # ((op, version_text), ...)

    @property
    def exact(self) -> bool:
        return len(self.specifiers) == 1 and self.specifiers[0][0] in {"==", "==="} \
            and "*" not in self.specifiers[0][1]


def parse_requirement(text: str) -> Requirement:
    if not isinstance(text, str) or not text.strip() or len(text) > 512:
        raise _err("INVALID", f"requirement must be a non-empty short string: {text!r}")
    if any(c in text for c in ";@[") :
        raise _err("INVALID", "markers, extras and direct URLs are outside the supported subset")
    m = re.match(r"^\s*([A-Za-z0-9._-]+)\s*(.*)$", text)
    name, rest = m.group(1), m.group(2).strip()
    if not _NAME_RE.match(name):
        raise _err("INVALID", f"bad project name {name!r}")
    specs = []
    if rest:
        for part in rest.split(","):
            part = part.strip()
            op = next((o for o in _OPS if part.startswith(o)), None)
            if op is None:
                raise _err("INVALID", f"bad specifier {part!r}")
            ver = part[len(op):].strip()
            if op in {"==", "!="} and ver.endswith(".*"):
                parse_version(ver[:-2])
            elif op == "===":
                if not ver:
                    raise _err("INVALID", "=== needs a value")
            else:
                v = parse_version(ver)
                if op == "~=" and len(v.release) < 2:
                    raise _err("INVALID", "~= needs at least two release segments")
                if v.local and op not in {"==", "!="}:
                    raise _err("INVALID", "local versions only allowed with == / !=")
            specs.append((op, ver))
    return Requirement(re.sub(r"[-_.]+", "-", name).lower(), tuple(specs))


def _match_one(v: Version, op: str, spec: str) -> bool:
    if op == "===":
        return v.text == spec.lower()
    if spec.endswith(".*"):
        prefix = parse_version(spec[:-2]).release
        hit = v.release[:len(prefix)] == prefix
        return hit if op == "==" else not hit
    s = parse_version(spec)
    vk = (v if s.local else v.public()).key()
    sk = s.key()
    if op == "==":
        return vk == sk
    if op == "!=":
        return vk != sk
    if op == "<=":
        return vk <= sk
    if op == ">=":
        return vk >= sk
    if op == "<":
        return vk < sk and not (v.pre and v.public().release == s.release and s.pre is None)
    if op == ">":
        return vk > sk and not (v.post is not None and s.post is None and v.release == s.release)
    if op == "~=":
        prefix = s.release[:-1]
        return vk >= sk and v.release[:len(prefix)] == prefix
    raise _err("INVALID", f"unknown operator {op}")


def satisfies(version: str, req: Requirement) -> bool:
    v = parse_version(version)
    return all(_match_one(v, op, spec) for op, spec in req.specifiers)

# ------------------------------------------------------------------ lock file

def validate_lock(lock: dict) -> list[str]:
    p: list[str] = []
    if not isinstance(lock, dict):
        return ["lock must be an object"]
    if lock.get("schema") != LOCK_SCHEMA:
        p.append(f"schema must be {LOCK_SCHEMA}")
    if lock.get("package") != "pk_core":
        p.append("package must be pk_core")
    state = lock.get("state")
    if state not in LOCK_STATES:
        p.append(f"state must be one of {sorted(LOCK_STATES)}")
    if state == "RESOLVED":
        try:
            req = parse_requirement(lock.get("requirement") or "")
            if not req.exact:
                p.append("RESOLVED lock requires an exact == pin")
            elif req.specifiers[0][1] != lock.get("version"):
                p.append("requirement pin and version disagree")
        except Inv08Error as exc:
            p.append(exc.message)
        if not re.fullmatch(r"[0-9a-f]{64}", str(lock.get("sha256") or "")):
            p.append("RESOLVED lock requires a 64-hex sha256")
        wheel = str(lock.get("wheel") or "")
        if not re.fullmatch(r"pk_core-[^/\\]+\.whl", wheel):
            p.append("RESOLVED lock requires a pk_core-*.whl filename")
    elif state == "UNRESOLVED":
        if lock.get("sha256") is not None:
            p.append("UNRESOLVED lock must not carry a digest")
        if not lock.get("blocker"):
            p.append("UNRESOLVED lock must name its blocker")
    return p


def load_lock(path: Path = LOCK_PATH) -> dict:
    lock = json.loads(Path(path).read_text(encoding="utf-8"))
    problems = validate_lock(lock)
    if problems:
        raise _err("LOCK_INVALID", "; ".join(problems))
    return lock


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            size += len(chunk)
            if size > _MAX_READ:
                raise _err("TOO_LARGE", f"{path.name} exceeds {_MAX_READ} bytes")
            h.update(chunk)
    return h.hexdigest()


def resolve_wheelhouse(lock: dict, wheelhouse: str | Path) -> Path:
    """Return the verified wheel path or raise (fail closed)."""
    if validate_lock(lock):
        raise _err("LOCK_INVALID", "; ".join(validate_lock(lock)))
    if lock["state"] != "RESOLVED":
        raise _err("UNRESOLVED", "pk_core lock is UNRESOLVED: " + str(lock.get("blocker")))
    if "://" in str(wheelhouse):
        raise _err("REMOTE_FORBIDDEN", "wheelhouse must be a local directory, not a URL")
    root = Path(wheelhouse)
    if not root.is_dir():
        raise _err("NO_WHEEL", f"wheelhouse {root} does not exist")
    cand = root / lock["wheel"]
    if not cand.is_file() or cand.is_symlink():
        raise _err("NO_WHEEL", f"{lock['wheel']} not present in wheelhouse")
    got = _sha256_file(cand)
    if got != lock["sha256"]:
        raise _err("HASH_MISMATCH", "wheel digest does not match lock", expected=lock["sha256"], got=got)
    return cand

# ------------------------------------------------------------------ API surface

def _file_surface(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: set[str] = set()
    aliases: dict[str, str] = {}
    bases_from_pk: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "pk_core":
            for a in node.names:
                out.add(f"{node.module}.{a.name}")
                aliases[a.asname or a.name] = f"{node.module}.{a.name}"
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] == "pk_core":
                    out.add(a.name)
                    aliases[(a.asname or a.name).split(".")[0]] = a.name.split(".")[0] if not a.asname else a.name
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            chain, cur = [], node
            while isinstance(cur, ast.Attribute):
                chain.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name) and cur.id in aliases and aliases[cur.id].split(".")[0] == "pk_core":
                if cur.id in {"pk_core"} and aliases[cur.id] == "pk_core":
                    out.add(".".join(["pk_core"] + list(reversed(chain))))
        if isinstance(node, ast.ClassDef):
            for b in node.bases:
                if isinstance(b, ast.Name) and b.id in aliases:
                    bases_from_pk.add(node.name)
                    base = aliases[b.id]
                    local = {n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) \
                                and sub.value.id == "self" and sub.attr not in local \
                                and isinstance(getattr(sub, "ctx", None), ast.Load):
                            out.add(f"{base}.{sub.attr}")
                        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Call) \
                                and isinstance(sub.value.func, ast.Name) and sub.value.func.id == "super":
                            out.add(f"{base}.{sub.attr}")
    return out


# Symbols reached dynamically (via the package's lazy COMPONENT attribute and on
# returned objects), which static import analysis cannot see; see tests/test_component.py.
DYNAMIC_SURFACE = (
    "pk_core.component.Component.assess_all",
    "pk_core.checklist.Finding.check_id",
    "pk_core.checklist.Finding.status",
    "pk_core.checklist.Finding.note",
)


def api_surface(package_dir: Path = PKG_DIR, *, include_dynamic: bool = True) -> list[str]:
    files = [package_dir / "component.py", package_dir / "contract.py"]
    files += sorted((package_dir / "tests").glob("*.py"))
    out: set[str] = set()
    for f in files:
        if f.is_file():
            out |= _file_surface(f)
    if include_dynamic:
        out |= set(DYNAMIC_SURFACE)
    # instance attributes set on the subclass itself are not pk_core API
    return sorted(s for s in out if not s.endswith((".element_id", ".element_name")))


def check_compat(surface: list[str], importer: Callable[[str], object] = importlib.import_module) -> dict:
    """Resolve each dotted symbol against an importable pk_core."""
    try:
        importer("pk_core")
    except ImportError:
        return {"state": "BLOCKED", "blocker": "pk_core not importable", "missing": list(surface),
                "checked": 0}
    missing = []
    for sym in surface:
        parts = sym.split(".")
        obj = None
        for i in range(len(parts), 0, -1):
            try:
                obj = importer(".".join(parts[:i]))
            except ImportError:
                continue
            try:
                for attr in parts[i:]:
                    obj = getattr(obj, attr)
            except AttributeError:
                obj = None
            break
        if obj is None:
            missing.append(sym)
    return {"state": "COMPATIBLE" if not missing else "INCOMPATIBLE", "missing": missing,
            "checked": len(surface)}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="pk_core pin / lock / API probe")
    ap.add_argument("cmd", choices=["status", "surface"])
    a = ap.parse_args(argv)
    if a.cmd == "surface":
        print(json.dumps(api_surface(), indent=1))
        return 0
    lock = load_lock()
    res = {"lock_state": lock["state"], "blocker": lock.get("blocker"),
           "compat": check_compat(api_surface())}
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0 if lock["state"] == "RESOLVED" and res["compat"]["state"] == "COMPATIBLE" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
