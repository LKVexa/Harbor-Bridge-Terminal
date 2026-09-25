#!/usr/bin/env python3
"""Generate and validate the release SBOM as SPDX 2.3 JSON (M07).

The SBOM is derived from version-controlled metadata only (VERSION, toolchains/LOCK.json,
LICENSE presence). It is
deterministic: the creation time comes from SOURCE_DATE_EPOCH or the CHANGELOG release date,
and no local paths, usernames or URLs with credentials are written.

  python tools/sbom.py            # generate; fails if either LCTL pin is not APPROVED
  python tools/sbom.py --draft    # candidate SBOM: unpinned hashes recorded as NOASSERTION
  python tools/sbom.py --check    # validate the committed SBOM and its consistency with the lock
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
LOCK = PKG / "toolchains/LOCK.json"
NOA = "NOASSERTION"


def version() -> str:
    return (PKG / "VERSION").read_text(encoding="utf-8").strip()


def out_path() -> Path:
    return PKG / "sbom" / f"iOS735_LCTL-{version()}.spdx.json"


def created() -> str:
    if os.environ.get("SOURCE_DATE_EPOCH"):
        t = dt.datetime.fromtimestamp(int(os.environ["SOURCE_DATE_EPOCH"]), dt.timezone.utc)
    else:
        m = re.search(rf"^## {re.escape(version())} — (\d{{4}}-\d{{2}}-\d{{2}})", (PKG / "CHANGELOG.md").read_text("utf-8"), re.M)
        if not m:
            raise SystemExit("FAIL: CHANGELOG.md has no dated entry for VERSION")
        t = dt.datetime.fromisoformat(m.group(1)).replace(tzinfo=dt.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def repo_license() -> str:
    lic = PKG / "LICENSE"
    if not lic.is_file():
        return NOA
    m = re.search(r"SPDX-License-Identifier:\s*(\S+)", lic.read_text("utf-8", "replace"))
    return m.group(1) if m else "LicenseRef-iOS735-LCTL-Owner"


def build(draft: bool) -> dict:
    lock_raw = LOCK.read_bytes()
    lock = json.loads(lock_raw)
    ver = version()
    pk = [{
        "SPDXID": "SPDXRef-Package-iOS735-LCTL", "name": "iOS735_LCTL", "versionInfo": ver,
        "supplier": "Organization: iOS735 LCTL repository owner", "downloadLocation": NOA,
        "filesAnalyzed": False, "licenseConcluded": repo_license(), "licenseDeclared": repo_license(),
        "copyrightText": NOA, "primaryPackagePurpose": "SOURCE",
        "comment": "Python tooling is standard-library only: zero third-party Python packages. "
                   f"Toolchain lock sha256={hashlib.sha256(lock_raw).hexdigest()}.",
    }, {
        "SPDXID": "SPDXRef-Runtime-Python", "name": "CPython", "versionInfo": ">=3.10",
        "supplier": "Organization: Python Software Foundation", "downloadLocation": "https://www.python.org/downloads/",
        "filesAnalyzed": False, "licenseConcluded": "PSF-2.0", "licenseDeclared": "PSF-2.0", "copyrightText": NOA,
        "primaryPackagePurpose": "APPLICATION", "comment": "Build/verification interpreter requirement; not redistributed.",
    }, {
        "SPDXID": "SPDXRef-Runtime-Java", "name": "Java SE runtime", "versionInfo": f">={lock['java_policy']['min_major']}",
        "supplier": NOA, "downloadLocation": NOA, "filesAnalyzed": False,
        "licenseConcluded": NOA, "licenseDeclared": NOA, "copyrightText": NOA, "primaryPackagePurpose": "APPLICATION",
        "comment": "Vendor unconstrained by lock policy; the exact runtime of a verification run is recorded in evidence/VERIFY.json.",
    }]
    rel = [{"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES", "relatedSpdxElement": pk[0]["SPDXID"]},
           {"spdxElementId": "SPDXRef-Runtime-Python", "relationshipType": "BUILD_TOOL_OF", "relatedSpdxElement": pk[0]["SPDXID"]},
           {"spdxElementId": "SPDXRef-Runtime-Java", "relationshipType": "BUILD_DEPENDENCY_OF", "relatedSpdxElement": pk[0]["SPDXID"]}]
    for tc in lock["toolchains"]:
        sid = f"SPDXRef-Toolchain-{tc['role']}"
        p = {"SPDXID": sid, "name": tc["name"], "versionInfo": tc["version"], "supplier": f"Organization: {tc['publisher']}",
             "downloadLocation": NOA, "filesAnalyzed": False, "licenseConcluded": NOA, "licenseDeclared": NOA,
             "copyrightText": NOA, "primaryPackagePurpose": "APPLICATION",
             "comment": f"External; not redistributed. Required file {tc['jar_path']}. Lock status {tc['status']}."}
        if tc["status"] == "APPROVED":
            p["checksums"] = [{"algorithm": "SHA256", "checksumValue": tc["sha256"]}]
        elif not draft:
            raise SystemExit(f"FAIL: {tc['role']} is {tc['status']} in the lock; a release SBOM needs approved pins (use --draft for a candidate)")
        pk.append(p)
        rel.append({"spdxElementId": sid, "relationshipType": "BUILD_DEPENDENCY_OF", "relatedSpdxElement": pk[0]["SPDXID"]})
    return {
        "spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0", "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"iOS735_LCTL-{ver}" + ("-DRAFT" if draft else ""),
        "documentNamespace": f"https://ios735-lctl.invalid/spdx/iOS735_LCTL-{ver}-{hashlib.sha256(lock_raw).hexdigest()[:16]}",
        "creationInfo": {"created": created(), "creators": ["Tool: iOS735_LCTL tools/sbom.py"],
                         "comment": "DRAFT: owner toolchain pins and/or licence are unresolved." if draft else "Release SBOM."},
        "packages": pk, "relationships": rel,
    }


REQ_DOC = ("spdxVersion", "dataLicense", "SPDXID", "name", "documentNamespace", "creationInfo", "packages")
REQ_PKG = ("SPDXID", "name", "downloadLocation")


def validate(doc: dict) -> list[str]:
    errs = [f"missing {k}" for k in REQ_DOC if k not in doc]
    if doc.get("spdxVersion") != "SPDX-2.3" or doc.get("dataLicense") != "CC0-1.0":
        errs.append("spdxVersion/dataLicense invalid")
    ids = set()
    for p in doc.get("packages", []):
        errs += [f"{p.get('SPDXID')}: missing {k}" for k in REQ_PKG if k not in p]
        if not re.fullmatch(r"SPDXRef-[A-Za-z0-9.-]+", p.get("SPDXID", "")):
            errs.append(f"bad SPDXID {p.get('SPDXID')}")
        if p["SPDXID"] in ids:
            errs.append(f"duplicate {p['SPDXID']}")
        ids.add(p["SPDXID"])
        for c in p.get("checksums", []):
            if c["algorithm"] != "SHA256" or not re.fullmatch(r"[0-9a-f]{64}", c["checksumValue"]):
                errs.append(f"{p['SPDXID']}: bad checksum")
    for r in doc.get("relationships", []):
        for k in ("spdxElementId", "relatedSpdxElement"):
            if r[k] != "SPDXRef-DOCUMENT" and r[k] not in ids:
                errs.append(f"relationship references unknown {r[k]}")
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", doc.get("creationInfo", {}).get("created", "")):
        errs.append("creationInfo.created malformed")
    blob = json.dumps(doc)
    if re.search(r"(/home/|/Users/|C:\\\\|token=|password)", blob):
        errs.append("SBOM leaks a local path or credential")
    return errs


def consistency(doc: dict) -> list[str]:
    errs = []
    lock = json.loads(LOCK.read_bytes())
    main_pkg = doc["packages"][0]
    if main_pkg["versionInfo"] != version():
        errs.append("SBOM version != VERSION")
    if main_pkg["licenseDeclared"] != repo_license():
        errs.append("SBOM licence != LICENSE")
    byrole = {p["SPDXID"].rsplit("-", 1)[-1]: p for p in doc["packages"] if p["SPDXID"].startswith("SPDXRef-Toolchain-")}
    for tc in lock["toolchains"]:
        p = byrole.get(tc["role"])
        if p is None:
            errs.append(f"toolchain {tc['role']} missing from SBOM")
            continue
        got = (p.get("checksums") or [{}])[0].get("checksumValue")
        if got != tc.get("sha256"):
            errs.append(f"{tc['role']}: SBOM hash != lock pin")
    if set(byrole) - {tc["role"] for tc in lock["toolchains"]}:
        errs.append("SBOM lists a toolchain the lock does not")
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        path = out_path()
        if not path.is_file():
            print(f"FAIL: {path.relative_to(PKG)} missing")
            return 1
        doc = json.loads(path.read_text(encoding="utf-8"))
        errs = validate(doc) + consistency(doc)
        for e in errs:
            print("FAIL:", e)
        if not errs:
            print(f"PASS: {path.relative_to(PKG).as_posix()} valid SPDX-2.3 and consistent with VERSION/LICENSE/lock"
                  + (" (DRAFT)" if doc["name"].endswith("-DRAFT") else ""))
        return 1 if errs else 0
    doc = build(a.draft)
    errs = validate(doc)
    if errs:
        print("FAIL:", "; ".join(errs))
        return 1
    path = out_path()
    path.parent.mkdir(exist_ok=True)
    for old in path.parent.glob("iOS735_LCTL-*.spdx.json"):
        if old != path:
            old.unlink()
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(doc, indent=1, sort_keys=False) + "\n")
    os.replace(tmp, path)
    print(f"wrote {path.relative_to(PKG).as_posix()}" + (" (DRAFT)" if a.draft else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
