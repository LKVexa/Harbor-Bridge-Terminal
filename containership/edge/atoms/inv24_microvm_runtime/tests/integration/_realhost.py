"""Real-host integration gating.  These tests run ONLY on an approved KVM host with
pinned artifacts:  INV24_REAL_HOST=1 INV24_FIRECRACKER=/abs/firecracker
INV24_KERNEL=/abs/vmlinux INV24_ROOTFS=/abs/rootfs.ext4 INV24_MANIFEST=/abs/manifest.json
A skip here is recorded by tools/run_evidence.py as NOT_TESTED — never PASS."""
import os
import unittest

REAL = os.environ.get("INV24_REAL_HOST") == "1" and os.path.exists("/dev/kvm")
need_real_host = unittest.skipUnless(REAL, "NOT_TESTED: requires approved KVM host (INV24_REAL_HOST=1 and /dev/kvm)")


def env(name):
    v = os.environ.get(name)
    if not v:
        raise unittest.SkipTest(f"NOT_TESTED: {name} not set")
    return v


def adapter(**kw):
    from inv24_microvm_runtime.adapters.firecracker import FirecrackerAdapter
    from inv24_microvm_runtime.security.artifacts import ArtifactManifest
    return FirecrackerAdapter(ArtifactManifest.load(env("INV24_MANIFEST")), firecracker_path=env("INV24_FIRECRACKER"),
                              kernel_path=env("INV24_KERNEL"), rootfs_path=env("INV24_ROOTFS"),
                              run_dir=os.environ.get("INV24_RUN_DIR", "/tmp"), **kw)
