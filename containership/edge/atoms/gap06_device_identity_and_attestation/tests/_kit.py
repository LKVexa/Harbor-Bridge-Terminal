"""Shared fixtures for the v5 missing-component tests (software attester only)."""
import datetime as dt
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.asymmetric import ec, ed25519  # noqa: E402
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402

from gap06_device_identity_and_attestation.mc import (  # noqa: E402
    audit, authz, certchain, clock, enrollment, keys, ops, policy, ratelimit, replay, service, simulator, store)

T0 = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc).timestamp()
ENV = "prod"


def pem(pub):
    return pub.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


def boot_pcrs(t):
    for pcr, data in [(0, b"firmware-1.2"), (1, b"fw-config"), (2, b"option-roms"), (7, b"secureboot-on")]:
        t.extend(pcr, data)


def operator(roles=("enroll", "revoke", "read", "quarantine_release", "policy_publish")):
    return authz.Principal("op-alice", frozenset(roles), frozenset({ENV}))


def node_principal(node):
    return authz.Principal(f"node:{node}", frozenset({"attest"}), frozenset({ENV}), node=node)


class World:
    """A fully wired service in a temp dir with one software root."""

    def __init__(self, tmp=None, approvers=3, threshold=2):
        self.tmp = pathlib.Path(tmp or tempfile.mkdtemp(prefix="gap06-"))
        self.mono = clock.FakeMonotonic(100.0)
        self.clock = clock.TrustedClock(monotonic=self.mono)
        self.clock.sync(T0)
        self.store = store.DurableStore(self.tmp / "state", fsync=False)
        self.root_key = ec.generate_private_key(ec.SECP256R1())
        self.root = simulator.make_cert("test-root", self.root_key, "test-root", self.root_key, ca=True, days=3650)
        self.trust = certchain.TrustStore(anchors=[self.root], allow_test_roots=True)
        self.authz = authz.Authorizer(ENV)
        self.ks = keys.SoftwareKeyStore(acl={"audit": {"gap06-audit": {"sign"}}, "wl": {"gap06-workload": {"sign"}}})
        self.audit_kid = self.ks.create("audit")
        self.ledger = audit.AuditLedger(self.tmp / "audit.jsonl", self.ks, self.audit_kid)
        self.approver_keys = {f"ap{i}": ed25519.Ed25519PrivateKey.generate() for i in range(approvers)}
        self.publisher = policy.PolicyPublisher({k: pem(v.public_key()) for k, v in self.approver_keys.items()},
                                                threshold, self.store, ENV)
        self.peers = None
        self.enroll = enrollment.Enrollment(self.store, self.trust, self.authz, self.clock, self.ledger)
        self.book = replay.ChallengeBook(self.store, ttl=30.0)
        self.cordoned = set()
        self.quarantine = ops.QuarantineEnforcer(self.store, {"gap01": self._sink, "sch01": self._sink})
        self.svc = service.AttestationService(ENV, self.store, self.clock, self.authz, ratelimit.Admission(),
                                              self.publisher, self.ledger, self.quarantine, self.enroll, self.book)

    def _sink(self, cmd):
        self.cordoned.add(cmd["node"])
        return True

    def tpm(self, name):
        t = simulator.SoftTPM(name, self.root_key, self.root)
        boot_pcrs(t)
        return t

    def sign_policy(self, doc, who=("ap0", "ap1")):
        body = policy.canonical(doc)
        return {w: self.approver_keys[w].sign(body).hex() for w in who}

    def publish_for(self, t, version=1, pcrs=(0, 1, 2, 7), **extra):
        doc = {"environment": ENV, "version": version, "not_before": T0 - 10,
               "accepted": {str(p): [t.pcrs[("sha256", p)].hex()] for p in pcrs}, **extra}
        return self.publisher.activate(doc, self.sign_policy(doc), now=self.clock.now())

    def enrol(self, name, t=None):
        t = t or self.tpm(name)
        b = self.enroll.begin(name, t.ek_cert.public_bytes(serialization.Encoding.PEM), t.ak_public_pem, operator=operator())
        sig = t.sign_raw(enrollment.DOMAIN + b["challenge"] + b["ak_name"])
        self.enroll.complete(b["ticket"], sig)
        return t

    def attest_msg(self, name, t, nonce_hex=None, idem="k1", with_log=True):
        nonce_hex = nonce_hex or self.svc.challenge(node_principal(name), name)["nonce"]
        attest, sig, pcrs = t.quote(bytes.fromhex(nonce_hex))
        m = {"schema": "PK_ATTESTATION/1", "node": name, "nonce": nonce_hex, "attest": attest.hex(),
             "signature": sig.hex(), "pcrs": {str(k): v.hex() for k, v in pcrs.items()}, "idempotency_key": idem}
        if with_log:
            m["event_log"] = t.event_log().hex()
        return m
