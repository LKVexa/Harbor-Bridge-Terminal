"""Version consistency: VERSION == _version.__version__ == pyproject dynamic source == CHANGELOG head."""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def check() -> list:
    v = (ROOT / "VERSION").read_text().strip()
    errs = []
    m = re.search(r'__version__ = "([^"]+)"', (ROOT / "_version.py").read_text())
    if not m or m.group(1) != v:
        errs.append(f"_version.py {m and m.group(1)} != VERSION {v}")
    if 'attr = "inv23_hardware_virtualization_primitive._version.__version__"' not in (ROOT / "pyproject.toml").read_text():
        errs.append("pyproject version is not sourced from _version.py")
    head = re.search(r"^## (\S+)", (ROOT / "CHANGELOG.md").read_text(), re.M)
    if not head or head.group(1) != v:
        errs.append(f"CHANGELOG head {head and head.group(1)} != VERSION {v}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        errs.append("VERSION is not SemVer MAJOR.MINOR.PATCH")
    return errs


if __name__ == "__main__":
    e = check()
    print("\n".join(e) or "version consistent")
    sys.exit(1 if e else 0)
