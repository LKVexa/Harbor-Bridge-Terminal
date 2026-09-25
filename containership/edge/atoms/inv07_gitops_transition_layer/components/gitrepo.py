"""Real Git transport and repository adapter (component 01).

Drives the system ``git`` executable (>= 2.31) through ``subprocess`` with an
argument vector -- never a shell -- against a controller-owned bare mirror.

Safety invariants
-----------------
* **Remote pinning.**  The mirror's ``origin`` URL is fixed at construction and
  re-checked before every fetch; a changed URL is ``RepositoryIdentity``.
* **Repository identity.**  When ``root_commit`` is configured, every resolved
  commit must descend from it (full fetch only; a shallow mirror cannot prove
  identity, so ``root_commit`` + ``depth > 0`` is refused).
* **URL policy.**  Only ``https``/``ssh`` (``file`` only when explicitly
  allowed, e.g. tests and air-gapped mirrors); credentials embedded in the URL,
  option-looking URLs (``-u...``) and hosts outside ``allowed_hosts`` are
  refused before git runs (SSRF / option-injection guard).
* **Credential flow.**  A bearer/basic header resolved from ``credential_ref``
  is handed to git via ``GIT_CONFIG_COUNT`` environment entries, never argv
  (so it cannot show up in ``ps``), and every stderr/exception is redacted.
* **Isolation.**  ``GIT_CONFIG_NOSYSTEM``, a private ``GIT_CONFIG_GLOBAL``,
  ``GIT_TERMINAL_PROMPT=0`` and ``protocol.allow=never`` except the allowed
  schemes: user/system git config cannot redirect or weaken the controller.
* **Bounded.**  Every call has a timeout; blob reads check ``cat-file -s``
  against ``max_blob_bytes`` before reading.
* **Availability.**  ``last_fetch_ok`` / ``last_error`` feed offline policy
  (component 18) and health; timeouts and non-zero exits are
  ``RepositoryUnavailable`` (retryable).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlsplit

from .errors import LimitExceeded, Malformed, NetworkPolicy, RepositoryIdentity, RepositoryUnavailable
from .redact import scrub_text

OID_RE = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
REF_RE = re.compile(r"^refs/(heads|tags|notes)/[A-Za-z0-9._/-]{1,200}$")
MIN_GIT = (2, 31)


def git_version(git: str = "git") -> tuple[int, int, int]:
    out = subprocess.run([git, "--version"], capture_output=True, text=True, timeout=10).stdout
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
    if not m:
        raise RepositoryUnavailable("git executable not usable")
    return tuple(int(x) for x in m.groups())  # type: ignore[return-value]


def check_url(url: str, *, allowed_hosts: list[str] | tuple = (), allow_file: bool = False) -> str:
    if not isinstance(url, str) or not url or url.startswith("-") or any(c in url for c in "\n\r\t\x00 "):
        raise NetworkPolicy("repository URL rejected")
    if re.match(r"^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:", url):          # scp-like ssh form
        scheme, host = "ssh", url.split("@", 1)[1].split(":", 1)[0]
    else:
        parts = urlsplit(url)
        scheme, host = parts.scheme.lower(), (parts.hostname or "")
        if parts.username and scheme in ("http", "https"):
            raise NetworkPolicy("credentials must not be embedded in the repository URL")
        if parts.password:
            raise NetworkPolicy("credentials must not be embedded in the repository URL")
    if scheme == "file":
        if not allow_file:
            raise NetworkPolicy("file:// repositories are disabled by policy")
        return scheme
    if scheme not in ("https", "ssh"):
        raise NetworkPolicy("repository scheme not allowed", scheme=scheme)
    if allowed_hosts and host.lower() not in {h.lower() for h in allowed_hosts}:
        raise NetworkPolicy("repository host not in allowed_hosts", host=host)
    return scheme


@dataclass(frozen=True)
class CommitInfo:
    oid: str
    tree: str
    parents: tuple[str, ...]
    author: str
    committer: str
    committer_email: str
    commit_time: int
    message: str
    signature: str | None
    signed_payload: bytes


def parse_commit(oid: str, raw: bytes) -> CommitInfo:
    """Parse a raw commit object; ``signed_payload`` is the object without its
    ``gpgsig``/``gpgsig-sha256`` header -- exactly what git signs."""
    head, sep, msg = raw.partition(b"\n\n")
    if not sep:
        raise Malformed("commit object has no header/body separator", oid=oid)
    lines = head.split(b"\n")
    fields: dict[str, list[str]] = {}
    kept: list[bytes] = []
    sig_lines: list[bytes] | None = None
    in_sig = False
    for ln in lines:
        if in_sig and ln.startswith(b" "):
            sig_lines.append(ln[1:])  # type: ignore[union-attr]
            continue
        in_sig = False
        if ln.startswith(b"gpgsig ") or ln.startswith(b"gpgsig-sha256 "):
            if sig_lines is not None:
                raise Malformed("commit carries more than one signature header", oid=oid)
            sig_lines = [ln.split(b" ", 1)[1]]
            in_sig = True
            continue
        kept.append(ln)
        k, _, v = ln.partition(b" ")
        fields.setdefault(k.decode("ascii", "replace"), []).append(v.decode("utf-8", "replace"))
    if "tree" not in fields or "committer" not in fields:
        raise Malformed("commit object missing tree/committer", oid=oid)
    committer = fields["committer"][0]
    m = re.match(r"^(.*) <([^>]*)> (\d+) ([+-]\d{4})$", committer)
    if not m:
        raise Malformed("committer line unparseable", oid=oid)
    return CommitInfo(oid=oid, tree=fields["tree"][0], parents=tuple(fields.get("parent", [])),
                      author=fields.get("author", [""])[0], committer=committer, committer_email=m.group(2),
                      commit_time=int(m.group(3)), message=msg.decode("utf-8", "replace"),
                      signature=(b"\n".join(sig_lines).decode("utf-8", "replace") if sig_lines is not None else None),
                      signed_payload=b"\n".join(kept) + b"\n\n" + msg)


class GitRepository:
    """A pinned, bare mirror of one remote repository."""

    def __init__(self, url: str, mirror_dir: str, *, allowed_hosts=(), allow_file: bool = False,
                 root_commit: str | None = None, depth: int = 0, timeout: float = 120.0,
                 credential: Callable[[], str] | None = None, git: str = "git",
                 max_blob_bytes: int = 1 << 20, clock: Callable[[], float] = time.time) -> None:
        self.scheme = check_url(url, allowed_hosts=allowed_hosts, allow_file=allow_file)
        if root_commit and depth:
            raise RepositoryIdentity("root_commit identity pinning requires a full (depth=0) fetch")
        if root_commit and not OID_RE.match(root_commit):
            raise Malformed("root_commit must be a full OID")
        ver = git_version(git)
        if ver[:2] < MIN_GIT:
            raise RepositoryUnavailable("git too old", version=".".join(map(str, ver)))
        self.url, self.dir, self.git = url, os.path.abspath(mirror_dir), git
        self.root_commit, self.depth, self.timeout = root_commit, depth, timeout
        self.max_blob_bytes, self._cred, self._clock = max_blob_bytes, credential, clock
        self._lock = threading.RLock()
        self.last_fetch_ok: float | None = None
        self.last_error: str | None = None
        self._global_cfg = os.path.join(self.dir + ".gitconfig")

    # -- process plumbing -------------------------------------------------
    def _env(self) -> dict:
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "LANG", "HOME",
                                                              "SSH_AUTH_SOCK", "GNUPGHOME")}
        env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": self._global_cfg,
                    "GIT_ASKPASS": "", "SSH_ASKPASS": "", "LC_ALL": "C"})
        cfg = [("protocol.allow", "never"), (f"protocol.{self.scheme}.allow", "always"),
               ("core.hooksPath", os.devnull), ("transfer.fsckObjects", "true"), ("http.followRedirects", "false")]
        if self._cred is not None:
            cfg.append(("http.extraHeader", "Authorization: " + self._cred()))
        env["GIT_CONFIG_COUNT"] = str(len(cfg))
        for i, (k, v) in enumerate(cfg):
            env[f"GIT_CONFIG_KEY_{i}"], env[f"GIT_CONFIG_VALUE_{i}"] = k, v
        return env

    def _run(self, *args: str, input: bytes | None = None, check: bool = True, git_dir: bool = True) -> bytes:
        argv = [self.git] + (["--git-dir", self.dir] if git_dir else []) + list(args)
        try:
            p = subprocess.run(argv, input=input, capture_output=True, timeout=self.timeout, env=self._env())
        except subprocess.TimeoutExpired:
            raise RepositoryUnavailable("git operation timed out", op=args[0], timeout=self.timeout) from None
        except OSError as exc:
            raise RepositoryUnavailable("git executable failed to start", op=args[0], cause=type(exc).__name__) from None
        if check and p.returncode != 0:
            raise RepositoryUnavailable("git operation failed", op=args[0], rc=p.returncode,
                                        stderr=scrub_text(p.stderr.decode("utf-8", "replace"))[-400:])
        return p.stdout

    # -- lifecycle ----------------------------------------------------------
    def ensure(self) -> None:
        with self._lock:
            if not os.path.isdir(self.dir):
                os.makedirs(os.path.dirname(self.dir) or ".", exist_ok=True)
                open(self._global_cfg, "a").close()
                self._run("init", "--bare", "--quiet", self.dir, git_dir=False)
                self._run("config", "remote.origin.url", self.url)
            pinned = self._run("config", "--get", "remote.origin.url", check=False).decode().strip()
            if pinned != self.url:
                raise RepositoryIdentity("mirror remote URL differs from the pinned repository URL")

    def fetch(self) -> dict:
        """Fetch all heads/tags (+ provenance notes) into the mirror; prune deleted refs."""
        with self._lock:
            self.ensure()
            args = ["fetch", "--prune", "--no-write-fetch-head", "--quiet"]
            if self.depth:
                args += ["--depth", str(self.depth)]
            args += ["origin", "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*",
                     "+refs/notes/*:refs/notes/*"]
            try:
                self._run(*args)
            except RepositoryUnavailable as exc:
                self.last_error = exc.code
                raise
            self.last_fetch_ok, self.last_error = self._clock(), None
            return {"fetched_at": self.last_fetch_ok, "refs": len(self.refs())}

    def refs(self) -> dict[str, str]:
        out = self._run("for-each-ref", "--format=%(refname) %(objectname)", check=False).decode()
        return dict(ln.split(" ", 1)[::1] for ln in out.splitlines() if " " in ln)  # type: ignore[misc]

    def resolve(self, ref: str) -> str:
        if not REF_RE.match(ref) or ".." in ref:
            raise Malformed("ref name rejected", ref=ref)
        oid = self._run("rev-parse", "--verify", "--quiet", "--end-of-options", ref + "^{commit}",
                        check=False).decode().strip()
        if not OID_RE.match(oid):
            raise RepositoryUnavailable("ref does not resolve to a commit", ref=ref)
        self.verify_identity(oid)
        return oid

    def verify_identity(self, oid: str) -> None:
        if not self.root_commit:
            return
        roots = self._run("rev-list", "--max-parents=0", "--end-of-options", oid).decode().split()
        if self.root_commit not in roots:
            raise RepositoryIdentity("commit does not descend from the pinned root commit", oid=oid)

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        for o in (ancestor, descendant):
            if not OID_RE.match(o):
                raise Malformed("OID expected")
        p = subprocess.run([self.git, "--git-dir", self.dir, "merge-base", "--is-ancestor", ancestor, descendant],
                           capture_output=True, timeout=self.timeout, env=self._env())
        if p.returncode not in (0, 1):
            raise RepositoryUnavailable("merge-base failed", rc=p.returncode)
        return p.returncode == 0

    def object_type(self, oid: str) -> str:
        return self._run("cat-file", "-t", oid).decode().strip()

    def read_commit(self, oid: str) -> CommitInfo:
        if not OID_RE.match(oid):
            raise Malformed("OID expected")
        return parse_commit(oid, self._run("cat-file", "commit", oid))

    def read_raw(self, oid: str, kind: str) -> bytes:
        return self._run("cat-file", kind, oid)

    def ls_tree(self, oid: str, prefix: str = "") -> list[tuple[str, str, str]]:
        """Return (mode, blob_oid, path) for blobs under ``prefix`` at commit ``oid``."""
        args = ["ls-tree", "-r", "-z", "--full-tree", oid]
        out = self._run(*args)
        items = []
        for rec in out.split(b"\0"):
            if not rec:
                continue
            meta, path = rec.split(b"\t", 1)
            mode, typ, boid = meta.decode().split(" ")
            p = path.decode("utf-8", "strict")
            if typ == "blob" and (not prefix or p == prefix or p.startswith(prefix.rstrip("/") + "/")):
                items.append((mode, boid, p))
        return items

    def read_blob(self, blob_oid: str) -> bytes:
        size = int(self._run("cat-file", "-s", blob_oid).decode().strip())
        if size > self.max_blob_bytes:
            raise LimitExceeded("blob exceeds max_blob_bytes", size=size, limit=self.max_blob_bytes)
        return self._run("cat-file", "blob", blob_oid)

    def note(self, oid: str, notes_ref: str = "refs/notes/provenance") -> bytes | None:
        p = subprocess.run([self.git, "--git-dir", self.dir, "notes", "--ref", notes_ref, "show", oid],
                           capture_output=True, timeout=self.timeout, env=self._env())
        return p.stdout if p.returncode == 0 else None

    def verify_commit_openpgp(self, oid: str, gnupghome: str) -> list[str]:
        """OpenPGP lane: run ``git verify-commit --raw`` with an isolated keyring
        and return the gpg status lines (``[GNUPG:] VALIDSIG ...``)."""
        env = self._env()
        env["GNUPGHOME"] = gnupghome
        p = subprocess.run([self.git, "--git-dir", self.dir, "verify-commit", "--raw", oid], capture_output=True,
                           timeout=self.timeout, env=env)
        return p.stderr.decode("utf-8", "replace").splitlines()

    def destroy(self) -> None:
        with self._lock:
            shutil.rmtree(self.dir, ignore_errors=True)
