"""M75/M64 - machine-readable release acceptance evidence for every M-item."""
import datetime, hashlib, json, pathlib, sys
PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent)); sys.path.insert(0, str(PKG / "tools")); sys.dont_write_bytecode = True
from inv60_wasm_application_fabric.fabric import config as cf
rel = PKG / "release"


def tree_digest(root: pathlib.Path, exclude=("release", "__pycache__", "SHA256SUMS")) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(x in p.relative_to(root).parts for x in exclude) and p.name != "SHA256SUMS":
            h.update(p.relative_to(root).as_posix().encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def fhash(rel_path):
    p = PKG / rel_path
    if p.is_file():
        return hashlib.sha256(p.read_bytes()).hexdigest()
    if p.is_dir():
        return tree_digest(p)
    return None


tr = json.loads((rel / "TRACEABILITY.json").read_text())
tests = json.loads((rel / "TEST_RESULTS.json").read_text())
conf = json.loads((rel / "CONFORMANCE.json").read_text())
base = cf.render(json.loads((PKG / "config/base.json").read_text()), ("production", json.loads((PKG / "config/overlays/production.json").read_text())))
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
items = {}
for m, r in tr["m_items"].items():
    items[m] = {"status": r["effective"], "declared": r["declared"], "evidence": {a: fhash(a) for a in r["artifacts"]},
                "tests": r["tests"], "blocker": r["blocker"] or None, "waiver": r["waiver"],
                "owner": "UNASSIGNED", "reviewer": None, "completed_at": now if r["effective"] == "LOCALLY_VERIFIED" else None}
acc = {"schema": "inv60.acceptance/1", "release": (PKG / "VERSION").read_text().strip(), "generated_at": now,
       "lineage": {"source_tree_sha256": tree_digest(PKG), "pk_core_tree_sha256": tree_digest(PKG.parent / "pk_core"),
                   "master_md_sha256": fhash("MASTER.md"), "checklist_sha256": fhash("CHECKLIST.json"),
                   "production_config_digest": cf.digest(base), "config_schema": cf.CONFIG_SCHEMA_VERSION,
                   "fixtures_index_sha256": fhash("fixtures/INDEX.json"), "source_commit": None,
                   "note": "no VCS commit exists for this build; source_tree_sha256 is the immutable identifier"},
       "test_summary": tests["summary"], "conformance": {"pk_core_certified": conf["workflow"]["certified"],
       "pk_core_gate": conf["gate"]["verdict"], "evidence_head": conf["evidence_head"]},
       "traceability": tr["summary"], "items": items}
(rel / "ACCEPTANCE.json").write_text(json.dumps(acc, indent=1))
print(json.dumps({"items": len(items), "status": tr["summary"]["m_effective"]}))
