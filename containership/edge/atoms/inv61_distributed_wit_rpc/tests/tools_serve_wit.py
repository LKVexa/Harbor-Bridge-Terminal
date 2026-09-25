import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from serve import DEMO_WIT  # noqa: E402,F401
