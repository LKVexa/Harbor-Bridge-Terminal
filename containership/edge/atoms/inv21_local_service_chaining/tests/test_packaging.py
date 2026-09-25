"""GAP-002 packaging: PEP 517 wheel + sdist build, content policy, reproducibility,
clean isolated install + smoke through the public call path from the built artifact."""
import hashlib, os, pathlib, subprocess, sys, tempfile, unittest, zipfile, tarfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PKG = REPO / "inv21_local_service_chaining"
FORBIDDEN = ("/tests/", "__pycache__", ".pyc", "/evidence/", ".env", "id_rsa", ".git/")


def _pinned_backend():
    """(name, sha256) of the build backend pinned in constraints.txt."""
    for line in (REPO / "constraints.txt").read_text().splitlines():
        if line.startswith("setuptools=="):
            ver = line.split("==")[1].split()[0]
            return f"setuptools-{ver}-py3-none-any.whl", line.split("sha256:")[1].strip()
    raise AssertionError("constraints.txt does not pin the build backend")


def _venv(tmp):
    subprocess.run([sys.executable, "-m", "venv", tmp], check=True, capture_output=True)
    py = str(pathlib.Path(tmp) / "bin" / "python")
    name, digest = _pinned_backend()
    have = subprocess.run([py, "-c", "import setuptools;print(setuptools.__version__)"], capture_output=True, text=True)
    if have.returncode == 0 and name.split("-")[1] == have.stdout.strip():
        return py
    import glob
    cands = [os.environ.get("INV21_BACKEND_WHEEL", "")] + glob.glob(f"/usr/lib/python3*/ensurepip/_bundled/{name}")
    for c in filter(None, cands):
        if os.path.exists(c) and hashlib.sha256(pathlib.Path(c).read_bytes()).hexdigest() == digest:
            subprocess.run([py, "-m", "pip", "install", "-q", "--no-index", "--no-deps", c], check=True,
                           capture_output=True)
            return py
    raise AssertionError(f"pinned build backend {name} (sha256 {digest[:12]}...) not available; "
                         "set INV21_BACKEND_WHEEL -- a missing prerequisite fails, it never skips")


def _build(py, out, epoch="1790000000"):
    os.makedirs(out, exist_ok=True)
    # NB: setuptools.build_meta reads sys.argv, so paths travel via the environment
    env = dict(os.environ, SOURCE_DATE_EPOCH=epoch, PYTHONDONTWRITEBYTECODE="1", INV21_OUT=out)
    code = ("import os; from setuptools import build_meta as b; o=os.environ['INV21_OUT'];"
            "w=b.build_wheel(o); s=b.build_sdist(o); print('RESULT', w, s)")
    r = subprocess.run([py, "-c", code], env=env, capture_output=True, text=True, cwd=str(REPO))
    if r.returncode:
        raise AssertionError(r.stderr[-3000:])
    line = [l for l in r.stdout.splitlines() if l.startswith("RESULT ")][-1]
    return [pathlib.Path(out) / n for n in line.split()[1:]]


class PackagingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.py = _venv(os.path.join(cls.tmp.name, "venv"))
        cls.wheel, cls.sdist = _build(cls.py, os.path.join(cls.tmp.name, "d1"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
        for p in (REPO / "build", REPO / "inv21_local_service_chaining.egg-info"):
            subprocess.run(["rm", "-rf", str(p)])

    def test_metadata_version_single_source(self):
        v = (PKG / "VERSION").read_text().strip()
        self.assertIn(f"-{v}-", self.wheel.name)
        with zipfile.ZipFile(self.wheel) as z:
            meta = z.read(f"inv21_local_service_chaining-{v}.dist-info/METADATA").decode()
        self.assertIn(f"Version: {v}", meta)
        self.assertIn("Requires-Python: <3.14,>=3.10", meta)

    def test_content_policy(self):
        with zipfile.ZipFile(self.wheel) as z:
            names = z.namelist()
        self.assertTrue(any(n.endswith("schemas/residency.schema.json") for n in names))
        bad = [n for n in names if any(f in "/" + n for f in FORBIDDEN)]
        self.assertEqual(bad, [])
        with tarfile.open(self.sdist) as t:
            snames = t.getnames()
        self.assertFalse([n for n in snames if "__pycache__" in n or n.endswith(".pyc")])

    def test_reproducible_wheel(self):
        w2, _ = _build(self.py, os.path.join(self.tmp.name, "d2"))
        h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(h(self.wheel), h(w2))

    def test_clean_install_and_smoke_from_artifact(self):
        target = os.path.join(self.tmp.name, "site")
        r = subprocess.run([self.py, "-m", "pip", "install", "--no-index", "--no-deps", "--target", target,
                            str(self.wheel)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        smoke = (
            "import sys; sys.path[:]=[sys.argv[1]]+[p for p in sys.path if 'site-packages' not in p and p];"
            "import inv21_local_service_chaining as m, json;"
            "assert m.__file__.startswith(sys.argv[1]), m.__file__;"
            "from inv21_local_service_chaining.chain import Chainer;"
            "from inv21_local_service_chaining.residency import Residency;"
            "from inv21_local_service_chaining.schema import schema_names;"
            "r=Residency('h'); r.place('b','t',lambda *a:'ok');"
            "print(json.dumps([m.__version__, Chainer(r).call('b','t',1), len(schema_names()), m.PK_CORE_AVAILABLE]))")
        r = subprocess.run([self.py, "-I", "-c", smoke, target], capture_output=True, text=True, cwd="/")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"4.3.0", "ok", 9, false', r.stdout)


if __name__ == "__main__":
    unittest.main()
