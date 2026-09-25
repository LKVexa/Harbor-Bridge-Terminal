"""Put the directory containing the package on sys.path (declared, not ambient: tests only)."""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
