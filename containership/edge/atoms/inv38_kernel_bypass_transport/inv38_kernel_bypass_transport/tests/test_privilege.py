from inv38_kernel_bypass_transport import privilege_check as pc
def _auth(**kw):
    base = dict(caps=frozenset({"CAP_IPC_LOCK"}), writable_paths=frozenset({"/var/lib/inv38/state"}),
                open_device_nodes=frozenset({"/dev/infiniband/uverbs0"}))
    base.update(kw); return pc.RuntimeAuthority(**base)
DEV = frozenset({"/dev/infiniband/uverbs0"})
def test_minimal_privilege_passes():
    assert pc.check(_auth(), assigned_devices=DEV) == []
def test_forbidden_capability_flagged():
    v = pc.check(_auth(caps=frozenset({"CAP_SYS_ADMIN"})), assigned_devices=DEV)
    assert any("forbidden" in x for x in v)
def test_stray_device_flagged():
    v = pc.check(_auth(open_device_nodes=frozenset({"/dev/mem"})), assigned_devices=DEV)
    assert any("device nodes" in x for x in v)
def test_env_secret_and_inherited_fd_flagged():
    v = pc.check(_auth(env_secrets=frozenset({"AWS_SECRET"}), inherited_fds=frozenset({7})), assigned_devices=DEV)
    assert pc.fails_closed(_auth(env_secrets=frozenset({"X"})), assigned_devices=DEV)
    assert len(v) >= 2
