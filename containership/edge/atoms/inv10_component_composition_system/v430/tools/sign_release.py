"""MC-43: release checksums + signature envelope, and verification gate.

  python tools/sign_release.py sign    # needs INV10_SIGNING_KEY (>=16 bytes) and INV10_SIGNER identity
  python tools/sign_release.py verify  # CI gate: checksums + signature must verify

Envelope: release/RELEASE.sha256 (sha256sum format, every tracked file) and
release/RELEASE.sig.json {version, manifest_sha256, key_id, signer, alg, signature}.
HMAC-SHA256 (stdlib); swap for Sigstore/ed25519 for third-party verifiability (ADR-0001 §2).
"""
import hashlib, hmac, json, os, sys
import _path  # noqa: F401
from _path import ROOT
from inv10_component_composition_system import __version__

EXCLUDE_DIRS = {".git", "__pycache__", "release", "dist", "build", ".github-cache"}
REL = ROOT / "release"


def files():
    out = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & EXCLUDE_DIRS) and not p.name.endswith(".pyc"):
            out.append(p)
    return out


def manifest_text():
    return "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT).as_posix()}\n" for p in files())


def key():
    k = os.environ.get("INV10_SIGNING_KEY", "").encode()
    if len(k) < 16:
        sys.exit("INV10_SIGNING_KEY missing or shorter than 16 bytes")
    return k


def sign():
    REL.mkdir(exist_ok=True)
    text = manifest_text()
    (REL / "RELEASE.sha256").write_text(text)
    k = key()
    digest = hashlib.sha256(text.encode()).hexdigest()
    env = {"version": __version__, "manifest_sha256": digest, "alg": "HMAC-SHA256",
           "key_id": hashlib.sha256(k).hexdigest()[:16], "signer": os.environ.get("INV10_SIGNER", "unspecified"),
           "signature": hmac.new(k, digest.encode(), "sha256").hexdigest()}
    (REL / "RELEASE.sig.json").write_text(json.dumps(env, indent=1) + "\n")
    print(json.dumps(env, indent=1))


def verify():
    recorded = (REL / "RELEASE.sha256").read_text()
    current = manifest_text()
    if recorded != current:
        a, b = set(recorded.splitlines()), set(current.splitlines())
        sys.exit("checksum mismatch:\n" + "\n".join(sorted(f"- {l}" for l in a - b) + sorted(f"+ {l}" for l in b - a)))
    env = json.loads((REL / "RELEASE.sig.json").read_text())
    digest = hashlib.sha256(recorded.encode()).hexdigest()
    k = key()
    ok = env["manifest_sha256"] == digest and hmac.compare_digest(
        env["signature"], hmac.new(k, digest.encode(), "sha256").hexdigest())
    if not ok:
        sys.exit("signature invalid")
    print(f"release {env['version']} verified: {len(recorded.splitlines())} files, signer={env['signer']}")


if __name__ == "__main__":
    {"sign": sign, "verify": verify}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
