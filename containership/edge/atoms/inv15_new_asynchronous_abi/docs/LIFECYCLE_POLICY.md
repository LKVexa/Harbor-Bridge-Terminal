# Patch, vulnerability and EOL policy (component 72) — PROPOSED, unapproved
- Semantic versioning on the package; interface version (pk:async@1.x) moves independently and only additively within a major.
- Security fixes: patch release within 7 days of confirmed P0, 30 days for P1; advisories list affected versions and handle-format impact.
- Support window: current minor + previous minor; a minor reaches EOL 6 months after its successor ships.
- Discriminants, error codes and handle format v1 are never repurposed, even after EOL.
- No owner, security contact or advisory channel has been named — that is the owner's decision.
