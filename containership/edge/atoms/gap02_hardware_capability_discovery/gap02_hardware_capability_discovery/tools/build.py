"""GAP02-MC-52 — reproducible package + SBOM + MANIFEST.

Deterministic zip: sorted entries, fixed timestamp (SOURCE_DATE_EPOCH or
2026-09-22T00:00:00Z), fixed permissions, no __pycache__. Two builds of the
same tree produce identical bytes.

    python -m gap02_hardware_capability_discovery.tools.build OUT.zip
"""
import hashlib, json, os, sys, time, zipfile

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = os.path.basename(PKG)
EXCLUDE_DIRS = {"__pycache__", ".git", "evidence_runs"}
EPOCH = int(os.environ.get("SOURCE_DATE_EPOCH", "1790035200"))  # 2026-09-22T00:00:00Z


def files():
    out = []
    for root, dirs, fs in os.walk(PKG):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
        for f in sorted(fs):
            if f.endswith((".pyc", ".zip")):
                continue
            out.append(os.path.relpath(os.path.join(root, f), PKG).replace(os.sep, "/"))
    return sorted(out)


def sha(p):
    return hashlib.sha256(open(os.path.join(PKG, p), "rb").read()).hexdigest()


def write_manifest():
    lines = [f"{sha(p)}  ./{p}" for p in files() if p != "MANIFEST.sha256"]
    open(os.path.join(PKG, "MANIFEST.sha256"), "w", newline="\n").write("\n".join(lines) + "\n")


def sbom(version):
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(EPOCH)),
                         "component": {"type": "library", "name": NAME, "version": version}},
            "components": [
                {"type": "platform", "name": "cpython", "version": ">=3.10", "scope": "required"},
                {"type": "library", "name": "pk_core", "scope": "optional",
                 "description": "external suite dependency, not bundled (see PK_CORE_CONTRACT.json)"},
                {"type": "library", "name": "opentelemetry-api", "scope": "optional"}],
            "properties": [{"name": "third_party_code_bundled", "value": "none"}]}


def build(out):
    version = open(os.path.join(PKG, "VERSION")).read().strip()
    json.dump(sbom(version), open(os.path.join(PKG, "SBOM.cdx.json"), "w"), indent=1, sort_keys=True)
    write_manifest()
    dt = time.gmtime(EPOCH)[:6]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files():
            zi = zipfile.ZipInfo(f"{NAME}/{p}", date_time=dt)
            zi.external_attr = 0o644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, open(os.path.join(PKG, p), "rb").read())
    return hashlib.sha256(open(out, "rb").read()).hexdigest()


if __name__ == "__main__":
    print(build(sys.argv[1]))
