# GAP-02 Support & Security Lifecycle Policy (GAP02-MC-50) — DRAFT

- **Versioning:** SemVer. Schema majors (`NAME/N`) change only in a GAP-02 major release; error codes are append-only (`errors.RESERVED`).
- **Support windows (proposed):** latest minor fully supported; previous minor security fixes for 6 months after the next minor ships.
- **Vulnerability intake:** report privately to the GAP-02 owner (contact _UNASSIGNED_); triage within 5 business days; fix-or-mitigate targets Critical 14 d, High 30 d, Medium 90 d.
- **Security fixes** that touch the promotion gate, envelope, replay or authz require an independent reviewer and a regression test.
- **Deprecation:** announced one minor ahead; removed features keep their error codes reserved.
- **Review cadence:** re-review this policy when supported platforms, trust model or dependencies change, and at least every 12 months.

_Status: draft — windows, contact and SLAs require owner approval._
