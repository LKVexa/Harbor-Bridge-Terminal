"""MC-009/020/044/046/075/080/081/089 — the production path end to end, with real launches."""
from __future__ import annotations

import io
import json
import threading
import unittest
from importlib import import_module

from _support import LINUX, PKG_DIR, require

rt = import_module(PKG_DIR.name + ".runtime")
att = import_module(PKG_DIR.name + ".attestation")
ctl = import_module(PKG_DIR.name + ".control")
errors = import_module(PKG_DIR.name + ".errors")
profiles = import_module(PKG_DIR.name + ".profiles")
sc = import_module(PKG_DIR.name + ".schema_check")
integ = import_module(PKG_DIR.name + ".integration")
pkg = import_module(PKG_DIR.name)
K = b"s" * 32


def service(**kw):
    a = ctl.Authorizer()
    a.grant("op", "tenant-operator", "t1")
    a.grant("sec", "security-responder", "*")
    return rt.SandboxService(identity=att.NodeIdentity("node-1", K), principal_keys={"op": K, "sec": K},
                             authz=a, log_stream=io.StringIO(), **kw)


def req(svc, **kw):
    base = dict(token=ctl.issue_token(K, "op", svc.AUDIENCE, 60), tenant="t1", workload="w1",
                profile=profiles.load_profile("posix-minimal"), argv=("/bin/true",))
    base.update(kw)
    return rt.LaunchRequest(**base)


class RefusalPathTest(unittest.TestCase):
    """These refusals happen before any process is created, on any OS."""

    def assertCode(self, code, fn):
        with self.assertRaises(errors.SandboxError) as c:
            fn()
        self.assertEqual(c.exception.code, code)

    def test_refusals(self):
        svc = service()
        self.assertCode("E_UNAUTHENTICATED", lambda: svc.launch(req(svc, token="bad.token")))
        self.assertCode("E_UNAUTHORIZED", lambda: svc.launch(req(svc, tenant="t2")))
        bad = pkg.SandboxProfile("bad", {"read", "execve", "exit_group"}, {"CAP_SYS_ADMIN"})
        self.assertCode("E_PROFILE_INVALID", lambda: svc.launch(req(svc, profile=bad)))
        big = pkg.SandboxProfile("big", frozenset(list(__import__(PKG_DIR.name + ".linux.syscall_tables",
                                  fromlist=["X86_64"]).X86_64)[:80]))
        self.assertCode("E_PROFILE_INVALID", lambda: svc.launch(req(svc, profile=big)))
        svc.quarantine.set("sec", "t1", "t1/w1", "incident")
        self.assertCode("E_QUARANTINED", lambda: svc.launch(req(svc)))
        off = service(dependencies_online=lambda: False)
        self.assertCode("E_DEPENDENCY_UNAVAILABLE", lambda: off.launch(req(off)))
        self.assertFalse(off.status()["ready"])
        reasons = [e for e in svc.audit.entries if e["kind"] == "reason"]
        self.assertGreaterEqual(len(reasons), 5)
        self.assertEqual(svc.admission.total, 0)          # nothing leaked
        self.assertEqual(svc.reasons.explain("t1/w1")[-1]["data"]["code"], "E_QUARANTINED")


@require(LINUX, "Linux enforcement not available")
class EndToEndTest(unittest.TestCase):
    def test_launch_produces_verifiable_signed_evidence(self):
        svc = service()
        out = svc.launch(req(svc, traceparent="00-" + "12" * 16 + "-" + "34" * 8 + "-01"))
        self.assertEqual(out["outcome"], "success")
        ev = out["evidence"]
        self.assertEqual(sc.validate(ev), [])
        self.assertTrue(ev["os_enforcement_proven"])
        self.assertEqual(ev["trace_id"], "12" * 16)
        att.EvidenceVerifier({"node-1": K}).verify(ev, expect={"sandbox_id": out["sandbox_id"],
                                                                "profile_digest": ev["profile_digest"]})
        self.assertEqual(out["lifecycle"], ["APPLYING", "VERIFYING", "READY", "RUNNING", "TERMINATING", "CLEANED"])
        self.assertTrue(att.verify_chain(svc.audit.entries)[0])
        st = svc.status()
        self.assertTrue(st["ready"])
        self.assertEqual(sc.validate(json.loads(json.dumps(st)), "PK_SANDBOX_STATUS/1"), [])
        self.assertIn("inv39_sandbox_starts_total", integ.gap09_export(svc)["metrics"])

    def test_idempotent_launch_runs_once(self):
        svc = service()
        a = svc.launch(req(svc, idempotency_key="k1"))
        b = svc.launch(req(svc, idempotency_key="k1"))
        self.assertEqual(a["sandbox_id"], b["sandbox_id"])
        with self.assertRaises(errors.SandboxError):
            svc.launch(req(svc, idempotency_key="k1", argv=("/bin/false",)))

    def test_nonzero_exit_is_partial(self):
        svc = service()
        self.assertEqual(svc.launch(req(svc, argv=("/bin/false",)))["outcome"], "partial")

    def test_concurrent_launches_respect_quota_and_isolate_evidence(self):
        svc = service(config={"max_per_tenant": 4})
        results, errs = [], []

        def go(i):
            try:
                results.append(svc.launch(req(svc, workload=f"w{i}",
                                              argv=("/bin/sh", "-c", "i=0; while [ $i -lt 20000 ]; do i=$((i+1)); done"))))
            except errors.SandboxError as e:
                errs.append(e.code)
        ts = [threading.Thread(target=go, args=(i,)) for i in range(12)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(len(results) + len(errs), 12)
        self.assertTrue(set(errs) <= {"E_QUOTA_EXCEEDED"}, errs)
        self.assertEqual(len({r["evidence"]["nonce"] for r in results}), len(results))
        self.assertEqual(len({r["sandbox_id"] for r in results}), len(results))
        self.assertEqual(svc.admission.total, 0)
        self.assertTrue(att.verify_chain(svc.audit.entries)[0])


class InteropTest(unittest.TestCase):
    """Reference-stub interoperability with PLN-04, GAP-13 and GAP-09 obligations."""

    def test_pln04_trust_classes(self):
        integ.pln04_admit({"trust_class": "trusted"})
        for c in ("untrusted", "hostile", None):
            with self.subTest(c), self.assertRaises(errors.SandboxError):
                integ.pln04_admit({"trust_class": c})

    def test_gap13_policy_documents(self):
        doc = {"kind": "sandbox-profile", "decision": "allow",
               "profile": {"name": "svc", "syscalls": ["read"], "namespaces": sorted(pkg.REQUIRED_NAMESPACES)}}
        self.assertEqual(integ.gap13_profile(doc).syscalls, frozenset({"read"}))
        for bad in (dict(doc, decision="deny"), dict(doc, kind="other"), dict(doc, profile={"name": "x"})):
            with self.assertRaises(errors.SandboxError):
                integ.gap13_profile(bad)

    def test_gap09_export_shape(self):
        exp = integ.gap09_export(service())
        self.assertEqual(set(exp), {"metrics", "status", "audit_head", "log_tail"})


if __name__ == "__main__":
    unittest.main()
