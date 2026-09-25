"""Adversarial suite for the threat model (MC-036/037; C041, C050, C085, C087).

Each test names the THREAT-xx id from docs/THREAT_MODEL.md it exercises.
"""
from __future__ import annotations

import io
import json
import unittest

from tests.support import EcpError, Estate
from inv66_enterprise_wasm_control_plane.production.telemetry import Logger
from inv66_enterprise_wasm_control_plane.production.keys import Signer


class ThreatTest(unittest.TestCase):
    def setUp(self):
        self.buf = io.StringIO()
        self.e = Estate(logger=Logger(self.buf))
        self.s = self.e.service

    def test_T01_attacker_registry_never_forwarded(self):
        d = self.s.admit(self.e.request("api", registry="ghcr.evil.example"), self.e.token("ops"))
        self.assertFalse(d["admitted"])
        self.assertIn("ECP_REGISTRY_NOT_APPROVED", [r["code"] for r in d["reasons"]])
        self.assertEqual(self.s.deployer.calls, 0)

    def test_T02_developer_to_production(self):
        with self.assertRaises(EcpError) as cm:
            self.s.admit(self.e.request("api"), self.e.token("dev"))
        self.assertEqual(cm.exception.code, "ECP_FORBIDDEN")
        refused = self.s.journal.query(kind="admit.refused")
        self.assertEqual(refused[-1]["body"]["code"], "ECP_FORBIDDEN")

    def test_T03_audit_rewrite_after_incident(self):
        self.s.admit(self.e.request("api"), self.e.token("ops"))
        anchor_key = Signer("anchor-1")
        self.s.journal.anchor(anchor_key)
        seg = self.s.journal._segments()[0]
        seg.write_bytes(seg.read_bytes().replace(b'"admitted":true', b'"admitted":false', 1))
        with self.assertRaises(EcpError):
            self.e.open()  # startup refuses a broken chain

    def test_T04_spoofed_identity_and_forged_token(self):
        with self.assertRaises(EcpError):
            self.s.admit(self.e.request("api"), "ops")  # a bare user string is no longer a credential
        other_idp = Signer("idp-key-1")
        from inv66_enterprise_wasm_control_plane.production.identity import mint_token
        t = self.e.token("ops")
        forged = mint_token(other_idp, json.loads(__import__("base64").urlsafe_b64decode(t.split(".")[1] + "==")))
        with self.assertRaises(EcpError) as cm:
            self.s.admit(self.e.request("api"), forged)
        self.assertEqual(cm.exception.code, "ECP_UNAUTHENTICATED")

    def test_T05_signature_replay_onto_other_component_or_digest(self):
        good = self.e.component("api")
        swapped = dict(self.e.component("web"), signature=good["signature"])
        r = self.e.request("web")
        r["manifest"]["components"] = [swapped]
        d = self.s.admit(r, self.e.token("ops"))
        self.assertIn("ECP_SIGNATURE_INVALID", [x["code"] for x in d["reasons"]])

    def test_T06_signer_scope_confusion(self):
        d = self.s.admit(self.e.request("api", signer=self.e.other_signer), self.e.token("ops"))
        self.assertIn("ECP_SIGNER_NOT_APPROVED", [x["code"] for x in d["reasons"]])

    def test_T07_confused_deputy_workload_other_tenant(self):
        p = self.e.auth.authenticate_peer("spiffe://acme.example/ns/payments/sa/deployer")
        self.assertTrue(self.s.admit(self.e.request("api", lattice="staging"), p)["admitted"])
        with self.assertRaises(EcpError):
            self.s.admit(self.e.request("api", tenant="analytics", lattice="prod"), p)

    def test_T08_privilege_escalation_by_delegation(self):
        with self.assertRaises(EcpError):
            self.s.rbac({"protocol": "PK_ECP_RBAC/1", "op": "bind", "request_id": "x",
                         "binding": {"subject": "tadmin", "role": "org-admin", "scope": "acme", "effect": "allow"}},
                        self.e.principal("tadmin"))
        with self.assertRaises(EcpError):
            self.s.rbac({"protocol": "PK_ECP_RBAC/1", "op": "bind", "request_id": "x",
                         "binding": {"subject": "tadmin", "role": "security-admin", "scope": "acme/payments", "effect": "allow"}},
                        self.e.principal("tadmin"))

    def test_T09_injection_and_control_characters(self):
        r = self.e.request("api")
        r["manifest"]["components"][0]["name"] = "api\n{\"admitted\":true}"
        with self.assertRaises(EcpError):  # schema pattern refuses before evaluation
            self.s.admit(r, self.e.token("ops"))
        for bad in ("prod\x00", " prod", "../prod"):
            r2 = self.e.request("api")
            r2["lattice"] = bad
            with self.assertRaises(EcpError):
                self.s.admit(r2, self.e.token("ops"))

    def test_T10_parser_bombs_and_resource_exhaustion(self):
        r = self.e.request("api")
        r["manifest"]["components"] = [self.e.component(f"c{i}") for i in range(300)]
        d = self.s.admit(r, self.e.token("ops"))
        self.assertIn("ECP_RESOURCE_LIMIT", [x["code"] for x in d["reasons"]])
        deep = {"a": None}
        cur = deep
        for _ in range(50):
            cur["a"] = {"a": None}
            cur = cur["a"]
        r3 = self.e.request("api")
        r3["manifest"]["components"][0]["x"] = deep
        with self.assertRaises(EcpError):
            self.s.admit(r3, self.e.token("ops"))

    def test_T11_idempotency_key_reuse_with_other_body(self):
        r = self.e.request("api", key="k-1")
        self.s.admit(r, self.e.token("ops"))
        r2 = dict(r, manifest={"app": "x", "components": [self.e.component("other")]})
        with self.assertRaises(EcpError) as cm:
            self.s.admit(r2, self.e.token("ops"))
        self.assertEqual(cm.exception.code, "ECP_IDEMPOTENCY_CONFLICT")

    def test_T12_secrets_and_tokens_never_logged_or_journaled(self):
        tok = self.e.token("ops")
        self.s.admit(self.e.request("api"), tok)
        with self.assertRaises(EcpError):
            self.s.admit(self.e.request("api"), self.e.token("dev"))
        raw = b"".join(p.read_bytes() for p in self.s.journal._segments())
        sig = tok.split(".")[2].encode()
        self.assertNotIn(sig, raw)
        self.assertNotIn(tok.split(".")[2], self.buf.getvalue())

    def test_T13_quarantine_needs_two_to_release(self):
        sec1, sec2 = self.e.principal("sec1"), self.e.principal("sec2")
        self.s.freeze("acme/payments", sec1, "incident 42")
        with self.assertRaises(EcpError) as cm:
            self.s.admit(self.e.request("api"), self.e.token("ops"))
        self.assertEqual(cm.exception.code, "ECP_QUARANTINED")
        self.assertFalse(self.s.release("acme/payments", sec1, "done")["released"])
        self.assertFalse(self.s.release("acme/payments", sec1, "again")["released"])  # same person twice
        self.assertTrue(self.s.release("acme/payments", sec2, "done")["released"])
        self.assertTrue(self.s.admit(self.e.request("api"), self.e.token("ops"))["admitted"])

    def test_T14_freeze_survives_restart(self):
        self.s.emergency_disable(self.e.principal("sec1"), "kill switch drill")
        s2 = self.e.open()
        with self.assertRaises(EcpError):
            s2.admit(self.e.request("api"), self.e.token("ops"))
        self.assertEqual(s2.health()["mode"], "frozen")

    def test_T15_config_change_needs_two_other_people(self):
        sec1 = self.e.principal("sec1")
        gen = self.s.stage_config(self.e.config(registries=[{"host": "ghcr.evil.example", "scope": "acme"}]), sec1,
                                  source_repo="git", source_rev="x")
        with self.assertRaises(EcpError):
            self.s.approve_config(gen, sec1)
        with self.assertRaises(EcpError):
            self.s.activate_config(gen, self.e.principal("platform", groups=["platform-admins"]),
                                   expected_active=self.s.config.active.generation)
        with self.assertRaises(EcpError) as cm:  # no principal = no activation once bootstrapped
            self.s.activate_config(gen, None, expected_active=self.s.config.active.generation)
        self.assertEqual(cm.exception.code, "ECP_UNAUTHENTICATED")
        with self.assertRaises(EcpError):  # a deployer cannot stage policy at all
            self.s.stage_config(self.e.config(), self.e.principal("ops"), source_repo="g", source_rev="r")

    def test_T17_adapter_endpoints_only_http(self):
        from inv66_enterprise_wasm_control_plane.production.adapters import HttpDeploymentManager
        from inv66_enterprise_wasm_control_plane.production.policy_engine import HttpPolicyClient
        for bad in ("file:///etc/passwd", "ftp://x/y", "gopher://x", "http:///nohost", ""):
            with self.assertRaises(EcpError):
                HttpDeploymentManager(bad)
            with self.assertRaises(EcpError):
                HttpPolicyClient(bad)
        pol = dict(self.e.config()["policy"], engine="external", external_endpoint="file:///etc/passwd")
        with self.assertRaises(EcpError):
            self.s.config.stage(self.e.config(policy=pol), author="a", source_repo="g", source_rev="r")

    def test_T16_timing_side_channel_note(self):
        # Ed25519 verification in `cryptography` is constant-time for a given key; authentication failures
        # return a single generic message ("credential rejected") so the reason code is the only oracle,
        # and it is only exposed in `details.reason` which carries no secret material.
        with self.assertRaises(EcpError) as cm:
            self.s.admit(self.e.request("api"), self.e.token("ops", aud="x"))
        self.assertEqual(cm.exception.message, "credential rejected")


if __name__ == "__main__":
    unittest.main()
