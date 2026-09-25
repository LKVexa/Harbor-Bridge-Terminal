# Authoritative master-source artifact (MC-003) — OPEN (external)

The 4.1.0 README referenced a verbatim `MASTER.md` that was never in the archive. 4.2.0 removed the reference;
4.3.0 does **not** reconstruct it, because a reconstruction would be presented as source material it is not.

What exists instead: `CHECKLIST.json` (100 items) and the supplied
`inv62_edge_topology_v4.2.0_MISSING_COMPONENTS_ENGINEERING_CHECKLIST.md` (94 MC items, SHA-256
`6d8bed00…e4c9`, preserved in the work order). The requirements derived for this release are in
`conformance/requirements.json` and are traceable to both.

To close: obtain the original master source from the series owner (Post-Kubernetes Master Prompt & Workflow
Series v4.0.0), add it with its digest and provenance, and reconcile `requirements.json` against it.
