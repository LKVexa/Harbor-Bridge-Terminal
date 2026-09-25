"""Integration with INV-27, GAP-15, GAP-08; cross-architecture and cross-toolchain/version matrices
(MC-041..MC-045, MC-097, MC-098).

The neighbours are exercised through their *contract seams* shipped here (``binding.Inv27Adapter``,
``certification.CertificationStore`` fed by a GAP-15-shaped issuer, ``rollout.Gap08Port``).  Certifying
against the real INV-27 / GAP-15 / GAP-08 deployments is an environment step recorded as a blocker in
ops/MC_STATUS.json, not claimed here.
"""
import datetime as dt
import itertools
import unittest

from harness import BindingError, F, Reason, refusal
from inv28_unikernel_implementations.certification import CertificationStore, issue
from inv28_unikernel_implementations.model import fmt_utc
from inv28_unikernel_implementations.rollout import Stage

R = Reason


class Inv27Binding(unittest.TestCase):                                        # MC-041, MC-098
    def setUp(self):
        self.w = F.world()
        self.res = self.w["selector"].select(F.request(), now=F.NOW)

    def test_happy_path(self):
        out = self.w["inv27"].verify(self.res.ticket, F.artifact_bytes(self.res.ref), now=F.NOW)
        self.assertTrue(out["verified"])

    def test_substituted_artifact(self):
        with self.assertRaises(BindingError) as cm:
            self.w["inv27"].verify(self.res.ticket, F.artifact_bytes("nanos@1.0.0-fixture"), now=F.NOW)
        self.assertEqual(cm.exception.code, R.BINDING_MISMATCH)

    def test_ticket_field_tamper(self):
        for field, value in (("toolchain_ref", "nanos@1.0.0-fixture"), ("artifact_sha256", "0" * 64),
                             ("expires_at", "2030-01-01T00:00:00Z")):
            with self.subTest(field=field), self.assertRaises(BindingError) as cm:
                self.w["inv27"].verify({**self.res.ticket, field: value}, F.artifact_bytes(self.res.ref), now=F.NOW)
            self.assertEqual(cm.exception.code, R.BINDING_TAMPERED)

    def test_ticket_expiry(self):
        with self.assertRaises(BindingError) as cm:
            self.w["inv27"].verify(self.res.ticket, F.artifact_bytes(self.res.ref), now=F.NOW + dt.timedelta(hours=1))
        self.assertEqual(cm.exception.code, R.BINDING_EXPIRED)

    def test_register_changed_after_selection(self):
        reg = self.w["registry"]
        reg.update(reg.get(self.res.ref).replace(notes="changed"), actor="operator", expected_revision=reg.revision)
        with self.assertRaises(BindingError):
            self.w["inv27"].verify(self.res.ticket, F.artifact_bytes(self.res.ref), now=F.NOW)

    def test_disabled_after_selection(self):
        self.w["registry"].emergency_disable(self.res.ref, actor="operator", reason="CVE")
        with self.assertRaises(BindingError):
            self.w["inv27"].verify(self.res.ticket, F.artifact_bytes(self.res.ref), now=F.NOW)

    def test_ticket_from_other_deployment(self):
        other = F.world()
        foreign = other["selector"].select(F.request(), now=F.NOW).ticket
        with self.assertRaises(BindingError) as cm:
            self.w["inv27"].verify(foreign, F.artifact_bytes(self.res.ref), now=F.NOW)
        self.assertEqual(cm.exception.code, R.BINDING_TAMPERED)


class Gap15(unittest.TestCase):                                                # MC-042, MC-097
    def test_pull_from_source(self):
        w = F.world(with_certs=False)
        docs = []
        for r in w["registry"].entries:
            docs.append(issue(w["ring"], toolchain=r.name, version=r.version,
                              artifact_sha256=r.integrity.artifact_sha256, architecture="x86_64",
                              issued_at=fmt_utc(F.NOW - dt.timedelta(days=1)),
                              expires_at=fmt_utc(F.NOW + dt.timedelta(days=1))))
        store = CertificationStore(w["ring"], source=lambda: docs)
        w["selector"].certifications = store
        w["selector"].invalidate()
        self.assertEqual(w["selector"].select(F.request(), now=F.NOW).toolchain, "rumprun")
        self.assertEqual(len(store), 4)

    def test_source_down_fails_closed_in_production_only(self):
        w = F.world()
        w["selector"].certifications = CertificationStore(w["ring"], source=lambda: 1 / 0)
        w["selector"].invalidate()
        code, _ = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertEqual(code, R.DEPENDENCY_UNAVAILABLE.value)
        self.assertTrue(w["selector"].select(F.request(environment="dev"), now=F.NOW))

    def test_no_store_configured_production(self):
        w = F.world()
        w["selector"].certifications = None
        w["selector"].invalidate()
        code, _ = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertEqual(code, R.DEPENDENCY_UNAVAILABLE.value)

    def test_malformed_certificates(self):
        w = F.world()
        good = issue(w["ring"], toolchain="t", version="1", artifact_sha256="a" * 64, architecture="x86_64",
                     issued_at="2026-09-01T00:00:00Z", expires_at="2026-10-01T00:00:00Z")
        bads = [dict(good, schema="X"), {k: v for k, v in good.items() if k != "signature"},
                dict(good, signature=dict(good["signature"], key_id="nope"))]
        inverted = issue(w["ring"], toolchain="t", version="1", artifact_sha256="a" * 64, architecture="x86_64",
                         issued_at="2026-10-01T00:00:00Z", expires_at="2026-09-01T00:00:00Z")
        for bad in bads + [inverted]:
            with self.subTest(), self.assertRaises(Exception) as cm:
                w["certs"].ingest(bad)
            self.assertEqual(getattr(cm.exception, "code", None), R.CERTIFICATION_INVALID)

    def test_profile_specific_certificate(self):
        w = F.world(records=[F.record("t", runtimes=("posix-libc", "rust-std"))], with_certs=False)
        r = w["registry"].entries[0]
        w["certs"].ingest(issue(w["ring"], toolchain="t", version=r.version, artifact_sha256=r.integrity.artifact_sha256,
                                architecture="x86_64", runtime="rust-std", hypervisor="qemu-kvm",
                                issued_at="2026-09-01T00:00:00Z", expires_at="2026-12-01T00:00:00Z"))
        refusal(lambda: w["selector"].select(F.request(runtime="posix-libc", hypervisor="qemu-kvm"), now=F.NOW))
        self.assertEqual(w["selector"].select(F.request(runtime="rust-std", hypervisor="qemu-kvm"), now=F.NOW).toolchain, "t")


class FakeGap08:
    def __init__(self, up=True):
        self.up, self.events = up, []

    def announce(self, event):
        if not self.up:
            raise ConnectionError("gap08 down")
        self.events.append(event)


class Gap08Rollout(unittest.TestCase):                                         # MC-043, MC-068
    def test_staged_rollout_with_announcements(self):
        gap08 = FakeGap08()
        w = F.world(records=[F.record("old", version="1.0.0"), F.record("old", version="2.0.0")], gap08=gap08)
        ro = w["rollout"]
        ro.plan("old@2.0.0", [Stage("canary", 0, frozenset({"edge-1"})), Stage("half", 50), Stage("all", 100)])
        w["selector"].invalidate()
        s_edge = w["selector"].select(F.request(site=F.site("edge-1")), now=F.NOW)
        s_other = w["selector"].select(F.request(site=F.site("edge-9")), now=F.NOW)
        self.assertEqual((s_edge.version, s_other.version), ("2.0.0", "1.0.0"))
        ro.promote("old@2.0.0", selections=100, refusals=0, binding_failures=0)
        ro.promote("old@2.0.0", selections=100, refusals=0, binding_failures=0)
        ro.promote("old@2.0.0", selections=100, refusals=0, binding_failures=0)
        w["selector"].invalidate()
        self.assertEqual(ro.state("old@2.0.0").state, "completed")
        self.assertEqual(w["selector"].select(F.request(site=F.site("edge-9")), now=F.NOW).version, "2.0.0")
        self.assertEqual([e["event"] for e in gap08.events], ["plan", "promote", "promote", "promote"])

    def test_auto_halt_on_budget_and_rollback(self):
        gap08 = FakeGap08()
        w = F.world(records=[F.record("old", version="1.0.0"), F.record("old", version="2.0.0")], gap08=gap08)
        ro = w["rollout"]
        ro.plan("old@2.0.0", [Stage("canary", 0, frozenset({"edge-1"})), Stage("all", 100)])
        self.assertEqual(ro.promote("old@2.0.0", selections=100, refusals=20, binding_failures=0).state, "halted")
        ro.rollback("old@2.0.0", reason="refusal spike")
        w["selector"].invalidate()
        self.assertEqual(w["selector"].select(F.request(site=F.site("edge-1")), now=F.NOW).version, "1.0.0")

    def test_gap08_down_blocks_promotion_not_rollback(self):
        gap08 = FakeGap08()
        w = F.world(records=[F.record("old", version="2.0.0")], gap08=gap08)
        ro = w["rollout"]
        ro.plan("old@2.0.0", [Stage("canary", 10), Stage("all", 100)])
        gap08.up = False
        code, _ = refusal(lambda: ro.promote("old@2.0.0", selections=10, refusals=0, binding_failures=0))
        self.assertEqual(code, R.DEPENDENCY_UNAVAILABLE.value)
        ro.rollback("old@2.0.0", reason="peer down")
        self.assertEqual(ro.state("old@2.0.0").state, "rolled_back")
        self.assertEqual(ro.pending_announcements[-1]["event"], "rollback")

    def test_cohort_is_deterministic(self):
        from inv28_unikernel_implementations.rollout import cohort
        self.assertEqual([cohort("wl-1")] * 3, [cohort("wl-1") for _ in range(3)])

    def test_plan_validation(self):
        w = F.world()
        for stages in ([], [Stage("a", 50)], [Stage("a", 60), Stage("b", 50), Stage("c", 100)], [Stage("a", 101)]):
            with self.subTest(stages=stages), self.assertRaises(Exception):
                w["rollout"].plan("x@1", stages)


class Matrices(unittest.TestCase):                                             # MC-044, MC-045, MC-071
    ARCHES = ("x86_64", "aarch64", "riscv64")

    def test_cross_architecture_matrix(self):
        recs = [F.record("a", architectures=("x86_64",)), F.record("b", architectures=("aarch64",)),
                F.record("c", architectures=("x86_64", "aarch64"), maturity="beta")]
        w = F.world(records=recs)
        expect = {("production", "x86_64"): "a", ("production", "aarch64"): "b", ("production", "riscv64"): None,
                  ("staging", "x86_64"): "a", ("staging", "aarch64"): "b", ("staging", "riscv64"): None}
        for (env, arch), want in expect.items():
            with self.subTest(env=env, arch=arch):
                if want is None:
                    refusal(lambda: w["selector"].select(F.request(environment=env, architecture=arch), now=F.NOW))
                else:
                    self.assertEqual(w["selector"].select(F.request(environment=env, architecture=arch), now=F.NOW).toolchain, want)

    def test_cross_toolchain_version_matrix_is_consistent(self):
        """Every (toolchain, version, arch, env) cell agrees with an independent oracle."""
        versions = ("1.0.0", "1.1.0")
        recs = []
        for name, mat, arches in (("mirageos", "mature", ("x86_64", "aarch64")), ("unikraft", "beta", ("x86_64",)),
                                  ("nanos", "experimental", ("x86_64",))):
            for v in versions:
                recs.append(F.record(name, version=v, maturity=mat, architectures=arches, languages=("c",)))
        w = F.world(records=recs)
        floor = {"production": 2, "staging": 1, "dev": 0}
        rank = {"experimental": 0, "beta": 1, "mature": 2}
        for env, arch in itertools.product(("production", "staging", "dev"), self.ARCHES):
            ok = [r for r in recs if arch in r.architectures and rank[r.maturity] >= floor[env]]
            with self.subTest(env=env, arch=arch):
                if not ok:
                    refusal(lambda: w["selector"].select(F.request(environment=env, architecture=arch), now=F.NOW))
                    continue
                best = sorted(ok, key=lambda r: (-rank[r.maturity], r.name, [-int(x) for x in r.version.split(".")]))[0]
                got = w["selector"].select(F.request(environment=env, architecture=arch), now=F.NOW)
                self.assertEqual(got.ref, best.ref)

    def test_compatibility_matrix_document_matches_engine(self):
        import json
        m = json.loads((F.__file__ and __import__("pathlib").Path(F.__file__).parent / "ops" / "COMPATIBILITY_MATRIX.json").read_text())
        self.assertEqual(m["schema"], "PK_COMPAT_MATRIX/1")
        for row in m["interfaces"]:
            self.assertIn(row["status"], ("current", "deprecated", "planned"))
        self.assertEqual({r["interface"] for r in m["interfaces"] if r["status"] == "current"},
                         {"PK_TOOLCHAIN/2", "PK_TOOLCHAIN_SELECTION/2", "PK_TOOLCHAIN_REFUSAL/1",
                          "PK_TOOLCHAIN_SELECTION_REQUEST/1", "PK_TOOLCHAIN_TICKET/1", "PK_TOOLCHAIN_POLICY/1",
                          "PK_TOOLCHAIN_REGISTRY/1", "PK_RUNTIME_CERT/1", "PK_ADVISORY_FEED/1"})


if __name__ == "__main__":
    unittest.main()
