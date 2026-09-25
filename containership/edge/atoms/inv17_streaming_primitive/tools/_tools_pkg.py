import importlib, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.dont_write_bytecode = True
pkg = importlib.import_module(ROOT.name)
def mod(name): return importlib.import_module(f"{ROOT.name}.{name}")
