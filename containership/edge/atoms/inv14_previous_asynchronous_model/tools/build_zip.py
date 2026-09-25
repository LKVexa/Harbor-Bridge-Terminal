"""Deterministic release zip: sorted entries, fixed timestamp, fixed permissions,
no __pycache__/.pyc.  usage: python3 tools/build_zip.py OUT.zip [--no-evidence]"""
import sys, zipfile
import _path  # noqa
PKG = _path.PKG
FIXED = (2026, 9, 22, 0, 0, 0)


def build(out, include_evidence=True):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo(PKG.name + "/", FIXED), b"")
        for p in sorted(PKG.rglob("*")):
            rel = p.relative_to(PKG).as_posix()
            if "__pycache__" in p.parts or p.suffix == ".pyc" or (not include_evidence and rel.startswith("evidence/")):
                continue
            zi = zipfile.ZipInfo(f"{PKG.name}/{rel}" + ("/" if p.is_dir() else ""), FIXED)
            zi.external_attr = (0o40755 if p.is_dir() else 0o100644) << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, b"" if p.is_dir() else p.read_bytes())


if __name__ == "__main__":
    build(sys.argv[1], "--no-evidence" not in sys.argv)
