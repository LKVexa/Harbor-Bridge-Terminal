"""End-to-end, integration-adapter, concurrency, property/fuzz and mTLS tests."""
import datetime as dt
import json
import random
import ssl
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

import _kit as k
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from gap06_device_identity_and_attestation.mc import audit, integrations, simulator, store, transport, workload
from gap06_device_identity_and_attestation.mc.errors import Gap06Error


def code(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except Gap06Error as e:
        return e.code
    return "NO_ERROR"


class EndToEndTest(unittest.TestCase):
    def setUp(self):
        self.w = k.World()
        self.t = self.w.enrol("n1")
        self.w.publish_for(self.t)
        self.p = k.node_principal("n1")

    def test_trusted_then_expiry(self):
        r = self.w.svc.attest(self.p, self.w.attest_msg("n1", self.t))
        self.assertEqual(r["decision"], "trusted")
        self.assertEqual(self.w.svc.level_of("n1"), "hardware")
        self.w.mono.advance(self.w.svc.verdict_ttl)
        self.w.clock.sync(k.T0 + self.w.svc.verdict_ttl)
        self.assertEqual(self.w.svc.level_of("n1"), "untrusted")

    def test_no_policy_fails_closed(self):
        w = k.World()
        t = w.enrol("n1")
        self.assertEqual(code(w.svc.attest, self.p, w.attest_msg("n1", t)), "E_MEASUREMENT_REJECTED")
        self.assertEqual(w.svc.level_of("n1"), "untrusted")

    def test_replay_idempotency_and_conflict(self):
        m = self.w.attest_msg("n1", self.t)
        r1 = self.w.svc.attest(self.p, m)
        self.assertEqual(self.w.svc.attest(self.p, m), r1)  # idempotent retry
        self.assertEqual(code(self.w.svc.attest, self.p, dict(m, idempotency_key="other")), "E_REPLAY")
        m2 = self.w.attest_msg("n1", self.t, idem="k1")
        self.assertEqual(code(self.w.svc.attest, self.p, m2), "E_CONFLICT")

    def test_drift_quarantines_and_peers_cordon(self):
        peers = integrations.ReferencePeers(self.w.svc.level_of)
        self.w.quarantine.sinks = {"gap01": peers.cordon, "sch01": peers.exclude}
        self.w.svc.attest(self.p, self.w.attest_msg("n1", self.t))
        self.assertTrue(peers.may_grant("n1"))
        self.t.extend(7, b"secureboot-off")
        r = self.w.svc.attest(self.p, self.w.attest_msg("n1", self.t, idem="k2"))
        self.assertEqual(r["error"]["code"], "E_MEASUREMENT_REJECTED")
        self.assertTrue(self.w.quarantine.enforced("n1"))
        self.assertEqual(self.w.svc.level_of("n1"), "untrusted")
        self.assertFalse(peers.may_report_ready("n1"))
        self.assertEqual(peers.candidates(["n1"]), [])

    def test_unbound_evidence_cannot_quarantine(self):
        m = self.w.attest_msg("n1", self.t)
        m["nonce"] = "ab" * 32
        self.assertEqual(code(self.w.svc.attest, self.p, m), "E_UNISSUED_CHALLENGE")
        self.assertFalse(self.w.quarantine.is_quarantined("n1"))

    def test_forged_signature_does_not_quarantine(self):
        m = self.w.attest_msg("n1", self.t)
        m["signature"] = m["signature"][:-2] + ("00" if m["signature"][-2:] != "00" else "01")
        r = self.w.svc.attest(self.p, m)
        self.assertEqual(r["error"]["code"], "E_SIGNATURE")
        self.assertFalse(self.w.quarantine.is_quarantined("n1"))

    def test_other_node_cannot_attest_or_steal(self):
        self.assertEqual(code(self.w.svc.challenge, k.node_principal("n2"), "n1"), "E_FORBIDDEN")
        t2 = self.w.enrol("n2")
        n = self.w.svc.challenge(self.p, "n1")["nonce"]
        m = self.w.attest_msg("n2", t2, nonce_hex=n)
        self.assertEqual(code(self.w.svc.attest, k.node_principal("n2"), m), "E_UNISSUED_CHALLENGE")
        self.w.svc.attest(self.p, self.w.attest_msg("n1", self.t, nonce_hex=n))  # n1's challenge still valid

    def test_revoked_node(self):
        self.w.svc.attest(self.p, self.w.attest_msg("n1", self.t))
        self.w.enroll.revoke("n1", operator=k.operator(), reason="stolen")
        self.assertEqual(self.w.svc.level_of("n1"), "untrusted")
        self.assertEqual(code(self.w.svc.challenge, self.p, "n1"), "E_UNKNOWN_NODE")

    def test_restart_keeps_verdict_and_replay_state(self):
        m = self.w.attest_msg("n1", self.t)
        self.w.svc.attest(self.p, m)
        s2 = store.DurableStore(self.w.tmp / "state")
        self.assertEqual(s2.get("verdicts", "n1")["level"], "hardware")
        self.assertEqual(s2.get("challenges", m["nonce"])["state"], "consumed")

    def test_explain_and_audit_chain(self):
        self.w.svc.attest(self.p, self.w.attest_msg("n1", self.t))
        e = self.w.svc.explain(k.operator(), "n1")
        self.assertEqual((e["decision"], e["policy_version"]), ("trusted", "1"))
        self.assertTrue(e["policy_digest"] and e["raw_evidence_sha256"] and e["expires_at"])
        n = audit.AuditLedger.verify(self.w.ledger.path, {self.w.audit_kid: self.w.ks.public_key_pem(self.w.audit_kid)},
                                     self.w.ledger.anchor())
        self.assertGreaterEqual(n, 3)

    def test_policy_upgrade_changes_verdict_version(self):
        self.w.svc.attest(self.p, self.w.attest_msg("n1", self.t))
        self.w.publish_for(self.t, version=2)
        self.w.svc.attest(self.p, self.w.attest_msg("n1", self.t, idem="k2"))
        self.assertEqual(self.w.store.get("verdicts", "n1")["policy_version"], 2)

    def test_workload_identity(self):
        self.w.svc.attest(self.p, self.w.attest_msg("n1", self.t))
        wl = workload.WorkloadIssuer(self.w.ks, "wl")
        self.w.ks.create("wl")
        v = self.w.store.get("verdicts", "n1")
        allowed = {"t1": {"sha256:img"}}
        kw = dict(workload="api", tenant="t1", node="n1", node_verdict=v, quarantined=False, image_digest="sha256:img",
                  allowed_images=allowed, trust_class="hardware", now=k.T0)
        tok = wl.issue(**kw)
        pubs = {tok["kid"]: self.w.ks.public_key_pem(tok["kid"])}
        self.assertEqual(workload.WorkloadIssuer.verify(tok, pubs, now=k.T0 + 1, tenant="t1")["node"], "n1")
        self.assertLessEqual(tok["claims"]["exp"], v["expires_at"])
        self.assertEqual(code(workload.WorkloadIssuer.verify, tok, pubs, now=k.T0 + 1, tenant="t2"), "E_TENANT_BOUNDARY")
        self.assertEqual(code(workload.WorkloadIssuer.verify, tok, pubs, now=k.T0 + 10_000, tenant="t1"), "E_CHALLENGE_EXPIRED")
        self.assertEqual(code(wl.issue, **dict(kw, quarantined=True)), "E_FORBIDDEN")
        self.assertEqual(code(wl.issue, **dict(kw, image_digest="sha256:evil")), "E_MEASUREMENT_REJECTED")
        self.assertEqual(code(wl.issue, **dict(kw, tenant="t2")), "E_MEASUREMENT_REJECTED")
        self.assertEqual(code(wl.issue, **dict(kw, node_verdict=dict(v, level="software"))), "E_FORBIDDEN")
        forged = dict(tok, claims=dict(tok["claims"], tenant="t2"))
        self.assertEqual(code(workload.WorkloadIssuer.verify, forged, pubs, now=k.T0 + 1, tenant="t2"), "E_SIGNATURE")


class ConcurrencyTest(unittest.TestCase):
    def test_racing_consumers_one_winner(self):
        w = k.World()
        t = w.enrol("n1")
        w.publish_for(t)
        for trial in range(5):
            n = w.svc.challenge(k.node_principal("n1"), "n1")["nonce"]
            results = []
            barrier = threading.Barrier(8)

            def go(i):
                barrier.wait()
                try:
                    w.book.consume(n, "n1", w.clock.now(), audience="gap06")
                    results.append("ok")
                except Gap06Error as e:
                    results.append(e.code)
            ts = [threading.Thread(target=go, args=(i,)) for i in range(8)]
            [x.start() for x in ts]
            [x.join() for x in ts]
            self.assertEqual(results.count("ok"), 1, results)

    def test_parallel_nodes(self):
        w = k.World()
        tpms = {f"n{i}": w.enrol(f"n{i}") for i in range(6)}
        w.publish_for(tpms["n0"])
        out = {}

        def go(name):
            try:
                out[name] = w.svc.attest(k.node_principal(name), w.attest_msg(name, tpms[name], idem=name))["decision"]
            except Exception as e:  # a thread that raises must fail the test, not vanish
                out[name] = f"raised {type(e).__name__}: {e}"
        ts = [threading.Thread(target=go, args=(n,)) for n in tpms]
        [x.start() for x in ts]
        [x.join() for x in ts]
        self.assertEqual(out, {n: "trusted" for n in tpms})
        self.assertEqual(w.store.generation, store.DurableStore(w.tmp / "state").generation)


class PropertyFuzzTest(unittest.TestCase):
    def test_random_mutation_never_trusted(self):
        w = k.World()
        t = w.enrol("n1")
        w.publish_for(t)
        rng = random.Random(1234)
        trusted = 0
        for i in range(150):
            w.mono.advance(1.0)  # stay inside the per-principal admission rate
            m = w.attest_msg("n1", t, idem=f"f{i}")
            field_ = rng.choice(["attest", "signature", "event_log"])
            b = bytearray(bytes.fromhex(m[field_]))
            op = rng.randrange(3)
            if op == 0 and b:
                j = rng.randrange(len(b)); b[j] ^= 1 << rng.randrange(8)
            elif op == 1:
                b = b[: rng.randrange(len(b) + 1)]
            else:
                b += bytes([rng.randrange(256)])
            if bytes(b).hex() == m[field_]:
                continue  # no-op mutation (e.g. truncation to full length)
            m[field_] = bytes(b).hex()
            try:
                r = w.svc.attest(k.node_principal("n1"), m)
                if r["decision"] == "trusted":
                    # Only the unauthenticated, informational Spec ID header bytes of the
                    # event log (not extended into any PCR) may change without rejection;
                    # the PCR values are untouched by construction (pcrs field never mutated).
                    header_len = 32 + int.from_bytes(bytes.fromhex(m["event_log"])[28:32], "little")
                    self.assertEqual(field_, "event_log", (field_, op))
                    self.assertTrue(op == 0 and j < header_len, (op, j))
                    trusted += 1
            except Gap06Error:
                pass
        self.assertLessEqual(trusted, 3)


class TransportMtlsTest(unittest.TestCase):
    def test_mutual_tls_roundtrip(self):
        d = Path(tempfile.mkdtemp())
        ca = ec.generate_private_key(ec.SECP256R1())
        ca_cert = simulator.make_cert("svc-ca", ca, "svc-ca", ca, ca=True, days=3650,
                                      not_before=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1))
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes

        def leaf(cn, server):
            kk = ec.generate_private_key(ec.SECP256R1())
            b = (x509.CertificateBuilder().subject_name(simulator._name(cn)).issuer_name(ca_cert.subject)
                 .public_key(kk.public_key()).serial_number(x509.random_serial_number())
                 .not_valid_before(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1))
                 .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)))
            if server:
                b = b.add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
            c = b.sign(ca, hashes.SHA256())
            (d / f"{cn}.pem").write_bytes(c.public_bytes(serialization.Encoding.PEM))
            (d / f"{cn}.key").write_bytes(kk.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                           serialization.NoEncryption()))
        (d / "ca.pem").write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
        for cn, srv in (("server", True), ("n1", False), ("stranger", False)):
            leaf(cn, srv)
        w = k.World()
        t = w.enrol("n1")
        w.publish_for(t)
        srv = transport.make_server(w.svc.handle, host="127.0.0.1", port=0, cert_file=str(d / "server.pem"),
                                    key_file=str(d / "server.key"), client_ca_file=str(d / "ca.pem"),
                                    principal_map={"n1": k.node_principal("n1")})
        port = srv.server_address[1]
        try:
            def call(cn, path, body):
                ctx = ssl.create_default_context(cafile=str(d / "ca.pem"))
                ctx.check_hostname = False
                if cn:
                    ctx.load_cert_chain(str(d / f"{cn}.pem"), str(d / f"{cn}.key"))
                req = urllib.request.Request(f"https://127.0.0.1:{port}{path}", data=json.dumps(body).encode(), method="POST")
                try:
                    with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
                        return r.status, json.loads(r.read())
                except urllib.error.HTTPError as e:
                    return e.code, json.loads(e.read())
            st, ch = call("n1", "/v1/challenge", {"node": "n1"})
            self.assertEqual(st, 200)
            m = w.attest_msg("n1", t, nonce_hex=ch["nonce"])
            st, r = call("n1", "/v1/attest", m)
            self.assertEqual((st, r["decision"]), (200, "trusted"))
            st, r = call("stranger", "/v1/challenge", {"node": "n1"})
            self.assertEqual((st, r["code"]), (401, "E_UNAUTHENTICATED"))
            with self.assertRaises(Exception):
                call(None, "/v1/challenge", {"node": "n1"})  # no client cert -> handshake refused
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
