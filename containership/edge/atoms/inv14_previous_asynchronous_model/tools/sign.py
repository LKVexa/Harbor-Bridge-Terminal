"""Release signing + verification hook (component P2-29; C045).

Ed25519 detached signature over MANIFEST.sha256 (which itself hashes every file).
Backends: the `cryptography` package if importable, else the `openssl` CLI (>=1.1.1).
If neither exists, verification FAILS (exit 3) -- it never passes by default.

Trust policy: governance/TRUSTED_KEYS.json lists public keys with status
TRUSTED / REVOKED / UNTRUSTED_DEV.  `verify --require-trusted` accepts only a
signature by a TRUSTED key.  This archive ships only a build-generated
UNTRUSTED_DEV key: its signature proves integrity since build, NOT authority.

  python3 tools/sign.py keygen --out DIR --key-id NAME        (private key stays in DIR)
  python3 tools/sign.py sign --key DIR/NAME.pem --key-id NAME
  python3 tools/sign.py verify [--require-trusted]
"""
import argparse, base64, hashlib, json, os, shutil, subprocess, sys, tempfile
import _path  # noqa

PKG = _path.PKG
MANIFEST = PKG / "MANIFEST.sha256"
SIG = PKG / "MANIFEST.sha256.sig.json"
KEYS = PKG / "governance" / "TRUSTED_KEYS.json"


def backend():
    try:
        import cryptography  # noqa
        return "cryptography"
    except ImportError:
        return "openssl" if shutil.which("openssl") else None


def _crypto_sign(pem: bytes, data: bytes) -> bytes:
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    return load_pem_private_key(pem, None).sign(data)


def _crypto_verify(pub_raw: bytes, sig: bytes, data: bytes) -> bool:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    try:
        Ed25519PublicKey.from_public_bytes(pub_raw).verify(sig, data); return True
    except InvalidSignature:
        return False


def _openssl_verify(pub_raw: bytes, sig: bytes, data: bytes) -> bool:
    der = bytes.fromhex("302a300506032b6570032100") + pub_raw
    with tempfile.TemporaryDirectory() as d:
        pp, sp, dp = (os.path.join(d, n) for n in ("pub.der", "sig", "data"))
        open(pp, "wb").write(der); open(sp, "wb").write(sig); open(dp, "wb").write(data)
        r = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-keyform", "DER", "-inkey", pp, "-rawin", "-in", dp, "-sigfile", sp],
                           capture_output=True)
        return r.returncode == 0


def _has_crypto():
    try:
        import cryptography  # noqa
        return True
    except ImportError:
        return False


def _openssl_keygen(out, key_id):
    p = os.path.join(out, key_id + ".pem")
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", p], check=True, capture_output=True)
    os.chmod(p, 0o600)
    der = subprocess.run(["openssl", "pkey", "-in", p, "-pubout", "-outform", "DER"], check=True, capture_output=True).stdout
    return base64.b64encode(der[-32:]).decode()


def _openssl_sign(key_path, data):
    with tempfile.TemporaryDirectory() as d:
        dp, sp = os.path.join(d, "data"), os.path.join(d, "sig")
        open(dp, "wb").write(data)
        subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", key_path, "-rawin", "-in", dp, "-out", sp], check=True, capture_output=True)
        return open(sp, "rb").read()


def keygen(out, key_id):
    # D-06: clean-room run showed signing required `cryptography`; the openssl CLI is now a full fallback.
    os.makedirs(out, exist_ok=True)
    if not _has_crypto():
        return _openssl_keygen(out, key_id)
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization as s
    k = Ed25519PrivateKey.generate()
    os.makedirs(out, exist_ok=True)
    p = os.path.join(out, key_id + ".pem")
    open(p, "wb").write(k.private_bytes(s.Encoding.PEM, s.PrivateFormat.PKCS8, s.NoEncryption()))
    os.chmod(p, 0o600)
    return base64.b64encode(k.public_key().public_bytes(s.Encoding.Raw, s.PublicFormat.Raw)).decode()


def sign(key_path, key_id):
    data = MANIFEST.read_bytes()
    sig = _crypto_sign(open(key_path, "rb").read(), data) if _has_crypto() else _openssl_sign(key_path, data)
    SIG.write_text(json.dumps({"schema": "PK_POLL_SIGNATURE/1", "alg": "Ed25519", "key_id": key_id,
                               "manifest_sha256": hashlib.sha256(data).hexdigest(),
                               "signature": base64.b64encode(sig).decode()}, indent=1, sort_keys=True) + "\n")


def verify(require_trusted=False):
    be = backend()
    if be is None:
        return 3, "NO_CRYPTO_BACKEND"
    if not SIG.exists():
        return 4, "NO_SIGNATURE"
    s = json.loads(SIG.read_text()); keys = {k["key_id"]: k for k in json.loads(KEYS.read_text())["keys"]}
    k = keys.get(s.get("key_id"))
    if k is None:
        return 5, "UNKNOWN_KEY"
    if k["status"] == "REVOKED":
        return 5, "REVOKED_KEY"
    data = MANIFEST.read_bytes()
    if hashlib.sha256(data).hexdigest() != s.get("manifest_sha256"):
        return 6, "MANIFEST_CHANGED"
    ok = (_crypto_verify if be == "cryptography" else _openssl_verify)(base64.b64decode(k["public_key"]), base64.b64decode(s["signature"]), data)
    if not ok:
        return 6, "BAD_SIGNATURE"
    if require_trusted and k["status"] != "TRUSTED":
        return 7, "SIGNER_NOT_TRUSTED:" + k["status"]
    return 0, "OK:" + k["status"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="c", required=True)
    g = sub.add_parser("keygen"); g.add_argument("--out", required=True); g.add_argument("--key-id", required=True)
    sg = sub.add_parser("sign"); sg.add_argument("--key", required=True); sg.add_argument("--key-id", required=True)
    v = sub.add_parser("verify"); v.add_argument("--require-trusted", action="store_true")
    a = ap.parse_args()
    if a.c == "keygen":
        print(keygen(a.out, a.key_id))
    elif a.c == "sign":
        sign(a.key, a.key_id); print("signed")
    else:
        rc, msg = verify(a.require_trusted); print(msg); sys.exit(rc)
