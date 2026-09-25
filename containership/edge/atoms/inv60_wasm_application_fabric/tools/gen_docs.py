"""Generate human-readable docs from their machine-readable sources (no drift):
REQUIREMENTS.md, THREAT_MODEL.md, LIFECYCLE.md, PLACEMENT.md, CONFIG_REFERENCE.md,
MASTER_INDEX.md. ``--check`` exits 1 if any generated file is stale."""
import hashlib, json, pathlib, re, sys
PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent)); sys.dont_write_bytecode = True
from inv60_wasm_application_fabric.fabric import lifecycle, placement, config

D = PKG / "docs"
out = {}
req = json.loads((D / "requirements.json").read_text())
md = ["# Normative requirements (M08) — generated from requirements.json", "",
      f"Terminology: {req['terminology']}. Version {req['version']}. Deployment classes: {', '.join(req['deployment_classes'])}.", "",
      "| id | level | kind | requirement | verified by | criticality | owner |", "|---|---|---|---|---|---|---|"]
for r in req["requirements"]:
    md.append(f"| {r['id']} | {r['level']} | {r['kind']} | {r['text']} | `{r['verification'][0]}` | {r['criticality']} | {r['owner']} |")
md += ["", "**Prohibited states:** " + "; ".join(req["prohibited_states"]), "",
       f"**Control plane:** {req['planes']['control']}.  **Data plane:** {req['planes']['data']}.", "",
       "**Non-goals:** " + "; ".join(req["non_goals"])]
out["REQUIREMENTS.md"] = "\n".join(md) + "\n"

tm = json.loads((D / "THREAT_MODEL.json").read_text())
md = ["# Threat model (M34) — generated from THREAT_MODEL.json", "", f"Method: {tm['method']}", "",
      "**Assets:** " + ", ".join(tm["assets"]), "", "**Trust boundaries:** " + "; ".join(tm["trust_boundaries"]), "",
      "**Attackers:** " + ", ".join(tm["attackers"]), "", "## Data flow", "```mermaid", "flowchart LR",
      "  OP[Operator / CI] -->|signed tokens| CP[INV-60 control plane]", "  WL[Workload caller] -->|capability call| CP",
      "  CP -->|NATS over TLS| H1[wasmCloud host]", "  H1 --> G[Wasm guest]", "  G -->|link| PR[Capability provider]",
      "  CP --> ID[(Identity / policy / secrets)]", "  CP --> TE[(Telemetry export)]", "  CP --> LG[(Audit ledger)]", "```", "",
      "## Threats", "| id | flow | STRIDE | threat | L/I | controls | verified by |", "|---|---|---|---|---|---|---|"]
for t in tm["threats"]:
    md.append(f"| {t['id']} | {t['flow']} | {t['stride']} | {t['threat']} | {t['likelihood']}/{t['impact']} | "
              f"{'; '.join(t['controls'])} | {'<br>'.join('`' + x + '`' for x in t['verification'])} |")
md += ["", "## Residual risks (proposed, unapproved)"] + [f"- **{r['id']}** {r['risk']} — owner {r['owner']}, review by {r['expiry']}" for r in tm["residual_risks"]]
md += ["", f"Review cadence {tm['review']['cadence_days']} days; triggers: {', '.join(tm['review']['triggers'])}. Last review: none."]
out["THREAT_MODEL.md"] = "\n".join(md) + "\n"

out["LIFECYCLE.md"] = ("# Lifecycle state machines (M10) — generated from fabric/lifecycle.py\n\n"
    "States — component: " + ", ".join(lifecycle.COMPONENT_STATES) + "; host: " + ", ".join(lifecycle.HOST_STATES) +
    "; link: " + ", ".join(lifecycle.LINK_STATES) + ".\n\nAny (state, event) pair not listed is **illegal** and returns "
    "`ILLEGAL_TRANSITION` without mutating state. Repeating an event whose target is the current state is an idempotent no-op. "
    "Mutations are serialized by the control-plane mutex and fenced by the lease epoch; every transition is persisted to the WAL "
    "before it is acknowledged, so a crash between WAL append and acknowledgement replays to the same state. After restart, "
    "links are reconstructed as `revoked` (fail closed).\n\n" + lifecycle.transition_table_markdown() + "\n")

out["PLACEMENT.md"] = ("# Placement precedence (M14) — generated from fabric/placement.py\n\n"
    f"Policy `{placement.PRECEDENCE_VERSION}`. Hard (absolute, in order): {', '.join(placement.HARD)}. "
    f"Soft (optimised lexicographically): {', '.join(placement.SOFT)}, then load, then host id.\n\n"
    f"Only `{', '.join(sorted(placement.RELAXABLE))}` may be relaxed, and only with a break-glass decision id; the relaxation is recorded.\n\n"
    "## Worked example\nHosts: `a` (eu, latency 1, cost 2), `b` (eu, latency 1, cost 2), `c` (us, latency 0, cost 9). "
    "Request: component `x`, regions `[eu]`.\n\n1. security/isolation pass for all. 2. residency removes `c`. 3. capacity/anti-affinity pass. "
    "4. soft: `a` and `b` tie on latency and cost and load. 5. tie-break by id → **a**. The decision record lists all 15 rule evaluations.\n")

rows = ["| field | type | default | constraint | overlay protection |", "|---|---|---|---|---|"]
for k, (typ, dflt, cons, prot) in config.SCHEMA.items():
    rows.append(f"| `{k}` | {typ.__name__} | `{json.dumps(dflt)}` | {cons if cons is not None else ''} | {prot or ''} |")
out["CONFIG_REFERENCE.md"] = (f"# Configuration reference (M27) — generated from fabric/config.py\n\nSchema `{config.CONFIG_SCHEMA_VERSION}`. "
    "Unknown fields are rejected. Secrets are references `secret://<backend>/<path>#v<n>` only.\n\n"
    f"Overlay trust order: {json.dumps(config.TRUST_ORDER)}.\n\n" + "\n".join(rows) + "\n")

master = (PKG / "MASTER.md").read_bytes()
text = master.decode()
cids = sorted(set(re.findall(r"INV-60-C(\d{3})", text)))
out["MASTER_INDEX.md"] = ("# MASTER.md index (M01)\n\n| field | value |\n|---|---|\n"
    "| artifact id | INV-60-MASTER |\n| source | Post-Kubernetes Master Prompt & Workflow Series v4.0.0 (owner-supplied), restored verbatim from the UC32 payload |\n"
    f"| sha256 | `{hashlib.sha256(master).hexdigest()}` |\n| bytes | {len(master)} |\n| requirement sections | {len(cids)} (C{cids[0]}–C{cids[-1]}) |\n"
    "| repository compatibility | 4.x |\n| approval state | **unapproved** (no owner sign-off recorded) |\n| last review | none |\n\n"
    "MASTER.md is normative source material for the 100 checklist items; CHECKLIST.json is its machine-readable projection "
    "(ids must match — enforced by `tests/test_governance.py::Docs`). Edits to MASTER.md are breaking when they add, remove or renumber "
    "a C-id, and require owner review.\n\nWorkflow phases W0–W9 map to checklist dimensions as in `pk_core/component.py::STAGE_DIMENSIONS`; "
    "M-items map to C-ids in `tools/m_registry.py::CITES` and `release/TRACEABILITY.json`.\n")

stale = []
for name, body in out.items():
    p = D / name
    if "--check" in sys.argv:
        if not p.exists() or p.read_text() != body:
            stale.append(name)
    else:
        p.write_text(body)
if stale:
    print("stale generated docs:", stale); sys.exit(1)
print("docs ok" if "--check" in sys.argv else f"wrote {len(out)} docs")
