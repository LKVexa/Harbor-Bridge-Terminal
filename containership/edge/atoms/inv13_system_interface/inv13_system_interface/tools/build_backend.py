"""Minimal PEP 517 backend (stdlib only) so ``pip install .`` works offline."""
from __future__ import annotations
import base64, hashlib, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text().strip()
NAME = "inv13_system_interface"


def _rec(data: bytes) -> str:
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    fname = f"inv13_system_interface-{VERSION}-py3-none-any.whl"
    dist = f"inv13_system_interface-{VERSION}.dist-info"
    records = []
    with zipfile.ZipFile(Path(wheel_directory) / fname, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob("*")):
            rel = p.relative_to(ROOT)
            if p.is_file() and "__pycache__" not in rel.parts and rel.parts[0] not in ("dist", "evidence"):
                data = p.read_bytes()
                arc = f"{NAME}/{rel.as_posix()}"
                zi = zipfile.ZipInfo(arc, (2026, 9, 22, 0, 0, 0)); z.writestr(zi, data)
                records.append(f"{arc},{_rec(data)},{len(data)}")
        meta = f"Metadata-Version: 2.1\nName: inv13-system-interface\nVersion: {VERSION}\nRequires-Python: >=3.10\n".encode()
        wheel = b"Wheel-Version: 1.0\nGenerator: inv13-build-backend\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        for n, d in (("METADATA", meta), ("WHEEL", wheel)):
            z.writestr(zipfile.ZipInfo(f"{dist}/{n}", (2026, 9, 22, 0, 0, 0)), d)
            records.append(f"{dist}/{n},{_rec(d)},{len(d)}")
        records.append(f"{dist}/RECORD,,")
        z.writestr(zipfile.ZipInfo(f"{dist}/RECORD", (2026, 9, 22, 0, 0, 0)), "\n".join(records) + "\n")
    return fname


def get_requires_for_build_wheel(config_settings=None):
    return []
