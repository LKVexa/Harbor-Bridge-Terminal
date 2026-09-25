import pathlib, sys
PKG = pathlib.Path(__file__).resolve().parents[1]
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
sys.dont_write_bytecode = True
