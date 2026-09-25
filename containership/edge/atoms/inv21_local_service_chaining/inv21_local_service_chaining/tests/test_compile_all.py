"""Every module in the package (including tools/) compiles -- catches files no test imports."""
import compileall, pathlib, unittest

PKG = pathlib.Path(__file__).resolve().parents[1]


class CompileAllTest(unittest.TestCase):
    def test_compile(self):
        import py_compile
        bad = []
        for p in PKG.rglob("*.py"):
            try:
                compile(p.read_text(), str(p), "exec")
            except SyntaxError as e:
                bad.append(f"{p.name}:{e.lineno}")
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
