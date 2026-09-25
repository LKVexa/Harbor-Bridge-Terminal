"""Items 1, 5-15, 11, 32: every 4.3.0 control has a passing and a failing case."""
import unittest

from hkit import PROFILE_DIGEST, build, hardened_pod, request

from inv03_container_hardening.hardening import controls as C
from inv03_container_hardening.hardening.baseline import default_document


def ctx(**kw):
    d = dict(default_document()["settings"], namespace_default_deny=True)
    d.update(kw)
    return d


def app(pod):
    return pod["containers"][0]


class ControlCases(unittest.TestCase):
    def test_hardened_pod_passes_every_control(self):
        pod = hardened_pod()
        for name, fn in C.CONTROLS_43.items():
            self.assertEqual(fn(pod, ctx()), [], name)

    def violates(self, name, mutate, **kw):
        pod = hardened_pod()
        mutate(pod)
        self.assertTrue(C.CONTROLS_43[name](pod, ctx(**kw)), f"{name} did not fire")

    def test_item01_sandbox_runtime(self):
        self.violates("sandbox-runtime", lambda p: p.pop("runtimeClassName"))
        self.violates("sandbox-runtime", lambda p: p.update(runtimeClassName="runc"))

    def test_item11_uid_resolution(self):
        self.violates("non-root", lambda p: p["securityContext"].update(runAsUser=0))
        self.violates("non-root", lambda p: p["securityContext"].update(runAsUser="appuser"))
        self.violates("non-root", lambda p: p["securityContext"].update(runAsUser=True))
        self.violates("non-root", lambda p: p["securityContext"].update(runAsGroup=0))
        pod = hardened_pod()
        pod["securityContext"]["runAsUser"] = "appuser"
        self.assertEqual(C.non_root(pod, ctx(resolved_uids={"containers/app": 1000})), [])
        self.assertTrue(C.non_root(pod, ctx(resolved_uids={"containers/app": 0})))

    def test_container_context_overrides_pod_context(self):
        self.violates("non-root", lambda p: app(p)["securityContext"].update(runAsUser=0))

    def test_legacy_controls_per_container(self):
        self.violates("read-only-root", lambda p: app(p)["securityContext"].pop("readOnlyRootFilesystem"))
        self.violates("not-privileged", lambda p: app(p)["securityContext"].pop("privileged"))
        self.violates("drop-all-capabilities", lambda p: app(p)["securityContext"]["capabilities"].update(add=["NET_RAW"]))
        self.violates("seccomp", lambda p: p["securityContext"].update(seccompProfile={"type": "Unconfined"}))

    def test_items_apply_to_init_and_ephemeral_containers(self):
        def add_init(p):
            p["initContainers"] = [{"name": "init", "securityContext": {"privileged": True}}]
        self.violates("not-privileged", add_init)
        def add_eph(p):
            p["ephemeralContainers"] = [{"name": "dbg", "securityContext": {"privileged": False}}]
        self.violates("no-privilege-escalation", add_eph)

    def test_item32_localhost_seccomp_needs_registered_profile(self):
        self.violates("seccomp", lambda p: p["securityContext"].update(
            seccompProfile={"type": "Localhost", "localhostProfile": "profiles/x.json"}))
        pod = hardened_pod()
        pod["securityContext"]["seccompProfile"] = {"type": "Localhost", "localhostProfile": "profiles/x.json"}
        self.assertEqual(C.seccomp(pod, ctx(seccomp_profiles={"profiles/x.json": PROFILE_DIGEST})), [])

    def test_item05_no_privilege_escalation(self):
        self.violates("no-privilege-escalation", lambda p: app(p)["securityContext"].pop("allowPrivilegeEscalation"))

    def test_item06_host_namespaces(self):
        for k in ("hostPID", "hostIPC", "hostNetwork"):
            self.violates("host-namespaces", lambda p, k=k: p.update({k: True}))
        self.violates("host-namespaces", lambda p: p.update(shareProcessNamespace=True))

    def test_item12_user_namespace(self):
        self.violates("user-namespace", lambda p: p.pop("hostUsers"))
        pod = hardened_pod()
        pod.pop("hostUsers")
        self.assertEqual(C.user_namespace(pod, ctx(require_user_namespace=False)), [])

    def test_item07_host_devices(self):
        self.violates("host-devices", lambda p: app(p).update(volumeDevices=[{"name": "d", "devicePath": "/dev/sda"}]))
        self.violates("host-devices", lambda p: app(p)["resources"]["limits"].update({"nvidia.com/gpu": 1}))
        pod = hardened_pod()
        app(pod)["resources"]["limits"]["nvidia.com/gpu"] = 1
        self.assertEqual(C.host_devices(pod, ctx(device_allowlist=["nvidia.com/gpu"])), [])

    def test_item08_host_mounts(self):
        for path in ("/var/run/docker.sock", "/", "/etc", "/proc/1", "/run/containerd/containerd.sock",
                     "/opt/../etc", "/data"):
            self.violates("host-mounts", lambda p, path=path: p["volumes"].append(
                {"name": "h", "hostPath": {"path": path}}))
        self.violates("host-mounts", lambda p: app(p)["volumeMounts"][0].update(mountPropagation="Bidirectional"))
        pod = hardened_pod()
        pod["volumes"].append({"name": "h", "hostPath": {"path": "/opt/ca"}})
        app(pod)["volumeMounts"].append({"name": "h", "mountPath": "/ca", "readOnly": True})
        self.assertEqual(C.host_mounts(pod, ctx(hostpath_readonly_allowlist=["/opt/ca"])), [])
        app(pod)["volumeMounts"][-1]["readOnly"] = False
        self.assertTrue(C.host_mounts(pod, ctx(hostpath_readonly_allowlist=["/opt/ca"])))
        # an allowlist entry can never admit a runtime socket, wherever it lives
        pod = hardened_pod()
        pod["volumes"].append({"name": "s", "hostPath": {"path": "/srv/run/containerd.sock"}})
        app(pod)["volumeMounts"].append({"name": "s", "mountPath": "/s", "readOnly": True})
        self.assertTrue(C.host_mounts(pod, ctx(hostpath_readonly_allowlist=["/srv/run/containerd.sock"])))

    def test_item09_kernel_surface(self):
        self.violates("kernel-surface", lambda p: p["securityContext"].update(sysctls=[{"name": "kernel.msgmax", "value": "1"}]))
        self.violates("kernel-surface", lambda p: app(p)["securityContext"].update(procMount="Unmasked"))
        pod = hardened_pod()
        pod["securityContext"]["sysctls"] = [{"name": "net.ipv4.tcp_syncookies", "value": "1"}]
        self.assertEqual(C.kernel_surface(pod, ctx()), [])

    def test_item10_mac_profile(self):
        self.violates("mac-profile", lambda p: p["securityContext"].pop("appArmorProfile"))
        self.violates("mac-profile", lambda p: p["securityContext"].update(appArmorProfile={"type": "Unconfined"}))
        self.violates("mac-profile", lambda p: p["securityContext"].update(
            appArmorProfile={"type": "Localhost", "localhostProfile": "unknown"}))
        pod = hardened_pod()
        pod["securityContext"].pop("appArmorProfile")
        pod["securityContext"]["seLinuxOptions"] = {"type": "container_t"}
        self.assertEqual(C.mac_profile(pod, ctx()), [])
        pod["securityContext"]["seLinuxOptions"] = {"type": "spc_t"}
        self.assertTrue(C.mac_profile(pod, ctx()))

    def test_item13_writable_volumes(self):
        self.violates("writable-volumes", lambda p: p["volumes"][0]["emptyDir"].pop("sizeLimit"))
        self.violates("writable-volumes", lambda p: p["volumes"][0]["emptyDir"].update(sizeLimit="10Gi"))
        self.violates("writable-volumes", lambda p: p["volumes"].append({"name": "n", "nfs": {"server": "x"}}))

    def test_item14_resources(self):
        for r in ("cpu", "memory", "ephemeral-storage"):
            self.violates("resources", lambda p, r=r: app(p)["resources"]["limits"].pop(r))
        self.violates("resources", lambda p: app(p)["resources"]["limits"].update(memory="-1Mi"))
        self.violates("resources", lambda p: None, require_pid_limit=True)

    def test_item15_network_isolation(self):
        pod = hardened_pod()
        self.assertTrue(C.network_isolation(pod, ctx(namespace_default_deny=False)))
        self.assertTrue(C.network_isolation(pod, ctx(namespace_default_deny="true")))

    def test_quantity_parser_rejects_hostile_values(self):
        for q in (None, True, "", "abc", "1e999", "nan", "-5", "0", "9" * 40, [], {}):
            self.assertIsNone(C.parse_quantity(q), q)
        self.assertEqual(C.parse_quantity("64Mi"), 64 * 2**20)
        self.assertEqual(C.parse_quantity("500m"), 0.5)

    def test_engine_names_every_failed_control(self):
        eng, *_ = build()
        pod = hardened_pod()
        pod["hostPID"] = True
        app(pod)["securityContext"]["privileged"] = True
        d = eng.decide(request(pod))
        self.assertFalse(d["admit"])
        self.assertEqual(d["failed"], ["not-privileged", "host-namespaces"])
        self.assertIn("host-namespaces", d["explain"]["findings"])


if __name__ == "__main__":
    unittest.main()
