"""Traceability and bounded execution for the 375,000-record UC master series.

The attached prompts are engineering instructions, not executable code. This
module verifies every source record and records a conservative disposition.
Local execution profiles exercise relevant candidate surfaces; they never turn
unobserved hardware/network/production requirements into PASS.
"""
from __future__ import annotations
import datetime
import gzip
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile
from collections import Counter
from typing import Any

from . import Refusal
from . import strictjson as J
from . import engines as E
from . import safety as SAFE

TASK_RE = re.compile(r"C(\d{3})\.(\d{3})\.T(\d{2})\Z")
STATES = {"OPEN", "BLOCKED"}


def base(root: str | Path) -> Path:
    return Path(root) / "masterflow"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _records(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield J.loads(line)


def load(root):
    b = base(root)
    try:
        app = J.read(str(b / "APPLICATION.json"), max_bytes=4 * 1024 * 1024)
    except Exception as exc:
        raise Refusal("master workflow application manifest unavailable") from exc
    return b, app


def status(root):
    b, app = load(root)
    return {"schema": "UC/MASTER_WORKFLOW_STATUS/1", "candidate": app["candidate"],
            "source_version": app["source_version"], "volumes": app["volumes"],
            "components": app["components"], "checklist_items": app["checklist_items"],
            "tasks": app["tasks"], "task_status_counts": app["task_status_counts"],
            "component_status_counts": app["component_status_counts"],
            "source_tasks_promoted_pass": 0, "full_series_complete": False,
            "note": "Local implementation/evidence may advance a component while its generated engineering task remains OPEN or BLOCKED."}


def _verify_volume(path: Path, expected_sha: str, deep: bool, seen: set[str], component_names: dict[str, str], errors: list[str]) -> int:
    """Verify one source volume.

    Fast mode trusts the externally recorded whole-ZIP SHA-256 and does not
    inflate its very repetitive JSONL corpus. Deep mode streams each component
    exactly once, simultaneously checking its embedded checksum and canonical
    Cxxx.yyy.Tzz coverage.
    """
    if _sha(path) != expected_sha:
        errors.append(path.name + ": archive SHA-256 mismatch"); return 0
    if not deep:
        return 0
    import json as _fast_json
    count = 0
    with zipfile.ZipFile(path) as z:
        names = z.namelist(); roots = {n.split("/")[0] for n in names if n}
        if len(roots) != 1:
            errors.append(path.name + ": invalid volume root"); return 0
        root = next(iter(roots)); sums_name = root + "/SHA256SUMS.txt"
        if sums_name not in names:
            errors.append(path.name + ": SHA256SUMS missing"); return 0
        expected = {}
        for line in z.read(sums_name).decode("utf-8").splitlines():
            if not line.strip(): continue
            try: digest, rel = line.split("  ", 1)
            except ValueError:
                errors.append(path.name + ": malformed embedded checksum entry"); return 0
            expected[rel] = digest
        # Verify small non-component records directly. Component streams are
        # verified while checking IDs below to avoid a second decompression pass.
        for rel, digest in expected.items():
            if rel.startswith("components/") and rel.endswith(".jsonl"):
                continue
            try: raw = z.read(root + "/" + rel)
            except KeyError:
                errors.append(path.name + ": embedded member missing " + rel); return 0
            if hashlib.sha256(raw).hexdigest() != digest:
                errors.append(path.name + ": embedded checksum mismatch " + rel); return 0
        cfiles = sorted(n for n in names if "/components/" in n and n.endswith(".jsonl"))
        for name in cfiles:
            cid = Path(name).stem
            if not re.fullmatch(r"C\d{3}", cid):
                errors.append(path.name + ": invalid component filename " + name); return count
            comp_num = int(cid[1:]); h = hashlib.sha256(); line_count = 0; cname = None
            rel = name[len(root) + 1:]
            with z.open(name) as fh:
                for raw in fh:
                    h.update(raw); line_count += 1
                    try: rec = _fast_json.loads(raw)
                    except Exception:
                        errors.append(f"{path.name}:{name}:{line_count}: invalid JSON"); return count
                    expected_parent = (line_count - 1) // 25 + 1
                    expected_task = (line_count - 1) % 25 + 1
                    expected_id = f"{cid}.{expected_parent:03d}.T{expected_task:02d}"
                    tid = rec.get("id")
                    if tid != expected_id or rec.get("component_id") != cid or rec.get("checklist_id") != f"{cid}.{expected_parent:03d}":
                        errors.append(f"{path.name}:{name}:{line_count}: traceability mismatch"); return count
                    if tid in seen:
                        errors.append("duplicate task ID " + tid); return count
                    seen.add(tid); count += 1
                    this_name = rec.get("component")
                    if cname is None: cname = this_name
                    elif this_name != cname:
                        errors.append(cid + ": inconsistent component name"); return count
                    wf = rec.get("workflow")
                    if not isinstance(wf, list) or len(wf) != 8 or not rec.get("prompt") or not rec.get("task"):
                        errors.append(tid + ": prompt/workflow shape mismatch"); return count
            if line_count != 2500:
                errors.append(cid + f": expected 2500 records, got {line_count}"); return count
            if expected.get(rel) != h.hexdigest():
                errors.append(path.name + ": embedded checksum mismatch " + rel); return count
            component_names[cid] = cname
    return count


def check(root, deep=False):
    import json as _fast_json
    b, app = load(root); errors=[]; seen=set(); names={}; source_count=0
    source = b / "source"
    for vol in app["source_archives"]:
        source_count += _verify_volume(source / vol["file"], vol["sha256"], bool(deep), seen, names, errors)
        if errors: break
    components = J.read(str(b / "COMPONENTS.json"), max_bytes=8 * 1024 * 1024)
    if len(components) != 150:
        errors.append("component disposition coverage mismatch")
    if deep:
        if source_count != 375000 or len(seen) != 375000:
            errors.append(f"source task coverage mismatch: {source_count}")
        if len(names) != 150 or set(names) != set(components):
            errors.append(f"source component coverage mismatch: {len(names)}")
    # Ledger is compact enough to parse fully in both modes. Require exact
    # deterministic ID progression, so duplication/omission cannot hide behind a count.
    counts = Counter(); ledger_count = 0
    with gzip.open(b / "ledger.jsonl.gz", "rt", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip(): continue
            try: rec = _fast_json.loads(line)
            except Exception:
                errors.append("ledger contains invalid JSON"); break
            ledger_count += 1
            ci = (ledger_count - 1) // 2500 + 1
            within = (ledger_count - 1) % 2500
            pi = within // 25 + 1; ti = within % 25 + 1
            expected_id = f"C{ci:03d}.{pi:03d}.T{ti:02d}"
            if rec.get("id") != expected_id or rec.get("component_id") != f"C{ci:03d}":
                errors.append(expected_id + ": ledger ordering/traceability mismatch"); break
            if rec.get("status") not in STATES or not rec.get("reason"):
                errors.append(expected_id + ": ledger disposition invalid"); break
            counts[rec["status"]] += 1
    if ledger_count != 375000:
        errors.append(f"ledger task coverage mismatch: {ledger_count}")
    if dict(counts) != app["task_status_counts"]:
        errors.append("task status counts differ from application manifest")
    comp_counts = Counter(rec.get("status") for rec in components.values())
    if dict(comp_counts) != app["component_status_counts"]:
        errors.append("component status counts differ from application manifest")
    if errors:
        raise Refusal("master workflow traceability verification failed", {"errors": errors[:50], "error_count": len(errors)})
    return {"schema": "UC/MASTER_WORKFLOW_CHECK/1", "integrity": "PASS", "volumes": 15,
            "components": 150, "tasks": 375000, "unique_ids": 375000,
            "counts": dict(counts), "source_archives_verified": 15,
            "embedded_source_checksums_verified": bool(deep), "engineering_completion_verified": False,
            "source_tasks_promoted_pass": 0, "deep": bool(deep)}

def show(root, task):
    m=TASK_RE.fullmatch(task or "")
    if not m: raise Refusal("invalid master workflow task ID")
    b, app=load(root); cid="C"+m.group(1); wanted=task
    comp=J.read(str(b/"COMPONENTS.json"), max_bytes=8*1024*1024).get(cid)
    if not comp: raise Refusal("master workflow component not found")
    vol=b/"source"/comp["source_archive"]
    source=None
    with zipfile.ZipFile(vol) as z:
        target=[n for n in z.namelist() if n.endswith(f"/components/{cid}.jsonl")]
        if len(target)!=1: raise Refusal("component source entry missing")
        for line in z.read(target[0]).decode("utf-8").splitlines():
            rec=J.loads(line)
            if rec.get("id")==wanted: source=rec; break
    if source is None: raise Refusal("source prompt/workflow ID not found")
    disposition=None
    for rec in _records(b/"ledger.jsonl.gz"):
        if rec["id"]==wanted: disposition=rec; break
    if disposition is None: raise Refusal("task missing from disposition ledger")
    return {"schema":"UC/MASTER_WORKFLOW_TASK/1","source":source,"disposition":disposition,
            "component_disposition":comp}


PLAN = {
  1:["test_foundation.StrictJSON","test_foundation.ContractTests"],
  2:["test_foundation.Lifecycle","test_hardening.Lifecycle"],
  3:["test_pixel_fabric.AdmissionTests","test_pixel_fabric.HistoryTests"],
  4:["test_pixel_fabric.IndependentInteropTests","test_pixel_fabric.KernelTests"],
  5:["test_master_workflow.KernelContractTests","test_pixel_fabric.KernelTests"],
  6:["test_vws_integration.VWSIntegration","test_hardening.Names"],
  7:["test_platform_services.EventAndAuditTests","test_platform_services.MetricTests"],
  8:["test_platform_services.QueueTests","test_platform_services.HealthTests"],
  9:["test_foundation.Transactions","test_onebit.RecoveryReplayTests"],
 10:["test_master_workflow.MasterWorkflowTests"],
 11:["test_vws_integration.VWSIntegration"],
 12:["test_platform_services.ConfigTests","test_platform_services.HardwareTests"],
 13:["test_pixel_fabric.CapacityTests","test_foundation.Objects"],
 14:["test_platform_services.ConfigTests","test_platform_services.QueueTests"],
 15:["test_master_workflow.KernelContractTests","test_onebit.EquivalenceTests"],
}


def execute(root):
    check(root, deep=False)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out=Path(SAFE.contained_path(str(root), f"_runs/masterflow/{stamp}")); out.mkdir(parents=True)
    results=[]
    for volume, classes in PLAN.items():
        name=f"VOL_{volume:02d}"; log=out/(name+".log")
        cmd=[sys.executable,"-B","-m","unittest","-v",*classes]
        with log.open("wb") as fh:
            try:
                p=subprocess.run(cmd,cwd=Path(root)/"tests",stdout=fh,stderr=subprocess.STDOUT,timeout=120,check=False)
                code=p.returncode
            except subprocess.TimeoutExpired:
                code=124
        results.append({"volume":name,"local_tests":"PASS" if code==0 else "FAIL","exit":code,
                        "command":cmd,"log":log.relative_to(root).as_posix(),"log_sha256":_sha(log),
                        "source_task_promotion":"NONE","scope":"bounded local candidate evidence only"})
    value={"schema":"UC/MASTER_WORKFLOW_EXECUTION/1","candidate":"UC-2.7.0","source_version":"1.0.0",
           "results":results,"local_test_failures":sum(r["exit"]!=0 for r in results),
           "source_tasks_promoted_pass":0,"full_series_complete":False}
    SAFE.atomic_json(str(out/"RESULTS.json"),value)
    return value


def configure(sp):
    p=sp.add_parser("master-workflow",help="375,000-record master-series traceability and bounded local execution")
    p.add_argument("verb",choices=("status","check","show","execute"));p.add_argument("task",nargs="?")
    p.add_argument("--deep",action="store_true");p.set_defaults(fn=run)


def run(a):
    root=E.ship_root()
    if a.verb=="status": value=status(root)
    elif a.verb=="check": value=check(root,a.deep)
    elif a.verb=="show": value=show(root,a.task or "")
    else: value=execute(root)
    print(J.dumps(value,indent=2,sort_keys=True));return 1 if value.get("local_test_failures",0) else 0
