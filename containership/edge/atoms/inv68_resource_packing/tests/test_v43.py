"""INV-68 4.3.0 tests: missing-component implementations MC-06..MC-37.

Every test is hermetic (temp dirs, injected clocks, no network, no pk_core).
Test names carry the MC id they evidence; ``tools/build_ledger.py`` reads them.
"""
from __future__ import annotations

import io
import json
import math
import pathlib
import random
import sys
import tempfile
import threading
import time
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv68_resource_packing import packing as rp  # noqa: E402
from inv68_resource_packing.adjacent import (SchedulerClient, k8s_translate, power_overlay,  # noqa: E402
                                             split_accelerated)
from inv68_resource_packing.audit import AuditChainBroken, AuditLog, AuditUnavailable  # noqa: E402
from inv68_resource_packing.auth import Authorizer, mint  # noqa: E402
from inv68_resource_packing.config import (ConfigStore, PackingConfig, compose, defaults, plain,  # noqa: E402
                                           validate)
from inv68_resource_packing.errors import REGISTRY, PackError, registry_document  # noqa: E402
from inv68_resource_packing.explain import render_text  # noqa: E402
from inv68_resource_packing.redaction import REDACTED, redact  # noqa: E402
from inv68_resource_packing.resilience import (Admission, CircuitBreaker, Deadline, backoff_schedule,  # noqa: E402
                                               should_retry)
from inv68_resource_packing.service import PackingService  # noqa: E402
from inv68_resource_packing.telemetry import (Metrics, StructuredLogger, child_traceparent,  # noqa: E402
                                              parse_traceparent)

KEY = {"k1": bytes(range(32))}


def reference_pack_420(workloads, host_cpu, host_mem, headroom=0.1):
    """The 4.2.0 first-fit-decreasing loop, preserved verbatim in behaviour for differential testing."""
    norm = rp._normalize_workloads(workloads)
    limits = rp.effective_capacity(host_cpu, host_mem, headroom)
    order = sorted(norm, key=lambda i: (-max(i["cpu"] / limits["cpu"], i["mem"] / limits["mem"]), i["name"]))
    hosts, out = [], []
    for item in order:
        if any(item[d] > limits[d] + 1e-9 for d in ("cpu", "mem")):
            out.append((item["name"], None))
            continue
        target = next((h for h in hosts if h.fits(item, headroom)), None)
        if target is None:
            target = rp.Host(f"h{len(hosts)}", host_cpu, host_mem)
            hosts.append(target)
        target.place(item, headroom)
        out.append((item["name"], target.name))
    return out


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def token(kind="workload-scheduler", caps=("pack:submit",), tenants=("t1",), sub="sch01", **kw):
    return mint(KEY["k1"], kid="k1", sub=sub, kind=kind, tenants=tenants, caps=caps, **kw)


def make_service(tmp, cfg=None, **kw):
    audit = AuditLog(pathlib.Path(tmp) / "audit.jsonl")
    store = ConfigStore(pathlib.Path(tmp) / "cfg", audit=audit)
    store.activate(cfg or defaults(), actor="bootstrap", epoch=1)
    return PackingService(store, Authorizer(KEY), audit, **kw), store, audit


def req(n=5, tenant="t1", **extra):
    work = [{"name": f"w{i}", "cpu": 1 + (i % 3), "mem": 2 + (i % 5)} for i in range(n)]
    return dict({"tenant": tenant, "host_capacity": {"cpu": 16, "mem": 64}, "workloads": work}, **extra)


class EnginePerformanceFix(unittest.TestCase):
    def test_MC22_differential_against_420_reference(self):
        rng = random.Random(68)
        for trial in range(300):
            n = rng.randint(0, 120)
            work = [{"name": f"w{i}", "cpu": rng.choice([0, .1, .5, 1, 2, 4, 9, 30]),
                     "mem": rng.choice([0, .25, 1, 2, 8, 16, 40, 70])} for i in range(n)]
            h = rng.choice([0.0, 0.1, 0.25, 0.5])
            new = rp.pack_detailed(work, 16, 64, h)
            self.assertEqual([(d.workload, d.host) for d in new.decisions], reference_pack_420(work, 16, 64, h),
                             f"trial {trial}")

    def test_MC22_1000_workloads_under_declared_p99(self):
        rng = random.Random(7)
        work = [{"name": f"w{i}", "cpu": rng.choice([.25, .5, 1, 2, 4]), "mem": rng.choice([.5, 1, 2, 4, 8, 16])}
                for i in range(1000)]
        rp.pack_detailed(work, 16, 64)
        times = []
        for _ in range(15):
            t = time.perf_counter()
            rp.pack_detailed(work, 16, 64)
            times.append(time.perf_counter() - t)
        self.assertLess(max(times) * 1000, 100 * 3, "3x SLO guard band for shared CI hosts; bench is authoritative")

    def test_MC30_quality_against_exact_optimum_on_small_inputs(self):
        """Brute-force the optimal host count for <= 7 workloads; FFD must stay within 1.5*OPT + 1."""
        import itertools
        rng = random.Random(4242)
        worst = 1.0
        for _ in range(150):
            n = rng.randint(1, 7)
            work = [{"name": f"w{i}", "cpu": rng.choice([1, 3, 6, 9, 12]), "mem": rng.choice([4, 10, 20, 30, 40])}
                    for i in range(n)]
            lim = rp.effective_capacity(16, 64, 0.1)
            best = n
            for labels in itertools.product(range(n), repeat=n):
                if labels[0] != 0 or max(labels) + 1 >= best:
                    continue
                ok = all(sum(w["cpu"] for w, l in zip(work, labels) if l == b) <= lim["cpu"] + 1e-9 and
                         sum(w["mem"] for w, l in zip(work, labels) if l == b) <= lim["mem"] + 1e-9
                         for b in range(max(labels) + 1))
                if ok:
                    best = max(labels) + 1
            ffd = len(rp.pack_detailed(work, 16, 64).hosts)
            self.assertGreaterEqual(ffd, best)
            self.assertLessEqual(ffd, 1.5 * best + 1)
            worst = max(worst, ffd / best)
        self.assertLess(worst, 2.0)

    def test_MC22_worst_case_one_per_host_is_not_quadratic(self):
        work = [{"name": f"w{i}", "cpu": 12, "mem": 1} for i in range(3000)]
        t = time.perf_counter()
        res = rp.pack_detailed(work, 16, 64)
        self.assertEqual(len(res.hosts), 3000)
        self.assertLess(time.perf_counter() - t, 1.0)

    def test_MC10_configurable_cpu_overcommit_memory_fixed(self):
        self.assertEqual(rp.effective_capacity(10, 10, 0, cpu_overcommit=2.0), {"cpu": 20.0, "mem": 10.0})
        for bad in (0.5, 4.5, float("nan"), True):
            with self.assertRaises((ValueError, TypeError)):
                rp.effective_capacity(10, 10, 0, cpu_overcommit=bad)
        hosts, _ = rp.pack([{"name": "a", "cpu": 19, "mem": 1}], 10, 10, 0, cpu_overcommit=2.0)
        self.assertEqual(rp.fragmentation(hosts, 0, cpu_overcommit=2.0), {"cpu": 1.0, "mem": 9.0})


class FuzzFindingRegressions(unittest.TestCase):
    def test_MC30_lower_bound_overflow_is_a_value_error_not_overflow(self):
        # 4.2.0: OverflowError from math.ceil escaped the TypeError/ValueError contract
        with self.assertRaises(ValueError):
            rp.lower_bound([{"name": "a", "cpu": 1e308, "mem": 1}], 0.01, 64)

    def test_MC30_placeable_only_lower_bound(self):
        work = [{"name": "a", "cpu": 1, "mem": 1}, {"name": "whale", "cpu": 1, "mem": 1000}]
        self.assertEqual(rp.lower_bound(work, 16, 64), 18)  # 4.2.0 semantics kept by default
        self.assertEqual(rp.lower_bound(work, 16, 64, placeable_only=True), 1)

    def test_MC30_out_of_range_json_numbers_are_invalid_not_internal(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, _, _ = make_service(tmp)
            for raw in ('{"tenant":"t1","host_capacity":{"cpu":1e999,"mem":1},"workloads":[]}',
                        {"tenant": "t1", "host_capacity": {"cpu": float("inf"), "mem": 1}, "workloads": []}):
                with self.assertRaises(PackError) as cm:
                    svc.pack(raw, token())
                self.assertEqual(cm.exception.code, "INVALID_REQUEST")


class ErrorsAndRedaction(unittest.TestCase):
    def test_MC07_registry_is_complete_and_serialisable(self):
        doc = registry_document()
        self.assertEqual(len(doc["codes"]), len(REGISTRY))
        for spec in REGISTRY.values():
            self.assertIn(spec.outcome, doc["outcomes"])
        err = PackError("OVERLOADED", details={"x": 1}, correlation_id="c1").to_dict()
        self.assertEqual(err["schema"], "PK_PACK_ERROR/1")
        self.assertTrue(err["retryable"])
        with self.assertRaises(ValueError):
            PackError("NOPE")

    def test_MC11_error_messages_and_details_are_redacted(self):
        err = PackError("INVALID_REQUEST", "bad token Bearer abcdefghijklmnopqrstuvwxyz0123",
                        details={"password": "hunter22", "ok": "fine"})
        self.assertNotIn("abcdefghijklmnop", err.message)
        self.assertEqual(err.details["password"], REDACTED)
        self.assertEqual(err.details["ok"], "fine")

    def test_MC11_debug_level_does_not_bypass_redaction(self):
        buf = io.StringIO()
        StructuredLogger(buf, level="debug").log("debug", "x", password="hunter22", dsn="https://u:pw@h/x")
        self.assertNotIn("hunter22", buf.getvalue())
        self.assertNotIn("u:pw@", buf.getvalue())

    def test_MC11_structured_logs_redact_and_escape_injection(self):
        buf = io.StringIO()
        StructuredLogger(buf).log("info", "x", tenant="t\nFAKE", token="ghp_" + "a" * 40, note="line1\nline2")
        line = buf.getvalue()
        self.assertEqual(line.count("\n"), 1)
        self.assertNotIn("a" * 40, line)


class ConfigLifecycle(unittest.TestCase):
    def test_MC10_defaults_are_valid_and_secure(self):
        cfg = defaults()
        self.assertEqual(cfg.headroom, 0.1)
        self.assertEqual(cfg.cpu_overcommit, 1.5)
        self.assertEqual(validate(plain(cfg.document)), [])

    def test_MC10_unknown_keys_and_memory_overcommit_rejected(self):
        doc = plain(defaults().document)
        doc["mem_overcommit"] = 1.2
        with self.assertRaises(PackError) as cm:
            PackingConfig.from_document(doc)
        self.assertEqual(cm.exception.code, "CONFIG_INVALID")
        for field, value in (("headroom", 1.0), ("headroom", float("inf")), ("cpu_overcommit", 9)):
            d = plain(defaults().document)
            d[field] = value
            self.assertTrue(validate(d), field)

    def test_MC11_inline_secret_in_config_refused(self):
        doc = plain(defaults().document)
        doc["provenance"]["change_ref"] = "postgres://admin:hunter2@db/x"
        with self.assertRaises(PackError) as cm:
            PackingConfig.from_document(doc)
        self.assertEqual(cm.exception.code, "SECRET_IN_CONFIG")

    def test_MC10_overlays_compose_in_order_and_record_layers(self):
        cfg = compose(defaults().document, ("environment:prod", {"headroom": 0.2, "limits": {"max_queue": 4}}),
                      ("site:edge-7", {"limits": {"max_queue": 2}}))
        self.assertEqual(cfg.headroom, 0.2)
        self.assertEqual(cfg.limit("max_queue"), 2)
        self.assertEqual(list(cfg.document["provenance"]["layers"]),
                         ["base:0.0.0-defaults", "environment:prod", "site:edge-7"])
        with self.assertRaises(PackError):
            compose(defaults().document, ("bad", {"schema": "x"}))

    def test_MC10_snapshot_is_immutable(self):
        cfg = defaults()
        with self.assertRaises(TypeError):
            cfg.document["headroom"] = 0.5  # type: ignore[index]
        with self.assertRaises(TypeError):
            cfg.document["limits"]["max_queue"] = 1  # type: ignore[index]

    def test_MC10_activate_cas_rollback_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(pathlib.Path(tmp) / "a.jsonl")
            store = ConfigStore(tmp, audit=audit)
            a = defaults()
            b = compose(a.document, ("env:x", {"headroom": 0.3, "config_version": "1.0.0"}))
            store.activate(a, actor="op", epoch=1)
            with self.assertRaises(PackError) as cm:
                store.activate(b, actor="op", epoch=1, expected_digest="0" * 64)
            self.assertEqual(cm.exception.code, "CONFIG_CONFLICT")
            store.activate(b, actor="op", epoch=1, expected_digest=a.digest)
            self.assertEqual(store.active().digest, b.digest)
            store.rollback(actor="op", epoch=1)
            self.assertEqual(store.active().digest, a.digest)
            self.assertEqual([e["reason"] for e in store.history()], ["activate", "activate", "rollback"])
            self.assertEqual(audit.verify(), 6)

    def test_MC10_activation_records_config_diff(self):
        from inv68_resource_packing.config import diff
        a = defaults()
        b = compose(a.document, ("x", {"headroom": 0.2, "limits": {"max_queue": 4}}))
        paths = [c["path"] for c in diff(a.document, b.document)]
        self.assertIn("headroom", paths)
        self.assertIn("limits.max_queue", paths)
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(pathlib.Path(tmp) / "a.jsonl")
            store = ConfigStore(pathlib.Path(tmp) / "c", audit=audit)
            store.activate(a, actor="op", epoch=1)
            store.activate(b, actor="op", epoch=1)
            self.assertIn("headroom", store.history()[-1]["changed_paths"])
            self.assertTrue(any(r["detail"].get("change_count") for r in audit.records()))

    def test_MC20_unfreeze_requires_recovery_criteria(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, store, audit = make_service(tmp)
            op = lambda: token(kind="operator", caps=("control:freeze",), tenants=("*",), sub="alice")
            svc.freeze(op(), "drill")
            path = pathlib.Path(tmp) / "audit.jsonl"
            lines = path.read_text().splitlines()
            rec = json.loads(lines[0])
            rec["actor"] = "mallory"
            lines[0] = json.dumps(rec, sort_keys=True)
            path.write_text("\n".join(lines) + "\n")
            with self.assertRaises(PackError) as cm:
                svc.unfreeze(op(), "should refuse")
            self.assertEqual(cm.exception.code, "AUDIT_UNAVAILABLE")
            self.assertEqual(svc.status()["state"], "frozen")

    def test_MC19_stale_epoch_is_fenced(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConfigStore(tmp)
            store.activate(defaults(), actor="c2", epoch=5)
            with self.assertRaises(PackError) as cm:
                store.activate(defaults(), actor="c1", epoch=4)
            self.assertEqual(cm.exception.code, "STALE_EPOCH")

    def test_MC19_crash_recovery_falls_back_to_last_intact_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConfigStore(tmp)
            a = defaults()
            b = compose(a.document, ("env", {"headroom": 0.3}))
            store.activate(a, actor="op", epoch=1)
            store.activate(b, actor="op", epoch=1)
            (pathlib.Path(tmp) / "snapshots" / f"{b.digest}.json").write_text("{corrupt")
            with open(pathlib.Path(tmp) / "journal.jsonl", "a") as fh:
                fh.write('{"torn": ')
            fresh = ConfigStore(tmp)
            self.assertEqual(fresh.active().digest, a.digest)
            self.assertEqual(fresh.recovered_from, a.digest)

    def test_MC37_backup_restore_round_trip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConfigStore(pathlib.Path(tmp) / "src")
            store.activate(defaults(), actor="op", epoch=1)
            bundle = json.loads(json.dumps(store.export()))
            restored = ConfigStore.restore(pathlib.Path(tmp) / "dst", bundle)
            self.assertEqual(restored.active().digest, store.active().digest)
            dig = next(iter(bundle["snapshots"]))
            bundle["snapshots"][dig]["headroom"] = 0.5
            with self.assertRaises(PackError):
                ConfigStore.restore(pathlib.Path(tmp) / "dst2", bundle)

    def test_MC15_config_change_fails_closed_without_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            def broken(_p):
                raise OSError("disk gone")
            audit = AuditLog(pathlib.Path(tmp) / "a.jsonl", opener=broken, buffer_limit=0)
            store = ConfigStore(pathlib.Path(tmp) / "c", audit=audit)
            with self.assertRaises(PackError) as cm:
                store.activate(defaults(), actor="op", epoch=1)
            self.assertEqual(cm.exception.code, "AUDIT_UNAVAILABLE")
            self.assertIsNone(store.active())


class AuthBoundary(unittest.TestCase):
    def test_MC06_valid_token_authenticates_with_ceiling(self):
        az = Authorizer(KEY)
        p = az.authenticate(token(caps=("pack:submit", "config:activate")))
        self.assertIn("pack:submit", p.capabilities)
        self.assertNotIn("config:activate", p.capabilities)  # kind ceiling
        with self.assertRaises(PackError) as cm:
            az.require(p, "config:activate")
        self.assertEqual(cm.exception.code, "FORBIDDEN")

    def test_MC06_forged_expired_replayed_and_wildcard_tokens_refused(self):
        clock = Clock(time.time())
        az = Authorizer(KEY, clock=clock)
        good = token(now=clock.t)
        head, body, sig = good.split(".")
        forged = f"{head}.{body}.{'A' * len(sig)}"
        cases = {
            "forged": forged,
            "wrong_key": mint(b"z" * 32, kid="k1", sub="s", kind="operator", tenants=["*"], caps=["status:read"]),
            "unknown_kid": mint(KEY["k1"], kid="k9", sub="s", kind="operator", tenants=["*"], caps=[]),
            "expired": token(now=clock.t - 4000, ttl_s=60),
            "ttl_too_long": token(now=clock.t, ttl_s=7200),
            "wildcard_scheduler": token(tenants=("*",), now=clock.t),
            "bad_kind": mint(KEY["k1"], kid="k1", sub="s", kind="root", tenants=["t1"], caps=[], now=clock.t),
            "garbage": "v1.???.???",
            "not_str": None,
            "huge": "v1." + "a" * 5000 + ".x",
        }
        for name, tok in cases.items():
            with self.assertRaises(PackError, msg=name) as cm:
                az.authenticate(tok)
            self.assertEqual(cm.exception.code, "UNAUTHENTICATED", name)
        az.authenticate(good)
        with self.assertRaises(PackError) as cm:
            az.authenticate(good)
        self.assertEqual(cm.exception.code, "REPLAY_DETECTED")

    def test_MC16_confused_deputy_scheduler_cannot_reach_control_plane(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, store, _ = make_service(tmp)
            sched = token(caps=("pack:submit", "config:activate", "control:freeze"))
            for call in (lambda: svc.activate_config(sched, compose(defaults().document, ("x", {"headroom": 0.5}))),
                         lambda: svc.freeze(token(caps=("control:freeze",)), "x"),
                         lambda: svc.rollback_config(token(caps=("config:rollback",)))):
                with self.assertRaises(PackError) as cm:
                    call()
                self.assertEqual(cm.exception.code, "FORBIDDEN")
            self.assertEqual(store.active().headroom, 0.1)

    def test_MC14_key_rotation_without_interruption(self):
        keys = {"old": b"o" * 32}
        az = Authorizer(keys)
        az.authenticate(mint(keys["old"], kid="old", sub="s", kind="workload-scheduler", tenants=["t1"], caps=["pack:submit"]))
        keys["new"] = b"n" * 32  # step 1: add new kid (both valid)
        az.authenticate(mint(keys["old"], kid="old", sub="s", kind="workload-scheduler", tenants=["t1"], caps=["pack:submit"]))
        az.authenticate(mint(keys["new"], kid="new", sub="s", kind="workload-scheduler", tenants=["t1"], caps=["pack:submit"]))
        del keys["old"]  # step 3: retire old kid
        with self.assertRaises(PackError):
            az.authenticate(mint(b"o" * 32, kid="old", sub="s", kind="workload-scheduler", tenants=["t1"], caps=["pack:submit"]))
        az.authenticate(mint(keys["new"], kid="new", sub="s", kind="workload-scheduler", tenants=["t1"], caps=["pack:submit"]))

    def test_MC06_tenant_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, _, _ = make_service(tmp)
            with self.assertRaises(PackError) as cm:
                svc.pack(req(tenant="t2"), token())
            self.assertEqual(cm.exception.code, "FORBIDDEN")
            out = svc.pack(req(tenant="t1"), token())
            self.assertEqual(out["tenant"], "t1")


class ServiceBoundary(unittest.TestCase):
    def test_MC07_success_response_shape_and_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, _, audit = make_service(tmp)
            out = svc.pack(req(lineage={"app_release": "shop@1.4.2", "cluster": "edge-7", "junk": "x"}), token(),
                           traceparent="00-" + "a" * 32 + "-" + "b" * 16 + "-01")
            self.assertEqual(out["outcome"], "success")
            self.assertTrue(out["traceparent"].startswith("00-" + "a" * 32))
            self.assertEqual(out["explain"]["lineage"], {"app_release": "shop@1.4.2", "cluster": "edge-7"})
            self.assertEqual(out["config"]["config_digest"], svc.config.digest)
            self.assertGreaterEqual(audit.verify(), 2)

    def test_MC07_protocol_negotiation_and_420_compat(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, _, _ = make_service(tmp)
            svc.pack(req(), token())  # 4.2.0 shape: no protocol field
            svc.pack(req(protocol=["PK_PACK/2", "PK_PACK/1"]), token())
            with self.assertRaises(PackError) as cm:
                svc.pack(req(protocol=["PK_PACK/2"]), token())
            self.assertEqual(cm.exception.code, "UNSUPPORTED_PROTOCOL")

    def test_MC07_limits_payload_names_unknown_fields_nan(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = compose(defaults().document, ("t", {"limits": {"max_workloads": 3, "max_payload_bytes": 2048,
                                                                 "max_name_length": 8}}))
            svc, _, _ = make_service(tmp, cfg)
            cases = [
                (req(n=4), "PAYLOAD_TOO_LARGE"),
                (json.dumps(req(n=2, correlation_id="x" * 3000)), "PAYLOAD_TOO_LARGE"),
                (dict(req(n=1), workloads=[{"name": "n" * 9, "cpu": 1, "mem": 1}]), "INVALID_REQUEST"),
                (dict(req(n=1), extra=1), "INVALID_REQUEST"),
                ('{"tenant":"t1","workloads":[{"name":"a","cpu":NaN,"mem":1}],"host_capacity":{"cpu":1,"mem":1}}',
                 "INVALID_REQUEST"),
                (dict(req(n=1), headroom=0.01), "INVALID_REQUEST"),
                ("not json", "INVALID_REQUEST"),
            ]
            for raw, code in cases:
                with self.assertRaises(PackError) as cm:
                    svc.pack(raw, token())
                self.assertEqual(cm.exception.code, code, str(raw)[:80])
            deep_svc, _, _ = make_service(pathlib.Path(tmp) / "deep")
            with self.assertRaises(PackError) as cm:
                deep_svc.pack("[" * 200_000 + "]" * 200_000, token())
            self.assertEqual(cm.exception.code, "INVALID_REQUEST")

    def test_MC07_idempotency_replay_and_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, _, _ = make_service(tmp)
            a = svc.pack(req(idempotency_key="key-00001"), token())
            b = svc.pack(req(idempotency_key="key-00001"), token())
            self.assertTrue(b["replayed"])
            self.assertEqual(a["result"], b["result"])
            with self.assertRaises(PackError) as cm:
                svc.pack(req(n=6, idempotency_key="key-00001"), token())
            self.assertEqual(cm.exception.code, "IDEMPOTENCY_CONFLICT")

    def test_MC07_deadline_and_cancellation(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, _, _ = make_service(tmp)
            d = Deadline(0)
            with self.assertRaises(PackError) as cm:
                svc.pack(req(), token(), deadline=d)
            self.assertEqual(cm.exception.code, "DEADLINE_EXCEEDED")
            d = Deadline(10_000)
            d.cancel()
            with self.assertRaises(PackError) as cm:
                svc.pack(req(), token(), deadline=d)
            self.assertEqual(cm.exception.code, "CANCELLED")

    def test_MC05_tenant_quotas(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = compose(defaults().document, ("q", {"tenants": {"overrides": {"t1": {
                "max_requests_per_minute": 2, "max_workloads_per_request": 4}}}}))
            svc, _, _ = make_service(tmp, cfg)
            with self.assertRaises(PackError) as cm:
                svc.pack(req(n=5), token())
            self.assertEqual(cm.exception.code, "QUOTA_EXCEEDED")
            svc.pack(req(n=2), token())
            svc.pack(req(n=2), token())
            with self.assertRaises(PackError) as cm:
                svc.pack(req(n=2), token())
            self.assertEqual(cm.exception.code, "QUOTA_EXCEEDED")

    def test_MC20_freeze_refuses_packing_preserves_state_and_audits(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, store, audit = make_service(tmp)
            op = lambda: token(kind="operator", caps=("control:freeze",), tenants=("*",), sub="alice")
            with self.assertRaises(PackError):
                svc.freeze(token(), "not allowed")  # scheduler cannot freeze
            svc.freeze(op(), "bad placements seen in INC-1")
            self.assertEqual(svc.status()["state"], "frozen")
            with self.assertRaises(PackError) as cm:
                svc.pack(req(), token())
            self.assertEqual(cm.exception.code, "FROZEN")
            self.assertIsNotNone(store.active())
            restarted = PackingService(store, Authorizer(KEY), audit)
            self.assertEqual(restarted.status()["state"], "frozen")  # freeze survives restart
            svc.unfreeze(op(), "fixed")
            svc.pack(req(), token())
            ops = [r["operation"] for r in audit.records()]
            self.assertIn("control.freeze", ops)
            self.assertIn("control.unfreeze", ops)

    def test_MC25_status_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, _, _ = make_service(tmp)
            st = svc.status()
            for key in ("version", "live", "ready", "state", "config", "dependencies", "capabilities", "admission"):
                self.assertIn(key, st)
            self.assertTrue(st["ready"])
            store = ConfigStore(pathlib.Path(tmp) / "empty")
            svc2 = PackingService(store, Authorizer(KEY), AuditLog(pathlib.Path(tmp) / "a2.jsonl"))
            self.assertEqual(svc2.status()["state"], "not_ready")
            with self.assertRaises(PackError) as cm:
                svc2.pack(req(), token())
            self.assertEqual(cm.exception.code, "NOT_READY")

    def test_MC17_stall_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            mono = Clock(100.0)
            svc, _, _ = make_service(tmp, monotonic=mono, stall_after_s=5)
            svc._inflight["r"] = 90.0
            st = svc.status()
            self.assertTrue(st["stalled"])
            self.assertFalse(st["live"])
            self.assertEqual(st["state"], "degraded")

    def test_MC18_MC19_capacity_source_staleness_and_breaker(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = Clock(1000.0)
            mono = Clock(0.0)
            state = {"observed_at": 1000.0, "fail": False}

            def source(_tenant):
                if state["fail"]:
                    raise ConnectionError("down")
                return {"cpu": 16, "mem": 64, "observed_at": state["observed_at"], "source": "inventory"}
            svc, _, _ = make_service(tmp, capacity_source=source, clock=now, monotonic=mono)
            body = {k: v for k, v in req().items() if k != "host_capacity"}
            self.assertEqual(svc.pack(dict(body), token())["capacity_source"]["source"], "inventory")
            now.t = 1000.0 + 61
            with self.assertRaises(PackError) as cm:
                svc.pack(dict(body), token())
            self.assertEqual(cm.exception.code, "STALE_CAPACITY")
            state.update(observed_at=now.t, fail=True)
            codes = []
            for _ in range(4):
                try:
                    svc.pack(dict(body), token())
                except PackError as e:
                    codes.append(e.code)
            self.assertIn("CIRCUIT_OPEN", codes)
            self.assertEqual(svc.status()["state"], "degraded")
            state["fail"] = False
            mono.t += 10
            svc.pack(dict(body), token())
            self.assertEqual(svc.breaker.state, "closed")

    def test_MC26_metrics_and_cardinality_ceiling(self):
        m = Metrics()
        for i in range(500):
            m.inc("inv68_requests_total", labels={"tenant": f"t{i}", "code": "OK"})
        self.assertEqual(m.overflowed["inv68_requests_total"], 300)
        m.inc("inv68_other", labels={"tenant": "x"})
        self.assertEqual(m.value("inv68_other"), 1.0)  # tenant label dropped for non-allowlisted metric
        m.observe("inv68_request_latency_ms", 3.0)
        self.assertIn("inv68_request_latency_ms_bucket", m.prometheus())

    def test_MC26_traceparent(self):
        self.assertIsNone(parse_traceparent("00-" + "0" * 32 + "-" + "b" * 16 + "-01"))
        self.assertIsNone(parse_traceparent("garbage"))
        tid, sid, tp = child_traceparent(None)
        self.assertEqual(len(tid), 32)
        self.assertEqual(parse_traceparent(tp), (tid, sid))

    def test_MC27_explain_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, _, _ = make_service(tmp)
            r = req()
            r["workloads"].append({"name": "whale", "cpu": 1, "mem": 60})
            out = svc.pack(r, token())
            self.assertEqual(out["outcome"], "partial")
            whale = [d for d in out["explain"]["decisions"] if d["workload"] == "whale"][0]
            self.assertEqual(whale["rejected_constraints"][0]["dimension"], "mem")
            text = render_text(out["explain"])
            self.assertIn("exceeds mem limit", text)
            self.assertEqual(out["explain"]["summary"]["lower_bound"], out["lower_bound"])

    def test_MC15_pack_decisions_are_audited_and_chain_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, _, audit = make_service(tmp)
            for _ in range(3):
                svc.pack(req(), token())
            recs = [r for r in audit.records() if r["operation"] == "pack.decision"]
            self.assertEqual(len(recs), 3)
            self.assertTrue(all(r["tenant"] == "t1" for r in recs))
            key = b"k" * 32
            audit.seal(pathlib.Path(tmp) / "anchor.json", key=key)
            self.assertGreater(audit.verify(anchor_path=pathlib.Path(tmp) / "anchor.json", anchor_key=key), 3)
            lines = (pathlib.Path(tmp) / "audit.jsonl").read_text().splitlines()
            doc = json.loads(lines[1])
            doc["outcome"] = "tampered"
            lines[1] = json.dumps(doc, sort_keys=True)
            (pathlib.Path(tmp) / "audit.jsonl").write_text("\n".join(lines) + "\n")
            with self.assertRaises(AuditChainBroken):
                AuditLog(pathlib.Path(tmp) / "audit.jsonl").verify()

    def test_MC16_internal_defects_never_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            def source(_t):
                return {"cpu": 16, "mem": 64, "observed_at": "not-a-number"}
            svc, _, _ = make_service(tmp, capacity_source=source)
            body = {k: v for k, v in req().items() if k != "host_capacity"}
            with self.assertRaises(PackError) as cm:
                svc.pack(body, token())
            self.assertIn(cm.exception.code, ("INTERNAL", "STALE_CAPACITY"))
            self.assertNotIn("not-a-number", json.dumps(cm.exception.to_dict()))


class Resilience(unittest.TestCase):
    def test_MC18_admission_sheds_beyond_queue(self):
        adm = Admission(1, 1)
        d = Deadline(5_000)
        adm.acquire(d)
        results = []

        def waiter():
            try:
                adm.acquire(Deadline(5_000))
                results.append("admitted")
                adm.release()
            except PackError as e:
                results.append(e.code)
        t = threading.Thread(target=waiter)
        t.start()
        time.sleep(0.05)
        with self.assertRaises(PackError) as cm:
            adm.acquire(Deadline(5_000))
        self.assertEqual(cm.exception.code, "OVERLOADED")
        adm.release()
        t.join(2)
        self.assertEqual(results, ["admitted"])
        self.assertEqual(adm.shed, 1)

    def test_MC18_queue_wait_honours_deadline(self):
        adm = Admission(1, 5)
        adm.acquire(Deadline(1_000))
        with self.assertRaises(PackError) as cm:
            adm.acquire(Deadline(30))
        self.assertEqual(cm.exception.code, "DEADLINE_EXCEEDED")
        self.assertEqual(adm.waiting, 0)

    def test_MC18_breaker_states(self):
        mono = Clock(0.0)
        br = CircuitBreaker("x", failure_threshold=2, reset_after_s=5, clock=mono)
        for _ in range(2):
            with self.assertRaises(PackError):
                br.call(lambda: 1 / 0)
        self.assertEqual(br.state, "open")
        with self.assertRaises(PackError) as cm:
            br.call(lambda: 1)
        self.assertEqual(cm.exception.code, "CIRCUIT_OPEN")
        mono.t = 6
        self.assertEqual(br.call(lambda: 7), 7)
        self.assertEqual(br.state, "closed")

    def test_MC18_backoff_bounded_and_retry_classification(self):
        delays = backoff_schedule(10, base_ms=50, cap_ms=400, rng=random.Random(1))
        self.assertEqual(len(delays), 10)
        self.assertTrue(all(0 <= d <= 400 for d in delays))
        self.assertTrue(should_retry("OVERLOADED"))
        self.assertFalse(should_retry("FORBIDDEN"))
        self.assertFalse(should_retry("UNKNOWN"))


class RuntimeSafety(unittest.TestCase):
    def test_MC16_runtime_modules_have_no_ambient_authority_primitives(self):
        import ast
        banned_calls = {"eval", "exec", "compile", "__import__"}
        banned_modules = {"subprocess", "socket", "urllib.request", "http.client", "ctypes", "pickle", "marshal"}
        for path in sorted(PKG_DIR.glob("*.py")):
            if path.name in ("release_gate.py",):  # CLI tool: reads git revision via subprocess by design
                continue
            tree = ast.parse(path.read_text(), filename=path.name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, banned_calls, path.name)
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                    for n in names:
                        self.assertNotIn(n, banned_modules, path.name)


class AdjacentLayers(unittest.TestCase):
    def test_MC08_k8s_translation(self):
        pods = json.loads((PKG_DIR / "tests" / "fixtures" / "adjacent" / "inv67_pods.json").read_text())
        work = k8s_translate(pods["valid"])
        self.assertEqual(work[0], {"name": "shop/api-0", "cpu": 0.75, "mem": 1.5})
        for bad in pods["invalid"]:
            with self.assertRaises(PackError):
                k8s_translate([bad])

    def test_MC08_scheduler_retries_retryable_then_holds_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, _, _ = make_service(tmp)
            client = SchedulerClient(svc, lambda: token(), attempts=3, sleep=lambda s: None, rng=random.Random(1))
            self.assertEqual(client.place(req())["state"], "placed")
            svc.frozen = {"by": "x", "reason": "drill", "at": 0}
            held = client.place(req())
            self.assertEqual(held["state"], "held")
            self.assertEqual(held["error"]["code"], "FROZEN")
            self.assertEqual(len([l for l in client.log if "FROZEN" in l]), 4)  # retryable -> retried
            svc.frozen = None
            bad = SchedulerClient(svc, lambda: token(tenants=("t9",)), attempts=3, sleep=lambda s: None)
            self.assertEqual(bad.place(req())["state"], "held")
            self.assertEqual(len(bad.log), 1)  # FORBIDDEN is terminal: no retry

    def test_MC08_power_overlay_and_accelerator_split(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc, _, _ = make_service(tmp)
            mixed = req()["workloads"] + [{"name": "train", "cpu": 4, "mem": 16, "nvidia.com/gpu": 1}]
            mine, peer = split_accelerated(mixed)
            self.assertEqual([w["name"] for w in peer], ["train"])
            out = svc.pack(dict(req(), workloads=mine), token())
            view = power_overlay(out, idle_w=60, per_core_w=10, cap_w=100)
            self.assertEqual(view["over_cap"], [h["host"] for h in view["hosts"] if h["watts"] > 100])


if __name__ == "__main__":
    unittest.main()
