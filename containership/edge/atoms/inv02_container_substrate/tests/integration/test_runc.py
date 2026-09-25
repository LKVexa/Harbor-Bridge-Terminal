"""MC59 / MC60 / MC62 — real OCI runtime integration and isolation tests.

Runs a statically linked probe (``probe.c``) inside a container created by ``runc`` from
a spec produced by :func:`runtime.build_spec`, then asserts isolation properties from
inside the container.  Requires root, ``runc`` and ``gcc``; skips with an explicit
reason otherwise (a skip is *not* a pass — see RELEASE_EVIDENCE).
"""
import json
import os
import resource
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from inv02_container_substrate import runtime as rt

HERE = Path(__file__).parent
REASON = None
if os.environ.get("INV02_SKIP_INTEGRATION"):
    REASON = "INV02_SKIP_INTEGRATION set"
elif os.geteuid() != 0:
    REASON = "requires root"
elif not shutil.which("runc"):
    REASON = "runc not installed"
elif not shutil.which("gcc"):
    REASON = "gcc not installed (needed to build static probe)"


def _probe(tmp: str) -> str:
    out = os.path.join(tmp, "probe")
    subprocess.run(["gcc", "-static", "-O2", "-o", out, str(HERE / "probe.c")], check=True, capture_output=True)
    return out


@unittest.skipIf(REASON, REASON or "")
class RuncIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        try:
            cls.probe = _probe(cls.tmp)
        except subprocess.CalledProcessError as exc:
            raise unittest.SkipTest(f"cannot build static probe: {exc.stderr[-200:]!r}")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_probe(self, name: str, **cfg_kw) -> dict:
        bundle = Path(self.tmp) / name
        rootfs = bundle / "rootfs"
        for sub in ("etc", "mnt", "proc", "dev", "sys", "run/secrets"):
            (rootfs / sub).mkdir(parents=True, exist_ok=True)
        shutil.copy(self.probe, rootfs / "probe")
        secrets_dir = str(bundle / "secrets")
        cfg = rt.ContainerConfig(args=["/probe"], user=(0, 0), apparmor_profile=None,
                                 nofile=resource.getrlimit(resource.RLIMIT_NOFILE)[1], **cfg_kw)
        if cfg.secrets:
            rt.write_secrets(secrets_dir, cfg.secrets)
        (bundle / "config.json").write_text(json.dumps(rt.build_spec(cfg, secrets_dir=secrets_dir)))
        r = rt.OCIRuntime("runc", state_root=str(bundle / "state")).run(name, str(bundle))
        if r.returncode != 0 and "permission denied" in r.stderr and cfg.rootless:
            self.skipTest(f"host forbids user-namespace containers: {r.stderr.strip()[-160:]}")
        self.assertEqual(r.returncode, 0, r.stderr)
        return dict(line.split("=", 1) for line in r.stdout.split() if "=" in line) | {"_raw": r.stdout}

    def test_isolation_properties(self):
        out = self.run_probe("iso", rootless=False, secrets={"db-pass": b"s3cr3t"},
                             resources=rt.Resources(memory_max=64 << 20, pids_max=32))
        self.assertEqual(out["pid"], "1", "container must have its own PID namespace")
        self.assertEqual(out["mount"], "-1", "mount(2) must be denied (no CAP_SYS_ADMIN, seccomp)")
        self.assertEqual(out["unshare"], "-1", "creating new user namespaces must be denied")
        self.assertEqual(out["rootfs_write"], "no", "rootfs must be read-only")
        self.assertEqual(out["secret"], "s3cr3t", "secret must be delivered as a mounted file")

    def test_rootless_user_namespace(self):
        out = self.run_probe("userns", rootless=True)
        self.assertEqual(out["pid"], "1")
        self.assertEqual(out["mount"], "-1")


if __name__ == "__main__":
    unittest.main()
