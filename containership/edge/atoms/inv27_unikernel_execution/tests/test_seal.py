"""MC-001..MC-006, MC-008, MC-010, MC-049: seal verification from immutable bytes (real ELF fixtures)."""
import copy
import json
import struct
import unittest

from harness import (NOW, ROGUE_SEED, UkError, admission, admit, elf, envelope, facts, image, manifest, policy,
                     ref, signing, statement, trust_root, isolation, SEED, KEYID)
import datetime as dt


class Positive(unittest.TestCase):
    def test_unikraft_convention_image_is_admitted_from_bytes(self):
        a = admit()
        self.assertTrue(a.seal["sealed"])
        self.assertEqual(a.seal["syscalls"], ("clock_gettime", "read", "write"))
        self.assertEqual(a.seal["facts_source"], "binary")
        self.assertEqual([s["step"] for s in a.decision["steps"]], [f"A{i}" for i in range(14)])
        with self.assertRaises(TypeError):
            a.seal["sealed"] = False

    def test_solo5_convention_image_is_admitted(self):
        a = admit("solo5_good.elf", toolchain="solo5")
        self.assertEqual(a.seal["toolchain"], "solo5")
        self.assertEqual(a.seal["syscalls"], ("solo5.clock_monotonic", "solo5.console_write"))

    def test_decision_records_observed_facts_and_versions(self):
        d = admit().decision
        a4 = next(s for s in d["steps"] if s["step"] == "A4")
        self.assertEqual(a4["parser"], elf.PARSER_VERSION)
        self.assertIsNotNone(a4["build_id"])
        self.assertEqual(d["verifier"], admission.VERIFIER_VERSION)


class CallerClaimsAreNotEvidence(unittest.TestCase):
    """MC-001/MC-002 definition of done: no caller-controlled claim becomes an observed fact."""

    def test_manifest_cannot_hide_a_linked_syscall(self):
        data = image("uk_socket.elf")
        with self.assertRaises(UkError) as c:
            admit(data=data, man=manifest(data), pol=policy(permitted_syscalls=frozenset({"read", "write", "clock_gettime", "socket"})))
        self.assertEqual(c.exception.code, "UK_SEAL_DRIFT")
        self.assertEqual(c.exception.details["only_in_binary"], ["socket"])

    def test_binary_syscall_outside_permitted_set(self):
        data = image("uk_socket.elf")
        with self.assertRaises(UkError) as c:
            admit(data=data, man=manifest(data, syscalls=["read", "write", "clock_gettime", "socket"]))
        self.assertEqual(c.exception.code, "UK_SEAL_SYSCALL_FORBIDDEN")

    def test_there_is_no_single_address_space_flag_to_set(self):
        m = manifest(image("uk_good.elf"))
        m["single_address_space"] = True
        with self.assertRaises(UkError) as c:
            admit(man=m)
        self.assertEqual(c.exception.code, "UK_MANIFEST_INVALID")


class SealBreakers(unittest.TestCase):
    CASES = [("uk_fork.elf", "UK_SEAL_MULTIPROCESS"), ("uk_exec.elf", "UK_SEAL_MULTIPROCESS"),
             ("uk_dlopen.elf", "UK_SEAL_DYNLOAD"), ("uk_ptrace.elf", "UK_SEAL_DEBUG_SURFACE"),
             ("dyn_fork_dlopen.elf", "UK_SEAL_DYNAMIC"), ("plain.elf", "UK_SEAL_UNKNOWN_TOOLCHAIN"),
             ("uk_stripped.elf", "UK_SEAL_NO_EVIDENCE"), ("uk_wx.elf", "UK_SEAL_WX"),
             ("uk_arch_aarch64.elf", "UK_SEAL_ARCH"),
             ("uk_hidden_notype.elf", "UK_SEAL_DRIFT")]   # review finding: NOTYPE handler must still count

    def test_every_counterexample_is_refused_with_its_reason(self):
        for name, code in self.CASES:
            data = image(name)
            with self.subTest(name=name), self.assertRaises(UkError) as c:
                syscalls = None
                if name in ("uk_fork.elf", "uk_exec.elf"):
                    syscalls = ["read", "write", "clock_gettime", name[3:7]]
                admit(data=data, man=manifest(data, syscalls=syscalls))
            self.assertEqual(c.exception.code, code, name)

    def test_notype_handler_is_in_the_derived_surface(self):
        f = facts.derive(elf.parse(image("uk_hidden_notype.elf")))
        self.assertIn("socket", f.syscalls)
        data = image("uk_hidden_notype.elf")
        with self.assertRaises(UkError) as c:
            admit(data=data, man=manifest(data, syscalls=["read", "write", "clock_gettime", "socket"]))
        self.assertEqual(c.exception.code, "UK_SEAL_SYSCALL_FORBIDDEN")

    def test_sas_proof_lists_failing_clause(self):
        e = elf.parse(image("uk_fork.elf"))
        proof = facts.derive(e).sas_proof
        self.assertFalse(proof["proven"])
        failing = [c["clause"] for c in proof["clauses"] if not c["holds"]]
        self.assertEqual(failing, ["no_process_creation"])

    def test_stripped_image_admitted_only_with_enabled_and_verified_attestation(self):
        data = image("uk_stripped.elf")
        att = {"toolchain": "unikraft", "syscalls": ["read", "write", "clock_gettime"], "single_address_space": True}
        env = envelope(data, attested_facts=att)
        with self.assertRaises(UkError) as c:
            admit(data=data, env=env)
        self.assertEqual(c.exception.code, "UK_SEAL_NO_EVIDENCE")          # mode disabled by default
        a = admit(data=data, env=env, pol=policy(allow_attested_facts=True))
        self.assertEqual(a.seal["facts_source"], "attestation")
        rogue = signing.sign_envelope(statement(data, attested_facts=att), ROGUE_SEED, KEYID)
        with self.assertRaises(UkError) as c:
            admit(data=data, env=rogue, pol=policy(allow_attested_facts=True))
        self.assertEqual(c.exception.code, "UK_SIG_INVALID")


class Identity(unittest.TestCase):
    def test_bound_digest_mismatch(self):
        with self.assertRaises(UkError) as c:
            admit(bound="sha256:" + "0" * 64)
        self.assertEqual(c.exception.code, "UK_DIGEST_MISMATCH")

    def test_one_flipped_byte_fails_before_parsing(self):
        data = bytearray(image("uk_good.elf"))
        good = bytes(data)
        data[-1] ^= 1
        with self.assertRaises(UkError) as c:
            admission.admit(bytes(data), bound_digest=ref(good), manifest=manifest(good), envelope=envelope(good),
                            policy=policy(), tenant="t1", now=NOW)
        self.assertEqual(c.exception.code, "UK_DIGEST_MISMATCH")
        self.assertNotIn("A4", [s["step"] for s in c.exception.details["decision"]["steps"]])

    def test_provenance_for_another_image_is_refused(self):
        other = image("solo5_good.elf")
        with self.assertRaises(UkError) as c:
            admit(env=envelope(other))
        self.assertEqual(c.exception.code, "UK_PROVENANCE_INVALID")

    def test_manifest_for_another_image_is_refused(self):
        with self.assertRaises(UkError) as c:
            admit(man=manifest(image("solo5_good.elf")))
        self.assertEqual(c.exception.code, "UK_MANIFEST_INVALID")


class Signatures(unittest.TestCase):
    def test_missing_envelope(self):
        with self.assertRaises(UkError) as c:
            admit(env=None)
        self.assertEqual(c.exception.code, "UK_SIG_MISSING")

    def test_untrusted_key(self):
        data = image("uk_good.elf")
        with self.assertRaises(UkError) as c:
            admit(env=envelope(data, seed=ROGUE_SEED, keyid="someone-else"))
        self.assertEqual(c.exception.code, "UK_SIG_UNTRUSTED_KEY")

    def test_revoked_and_expired_keys(self):
        for tr in (trust_root(revoked=True), trust_root(not_after="2026-06-01T00:00:00+00:00")):
            with self.subTest(), self.assertRaises(UkError) as c:
                admit(pol=policy(trust=tr))
            self.assertEqual(c.exception.code, "UK_SIG_UNTRUSTED_KEY")

    def test_stale_trust_root_fails_closed(self):
        tr = trust_root()
        tr.fetched_at = NOW - dt.timedelta(days=3)
        with self.assertRaises(UkError) as c:
            admit(pol=policy(trust=tr))
        self.assertEqual(c.exception.code, "UK_TRUST_UNAVAILABLE")

    def test_tampered_payload_and_malleable_base64(self):
        data = image("uk_good.elf")
        env = envelope(data)
        body = json.loads(signing.base64.b64decode(env["payload"]))
        body["builder"] = "evil"
        bad = dict(env, payload=signing.base64.b64encode(signing.canonical(body)).decode())
        with self.assertRaises(UkError) as c:
            admit(env=bad)
        self.assertEqual(c.exception.code, "UK_SIG_INVALID")
        mall = copy.deepcopy(env)
        mall["signatures"][0]["sig"] = mall["signatures"][0]["sig"].rstrip("=") + "\n"
        with self.assertRaises(UkError) as c:
            admit(env=mall)
        self.assertEqual(c.exception.code, "UK_SIG_INVALID")

    def test_unapproved_builder_and_toolchain_version(self):
        data = image("uk_good.elf")
        for kw in ({"builder": "rogue"}, {"toolchain_version": "0.1.0"}, {"source": {"uri": "x"}}):
            with self.subTest(kw=kw), self.assertRaises(UkError) as c:
                admit(env=envelope(data, **kw))
            self.assertEqual(c.exception.code, "UK_PROVENANCE_POLICY")

    def test_rfc8032_vector_1(self):
        from harness import ed25519
        seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        sig = ed25519.sign(seed, b"")
        self.assertEqual(ed25519.public_key(seed).hex(),
                         "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        self.assertTrue(sig.hex().startswith("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e0652249015"))

    def test_cryptography_backend_agrees_when_installed(self):
        try:
            name = signing.set_backend("cryptography")
        except ImportError:
            self.skipTest("cryptography not installed")  # declared optional lane
        try:
            self.assertEqual(name, "cryptography")
            self.assertTrue(admit().seal["sealed"])
        finally:
            signing.set_backend("pure")


class Manifest(unittest.TestCase):
    def test_strictness(self):
        data = image("uk_good.elf")
        m = manifest(data)
        bad = []
        for mut in (lambda x: x.update(schema="PK_UNIKERNEL_SEAL_MANIFEST/2"),
                    lambda x: x["boot"].update(memory_mib=True),
                    lambda x: x["boot"].update(cmdline="a;rm -rf /"),
                    lambda x: x.update(syscalls=["read", "read"]),
                    lambda x: x["isolation"].update(devices=["vfio-pci"]),
                    lambda x: x["isolation"].update(storage=[{"digest": "sha256:" + "a" * 64, "read_only": False}]),
                    lambda x: x["isolation"].update(network="tap")):
            mm = copy.deepcopy(m)
            mut(mm)
            with self.assertRaises(UkError) as c:
                admit(data=data, man=mm)
            bad.append(c.exception.code)
        self.assertEqual(bad[0], "UK_UNSUPPORTED_VERSION")
        self.assertTrue(all(b == "UK_MANIFEST_INVALID" for b in bad[1:]), bad)

    def test_duplicate_json_keys_rejected(self):
        from harness import inv27
        import importlib
        mf = importlib.import_module(inv27.__name__ + ".manifest")
        txt = json.dumps(manifest(image("uk_good.elf")))
        txt = txt.replace('"toolchain": "unikraft"', '"toolchain": "unikraft", "toolchain": "solo5"')
        with self.assertRaises(UkError):
            mf.loads(txt)

    def test_json_schema_file_matches_parser_field_sets(self):
        import pathlib
        from harness import PKG
        schema = json.loads((PKG / "schemas" / "PK_UNIKERNEL_SEAL_MANIFEST-1.schema.json").read_text())
        self.assertEqual(set(schema["required"]), {"schema", "image", "toolchain", "architecture", "syscalls", "boot", "isolation"})
        self.assertFalse(schema["additionalProperties"])


class BootContract(unittest.TestCase):
    def test_entry_symbol_must_be_the_elf_entry(self):
        data = image("uk_good.elf")
        m = manifest(data)
        m["boot"]["entry_symbol"] = "ukplat_entry"
        self.assertIn("B3", admit(data=data, man=m).decision["steps"][12]["clauses"])
        m["boot"]["entry_symbol"] = "uk_syscall_r_read"
        with self.assertRaises(UkError) as c:
            admit(data=data, man=m)
        self.assertEqual(c.exception.code, "UK_BOOT_CONTRACT")

    def test_memory_budget(self):
        data = image("uk_good.elf")
        m = manifest(data)
        m["boot"]["memory_mib"] = 8
        admit(data=data, man=m)
        with self.assertRaises(UkError):
            m2 = copy.deepcopy(m)
            m2["boot"]["memory_mib"] = 4   # below the manifest schema floor
            admit(data=data, man=m2)

    def test_entry_outside_executable_segment(self):
        data = bytearray(image("uk_good.elf"))
        data[24:32] = struct.pack("<Q", 0x400000)   # entry -> first (read-only) PT_LOAD
        data = bytes(data)
        with self.assertRaises(UkError) as c:
            admit(data=data)
        self.assertIn(c.exception.code, ("UK_BOOT_CONTRACT", "UK_SEAL_NOT_SAS"))


class Isolation(unittest.TestCase):
    def test_network_device_storage_policy(self):
        data = image("uk_good.elf")
        cases = [({"network": "tap", "network_bridge": "br-t2", "devices": ["serial", "virtio-net"], "storage": []}, "t1"),
                 ({"network": "tap", "network_bridge": "br-t1", "devices": ["serial", "virtio-net"], "storage": []}, "t2"),
                 ({"network": "none", "devices": ["serial", "virtio-blk"], "storage": []}, "t1"),
                 ({"network": "none", "devices": ["serial", "virtio-net"], "storage": []}, "t1"),
                 ({"network": "none", "devices": ["serial", "virtio-blk"],
                   "storage": [{"digest": "sha256:" + "c" * 64, "read_only": True}]}, "t1")]
        for iso, tenant in cases:
            m = manifest(data, isolation=iso)
            with self.subTest(iso=iso, tenant=tenant), self.assertRaises(UkError) as c:
                admit(data=data, man=m, tenant=tenant)
            self.assertEqual(c.exception.code, "UK_ISOLATION_POLICY")
        ok = admit(data=data, man=manifest(data, isolation={"network": "tap", "network_bridge": "br-t1",
                                                            "devices": ["serial", "virtio-net"], "storage": []}))
        self.assertEqual(ok.plan.bridge, "br-t1")


class Legacy(unittest.TestCase):
    def test_legacy_verify_seal_is_retained_but_not_used_by_admission(self):
        import inspect
        src = inspect.getsource(admission)
        self.assertNotIn("verify_seal", src)
        self.assertNotIn("linked_syscalls", src)


if __name__ == "__main__":
    unittest.main()
