"""Repository delivery, exit gate falsifier, traceability, operator drills
(components 1, 6, 11, 21, 78, 83, 84, 88-96)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

from _support import PKG_DIR, ROOT, TmpDirCase
from inv53_message_reliability import gate as G
from inv53_message_reliability.durable import DurableQueue, _State

REQUIRED = ["README.md", "CHANGELOG.md", "VERSION", "MASTER.md", "SECURITY.md", "NOTICE", "CODEOWNERS", "pyproject.toml",
            "requirements/runtime.txt", "requirements/pk_core.lock.json", ".github/workflows/ci.yml",
            "governance/OWNERS.md", "governance/owners.json", "governance/service-catalog.json",
            "governance/COMPONENTS.json", "governance/WAIVERS.json", "docs/TRACEABILITY.md",
            "docs/adr/ADR-0001-delivery-semantics.md", "docs/spec/STATE_MACHINE.md", "docs/security/THREAT_MODEL.md",
            "docs/ops/RUNBOOKS.md", "perf/THRESHOLDS.json", "schemas/request.schema.json", "tools/ci.py", "tools/lint.py"]


def cli(*args, cwd=ROOT):
    return subprocess.run([sys.executable, "-B", "-m", "inv53_message_reliability", *map(str, args)], cwd=str(cwd),
                          capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


class RepositoryTest(unittest.TestCase):
    def test_required_artifacts_exist(self):
        missing = [p for p in REQUIRED if not (PKG_DIR / p).exists()]
        self.assertEqual(missing, [])

    def test_version_consistency(self):
        import inv53_message_reliability as P
        v = (PKG_DIR / "VERSION").read_text().strip()
        self.assertEqual(P.__version__, v)
        self.assertIn(f'version = "{v}"', (PKG_DIR / "pyproject.toml").read_text())
        self.assertIn(f"## {v}", (PKG_DIR / "CHANGELOG.md").read_text())
        self.assertIn(f"**Version:** {v}", (PKG_DIR / "README.md").read_text())

    def test_master_prompt_artifact_is_real(self):
        text = (PKG_DIR / "MASTER.md").read_text(encoding="utf-8")
        found = set(re.findall(r"^# (INV-53-C\d{3}) — Master Prompt & Workflow", text, re.M))
        self.assertEqual(found, {f"INV-53-C{i:03d}" for i in range(1, 101)})
        checklist = json.loads((PKG_DIR / "CHECKLIST.json").read_text())
        for item in checklist["items"]:
            self.assertIn(item["requirement"], text)

    def test_state_machine_doc_matches_code(self):
        doc = (PKG_DIR / "docs" / "spec" / "STATE_MACHINE.md").read_text()
        doc_ops = set(re.findall(r"^\| T\d \| `(\w+)` \|", doc, re.M))
        import inspect
        code_ops = set(re.findall(r'op == "(\w+)"', inspect.getsource(_State.apply)))
        self.assertEqual(doc_ops, code_ops)

    def test_traceability_matrix_is_generated_not_edited(self):
        self.assertEqual((PKG_DIR / "docs" / "TRACEABILITY.md").read_text(), G.traceability_markdown())

    def test_register_is_honest_about_the_tree(self):
        reg = json.loads((PKG_DIR / "governance" / "COMPONENTS.json").read_text())
        self.assertEqual(G.check_register(reg, None, PKG_DIR), [])
        self.assertEqual(len(reg["components"]), 96)
        self.assertFalse([c for c in reg["components"] if c["status"] == "COMPLETE"],
                         "nothing is COMPLETE without an owner's verified acceptance")
        tests_here = set()
        for f in (PKG_DIR / "tests").glob("test_*.py"):
            for cls, body in re.findall(r"^class (\w+)\(.*?\):\n(.*?)(?=^class |\Z)", f.read_text(), re.M | re.S):
                for m in re.findall(r"^    def (test_\w+)", body, re.M):
                    tests_here.add(f"{f.name}::{cls}::{m}")
        for c in reg["components"]:
            for t in c.get("tests", []):
                self.assertIn(t, tests_here, f"component {c['id']} cites a test that does not exist")

    def test_pk_core_pin_is_well_formed(self):
        lock = json.loads((PKG_DIR / "requirements" / "pk_core.lock.json").read_text())
        h = hashlib.sha256()
        for name, digest in sorted(lock["files"].items()):
            h.update(name.encode() + b"\0" + bytes.fromhex(digest))
        self.assertEqual(h.hexdigest(), lock["content_sha256"])

    def test_no_host_specific_values_in_tracked_files(self):
        bad = []
        for p in PKG_DIR.rglob("*"):
            rel = p.relative_to(PKG_DIR)
            if p.is_file() and rel.parts[0] not in ("evidence", "tests") and "__pycache__" not in rel.parts \
                    and p.suffix in (".py", ".md", ".json", ".toml", ".txt"):
                t = p.read_text(encoding="utf-8", errors="replace")
                if "/home/claude" in t or "C:\\Users\\" in t or "/tmp/inv53" in t:
                    bad.append(rel.as_posix())
        self.assertEqual(bad, [])


class GateTest(TmpDirCase):
    """The delivered gate is NO_GO; a synthetic, fully-satisfied tree reaches GO (so the gate is not a wall)."""

    def test_delivered_tree_is_no_go_with_named_blockers(self):
        res = G.evaluate(root=PKG_DIR, evidence_path=self.tmp / "absent.json")
        self.assertEqual(res["verdict"], "NO_GO")
        self.assertIn("role service_owner is UNASSIGNED", res["blockers"])
        self.assertTrue(any("thresholds are PROPOSED" in b for b in res["blockers"]))
        self.assertEqual(res["component_counts"]["COMPLETE"], 0)

    def _synthetic(self):
        root = self.tmp / "synthetic"
        (root / "governance" / "approvals").mkdir(parents=True)
        (root / "perf").mkdir()
        (root / "impl.py").write_text("x = 1\n")
        comps = [{"id": str(i), "title": f"c{i}", "status": "COMPLETE", "artifacts": ["impl.py"], "tests": ["t.py::T::test_a"]}
                 for i in (1, 2)]
        (root / "governance" / "COMPONENTS.json").write_text(json.dumps({"expected_count": 2, "components": comps}))
        (root / "governance" / "owners.json").write_text(json.dumps(
            {"roles": {r: {"name": f"Synthetic {r}"} for r in G.REQUIRED_ROLES}}))
        (root / "perf" / "THRESHOLDS.json").write_text(json.dumps({"status": "APPROVED", "limits": {}}))
        digest = G.source_digest(root)
        for r in G.REQUIRED_ROLES:
            (root / "governance" / "approvals" / f"NOT_THE_DELIVERED_{r}.json").write_text(json.dumps(
                {"role": r, "decision": "APPROVE", "source_digest": digest, "sig": "synthetic"}))
        ev = {"source_digest": digest, "lanes": {lane: {"status": "PASS"} for lane in G.REQUIRED_LANES},
              "tests": {"t.py::T::test_a": "pass"},
              "perf_gate": {"verdict": "PASS"}}
        (self.tmp / "ev.json").write_text(json.dumps(ev))
        return root

    def run_gate(self, root, **kw):
        return G.evaluate(root=root, evidence_path=self.tmp / "ev.json",
                          approval_verifier=kw.pop("verifier", lambda rec: rec.get("sig") == "synthetic"), **kw)

    def test_falsifier_fully_satisfied_synthetic_tree_reaches_go(self):
        res = self.run_gate(self._synthetic())
        self.assertEqual(res["verdict"], "GO", res.get("blockers"))

    def test_truth_table_each_single_omission_is_no_go(self):
        mutations = {
            "unverified approvals": lambda root: {"verifier": None},
            "rejecting verifier": lambda root: {"verifier": lambda rec: False},
            "role unassigned": lambda root: (root / "governance" / "owners.json").write_text(json.dumps(
                {"roles": {r: {"name": "x"} for r in G.REQUIRED_ROLES[1:]}})),
            "component partial": lambda root: self._mutate_register(root, "PARTIAL"),
            "thresholds proposed": lambda root: (root / "perf" / "THRESHOLDS.json").write_text(json.dumps({"status": "PROPOSED"})),
            "stale evidence": lambda root: (root / "impl.py").write_text("x = 2\n"),
            "lane failed": lambda root: self._mutate_evidence(lanes={"unit": {"status": "FAIL"}}),
            "lane not run": lambda root: self._mutate_evidence(lanes={"pk_core": {"status": "NOT_RUN"}}),
            "perf gate not pass": lambda root: self._mutate_evidence(perf_gate={"verdict": "MET_UNDER_PROPOSED"}),
            "lanes absent": lambda root: self._replace_evidence(lanes={}),
            "no passing tests": lambda root: self._replace_evidence(tests={}),
            "expired waiver": lambda root: (root / "governance" / "WAIVERS.json").write_text(json.dumps(
                {"waivers": [{"id": "W1", "component": "9", "expires": "2020-01-01", "approved_by": "x"}]})),
        }
        for name, mutate in mutations.items():
            with self.subTest(name):
                shutil.rmtree(self.tmp / "synthetic", ignore_errors=True)
                root = self._synthetic()
                kw = mutate(root) or {}
                res = self.run_gate(root, **kw) if isinstance(kw, dict) else self.run_gate(root)
                self.assertIn(res["verdict"], ("NO_GO", "ERROR"), name)

    def test_dishonest_register_is_an_error_not_a_verdict(self):
        root = self._synthetic()
        reg = json.loads((root / "governance" / "COMPONENTS.json").read_text())
        reg["components"][0]["tests"] = ["t.py::T::test_that_never_ran"]
        (root / "governance" / "COMPONENTS.json").write_text(json.dumps(reg))
        self.assertEqual(self.run_gate(root)["verdict"], "ERROR")

    def test_live_waiver_needs_named_approver_and_future_expiry(self):
        root = self._synthetic()
        self._mutate_register(root, "PARTIAL")
        w = {"waivers": [{"id": "W1", "component": "1", "expires": "2099-01-01", "approved_by": None}]}
        (root / "governance" / "WAIVERS.json").write_text(json.dumps(w))
        self.assertEqual(self.run_gate(root)["verdict"], "NO_GO")

    def _mutate_register(self, root, status):
        reg = json.loads((root / "governance" / "COMPONENTS.json").read_text())
        reg["components"][0]["status"] = status
        reg["components"][0]["blockers"] = ["synthetic"]
        (root / "governance" / "COMPONENTS.json").write_text(json.dumps(reg))
        # keep the evidence bound to the mutated tree so only the status differs
        ev = json.loads((self.tmp / "ev.json").read_text())
        ev["source_digest"] = G.source_digest(root)
        (self.tmp / "ev.json").write_text(json.dumps(ev))
        for p in (root / "governance" / "approvals").glob("*.json"):
            rec = json.loads(p.read_text()); rec["source_digest"] = ev["source_digest"]; p.write_text(json.dumps(rec))

    def test_R8_waiver_cannot_turn_missing_or_blocked_into_go(self):
        """Adversarial-review defect 8: a waived MISSING component plus empty lanes reached GO."""
        for status in ("MISSING", "BLOCKED"):
            with self.subTest(status):
                shutil.rmtree(self.tmp / "synthetic", ignore_errors=True)
                root = self._synthetic()
                self._mutate_register(root, status)
                (root / "governance" / "WAIVERS.json").write_text(json.dumps(
                    {"waivers": [{"id": "W1", "component": "1", "expires": "2099-01-01", "approved_by": "anyone",
                                  "sig": "synthetic"}]}))
                self._mutate_register(root, status)          # re-bind evidence to the edited tree
                self.assertEqual(self.run_gate(root)["verdict"], "NO_GO")

    def test_verified_waiver_on_partial_component_is_honoured(self):
        root = self._synthetic()
        (root / "governance" / "WAIVERS.json").write_text(json.dumps(
            {"waivers": [{"id": "W1", "component": "1", "expires": "2099-01-01", "approved_by": "x", "sig": "synthetic"}]}))
        self._mutate_register(root, "PARTIAL")
        self.assertEqual(self.run_gate(root)["verdict"], "GO", "a live, verified waiver is the one documented exception")

    def _replace_evidence(self, **changes):
        ev = json.loads((self.tmp / "ev.json").read_text())
        ev.update(changes)
        (self.tmp / "ev.json").write_text(json.dumps(ev))

    def _mutate_evidence(self, **changes):
        ev = json.loads((self.tmp / "ev.json").read_text())
        for k, v in changes.items():
            ev[k] = {**ev.get(k, {}), **v} if isinstance(v, dict) and k == "lanes" else v
        (self.tmp / "ev.json").write_text(json.dumps(ev))


class DrillTest(TmpDirCase):
    """Executed operator drills through the real CLI (backup/restore/redrive/explain/audit)."""

    def test_backup_restore_redrive_drill(self):
        store = self.tmp / "store"
        with DurableQueue(store, visibility=1, max_attempts=1) as q:
            for i in range(50):
                q.put({"id": f"m{i}"})
            q.receive(now=0)
            q.expire(now=5)                       # m0 dead-lettered
            before = q.state_digest()
        r = cli("store", "inspect", store, "--visibility", 1, "--max-attempts", 1)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["snapshot"]["dead_lettered"], 1)
        r = cli("store", "backup", store, self.tmp / "bk", "--visibility", 1, "--max-attempts", 1)
        self.assertEqual(json.loads(r.stdout)["state_digest"], before)
        r = cli("store", "restore", self.tmp / "bk", self.tmp / "restored", "--visibility", 1, "--max-attempts", 1)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = cli("store", "explain", self.tmp / "restored", "m0", "--visibility", 1, "--max-attempts", 1)
        self.assertEqual(json.loads(r.stdout)["state"], "dead_lettered")
        r = cli("store", "redrive", self.tmp / "restored", "m0", "--visibility", 1, "--max-attempts", 1, "--now", 6)
        self.assertEqual((r.returncode, json.loads(r.stdout)), (0, {"redriven": True}))
        r = cli("store", "purge", self.tmp / "restored", "nope", "--visibility", 1, "--max-attempts", 1)
        self.assertEqual(r.returncode, 1)

    def test_offline_cli_refuses_a_store_owned_by_a_live_writer(self):
        q = DurableQueue(self.tmp / "live")
        r = cli("store", "inspect", self.tmp / "live")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("OwnershipError", r.stderr)
        q.close()

    def test_cli_surfaces(self):
        self.assertEqual(json.loads(cli("version").stdout)["wire"], ["inv53.wire/1"])
        self.assertEqual(json.loads(cli("errors").stdout)["schema"], "inv53.errors/1")
        self.assertEqual(cli("schemas").returncode, 0)
        cfg = self.tmp / "site.json"
        cfg.write_text(json.dumps({"max_attempts": 9}))
        out = json.loads(cli("config", f"site:edge={cfg}").stdout)
        self.assertEqual(out["provenance"]["max_attempts"], "site:edge")
        cfg.write_text(json.dumps({"max_attempts": 0}))
        self.assertEqual(cli("config", f"site:edge={cfg}").returncode, 1)
        from inv53_message_reliability.security import AuditLog
        log = AuditLog(self.tmp / "a.jsonl")
        log.append("x")
        self.assertEqual(cli("audit", self.tmp / "a.jsonl", "--anchor", json.dumps(log.head())).returncode, 0)
        r = cli("gate", "--evidence", self.tmp / "none.json")
        self.assertEqual(r.returncode, 3, "delivered gate exits 3 (NO_GO)")


if __name__ == "__main__":
    unittest.main()
