"""Conformance fixtures, bootstrap, and the declared hardware lane."""
from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout

from _support import PKG_DIR, keys, tok
from fvt import config, schema
from fvt.provider import HostProbe, QemuKvmProvider
from fvt.service import FullVmService

EX = PKG_DIR / "docs/examples"
KVM_READY = HostProbe().probe().usable and shutil.which("qemu-system-x86_64") is not None


class FixtureTest(unittest.TestCase):
    def test_reference_examples_conform(self):
        schema.parse_and_validate((EX / "create_request.json").read_bytes(), "PK_FULL_VM_CREATE_REQUEST.v1")
        config.validate(config.layer(json.loads((EX / "config.staging.json").read_text())))


class BootstrapTest(unittest.TestCase):
    def test_bootstrap_ready_on_fake_lane_and_refuses_on_this_host_without_kvm(self):
        import sys
        sys.path.insert(0, str(PKG_DIR / "tools"))
        import bootstrap
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            self.assertEqual(bootstrap.main(["--state-dir", d, "--fake-provider", "--site", "dc1"]), 0)
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()) as out:
            rc = bootstrap.main(["--state-dir", d])
        self.assertEqual(rc, 0 if KVM_READY else 3)
        self.assertEqual(json.loads(out.getvalue())["primitive"]["usable"], HostProbe().probe().usable)


@unittest.skipUnless(KVM_READY, "LANE:kvm - requires /dev/kvm and qemu-system-x86_64")
class KvmLaneTest(unittest.TestCase):
    """Hardware-backed lane. Boots a diskless q35 guest paused->running over QMP."""

    def test_boot_stop_destroy_on_kvm(self):
        kp = keys()
        with tempfile.TemporaryDirectory() as d:
            svc = FullVmService(provider=QemuKvmProvider(), keys=kp, state_dir=d)
            iid = svc.create(tok(kp), {"schema": "PK_FULL_VM/1", "name": "kvm1", "tenant": "t1", "memory_mib": 256,
                                       "image_digest": "sha256:" + "a" * 64, "idempotency_key": "k"})["instance_id"]
            b = svc.boot(tok(kp), iid)
            self.assertGreater(b["resident_mib"], 0)
            svc.destroy(tok(kp), iid)
            self.assertEqual(svc.handles, {})


if __name__ == "__main__":
    unittest.main()
