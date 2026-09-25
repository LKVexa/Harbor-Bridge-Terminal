"""Component 33 - single-command deterministic bootstrap.

``python3 -m inv08_dynamic_infrastructure_model.production.bootstrap ROOT CONFIG.json
    --author NAME --source REF [--disaster]``

Steps (each idempotent, each verified on rerun; manifest ``PK_DYN_BOOTSTRAP/1``):
 1. layout   - ROOT/{trust,store,journal,config,registry,quarantine}
 2. trust    - NONPRODUCTION HMAC key (32 random bytes, file mode 0600) with key
               id ``nonprod-<sha256 prefix>``; production trust roots are BLOCKED
               on an external KMS/HSM.  Rerun keeps the existing key.
 3. store    - lease store schema file (``PK_DYN_LEASESTORE/1``) + journal dir
 4. config   - validated config envelope activated via ConfigDeployer
 5. registry - site + providers from config, signed with the trust key
The manifest records step digests (never key material).  Rerun with the same
config returns an identical manifest digest; rerun with a *different* config
fails with INV08.BOOTSTRAP.CONFLICT (use the config deployer instead).
Disaster path (``disaster=True``): corrupt store/registry files are moved to
quarantine/ and recreated empty; the manifest records that desired state must
be re-adopted from providers via ``Controller.recover``.
"""
from __future__ import annotations

import json
import os
import secrets as _stdlib_secrets
import shutil
import sys
from pathlib import Path
from typing import Callable

from .config import ConfigDeployer, with_provenance
from .core import Inv08Error, Outcome, TrustRoot, digest, sha256_hex
from .journal import Journal
from .leasestore import LeaseStore, _atomic_write

SCHEMA = "PK_DYN_BOOTSTRAP/1"


def _load_trust(root: Path, key_source: Callable[[int], bytes]) -> tuple[TrustRoot, str, bool]:
    kf = root / "trust" / "nonprod.key"
    created = False
    if not kf.exists():
        key = key_source(32)
        fd = os.open(kf, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(key)
            fh.flush()
            os.fsync(fh.fileno())
        created = True
    key = kf.read_bytes()
    kid = "nonprod-" + sha256_hex(key)[:12]
    tr = TrustRoot()
    tr.add(kid, key, production=False)
    return tr, kid, created


def bootstrap(root: str | os.PathLike, raw_config: dict, *, author: str, source: str, ts: float = 0.0,
              disaster: bool = False, key_source: Callable[[int], bytes] = _stdlib_secrets.token_bytes) -> dict:
    root = Path(root)
    steps: dict[str, str] = {}
    quarantined: list[str] = []
    for d in ("trust", "store", "journal", "config", "registry", "quarantine"):
        (root / d).mkdir(parents=True, exist_ok=True)
    steps["layout"] = "ok"

    trust, kid, created = _load_trust(root, key_source)
    steps["trust"] = "created" if created else "existing"

    envelope = with_provenance(raw_config, author=author, source=source, created_ts=ts)
    cfg = envelope["config"]

    def _quarantine(p: Path) -> None:
        dest = root / "quarantine" / f"{p.name}.{len(list((root / 'quarantine').iterdir()))}"
        shutil.move(str(p), dest)
        quarantined.append(dest.name)

    store_path = root / "store" / "leases.json"
    try:
        LeaseStore(store_path)
    except Inv08Error as exc:
        if not disaster:
            raise
        _quarantine(store_path)
        LeaseStore(store_path)
        steps["store_recovered"] = exc.code
    try:
        Journal(root / "journal")
    except Inv08Error as exc:
        if not disaster:
            raise
        _quarantine(root / "journal")
        Journal(root / "journal")
        steps["journal_recovered"] = exc.code
    steps["store"] = "ok"

    dep = ConfigDeployer(root / "config", env=cfg["env"], tenant=cfg["tenant"])
    active = dep.active()
    if active is None:
        sid = dep.stage(envelope)
        dep.validate_staged(sid)
        dep.activate(sid)
        steps["config"] = "activated"
    elif active["provenance"]["digest"] != envelope["provenance"]["digest"]:
        raise Inv08Error("INV08.BOOTSTRAP.CONFLICT", "bootstrap rerun with a different config",
                         outcome=Outcome.OPERATOR_REQUIRED,
                         remediation="use ConfigDeployer to change configuration after bootstrap")
    else:
        steps["config"] = "existing"

    registry = {"schema": "PK_DYN_REGISTRY/1", "site": cfg["site"], "env": cfg["env"],
                "tenant": cfg["tenant"],
                "providers": sorted(({"name": p["name"], "kind": p["kind"]} for p in cfg["providers"]),
                                    key=lambda p: p["name"])}
    reg_path = root / "registry" / "registry.json"
    if reg_path.exists():
        try:
            doc = json.loads(reg_path.read_bytes())
            if not trust.verify(doc["registry"], doc["signature"]):
                raise ValueError("signature")
            if doc["registry"] != registry:
                raise Inv08Error("INV08.BOOTSTRAP.CONFLICT", "registry differs from config",
                                 outcome=Outcome.OPERATOR_REQUIRED)
            steps["registry"] = "existing"
        except (ValueError, KeyError, TypeError):
            if not disaster:
                raise Inv08Error("INV08.BOOTSTRAP.CORRUPT", "registry unreadable or signature invalid",
                                 outcome=Outcome.OPERATOR_REQUIRED, remediation="rerun with --disaster") from None
            _quarantine(reg_path)
    if not reg_path.exists():
        _atomic_write(reg_path, json.dumps({"registry": registry, "signature": trust.sign(kid, registry)},
                                           sort_keys=True).encode())
        steps["registry"] = "registered"

    manifest = {"schema": SCHEMA, "trust_kid": kid, "trust_production": False,
                "config_digest": envelope["provenance"]["digest"], "registry_digest": digest(registry),
                "store_schema": "PK_DYN_LEASESTORE/1"}
    result = {"manifest": manifest, "manifest_digest": digest(manifest), "steps": steps,
              "quarantined": quarantined,
              "next": "Controller.recover(...) to re-adopt observed state" if disaster else "start controller"}
    _atomic_write(root / "bootstrap.json", json.dumps(result, sort_keys=True).encode())
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="inv08-bootstrap")
    ap.add_argument("root")
    ap.add_argument("config")
    ap.add_argument("--author", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--disaster", action="store_true")
    a = ap.parse_args(argv)
    try:
        res = bootstrap(a.root, json.loads(Path(a.config).read_text()), author=a.author, source=a.source,
                        disaster=a.disaster)
    except Inv08Error as exc:
        print(json.dumps(exc.to_dict()), file=sys.stderr)
        return 2
    print(json.dumps(res, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
