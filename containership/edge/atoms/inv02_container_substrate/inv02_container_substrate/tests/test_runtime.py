"""MC05-MC12 / MC22-MC28 / MC33 — runtime spec, cgroups, lifecycle, supervision."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from inv02_container_substrate import runtime as rt
from inv02_container_substrate.registry import ValidationError


class SpecTests(unittest.TestCase):
    def spec(self, **kw):
        return rt.build_spec(rt.ContainerConfig(args=["/bin/app"], **kw))

    def test_secure_defaults(self):
        s = self.spec()
        p, l = s["process"], s["linux"]
        self.assertTrue(p["noNewPrivileges"])
        self.assertEqual(p["capabilities"]["bounding"], [])
        self.assertEqual(p["user"], {"uid": 65534, "gid": 65534})
        self.assertTrue(s["root"]["readonly"])
        self.assertEqual(l["seccomp"]["defaultAction"], "SCMP_ACT_ERRNO")
        allowed = set(l["seccomp"]["syscalls"][0]["names"])
        self.assertFalse(allowed & rt.SECCOMP_DENY_ALWAYS)
        self.assertNotIn("clone3", allowed)
        types = {n["type"] for n in l["namespaces"]}
        self.assertEqual(types, {"pid", "ipc", "uts", "mount", "cgroup", "network", "user"})
        self.assertTrue(l["uidMappings"])
        self.assertIn("/proc/kcore", l["maskedPaths"])
        self.assertEqual(l["resources"]["devices"][0], {"allow": False, "access": "rwm"})
        self.assertEqual(p["apparmorProfile"], "inv02-default")
        json.dumps(s)  # serialisable

    def test_grants_required(self):
        for kw in ({"privileged": True}, {"cap_add": ["SYS_ADMIN"]}, {"network": "host"},
                   {"devices": ["/dev/null"]}, {"network": "netns:/tmp/x"}, {"env": {"DB_PASSWORD": "x"}},
                   {"runtime_class": "nope"}, {"cap_add": ["bad cap"]}):
            with self.subTest(kw), self.assertRaises(ValidationError):
                self.spec(**kw)
        s = rt.build_spec(rt.ContainerConfig(args=["x"], cap_add=["SYS_ADMIN"]), granted=frozenset({"cap:SYS_ADMIN"}))
        self.assertIn("CAP_SYS_ADMIN", s["process"]["capabilities"]["effective"])
        s = rt.build_spec(rt.ContainerConfig(args=["x"], devices=["/dev/null"]), granted=frozenset({"device:/dev/null"}))
        self.assertEqual(s["linux"]["devices"][0]["major"], 1)

    def test_seccomp_cannot_allow_escape_syscalls(self):
        with self.assertRaises(ValidationError):
            rt.seccomp_profile(["mount"])
        clone = [r for r in rt.seccomp_profile()["syscalls"] if r["names"] == ["clone"]][0]
        self.assertEqual(clone["args"][0]["op"], "SCMP_CMP_MASKED_EQ")

    def test_capability_baselines(self):
        self.assertEqual(rt.capability_set(), [])
        self.assertIn("CAP_CHOWN", rt.capability_set(baseline="default"))
        self.assertNotIn("CAP_CHOWN", rt.capability_set(drop=["chown"], baseline="default"))
        self.assertEqual(rt.capability_set(add=["NET_BIND_SERVICE"]), ["CAP_NET_BIND_SERVICE"])

    def test_secrets_are_mounted_not_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            sd = os.path.join(tmp, "sec")
            cfg = rt.ContainerConfig(args=["x"], secrets={"db-pass": b"s3cr3t"})
            s = rt.build_spec(cfg, secrets_dir=sd)
            rt.write_secrets(sd, cfg.secrets)
            self.assertNotIn("s3cr3t", json.dumps(s))
            m = [m for m in s["mounts"] if m["destination"] == "/run/secrets"][0]
            self.assertIn("ro", m["options"])
            self.assertEqual(os.stat(os.path.join(sd, "db-pass")).st_mode & 0o777, 0o400)
            with self.assertRaises(ValidationError):
                rt.build_spec(cfg)

    def test_volumes_binds_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = rt.ContainerConfig(args=["x"], volumes=[{"name": "data", "destination": "/data"}],
                                     binds=[{"source": tmp, "destination": "/in"}],
                                     resources=rt.Resources(memory_max=64 << 20, cpu_quota_us=50000, pids_max=100))
            s = rt.build_spec(cfg, volume_root="/var/lib/inv02/volumes", bind_prefixes=(tmp,))
            dests = {m["destination"] for m in s["mounts"]}
            self.assertTrue({"/data", "/in"} <= dests)
            r = s["linux"]["resources"]
            self.assertEqual(r["memory"]["limit"], 64 << 20)
            self.assertEqual(r["pids"]["limit"], 100)
        with self.assertRaises(ValidationError):
            rt.Resources(memory_max=1024).to_oci()

    def test_rootless_subuid(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as fh:
            fh.write("alice:100000:65536\nbob:200000:1000\n")
        try:
            self.assertEqual(rt.subid_range("alice", fh.name), rt.IDMap(0, 100000, 65536))
            for u in ("bob", "carol"):
                with self.assertRaises(ValidationError):
                    rt.subid_range(u, fh.name)
        finally:
            os.unlink(fh.name)

    def test_sandboxed_runtime_classes(self):
        self.assertEqual(rt.RUNTIME_CLASSES["gvisor"], "runsc")
        self.assertIn("kata", rt.SANDBOXED_CLASSES)
        self.assertEqual(self.spec(runtime_class="gvisor")["ociVersion"], rt.OCI_RUNTIME_SPEC_VERSION)


class CgroupTests(unittest.TestCase):
    def test_fake_cgroupfs(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "cgroup.controllers").write_text("cpu memory pids io")
            (Path(tmp) / "inv02.slice").mkdir()
            Path(tmp, "inv02.slice", "cgroup.subtree_control").write_text("")
            m = rt.CgroupV2Manager(tmp)
            cg = m.create("c1", rt.Resources(memory_max=128 << 20, cpu_quota_us=20000, pids_max=64))
            self.assertEqual((cg / "memory.max").read_text(), str(128 << 20))
            self.assertEqual((cg / "cpu.max").read_text(), "20000 100000")
            self.assertEqual((cg / "memory.swap.max").read_text(), "0")
            self.assertIn("+memory", Path(tmp, "inv02.slice", "cgroup.subtree_control").read_text())
            (cg / "memory.current").write_text("4096")
            self.assertEqual(m.stats("c1")["memory.current"], 4096)
            with self.assertRaises(ValidationError):
                m.create("../escape", rt.Resources())
            m.destroy("c1")
            self.assertFalse(cg.exists())


class LifecycleTests(unittest.TestCase):
    def test_state_machine(self):
        with tempfile.TemporaryDirectory() as tmp:
            ls = rt.LifecycleStore(tmp)
            ls.create("c1", "sha256:" + "a" * 64, "sha256:" + "b" * 64)
            with self.assertRaises(rt.IllegalTransition):
                ls.transition("c1", rt.State.PAUSED, "x")
            r = ls.transition("c1", rt.State.RUNNING, "start")
            with self.assertRaises(rt.IllegalTransition):
                ls.transition("c1", rt.State.STOPPED, "stop", expected_generation=r["generation"] - 1)
            ls.transition("c1", rt.State.STOPPED, "stop", expected_generation=r["generation"])
            ls.transition("c1", rt.State.DELETED, "rm")
            with self.assertRaises(rt.IllegalTransition):
                ls.transition("c1", rt.State.RUNNING, "zombie")
            self.assertEqual(rt.LifecycleStore(tmp).get("c1")["state"], "deleted")  # durable
            with self.assertRaises(ValidationError):
                ls.create("c1", "x", "y")
            with self.assertRaises(ValidationError):
                ls.get("../etc")


class SupervisorTests(unittest.TestCase):
    def test_restart_on_failure_with_limit(self):
        ev = []
        s = rt.Supervisor([sys.executable, "-c", "raise SystemExit(3)"],
                          rt.SupervisorPolicy(max_restarts=2, backoff_base_s=0.01), on_event=lambda e, f: ev.append(e))
        s.start()
        self.assertTrue(s.wait_done(10))
        self.assertEqual(s.exits, [3, 3, 3])
        self.assertIn("process.gave_up", ev)

    def test_success_not_restarted_and_graceful_stop(self):
        s = rt.Supervisor([sys.executable, "-c", "pass"])
        s.start()
        self.assertTrue(s.wait_done(10))
        self.assertEqual(s.exits, [0])
        s2 = rt.Supervisor([sys.executable, "-c", "import time; time.sleep(30)"], rt.SupervisorPolicy(stop_grace_s=2))
        s2.start()
        time.sleep(0.3)
        t0 = time.time()
        rc = s2.stop()
        self.assertLess(time.time() - t0, 5)
        self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
