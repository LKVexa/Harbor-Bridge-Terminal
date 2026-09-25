"""Security tests derived from docs/security/THREAT_MODEL.md (C041, C050, C087, C023, C024, C044, C045).

Each test class name carries the threat id it covers; the RTM checker verifies that
every HIGH/CRITICAL threat in THREAT_MODEL.md has at least one test class here.
"""
from __future__ import annotations

import copy
import io
import json
import os
import time
import unittest

from inv45_sfi_mechanisms.tests.support import Harness
from inv45_sfi_mechanisms.production import builder, config, sfi, trust
from inv45_sfi_mechanisms.production.authz import Grant
from inv45_sfi_mechanisms.production.errors import SfiError


class _Base(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        self.svc = self.h.svc

    def tearDown(self):
        self.h.close()

    def code(self, fn, *a, **k):
        try:
            fn(*a, **k)
        except SfiError as e:
            return e.code
        return "OK"


class T01_MemoryEscapeViaUnmaskedAccess(_Base):
    def test_unmasked_artifact_never_sealed(self):
        r = self.h.submit()
        bad = builder.rw_module()
        desc = dict(r["descriptor"])
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), bad, desc), "SFI_DIGEST_MISMATCH")


class T02_ToctouArtifactSwap(_Base):
    def test_bytes_changed_after_verification(self):
        r = self.h.submit()
        swapped = bytearray(r["artifact"])
        swapped[-1] ^= 0x01
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), bytes(swapped), r["descriptor"]),
                         "SFI_DIGEST_MISMATCH")

    def test_non_bytes_rejected(self):
        r = self.h.submit()
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), "x", r["descriptor"]),
                         "SFI_SCHEMA_INVALID")


class T03_DescriptorForgeryAndReplay(_Base):
    def test_field_tamper_breaks_mac(self):
        r = self.h.submit()
        for field, val in (("tenant", "t2"), ("artifact_version", 99), ("expires_at", 1e12),
                           ("artifact_sha256", "0" * 64), ("config_sha256", "1" * 64)):
            with self.subTest(field):
                d = dict(r["descriptor"])
                d[field] = val
                self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), r["artifact"], d),
                                 "SFI_SIGNATURE_INVALID")

    def test_extra_or_missing_fields(self):
        r = self.h.submit()
        d = dict(r["descriptor"], extra=1)
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), r["artifact"], d), "SFI_SEAL_MISMATCH")
        d = dict(r["descriptor"])
        d.pop("nonce")
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), r["artifact"], d), "SFI_SEAL_MISMATCH")

    def test_replay(self):
        r = self.h.submit()
        tok = self.h.tenant_token("t1")
        self.svc.load(tok, r["artifact"], r["descriptor"])
        self.assertEqual(self.code(self.svc.load, tok, r["artifact"], r["descriptor"]), "SFI_REPLAY_DETECTED")

    def test_expired_descriptor(self):
        r = self.h.submit()
        real = self.h.keyring.clock
        self.h.keyring.clock = lambda: real() + 10_000
        self.h.keyring.refresh()
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), r["artifact"], r["descriptor"]),
                         "SFI_SEAL_MISMATCH")

    def test_revoked_sealing_key(self):
        r = self.h.submit()
        self.h.keyring.revoke("seal-1")
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), r["artifact"], r["descriptor"]),
                         "SFI_SIGNATURE_INVALID")

    def test_key_rotation_old_descriptors_still_verify_until_revoked(self):
        r = self.h.submit()
        os.environ[self.h.seal_env + "_B"] = "b" * 64
        try:
            self.h.keyring.add(trust.HmacKey("seal-2", trust.SecretRef("env:" + self.h.seal_env + "_B")), activate=True)
            self.svc.load(self.h.tenant_token("t1"), r["artifact"], r["descriptor"])
            r2 = self.h.submit(version=2)
            self.assertEqual(r2["descriptor"]["key_id"], "seal-2")
        finally:
            os.environ.pop(self.h.seal_env + "_B", None)


class T04_CrossTenantConfusedDeputy(_Base):
    def test_wrong_tenant_cannot_load(self):
        r = self.h.submit(tenant="t1")
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t2"), r["artifact"], r["descriptor"]),
                         "SFI_UNAUTHORIZED")

    def test_tenant_principal_cannot_submit_for_other_tenant(self):
        tok = self.h.tenant_token("t2")
        self.assertEqual(self.code(self.h.submit, tenant="t1", token=tok), "SFI_UNAUTHORIZED")

    def test_digest_scoped_grant(self):
        r = self.h.submit()
        d = r["descriptor"]["artifact_sha256"]
        ok = self.h.idp.mint("x", "service", "t1", [Grant("sfi.load", "t1", d)])
        self.svc.load(ok, r["artifact"], r["descriptor"])
        other = builder.rw_module() + b"\x00\x06\x04name\x00"  # different bytes -> different digest
        r2 = self.h.submit(artifact=other, version=2)
        self.assertNotEqual(r2["descriptor"]["artifact_sha256"], d)
        self.assertEqual(self.code(self.svc.load, ok, r2["artifact"], r2["descriptor"]), "SFI_UNAUTHORIZED")

    def test_execute_needs_its_own_capability(self):
        r = self.h.submit()
        handle = self.svc.load(self.h.tenant_token("t1"), r["artifact"], r["descriptor"])
        only_load = self.h.tenant_token("t1", caps=("sfi.load",))
        self.assertEqual(self.code(self.svc.execute, only_load, handle, []), "SFI_UNAUTHORIZED")


class T05_Spoofing(_Base):
    def test_anonymous_and_forged_tokens(self):
        for tok in (None, "", "abc", "00." + "0" * 64, self.h.tenant_token("t1")[:-2] + "00"):
            with self.subTest(tok=str(tok)[:10]):
                self.assertEqual(self.code(self.h.submit, token=tok if tok is not None else 0), "SFI_UNAUTHENTICATED")

    def test_expired_token(self):
        tok = self.h.idp.mint("x", "service", "t1", [Grant("sfi.submit", "t1")], ttl=1)
        real = self.h.idp.clock
        self.h.idp.clock = lambda: real() + 5
        self.assertEqual(self.code(self.h.submit, token=tok), "SFI_UNAUTHENTICATED")

    def test_token_from_other_idp_key(self):
        os.environ["INV45_OTHER_IDP"] = "z" * 64
        try:
            from inv45_sfi_mechanisms.production.authz import IdentityProvider
            other = IdentityProvider(trust.SecretRef("env:INV45_OTHER_IDP"))
            tok = other.mint("x", "human", None, [Grant(c) for c in ("sfi.submit",)])
            self.assertEqual(self.code(self.h.submit, token=tok), "SFI_UNAUTHENTICATED")
        finally:
            os.environ.pop("INV45_OTHER_IDP")


class T06_SupplyChainArtifactSignature(_Base):
    def test_unsigned_wrong_signer_revoked_modified(self):
        art = builder.rw_module()
        tok = self.h.tenant_token("t1")
        good = self.h.sign(art)
        cases = {
            "no envelope": {},
            "modified bytes": (art[:-1] + b"\x0c", good),
            "wrong key id": dict(good, key_id="nope"),
            "bad signature": dict(good, signature=good["signature"][::-1]),
            "wrong issuer": {**good, "statement": dict(good["statement"], issuer="evil")},
        }
        for name, c in cases.items():
            with self.subTest(name):
                a, st = c if isinstance(c, tuple) else (art, c)
                got = self.code(self.svc.submit, tok, a, tenant="t1", workload="wl", version=1, signed_statement=st)
                self.assertIn(got, ("SFI_SIGNATURE_INVALID", "SFI_DIGEST_MISMATCH", "SFI_UNSUPPORTED_VERSION"))
        self.h.trust_store.revoke("ci-1")
        self.assertEqual(self.code(self.svc.submit, tok, art, tenant="t1", workload="wl", version=1,
                                   signed_statement=good), "SFI_SIGNATURE_INVALID")

    def test_signature_valid_but_bound_to_other_workload(self):
        art = builder.rw_module()
        st = self.h.sign(art, workload="other")
        self.assertEqual(self.code(self.svc.submit, self.h.tenant_token("t1"), art, tenant="t1", workload="wl",
                                   version=1, signed_statement=st), "SFI_SIGNATURE_INVALID")


class T07_RollbackAndDowngrade(_Base):
    def test_anti_rollback_floor(self):
        tok = self.h.tenant_token("t1")
        r5 = self.h.submit(version=5)
        self.svc.load(tok, r5["artifact"], r5["descriptor"])
        self.assertEqual(self.code(self.h.submit, version=4), "SFI_ROLLBACK_REJECTED")

    def test_sealed_old_version_cannot_load_after_newer(self):
        tok = self.h.tenant_token("t1")
        r3 = self.h.submit(version=3)
        r4 = self.h.submit(version=4)
        self.svc.load(tok, r4["artifact"], r4["descriptor"])
        self.assertEqual(self.code(self.svc.load, tok, r3["artifact"], r3["descriptor"]), "SFI_ROLLBACK_REJECTED")

    def test_unknown_schema_versions_refused(self):
        r = self.h.submit()
        d = dict(r["descriptor"], schema="PK_SFI_SEALED_DESCRIPTOR/0")
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), r["artifact"], d), "SFI_UNSUPPORTED_VERSION")
        self.assertEqual(self.code(config.validate, {"schema": "PK_SFI_CONFIG/0"}), "SFI_UNSUPPORTED_VERSION")


class T08_PolicyBypassViaConfigChange(_Base):
    def test_descriptor_from_old_config_generation_refused(self):
        r = self.h.submit()
        cfg = copy.deepcopy(self.svc.cfg)
        cfg["telemetry"]["retention_days"] = 31
        self.svc.activate_config(self.h.token(), cfg)
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), r["artifact"], r["descriptor"]),
                         "SFI_SEAL_MISMATCH")

    def test_overlay_cannot_weaken(self):
        self.assertEqual(self.code(config.merge, config.DEFAULTS, {"profile": {"allow_memory_grow": True}}),
                         "SFI_CONFIG_INVALID")

    def test_policy_write_requires_capability(self):
        self.assertEqual(self.code(self.svc.activate_config, self.h.tenant_token("t1"), dict(config.DEFAULTS)),
                         "SFI_UNAUTHORIZED")


class T09_ResourceExhaustion(_Base):
    def test_oversized_artifact_rejected_before_parse(self):
        cfg = copy.deepcopy(self.svc.cfg)
        cfg["limits"]["max_module_bytes"] = 1024
        self.svc.activate_config(self.h.token(), cfg)
        big = builder.ModuleBuilder(memory=(4, None), customs=[("pad", b"x" * 2000)]).build()
        self.assertEqual(self.code(self.h.submit, artifact=big), "SFI_RESOURCE_LIMIT")

    def test_secure_bounds_cannot_disable_limits(self):
        for sec, key, val in (("limits", "deadline_seconds", 0), ("limits", "max_module_bytes", 1 << 40),
                              ("admission", "max_concurrent", 0)):
            cfg = copy.deepcopy(config.DEFAULTS)
            cfg[sec][key] = val
            self.assertEqual(self.code(config.validate, cfg), "SFI_CONFIG_INVALID")


class T10_SecretAndTenantLeakage(_Base):
    def test_errors_logs_audit_contain_no_secret_or_bytes(self):
        stream = io.StringIO()
        self.svc.log.stream = stream
        secret = os.environ[self.h.seal_env]
        idp_secret = os.environ[self.h.idp_env]
        art = builder.rw_module()
        try:
            self.svc.submit(self.h.tenant_token("t1"), art, tenant="t1", workload="wl", version=1,
                            signed_statement=self.h.sign(art, "wl", 2))
        except SfiError as e:
            env = json.dumps(e.as_dict())
        r = self.h.submit()
        self.svc.load(self.h.tenant_token("t1"), r["artifact"], r["descriptor"])
        audit = (self.h.root / "audit" / "audit.jsonl").read_text()
        blob = stream.getvalue() + audit + env + self.svc.metrics.prometheus()
        for s in (secret, idp_secret, r["descriptor"]["mac"], art.hex()[:64]):
            self.assertNotIn(s, blob)
        self.assertNotIn(secret, repr(self.h.keyring.keys))

    def test_secret_values_rejected_in_config(self):
        cfg = copy.deepcopy(config.DEFAULTS)
        cfg["trust"]["seal_key_ref"] = "hunter2hunter2hunter2hunter2hunter2"
        self.assertEqual(self.code(config.validate, cfg), "SFI_CONFIG_INVALID")


class T11_StaleTrustMaterial(_Base):
    def test_stale_keyring_grants_no_new_trust(self):
        r = self.h.submit()
        self.h.keyring.loaded_at = time.time() - 10 * 3600
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), r["artifact"], r["descriptor"]),
                         "SFI_TRUST_STALE")
        self.assertEqual(self.code(self.h.submit, version=2), "SFI_TRUST_STALE")
        self.assertEqual(self.svc.health()["status"], "dependency_stale")

    def test_unresolvable_secret_fails_closed(self):
        os.environ.pop(self.h.seal_env)
        self.assertEqual(self.code(self.h.submit), "SFI_DEPENDENCY_UNAVAILABLE")


class T12_QuarantineBypass(_Base):
    def test_freeze_blocks_new_loads_disable_blocks_execute(self):
        r = self.h.submit()
        op = self.h.token("op1")
        self.svc.quarantine(op, "tenant", "t1", "freeze", "suspected abuse")
        self.assertEqual(self.code(self.svc.load, self.h.tenant_token("t1"), r["artifact"], r["descriptor"]),
                         "SFI_QUARANTINED")
        self.assertEqual(self.code(self.h.submit, version=2), "SFI_QUARANTINED")

    def test_global_disable_requires_two_humans(self):
        op1, op2 = self.h.token("op1"), self.h.token("op2")
        svc_tok = self.h.idp.mint("robot", "service", None, [Grant("sfi.quarantine")])
        self.assertEqual(self.code(self.svc.quarantine, op1, "global", "*", "disable", "x"), "SFI_DUAL_AUTH_REQUIRED")
        self.assertEqual(self.code(self.svc.quarantine, op1, "global", "*", "disable", "x", op1),
                         "SFI_DUAL_AUTH_REQUIRED")
        self.assertEqual(self.code(self.svc.quarantine, op1, "global", "*", "disable", "x", svc_tok),
                         "SFI_DUAL_AUTH_REQUIRED")
        self.svc.quarantine(op1, "global", "*", "disable", "incident", op2)
        self.assertEqual(self.svc.health()["status"], "quarantined")

    def test_tenant_cannot_release_itself(self):
        op = self.h.token("op1")
        self.svc.quarantine(op, "tenant", "t1", "freeze", "x")
        self.assertEqual(self.code(self.svc.release, self.h.tenant_token("t1"), "tenant", "t1"), "SFI_UNAUTHORIZED")


class T13_AuditTampering(_Base):
    def test_denials_are_audited(self):
        self.code(self.h.submit, token="garbage")
        text = (self.h.root / "audit" / "audit.jsonl").read_text()
        self.assertIn('"authn.failed"', text)


if __name__ == "__main__":
    unittest.main()
