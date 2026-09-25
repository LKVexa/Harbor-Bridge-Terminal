"""Operator CLI (day-0/1/2).  ``python -m inv66_enterprise_wasm_control_plane.production.cli --help``

    verify-journal ROOT [--trusted-keys FILE]   verify chain + signed anchors
    anchor ROOT --key-ref env:NAME              sign a checkpoint (Ed25519 seed, 32 bytes hex)
    export ROOT [--from N] [--to M]             self-verifying audit export to stdout
    backup ROOT DEST                            consistent copy of the journal (runbook RB-BACKUP)
    restore BACKUP ROOT                         restore into an EMPTY root, then verify
    validate-config FILE [FILE...]              layered config -> schema + semantic validation + digest
    demo [--port N]                             start a local estate + HTTP server for smoke tests
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from .config import build_policy, load_layers
from .errors import EcpError
from .journal import Journal
from .keys import LocalSecretProvider, Signer


def _signer(ref: str) -> Signer:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    seed = bytes.fromhex(LocalSecretProvider().resolve(ref).decode())
    return Signer("anchor-" + ref.split(":", 1)[1][:32], Ed25519PrivateKey.from_private_bytes(seed))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="inv66")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify-journal"); v.add_argument("root"); v.add_argument("--trusted-keys")
    a = sub.add_parser("anchor"); a.add_argument("root"); a.add_argument("--key-ref", required=True)
    e = sub.add_parser("export"); e.add_argument("root"); e.add_argument("--from", dest="f", type=int, default=1)
    e.add_argument("--to", type=int)
    b = sub.add_parser("backup"); b.add_argument("root"); b.add_argument("dest")
    r = sub.add_parser("restore"); r.add_argument("backup"); r.add_argument("root")
    c = sub.add_parser("validate-config"); c.add_argument("files", nargs="+")
    d = sub.add_parser("demo"); d.add_argument("--port", type=int, default=0); d.add_argument("--seconds", type=float, default=0)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "verify-journal":
            keys = json.loads(Path(args.trusted_keys).read_text()) if args.trusted_keys else None
            print(json.dumps(Journal(Path(args.root) / "journal").verify(keys), indent=1))
        elif args.cmd == "anchor":
            print(json.dumps(Journal(Path(args.root) / "journal").anchor(_signer(args.key_ref)), indent=1))
        elif args.cmd == "export":
            json.dump(Journal(Path(args.root) / "journal").export(args.f, args.to), sys.stdout)
        elif args.cmd == "backup":
            src = Path(args.root) / "journal"
            j = Journal(src)
            head = j.head
            dest = Path(args.dest)
            if dest.exists():
                raise EcpError("ECP_CONFIG_INVALID", "backup destination exists", field="dest")
            shutil.copytree(src, dest / "journal")
            (dest / "BACKUP.json").write_text(json.dumps({"head_seq": head[0], "head_hash": head[1],
                                                          "taken_at": time.time()}))
            Journal(dest / "journal").verify()
            print(json.dumps({"backup": str(dest), "head_seq": head[0]}))
        elif args.cmd == "restore":
            root = Path(args.root)
            if (root / "journal").exists() and any((root / "journal").rglob("*.jsonl")):
                raise EcpError("ECP_CONFIG_INVALID", "restore target not empty", field="root")
            meta = json.loads((Path(args.backup) / "BACKUP.json").read_text())
            shutil.copytree(Path(args.backup) / "journal", root / "journal", dirs_exist_ok=True)
            res = Journal(root / "journal").verify()
            if res["head_seq"] != meta["head_seq"] or res["head_hash"] != meta["head_hash"]:
                raise EcpError("ECP_STORE_CORRUPT", "restored head does not match backup manifest")
            print(json.dumps({"restored": str(root), **res}))
        elif args.cmd == "validate-config":
            p = build_policy(load_layers(*[Path(f) for f in args.files]))
            print(json.dumps({"valid": True, "generation": p.generation, "environment": p.environment}))
        elif args.cmd == "demo":
            from .http_api import Server
            from .testing import Estate
            est = Estate()
            srv = Server(est.service, port=args.port).start()
            print(json.dumps({"url": srv.url, "root": str(est.root), "ops_token": est.token("ops", ttl=3600)}))
            sys.stdout.flush()
            if args.seconds:
                time.sleep(args.seconds)
                srv.stop()
    except EcpError as err:
        print(json.dumps(err.envelope()), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
