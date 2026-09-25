"""Signer-side tooling: create PKED25519/1-signed commits, signed reverts and
provenance notes in a *working* repository with git plumbing.

This is what a developer/CI signer (not the controller) runs.  Rollback by
revert is ``revert_to``: a new commit whose tree is the target revision's
tree, whose parent is the current head (so it is a fast-forward and keeps
history), carrying the trailer ``PK-Revert-To: <oid>`` and a signature -- the
rollback therefore has an author, a signature and its own history entry.
"""
from __future__ import annotations

import os
import subprocess

from . import provenance
from .signing import insert_signature, sign_payload


def _git(repo: str, *args: str, input: bytes | None = None, env: dict | None = None) -> bytes:
    e = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", **(env or {})}
    p = subprocess.run(["git", "-C", repo, *args], input=input, capture_output=True, env=e, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {p.stderr.decode(errors='replace')[-300:]}")
    return p.stdout


def init(repo: str, *, branch: str = "main") -> None:
    os.makedirs(repo, exist_ok=True)
    _git(repo, "init", "-q", "-b", branch)
    _git(repo, "config", "user.name", "fixture")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "config", "commit.gpgsign", "false")


def write_files(repo: str, files: dict[str, str | None]) -> None:
    for rel, content in files.items():
        p = os.path.join(repo, rel)
        if content is None:
            if os.path.exists(p):
                os.unlink(p)
            continue
        os.makedirs(os.path.dirname(p) or repo, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)


def signed_commit(repo: str, message: str, *, key_id: str, secret: bytes | None, email: str,
                  name: str = "Signer", when: int = 1_790_000_000, ref: str = "refs/heads/main",
                  tree: str | None = None, sign_as: bytes | None = None) -> str:
    """Commit the working tree (or ``tree``) signed with ``secret``; ``secret=None`` -> unsigned."""
    if tree is None:
        _git(repo, "add", "-A")
        tree = _git(repo, "write-tree").decode().strip()
    head = _git(repo, "rev-parse", "--verify", "-q", ref).decode().strip() if _has(repo, ref) else None
    env = {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_NAME": name,
           "GIT_COMMITTER_EMAIL": email, "GIT_AUTHOR_DATE": f"{when} +0000", "GIT_COMMITTER_DATE": f"{when} +0000"}
    args = ["commit-tree", tree] + (["-p", head] if head else []) + ["-m", message]
    oid = _git(repo, *args, env=env).decode().strip()
    if secret is not None:
        raw = _git(repo, "cat-file", "commit", oid)
        signed = insert_signature(raw, sign_payload(sign_as or secret, key_id, raw))
        oid = _git(repo, "hash-object", "-t", "commit", "-w", "--stdin", input=signed).decode().strip()
    _git(repo, "update-ref", ref, oid)
    if ref == "refs/heads/main" or _git(repo, "symbolic-ref", "HEAD").decode().strip() == ref:
        _git(repo, "reset", "-q", "--hard", oid)
    return oid


def _has(repo: str, ref: str) -> bool:
    p = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "-q", ref], capture_output=True)
    return p.returncode == 0


def tree_of(repo: str, oid: str) -> str:
    return _git(repo, "rev-parse", oid + "^{tree}").decode().strip()


def revert_to(repo: str, target_oid: str, *, key_id: str, secret: bytes, email: str, when: int,
              ref: str = "refs/heads/main") -> str:
    msg = f"Revert to {target_oid[:12]}\n\nPK-Revert-To: {target_oid}\n"
    return signed_commit(repo, msg, key_id=key_id, secret=secret, email=email, when=when, ref=ref,
                         tree=tree_of(repo, target_oid))


def add_provenance(repo: str, oid: str, *, repo_url: str, ref: str, builder_id: str,
                   signers: list[tuple[str, bytes]], tree: str | None = None) -> None:
    st = provenance.make_statement(commit=oid, tree=tree or tree_of(repo, oid), repo_url=repo_url,
                                   builder_id=builder_id, ref=ref)
    env = provenance.sign_envelope(st, signers)
    _git(repo, "notes", "--ref", "refs/notes/provenance", "add", "-f", "-F", "-", oid, input=env)
