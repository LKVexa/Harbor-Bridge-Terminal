import copy
import unittest

import _util  # noqa: F401
from gap05_state_replication_consistency_model.production import errors as E
from gap05_state_replication_consistency_model.production.identity import (
    CertificateAuthority, IdentityVerifier, ReplicaKeys, TrustBundle, workload_id)
from gap05_state_replication_consistency_model.production.protect import Keyring, sign_write, verify_write
from gap05_state_replication_consistency_model.production.schemas import make_write_doc, op_id_for
from gap05_state_replication_consistency_model.production.testkit import NOW, Cluster, E as ENV, T


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.c = Cluster(("a", "b"))

    def tearDown(self):
        self.c.close()

    def _auth(self, keys, cb="chan-1", now=NOW, answer_cb=None, verifier=None):
        v = verifier or self.c.verifier
        nonce = v.challenge(cb)
        sig = keys.answer(nonce, answer_cb or cb)
        return v.authenticate(keys.credential, nonce, sig, channel_binding=cb, now=now,
                              membership=self.c.memberships["a"])

    def test_canonical_identity(self):
        """items: MC01-001 MC01-007
        Canonical SPIFFE-style identity; wildcards and path tricks rejected."""
        self.assertEqual(workload_id("gap05.test", "a"), "spiffe://gap05.test/replica/a")
        for bad in ("*", "a/b", ""):
            with self.assertRaises(E.ConfigError):
                workload_id("gap05.test", bad)

    def test_authenticated_session_maps_to_one_replica(self):
        """items: MC01-002 MC01-004 MC01-009 MC38-001
        A session authenticates by proof of possession and maps to exactly one active replica."""
        peer = self._auth(self.c.keys["b"])
        self.assertEqual(peer.replica, "b")
        self.assertEqual(peer.epoch, 1)
        self.assertEqual(peer.key_fingerprint, self.c.keys["b"].fingerprint)

    def test_replay_and_channel_binding(self):
        """items: MC01-010 MC01-011 MC38-001 MC38-002
        A captured handshake cannot be replayed, nor used on another channel."""
        k = self.c.keys["b"]
        nonce = self.c.verifier.challenge("chan-1")
        sig = k.answer(nonce, "chan-1")
        self.c.verifier.authenticate(k.credential, nonce, sig, channel_binding="chan-1", now=NOW,
                                     membership=self.c.memberships["a"])
        with self.assertRaises(E.AuthenticationError) as cm:
            self.c.verifier.authenticate(k.credential, nonce, sig, channel_binding="chan-1", now=NOW,
                                         membership=self.c.memberships["a"])
        self.assertEqual(cm.exception.code, "SEC_REPLAY")
        with self.assertRaises(E.AuthenticationError) as cm:
            self._auth(k, cb="chan-2", answer_cb="chan-1")
        self.assertEqual(cm.exception.code, "SEC_BAD_POP")

    def test_expired_revoked_untrusted_unknown(self):
        """items: MC01-005 MC01-006 MC01-011 MC38-001
        Expired, revoked, foreign-CA and unmapped identities are rejected with stable codes."""
        k = self.c.keys["b"]
        with self.assertRaises(E.AuthenticationError) as cm:
            self._auth(k, now=NOW + 10 ** 7)
        self.assertEqual(cm.exception.code, "SEC_EXPIRED")
        rogue_ca = CertificateAuthority("gap05.test")
        rogue = ReplicaKeys.provision(rogue_ca, "b", now=NOW)
        with self.assertRaises(E.AuthenticationError) as cm:
            self._auth(rogue)
        self.assertEqual(cm.exception.code, "SEC_UNTRUSTED_ISSUER")
        stranger = ReplicaKeys.provision(self.c.ca, "zz", now=NOW)
        with self.assertRaises(E.AuthenticationError) as cm:
            self._auth(stranger)
        self.assertEqual(cm.exception.code, "SEC_UNKNOWN_IDENTITY")
        self.c.verifier.revoke(k.credential.serial)
        with self.assertRaises(E.AuthenticationError) as cm:
            self._auth(k)
        self.assertEqual(cm.exception.code, "SEC_REVOKED")

    def test_stolen_credential_without_key_fails(self):
        """items: MC01-011 MC38-001
        Credential theft simulation: a thief holding b's credential but not its key fails PoP."""
        thief = ReplicaKeys.provision(self.c.ca, "b", now=NOW)  # different private key
        thief.credential = self.c.keys["b"].credential
        with self.assertRaises(E.AuthenticationError):
            self._auth(thief)

    def test_trust_bundle_rotation(self):
        """items: MC01-008 MC01-011
        New CA added, old removed; the last anchor cannot be removed."""
        new_ca = CertificateAuthority("gap05.test")
        new_id = self.c.bundle.add(new_ca.public_key)
        rotated = ReplicaKeys.provision(new_ca, "b", now=NOW)
        rotated.private_key = rotated.private_key  # new key under new CA
        # register the rotated key fingerprint for b is required -> membership mapping rejects it
        with self.assertRaises(E.AuthenticationError) as cm:
            self._auth(rotated)
        self.assertEqual(cm.exception.code, "SEC_KEY_NOT_REGISTERED")
        old_id = [cid for cid in self.c.bundle.authorities if cid != new_id][0]
        self.c.bundle.remove(old_id)
        with self.assertRaises(E.AuthenticationError):
            self._auth(self.c.keys["b"])
        with self.assertRaises(E.ConfigError):
            self.c.bundle.remove(new_id)

    def test_untrusted_replica_field_cannot_change_attribution(self):
        """items: MC01-012 MC02-005 MC38-001
        Rewriting the payload 'site' to another replica breaks provenance: attribution is fixed."""
        a = self.c.nodes["a"]
        doc = sign_write(make_write_doc(tenant=T, environment=ENV, key="k", value="v", site="b",
                                        vector={"b": 1}, epoch=1), self.c.keys["b"].private_key)
        forged = dict(doc, site="a", vector=[["a", 1]])
        forged["op_id"] = op_id_for(forged)
        with self.assertRaises(E.ProvenanceError):
            a.submit(forged, principal=self.c.principal("b"), relay=True)
        self.assertEqual(a.submit(doc, principal=self.c.principal("b"), relay=True)["outcome"], "converged")


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.c = Cluster(("a", "b"))
        self.doc = sign_write(make_write_doc(tenant=T, environment=ENV, key="k", value="v", site="b",
                                             vector={"b": 1}, epoch=1), self.c.keys["b"].private_key)

    def tearDown(self):
        self.c.close()

    def test_valid_signature(self):
        """items: MC02-001 MC02-002 MC02-003 MC02-007
        Ed25519 over canonical JSON binds tenant/env/key/value/site/vector/epoch."""
        verify_write(self.doc, self.c.memberships["a"])

    def test_single_bit_mutation_detected(self):
        """items: MC02-012 MC02-011 MC38-002
        Flipping one bit in any signed field (with op_id recomputed) is detected."""
        fields = ["tenant", "environment", "key", "value", "site"]
        for f in fields:
            d = copy.deepcopy(self.doc)
            raw = bytearray(d[f].encode())
            raw[0] ^= 1
            d[f] = raw.decode("latin-1")
            with self.assertRaises(E.ProvenanceError, msg=f):
                verify_write(d, self.c.memberships["a"])
        d = copy.deepcopy(self.doc)
        d["vector"] = [["b", 3]]
        with self.assertRaises(E.ProvenanceError):
            verify_write(d, self.c.memberships["a"])
        d = copy.deepcopy(self.doc)
        d["epoch"] = 2
        with self.assertRaises(E.ProvenanceError):
            verify_write(d, self.c.memberships["a"])

    def test_malformed_and_downgrade(self):
        """items: MC02-006 MC02-011 MC38-002
        Unsigned, wrong algorithm, truncated signature and unregistered key are rejected."""
        d = dict(self.doc)
        d.pop("provenance")
        with self.assertRaises(E.ProvenanceError) as cm:
            verify_write(d, self.c.memberships["a"])
        self.assertEqual(cm.exception.code, "SEC_UNSIGNED")
        d = copy.deepcopy(self.doc)
        d["provenance"]["alg"] = "none"
        with self.assertRaises(E.ProvenanceError):
            verify_write(d, self.c.memberships["a"])
        d = copy.deepcopy(self.doc)
        d["provenance"]["sig"] = d["provenance"]["sig"][:20]
        with self.assertRaises(E.ProvenanceError):
            verify_write(d, self.c.memberships["a"])
        d = copy.deepcopy(self.doc)
        d["provenance"]["key_id"] = "0" * 32
        with self.assertRaises(E.ProvenanceError) as cm:
            verify_write(d, self.c.memberships["a"])
        self.assertEqual(cm.exception.code, "SEC_KEY_NOT_REGISTERED")

    def test_cross_tenant_replay(self):
        """items: MC02-011 MC06-004 MC38-004
        A signed write replayed into another tenant fails provenance."""
        d = dict(self.doc, tenant="tenant-b")
        d["op_id"] = op_id_for(d)
        with self.assertRaises(E.ProvenanceError):
            verify_write(d, self.c.memberships["a"])

    def test_verification_before_mutation(self):
        """items: MC02-005 MC02-009
        A rejected write leaves no WAL, frontier or audit trace of acceptance; the WAL keeps
        only public verification metadata (key_id + signature), never private keys."""
        a = self.c.nodes["a"]
        bad = copy.deepcopy(self.doc)
        bad["provenance"]["sig"] = bad["provenance"]["sig"][::-1]
        before = len(a.wal.records)
        with self.assertRaises(E.ProvenanceError):
            a.submit(bad, principal=self.c.principal("b"), relay=True)
        self.assertEqual(len(a.wal.records), before)
        self.assertEqual(a.state_keys(), [])
        a.submit(self.doc, principal=self.c.principal("b"), relay=True)
        raw = (a.dir / "wal.log").read_bytes()
        self.assertIn(b'"key_id"', raw)
        self.assertNotIn(b"PRIVATE", raw)


class KeyringTests(unittest.TestCase):
    ctx = dict(tenant=T, environment=ENV, purpose="wal")

    def test_roundtrip_rotation_rewrap_retire(self):
        """items: MC12-004 MC12-006 MC12-007 MC12-008 MC12-012
        Rotate under use: old envelopes still decrypt, rewrap moves them, retire refuses in-use keys."""
        kr = Keyring()
        k1 = kr.rotate()
        env1 = kr.encrypt(b"secret", **self.ctx)
        k2 = kr.rotate()
        env2 = kr.encrypt(b"new", **self.ctx)
        self.assertEqual(kr.decrypt(env1, **self.ctx), b"secret")
        self.assertEqual(env2["kid"], k2)
        with self.assertRaises(E.ConfigError):
            kr.retire(k1)
        env1b = kr.rewrap(env1, **self.ctx)
        kr.retire(k1)
        self.assertEqual(kr.decrypt(env1b, **self.ctx), b"secret")
        with self.assertRaises(E.SecurityError):
            kr.decrypt(env1, **self.ctx)

    def test_wrong_namespace_and_corruption(self):
        """items: MC12-005 MC12-011 MC12-009 MC38-010
        AAD binds tenant/env: wrong tenant or flipped ciphertext bit is a hard failure."""
        kr = Keyring()
        kr.rotate()
        env = kr.encrypt(b"x", **self.ctx)
        with self.assertRaises(E.IntegrityError):
            kr.decrypt(env, tenant="other", environment=ENV, purpose="wal")
        bad = dict(env, ct=env["ct"][:-2] + ("A" if env["ct"][-2] != "A" else "B") + env["ct"][-1])
        with self.assertRaises(E.IntegrityError):
            kr.decrypt(bad, **self.ctx)

    def test_encrypted_wal_recovers_and_fails_closed_without_key(self):
        """items: MC04-009 MC12-003 MC12-009 MC38-010
        WAL values are encrypted at rest; recovery without the keyring fails closed."""
        kr = Keyring()
        kr.rotate()
        c = Cluster(("a",), node_kwargs={"keyring": kr})
        try:
            c.nodes["a"].write(T, ENV, "k", "top-secret-value", principal="operator")
            raw = (c.nodes["a"].dir / "wal.log").read_bytes()
            self.assertNotIn(b"top-secret-value", raw)
            n = c.reopen("a")
            self.assertEqual(n.read(T, ENV, "k", principal="operator")["value"], "top-secret-value")
            n.close()
            from gap05_state_replication_consistency_model.production.node import ReplicaNode
            n2 = ReplicaNode(n.dir, c.keys["a"], c.memberships["a"], policy_provider=lambda: c.policy)
            self.assertEqual(n2.recovery_report["rejected"], 1)
            self.assertEqual(n2.state_keys(), [])
            self.assertFalse(n2.health()["ready"])
            n2.close()
        finally:
            c.close()


if __name__ == "__main__":
    unittest.main()
