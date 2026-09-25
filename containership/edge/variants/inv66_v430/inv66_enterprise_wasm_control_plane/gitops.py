"""GitOps desired-state ingestion (MC-021).

A change-set is a directory checked out from Git at a known commit::

    <root>/
      CHANGESET.json      {"schema": "PK_ECP_CHANGESET/1", "commit": "<sha>", "author": "...",
                           "tenant": "...", "lattice": "...", "applications": ["app.json", ...]}
      app.json            INV-64 Application documents

:func:`ingest` converts each application with the INV-64 adapter, submits it
through the normal authenticated admission path (so GitOps gets no bypass),
and uses ``<commit>:<file>`` as the idempotency key so re-running the same
commit is a no-op.  The result lists every decision for the CI status check.
A webhook receiver or repository watcher calls ``ingest`` after checkout;
reconciliation remains INV-63's job.
"""
from __future__ import annotations

import json
import pathlib
import re

from .adapters import manifest_from_application
from .errors import ControlPlaneError, fail

_SHA = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")


def ingest(svc, token: str, root: str | pathlib.Path, environment: str | None = None) -> dict:
    root = pathlib.Path(root).resolve()
    cs = json.loads((root / "CHANGESET.json").read_text())
    if cs.get("schema") != "PK_ECP_CHANGESET/1" or not _SHA.match(str(cs.get("commit", ""))):
        raise fail("SCHEMA_INVALID", "CHANGESET.json must carry schema PK_ECP_CHANGESET/1 and a full commit sha")
    results = []
    for rel in cs.get("applications", []):
        path = (root / rel).resolve()
        if not path.is_relative_to(root):
            raise fail("SCHEMA_INVALID", f"application path escapes change-set: {rel}")
        app = json.loads(path.read_text())
        req = {"protocol": "PK_ECP_ADMIT/1", "request_id": f"gitops-{cs['commit'][:12]}-{path.stem}"[:200],
               "idempotency_key": f"{cs['commit']}:{rel}"[:256].replace("/", "_"),
               "tenant": cs["tenant"], "lattice": cs["lattice"], "manifest": manifest_from_application(app)}
        if environment:
            req["environment"] = environment
        try:
            r = svc.admit(token, req)
            results.append({"file": rel, "decision_id": r["decision_id"], "admitted": r["admitted"],
                            "errors": [e["code"] for e in r["errors"]], "replayed": r["replayed"]})
        except ControlPlaneError as exc:
            results.append({"file": rel, "decision_id": None, "admitted": False, "errors": [exc.error.code]})
    return {"commit": cs["commit"], "all_admitted": all(r["admitted"] for r in results), "results": results}
