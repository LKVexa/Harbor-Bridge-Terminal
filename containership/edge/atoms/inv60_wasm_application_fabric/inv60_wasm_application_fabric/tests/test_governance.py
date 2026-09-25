"""M01-M08 M15 M26 M33 M34 M51/M57 M75 M84-M86 - governance, packaging and evidence artifacts."""
import ast, json, os, pathlib, re, shutil, subprocess, sys, tempfile, unittest
PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools")); sys.path.insert(0, str(PKG.parent)); sys.dont_write_bytecode = True
import m_registry  # noqa: E402


def test_classes():
    out = {}
    for f in (PKG / "tests").glob("test_*.py"):
        tree = ast.parse(f.read_text())
        for n in tree.body:
            if isinstance(n, ast.ClassDef):
                out[f"{f.stem}.{n.name}"] = {m.name for m in n.body if isinstance(m, ast.FunctionDef) and m.name.startswith("test")}
    return out


class Docs(unittest.TestCase):
    def test_master_present_and_ids_match_checklist(self):
        text = (PKG / "MASTER.md").read_text()
        ids = {f"INV-60-C{x}" for x in re.findall(r"INV-60-C(\d{3})", text)}
        cl = {i["check_id"] for i in json.loads((PKG / "CHECKLIST.json").read_text())["items"]}
        self.assertEqual(ids, cl)

    def test_master_index_digest_current(self):
        import hashlib
        idx = (PKG / "docs/MASTER_INDEX.md").read_text()
        self.assertIn(hashlib.sha256((PKG / "MASTER.md").read_bytes()).hexdigest(), idx)

    def test_readme_references_resolve(self):
        text = (PKG / "README.md").read_text()
        for ref in set(re.findall(r"`((?:docs|tools|fabric|schemas|wit|fixtures|config|ops|release)/[A-Za-z0-9_./-]+)`", text)):
            if ref.startswith("release/"):
                continue
            self.assertTrue((PKG / ref).exists(), ref)
        self.assertIn("MASTER.md", text)

    def test_generated_docs_current(self):
        r = subprocess.run([sys.executable, "-B", str(PKG / "tools/gen_docs.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_adr_structure(self):
        adr = (PKG / "docs/ADR-0001-wasm-fabric.md").read_text()
        for h in ("Status:", "Alternatives considered", "Reconsideration triggers", "Reversibility", "Dependencies introduced"):
            self.assertIn(h, adr)
        self.assertRegex(adr, r"\*\*Status:\*\* (proposed|accepted|superseded|deprecated)")

    def test_runbooks_present_with_failure_paths(self):
        for n in ("DAY0", "DAY1", "DAY2", "ROLLOUT", "BACKUP_RESTORE", "INCIDENT"):
            t = (PKG / f"docs/runbooks/{n}.md").read_text()
            self.assertGreater(len(t), 400, n)
        self.assertIn("Abort if", (PKG / "docs/runbooks/ROLLOUT.md").read_text())
        self.assertIn("p99 < 3 ms", (PKG / "docs/SLO.md").read_text())


class Packaging(unittest.TestCase):
    def test_metadata(self):
        t = (PKG / "pyproject.toml").read_text()
        self.assertIn('version = "4.3.0"', t); self.assertIn("dependencies = []", t)
        self.assertEqual((PKG / "VERSION").read_text().strip(), "4.3.0")
        import inv60_wasm_application_fabric as m  # noqa
        self.assertEqual(m.__version__, "4.3.0")

    def test_notices(self):
        self.assertTrue((PKG / "NOTICE").exists()); self.assertTrue((PKG / "THIRD-PARTY-NOTICES.md").exists())
        self.assertTrue((PKG / "LICENSE-DECISION.md").exists())
        self.assertFalse((PKG / "LICENSE").exists(), "if a LICENSE is added, update M02 status and pyproject SPDX")

    def test_no_third_party_runtime_imports(self):
        allowed = set(sys.stdlib_module_names) | {"inv60_wasm_application_fabric", "pk_core", "_harness", "m_registry"}
        for p in list((PKG / "fabric").glob("*.py")) + [PKG / "runtime.py"]:
            for n in ast.walk(ast.parse(p.read_text())):
                if isinstance(n, ast.Import):
                    names = [a.name.split(".")[0] for a in n.names]
                elif isinstance(n, ast.ImportFrom) and n.level == 0:
                    names = [n.module.split(".")[0]]
                else:
                    continue
                for nm in names:
                    self.assertIn(nm, allowed, f"{p.name} imports {nm}")

    def test_sbom_generator(self):
        r = subprocess.run([sys.executable, "-B", str(PKG / "tools/gen_sbom.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        bom = json.loads((PKG / "release/sbom.cdx.json").read_text())
        self.assertEqual(bom["bomFormat"], "CycloneDX")
        self.assertTrue(any(c["name"].endswith("fabric/fabric.py") for c in bom["components"]))


class CI(unittest.TestCase):
    def test_workflow_calls_strict_runner(self):
        y = (PKG / ".github/workflows/ci.yml").read_text()
        self.assertIn("tools/ci.py --strict", y)
        for v in ("3.10", "3.11", "3.12"):
            self.assertIn(v, y)

    def test_runner_treats_missing_prereq_as_failure(self):
        src = (PKG / "tools/ci.py").read_text()
        self.assertIn("node missing (not a pass)", src)
        self.assertIn("critical_skipped", src)


class Ownership(unittest.TestCase):
    def test_structure_and_placeholders_block_gate(self):
        o = json.loads((PKG / "OWNERSHIP.json").read_text())
        for k in ("service_owner", "team", "escalation", "raci", "response_expectations", "transfer_policy"):
            self.assertIn(k, o)
        self.assertEqual(set(o["raci"]), {"architecture", "security", "operations", "incident_response", "dependency_upgrades", "release_certification"})
        self.assertIn("UNASSIGNED", (PKG / "CODEOWNERS").read_text())


class Requirements(unittest.TestCase):
    def test_every_requirement_maps_to_existing_test(self):
        req = json.loads((PKG / "docs/requirements.json").read_text())
        cls = test_classes()
        ids = [r["id"] for r in req["requirements"]]
        self.assertEqual(len(ids), len(set(ids)))
        for r in req["requirements"]:
            self.assertIn(r["level"], ("SHALL", "SHOULD", "MAY"))
            for v in r["verification"]:
                mod, c, meth = v.split(".")
                self.assertIn(f"{mod}.{c}", cls, v)
                self.assertIn(meth, cls[f"{mod}.{c}"], v)


class Traceability(unittest.TestCase):
    def test_registry_complete_and_resolvable(self):
        self.assertEqual(sorted(m_registry.M), [f"M{i:02d}" for i in range(1, 87)])
        cls = test_classes() | {"test_component.ConformanceTest": {"x"}}
        for m, (status, arts, tcls, blocker, waiver) in m_registry.M.items():
            self.assertIn(status, ("LOCALLY_VERIFIED", "PARTIAL", "BLOCKED"))
            for a in arts:
                if not a.startswith("release/"):
                    self.assertTrue((PKG / a).exists(), f"{m}: {a}")
            for c in tcls:
                self.assertIn(c, cls, f"{m}: {c}")
            if status != "LOCALLY_VERIFIED":
                self.assertTrue(blocker and waiver, m)
            else:
                self.assertTrue(tcls, f"{m} verified without tests")

    def test_waivers_cover_every_non_verified_item(self):
        w = {x["id"]: set(x["covers"]) for x in json.loads((PKG / "WAIVERS.json").read_text())["waivers"]}
        for m, (status, _, _, _, waiver) in m_registry.M.items():
            if status != "LOCALLY_VERIFIED":
                self.assertIn(m, w[waiver], m)


class Matrix(unittest.TestCase):
    def test_matrix_statuses(self):
        mx = json.loads((PKG / "SUPPORT_MATRIX.json").read_text())
        st = {c["status"] for c in mx["combinations"]}
        self.assertLessEqual(st, {"tested", "supported-untested", "untested", "deprecated", "blocked", "experimental"})
        self.assertTrue(any("wasmCloud" in c["component"] and c["status"] == "untested" for c in mx["combinations"]))


class Bootstrap(unittest.TestCase):
    def run_bs(self, d, *extra):
        return subprocess.run([sys.executable, "-B", str(PKG / "tools/bootstrap.py"), "--dir", d, *extra], capture_output=True, text=True)

    def test_idempotent_and_honest(self):
        with tempfile.TemporaryDirectory() as d:
            r1 = self.run_bs(d, "--env", "production")
            self.assertEqual(r1.returncode, 1)                     # no real lattice: not ok
            ev = json.loads(pathlib.Path(d, "bootstrap-evidence.json").read_text())
            self.assertFalse(ev["checks"]["external:nats"]["ok"])
            self.assertIn("enrolment code for h1", r1.stdout)
            r2 = self.run_bs(d, "--env", "production", "--reference")
            self.assertEqual(r2.returncode, 0, r2.stdout)
            self.assertNotIn("enrolment code", r2.stdout)          # not re-issued
            ev2 = json.loads(pathlib.Path(d, "bootstrap-evidence.json").read_text())
            self.assertEqual(ev2["checks"]["issuer_key"]["detail"], "reused")
            self.assertNotIn("code", pathlib.Path(d, "enrolment-codes.sha256.json").read_text().lower().replace("codes", ""))


class ThreatModel(unittest.TestCase):
    def test_threats_have_controls_and_real_verifications(self):
        tm = json.loads((PKG / "docs/THREAT_MODEL.json").read_text())
        cls = test_classes()
        ids = [t["id"] for t in tm["threats"]]
        self.assertEqual(len(ids), len(set(ids)))
        for t in tm["threats"]:
            self.assertTrue(t["controls"])
            for v in t["verification"]:
                mod, c, meth = v.split(".")
                self.assertIn(meth, cls.get(f"{mod}.{c}", set()), v)
        text = json.dumps(tm).lower()
        for abuse in ("cross-tenant", "forged link", "replay", "split-brain", "exfiltration", "tag substitution"):
            self.assertIn(abuse, text)


class Bench(unittest.TestCase):
    def test_bench_baseline_present(self):
        b = json.loads((PKG / "release/BENCHMARK_BASELINE.json").read_text())
        for k in ("auth_verify", "capability_checked_call", "authenticated_call", "failover_control_plane", "saturation"):
            self.assertIn(k, b["results"])
        self.assertFalse(b["representative_hardware"])
        self.assertIn("met_authenticated", b["slo_check"])


class Evidence(unittest.TestCase):
    def _gate(self, mutate):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "release").mkdir()
            for f in ("WAIVERS.json", "OWNERSHIP.json", "REVIEWS.json"):
                shutil.copy(PKG / f, root / f)
            acc = {"release": "4.3.0", "test_summary": {"failed": 0, "errors": 0, "critical_skipped": 0},
                   "conformance": {"pk_core_certified": True, "pk_core_gate": "GO"}, "traceability": {"m_effective": {}},
                   "items": {"M01": {"status": "LOCALLY_VERIFIED", "waiver": None, "blocker": None},
                             "M25": {"status": "PARTIAL", "waiver": "W-M25", "blocker": "no lattice"}}}
            tr = {"problems": []}
            mutate(root, acc, tr)
            (root / "release/ACCEPTANCE.json").write_text(json.dumps(acc)); (root / "release/TRACEABILITY.json").write_text(json.dumps(tr))
            r = subprocess.run([sys.executable, "-B", str(PKG / "tools/exit_gate.py")], capture_output=True, text=True,
                               env={**os.environ, "INV60_ROOT": d})
            self.assertEqual(r.returncode, 0, r.stderr)
            return json.loads((root / "release/EXIT_GATE.json").read_text())

    def test_unapproved_waiver_is_no_go(self):
        g = self._gate(lambda r, a, t: None)
        self.assertEqual(g["verdict"], "NO_GO")
        self.assertTrue(any("M25" in b for b in g["blockers"]))

    def test_self_approved_waiver_still_blocks(self):
        def m(root, a, t):
            w = json.loads((root / "WAIVERS.json").read_text())
            for x in w["waivers"]:
                x["status"] = "approved"; x["approver"] = x["requested_by"]
            (root / "WAIVERS.json").write_text(json.dumps(w))
        self.assertTrue(any("M25" in b for b in self._gate(m)["blockers"]))

    def test_failing_tests_block(self):
        def m(root, a, t):
            a["test_summary"]["failed"] = 1
        self.assertFalse(self._gate(m)["checks"]["tests"]["pass"])

    def test_gate_is_unsigned(self):
        self.assertIsNone(self._gate(lambda r, a, t: None)["signature"])


class Governance(unittest.TestCase):
    def test_waiver_register_shape(self):
        w = json.loads((PKG / "WAIVERS.json").read_text())
        for x in w["waivers"]:
            for k in ("id", "covers", "reason", "remediation", "status", "approver", "expires"):
                self.assertIn(k, x)
            self.assertRegex(x["expires"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertTrue(w["technical_debt"])

    def test_review_register(self):
        r = json.loads((PKG / "REVIEWS.json").read_text())
        self.assertIn("cadence", r); self.assertEqual(r["reviews"], [])


if __name__ == "__main__":
    unittest.main()
