"""Minimal standalone GAP-14 decision example."""
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gap14_data_gravity_manager import Dataset, GravityManager  # noqa: E402

manager = GravityManager(
    residency={"dub": {"public", "pii"}, "ams": {"public"}},
    distance={("dub", "ams"): 1.0, ("ams", "dub"): 1.0},
    compute_sites={"dub", "ams"},
    egress_per_gb={("dub", "ams"): 1.25},
)

print(manager.recommend(Dataset("lake", "dub", 500, "public"), "ams"))
