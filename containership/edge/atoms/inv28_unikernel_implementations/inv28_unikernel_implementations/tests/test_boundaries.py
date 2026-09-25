"""Boundary and defence-in-depth tests written to kill mutation-testing survivors (MC-054).

Each test names the survivor it kills.  Survivors that are *equivalent* (unreachable because an earlier
check already refuses) are documented in tools/mutation.py::EQUIVALENT instead of being tested."""
import datetime as dt
import unittest
from unittest import mock

from harness import BindingError, F, Inv28Error, Reason, RegistryError, ValidationError
from inv28_unikernel_implementations import certification
from inv28_unikernel_implementations.certification import issue
from inv28_unikernel_implementations.policy import SelectionPolicy, Waiver, default_policy
from inv28_unikernel_implementations.registry import verify_snapshot

R = Reason


class BindingBoundaries(unittest.TestCase):
    def setUp(self):
        self.w = F.world()
        self.res = self.w["selector"].select(F.request(), now=F.NOW)
        self.art = F.artifact_bytes(self.res.ref)

    def test_non_ticket_inputs(self):                       # binding.py:47/48
        for bad in (None, "ticket", [], {"schema": "OTHER/1"}, {**self.res.ticket, "schema": "PK_TOOLCHAIN_TICKET/2"}):
            with self.subTest(bad=bad), self.assertRaises(BindingError) as cm:
                self.w["inv27"].verify(bad, self.art, now=F.NOW)
            self.assertEqual(cm.exception.code, R.BINDING_TAMPERED)

    def test_validity_window_is_inclusive(self):            # binding.py:52
        issued = F.NOW
        expires = F.NOW + dt.timedelta(minutes=15)
        self.assertTrue(self.w["inv27"].verify(self.res.ticket, self.art, now=issued)["verified"])
        self.assertTrue(self.w["inv27"].verify(self.res.ticket, self.art, now=expires)["verified"])
        for t in (issued - dt.timedelta(seconds=1), expires + dt.timedelta(seconds=1)):
            with self.subTest(t=t), self.assertRaises(BindingError):
                self.w["inv27"].verify(self.res.ticket, self.art, now=t)

    def test_ticket_without_artifact_digest(self):          # binding.py:55
        w = F.world(records=[F.record("t", integrity=False)])
        res = w["selector"].select(F.request(environment="dev"), now=F.NOW)
        self.assertEqual(res.ticket["artifact_sha256"], "")
        with self.assertRaises(BindingError) as cm:
            w["inv27"].verify(res.ticket, b"", now=F.NOW)
        self.assertEqual(cm.exception.code, R.BINDING_MISMATCH)

    def test_toolchain_removed_after_selection(self):       # binding.py:63
        reg = self.w["registry"]
        for to in ("deprecated", "retired"):
            reg.transition(self.res.ref, to, actor="operator", expected_revision=reg.revision, reason="x")
        reg.remove(self.res.ref, actor="operator", expected_revision=reg.revision)
        with self.assertRaises(BindingError) as cm:
            self.w["inv27"].verify(self.res.ticket, self.art, now=F.NOW)
        self.assertEqual(cm.exception.code, R.BINDING_MISMATCH)


class CertificationBoundaries(unittest.TestCase):
    def _doc(self, ring, **kw):
        base = dict(toolchain="t", version="1", artifact_sha256="a" * 64, architecture="x86_64",
                    issued_at="2026-09-01T00:00:00Z", expires_at="2026-10-01T00:00:00Z")
        base.update(kw)
        return issue(ring, **base)

    def test_validity_window_inclusive(self):               # certification.py:58
        w = F.world()
        c = w["certs"].ingest(self._doc(w["ring"]))
        start = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
        end = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc)
        self.assertTrue(c.valid_at(start) and c.valid_at(end))
        self.assertFalse(c.valid_at(start - dt.timedelta(seconds=1)) or c.valid_at(end + dt.timedelta(seconds=1)))

    def test_correctly_signed_wrong_schema_refused(self):   # certification.py:85/86
        w = F.world()
        body = {k: v for k, v in self._doc(w["ring"]).items() if k != "signature"}
        for schema in ("PK_RUNTIME_CERT/2", None):
            with self.subTest(schema=schema):
                b = {**body, "schema": schema}
                with self.assertRaises(ValidationError):
                    w["certs"].ingest({**b, "signature": w["ring"].sign("gap15", b)})
        with self.assertRaises(ValidationError):
            w["certs"].ingest(["not", "a", "dict"])

    def test_zero_length_window_refused(self):               # certification.py:93
        w = F.world()
        with self.assertRaises(ValidationError):
            w["certs"].ingest(self._doc(w["ring"], issued_at="2026-09-01T00:00:00Z", expires_at="2026-09-01T00:00:00Z"))
        w["certs"].ingest(self._doc(w["ring"], issued_at="2026-09-01T00:00:00Z", expires_at="2026-09-01T00:00:01Z"))

    def test_missing_field_refused(self):                    # certification.py:104
        w = F.world()
        body = {k: v for k, v in self._doc(w["ring"]).items() if k not in ("signature", "issuer")}
        with self.assertRaises(ValidationError) as cm:
            w["certs"].ingest({**body, "signature": w["ring"].sign("gap15", body)})
        self.assertEqual(cm.exception.code, R.CERTIFICATION_INVALID)

    def test_store_capacity(self):                           # certification.py:106/107
        w = F.world(with_certs=False)
        with mock.patch.object(certification, "MAX_CERTS", 2):
            w["certs"].ingest(self._doc(w["ring"], version="1"))
            w["certs"].ingest(self._doc(w["ring"], version="2"))
            w["certs"].ingest(self._doc(w["ring"], version="2"))           # re-ingest of a held id is fine
            with self.assertRaises(Inv28Error) as cm:
                w["certs"].ingest(self._doc(w["ring"], version="3"))
            self.assertEqual(cm.exception.code, R.REGISTRY_FULL)
            self.assertEqual(len(w["certs"]), 2)


class SnapshotAndPolicyBoundaries(unittest.TestCase):
    def test_malformed_snapshots(self):                      # registry.py:273/279
        w = F.world()
        good = w["registry"].snapshot()
        body = {k: v for k, v in good.items() if k != "signature"}
        for mutate in ({"revision": "4"}, {"entries": {}}, {"schema": "PK_TOOLCHAIN_REGISTRY/2"}):
            b = {**body, **mutate}
            with self.subTest(mutate=mutate), self.assertRaises(RegistryError):
                verify_snapshot(w["ring"], {**b, "signature": w["ring"].sign("registry", b)})
        for bad in (None, [], "snap"):
            with self.subTest(bad=bad), self.assertRaises(RegistryError):
                verify_snapshot(w["ring"], bad)

    def test_head_must_match_last_event(self):               # registry.py:292
        w = F.world()
        body = {k: v for k, v in w["registry"].snapshot().items() if k != "signature"}
        for mutate in ({"head_digest": "0" * 64}, {"history": body["history"][:-1]},
                       {"history": body["history"][:-1] + [{**body["history"][-1], "revision": 99}]}):
            b = {**body, **mutate}
            with self.subTest(keys=list(mutate)), self.assertRaises(RegistryError):
                verify_snapshot(w["ring"], {**b, "signature": w["ring"].sign("registry", b)})
        empty = F.world(records=[])["registry"]
        verify_snapshot(empty._ring, empty.snapshot())      # revision 0 needs no history

    def test_waiver_codes_must_be_non_empty_subset(self):   # policy.py:105
        for codes in (frozenset(), frozenset({R.MATURITY_BELOW_POLICY.value, R.EOL.value})):
            with self.subTest(codes=codes), self.assertRaises(ValidationError):
                Waiver("W", "t@1", codes, frozenset({"production"}), "o", "a", "r", "2027-01-01T00:00:00Z")
        Waiver("W", "t@1", frozenset({R.REVIEW_STALE.value}), frozenset({"production"}), "o", "a", "r",
               "2027-01-01T00:00:00Z")
        from inv28_unikernel_implementations.policy import WAIVABLE
        Waiver("W", "t@1", WAIVABLE, frozenset({"production"}), "o", "a", "r", "2027-01-01T00:00:00Z")

    def test_policy_revision_validation(self):              # policy.py:151
        envs = default_policy().environments
        for rev in (0, -1, "1", 1.0, True):
            with self.subTest(rev=rev), self.assertRaises(ValidationError):
                SelectionPolicy("p", rev, envs)
        self.assertEqual(SelectionPolicy("p", 1, envs).revision, 1)


class ErrorsShape(unittest.TestCase):
    def test_error_to_dict_is_plain(self):
        e = Inv28Error(R.REGISTRY_FULL, "x", codes=[R.EOL], n=1)
        d = e.to_dict()
        self.assertEqual(d["code"], "REG_CAPACITY_EXCEEDED")
        self.assertEqual(d["detail"]["codes"], ["TC_END_OF_LIFE"])
        import json
        json.dumps(d)


if __name__ == "__main__":
    unittest.main()


class MoreBoundaries(unittest.TestCase):
    """Second round of survivors from the full (unsampled) mutation run."""

    def test_environment_rule_validation_matrix(self):                     # policy.py:54-65
        from inv28_unikernel_implementations.policy import EnvironmentRule
        bad = [{"min_maturity": "stable"}, {"min_response_sla_hours": -1}, {"min_response_sla_hours": "24"},
               {"advisory_block_severity": "urgent"}, {"allowed_catalog_status": frozenset()},
               {"allowed_catalog_status": frozenset({"official"})}, {"allow_deprecated": "no"}]
        for kw in bad:
            with self.subTest(kw=kw), self.assertRaises(ValidationError):
                EnvironmentRule(**{"production": False, **kw})
        ok = EnvironmentRule(production=False, min_response_sla_hours=0,
                             allowed_catalog_status=frozenset({"supported", "example", "unregistered"}))
        self.assertEqual(len(ok.allowed_catalog_status), 3)

    def test_waiver_ref_status_and_expiry_boundary(self):                  # policy.py:103/114/121
        mk = lambda **kw: Waiver(**{"id": "W", "toolchain_ref": "t@1", "codes": frozenset({R.REVIEW_STALE.value}),  # noqa: E731
                                    "environments": frozenset({"production"}), "owner": "o", "approver": "a",
                                    "reason": "r", "expires": "2026-09-23T12:00:00Z", **kw})
        for kw in ({"toolchain_ref": "t"}, {"status": "maybe"}):
            with self.subTest(kw=kw), self.assertRaises(ValidationError):
                mk(**kw)
        w = mk()
        self.assertTrue(w.active(F.NOW))                                     # exactly at expiry: still active
        self.assertFalse(w.active(F.NOW + dt.timedelta(seconds=1)))

    def test_policy_structure_validation(self):                             # policy.py:154/158/163
        envs = default_policy().environments
        w = Waiver("W", "t@1", frozenset({R.REVIEW_STALE.value}), frozenset({"production"}), "o", "a", "r",
                   "2027-01-01T00:00:00Z")
        for args in (("p", 1, {}), ("p", 1, {"production": {"min_maturity": "mature"}}), ("p", 1, envs, {}, (w, w))):
            with self.subTest(n=len(args)), self.assertRaises(ValidationError):
                SelectionPolicy(*args)

    def _signed(self, w, body):
        return {**body, "signature": w["ring"].sign("registry", body)}

    def test_snapshot_capacity_duplicates_state_and_invalid_entry(self):   # registry.py:280-290
        from inv28_unikernel_implementations import registry as regmod
        w = F.world()
        body = {k: v for k, v in w["registry"].snapshot().items() if k != "signature"}
        with mock.patch.object(regmod, "MAX_ENTRIES", 4):
            verify_snapshot(w["ring"], self._signed(w, body))              # exactly at capacity: fine
        with mock.patch.object(regmod, "MAX_ENTRIES", 3), self.assertRaises(RegistryError) as cm:
            verify_snapshot(w["ring"], self._signed(w, body))
        self.assertEqual(cm.exception.code, R.REGISTRY_FULL)
        cases = {"dup": {**body, "entries": body["entries"] + body["entries"][:1]},
                 "state": {**body, "state_digest": "0" * 64},
                 "invalid": {**body, "entries": [dict(body["entries"][0], maturity="stable")] + body["entries"][1:]}}
        for name, b in cases.items():
            with self.subTest(name=name), self.assertRaises(RegistryError):
                verify_snapshot(w["ring"], self._signed(w, b))

    def test_register_type_and_reload_same_revision(self):                 # registry.py:120/196
        from inv28_unikernel_implementations.registry import Registry
        w = F.world()
        with self.assertRaises(ValidationError):
            w["registry"].register(F.record("x").to_dict(), actor="operator", expected_revision=w["registry"].revision)
        snap = w["registry"].snapshot()
        fresh = Registry(w["ring"])
        fresh.load(snap)
        fresh.load(snap)                                                   # same revision reload is idempotent
        self.assertEqual(fresh.revision, w["registry"].revision)
        w["registry"].register(F.record("y"), actor="operator", expected_revision=w["registry"].revision)
        fresh.load(w["registry"].snapshot())
        fresh.load(snap, allow_older=True)                                 # explicit operator override only
        self.assertEqual(fresh.revision, snap["revision"])

    def test_token_and_set_bounds_exact(self):                             # model.py:57/63/65
        from inv28_unikernel_implementations.model import MAX_SET_SIZE, MAX_TOKEN_LEN, token, token_set
        self.assertEqual(len(token("a" * MAX_TOKEN_LEN, "t")), MAX_TOKEN_LEN)
        with self.assertRaises(ValidationError):
            token("a" * (MAX_TOKEN_LEN + 1), "t")
        self.assertEqual(len(token_set([f"f{i}" for i in range(MAX_SET_SIZE)], "s")), MAX_SET_SIZE)
        for bad in (b"ocaml", "ocaml", 5, None, {"a": 1}.keys()):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                token_set(bad, "s")

    def test_select_type_cache_bound_and_candidate_limit(self):            # selection.py:231/250/301
        from inv28_unikernel_implementations import selection as selmod
        w = F.world()
        with self.assertRaises(ValidationError):
            w["selector"].select(F.request().to_dict(), now=F.NOW)
        with mock.patch.object(selmod, "CACHE_SIZE", 3):
            for i in range(5):
                w["selector"].select(F.request(workload_id=f"c{i}"), now=F.NOW)
            self.assertEqual(len(w["selector"]._cache), 3)
        with mock.patch.object(selmod, "MAX_CANDIDATES", 3):
            w["selector"].invalidate()
            with self.assertRaises(Inv28Error) as cm:
                w["selector"].select(F.request(workload_id="z"), now=F.NOW)
            self.assertEqual(cm.exception.code, R.LIMIT_EXCEEDED)
        with mock.patch.object(selmod, "MAX_CANDIDATES", 4):
            w["selector"].select(F.request(workload_id="z2"), now=F.NOW)

    def test_result_without_dependencies_in_dev(self):                      # selection.py:356/357
        w = F.world()
        w["selector"].certifications = None
        w["selector"].advisories = None
        w["selector"].invalidate()
        r = w["selector"].select(F.request(environment="dev"), now=F.NOW)
        self.assertEqual((r.certification_snapshot, r.advisory_snapshot, r.certification_id), ("", "", ""))

    def test_site_allow_list_only(self):                                    # selection.py:373
        from inv28_unikernel_implementations.policy import SitePolicy
        base = default_policy()
        pol = SelectionPolicy(base.policy_id, 2, base.environments, {"edge-1": SitePolicy(frozenset(), frozenset({"t"}))})
        w = F.world(records=[F.record("t"), F.record("u")], policy=pol)
        self.assertEqual(w["selector"].select(F.request(site=F.site()), now=F.NOW).toolchain, "t")
        pol2 = SelectionPolicy(base.policy_id, 2, base.environments, {"edge-1": SitePolicy(frozenset({"t"}))})
        w2 = F.world(records=[F.record("t"), F.record("u")], policy=pol2)
        self.assertEqual(w2["selector"].select(F.request(site=F.site()), now=F.NOW).toolchain, "u")

    def test_sla_boundary(self):                                            # selection.py:409
        from inv28_unikernel_implementations.policy import EnvironmentRule
        base = default_policy()
        pol = SelectionPolicy(base.policy_id, 2, {**base.environments, "production": EnvironmentRule(min_response_sla_hours=24)})
        self.assertEqual(F.world(records=[F.record("t", sla=24)], policy=pol)["selector"].select(F.request(), now=F.NOW).toolchain, "t")
        from harness import refusal
        refusal(lambda: F.world(records=[F.record("t", sla=25)], policy=pol)["selector"].select(F.request(), now=F.NOW))
        w_nc = F.world(records=[F.record("t", contact="")], policy=pol)
        refusal(lambda: w_nc["selector"].select(F.request(environment="staging"), now=F.NOW))

    def test_site_hypervisor_with_requested_hypervisor(self):               # selection.py:400
        from harness import codes_for, refusal
        w = F.world(records=[F.record("t", hypervisors=("qemu-kvm", "xen"))])
        site = F.site(hypervisors=("qemu-kvm",))
        _, ref = refusal(lambda: w["selector"].select(F.request(site=site, hypervisor="xen"), now=F.NOW))
        self.assertIn(R.SITE_HYPERVISOR_UNSUPPORTED.value, codes_for(ref, "t@1.0.0-fixture"))
        self.assertEqual(w["selector"].select(F.request(site=site, hypervisor="qemu-kvm"), now=F.NOW).toolchain, "t")


class LayeredSnapshotChecks(unittest.TestCase):
    """Each snapshot check must hold on its own, not only because a later layer also fails."""

    def _forge(self, w, body):
        from inv28_unikernel_implementations.model import ToolchainRecord
        from inv28_unikernel_implementations.registry import chain, state_digest
        recs = [ToolchainRecord.from_dict(e) for e in body["entries"]]
        b = dict(body)
        b["state_digest"] = state_digest(recs)
        b["head_digest"] = chain(b["prev_digest"], b["state_digest"], b["history"][-1])
        return {**b, "signature": w["ring"].sign("registry", b)}

    def test_duplicates_refused_even_with_consistent_digests(self):        # registry.py:284
        w = F.world()
        body = {k: v for k, v in w["registry"].snapshot().items() if k != "signature"}
        with self.assertRaises(RegistryError) as cm:
            verify_snapshot(w["ring"], self._forge(w, {**body, "entries": body["entries"] + body["entries"][:1]}))
        self.assertEqual(cm.exception.code, R.REGISTRY_DUPLICATE)

    def test_state_mismatch_refused_even_with_consistent_head(self):       # registry.py:290
        from inv28_unikernel_implementations.registry import chain
        w = F.world()
        body = {k: v for k, v in w["registry"].snapshot().items() if k != "signature"}
        b = {**body, "state_digest": "0" * 64}
        b["head_digest"] = chain(b["prev_digest"], b["state_digest"], b["history"][-1])
        with self.assertRaises(RegistryError) as cm:
            verify_snapshot(w["ring"], {**b, "signature": w["ring"].sign("registry", b)})
        self.assertIn("state digest", str(cm.exception))

    def test_contact_without_sla_fails_sla_policy(self):                   # selection.py:409
        from harness import codes_for, refusal
        from inv28_unikernel_implementations.policy import EnvironmentRule
        base = default_policy()
        pol = SelectionPolicy(base.policy_id, 2, {**base.environments, "production": EnvironmentRule(min_response_sla_hours=24)})
        w = F.world(records=[F.record("t", sla=0)], policy=pol)
        _, ref = refusal(lambda: w["selector"].select(F.request(), now=F.NOW))
        self.assertIn(R.SECURITY_RESPONSE_INADEQUATE.value, codes_for(ref, "t@1.0.0-fixture"))
