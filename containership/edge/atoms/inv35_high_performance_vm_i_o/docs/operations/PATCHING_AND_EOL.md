# Patching, vulnerability response and end-of-life (C094)

| Severity (CVSS / impact) | Triage | Fix available | Fleet patched |
|---|---|---|---|
| Critical (guest→host escape, isolation break) | 4 h | 72 h | 7 d |
| High | 1 business day | 14 d | 30 d |
| Medium | 5 business days | 60 d | next MINOR |
| Low | best effort | next MINOR | next MINOR |

* Intake: `SECURITY.md` (private channel); CVE feed reviewed monthly (REV-DEPS).
* Embargo: fixes developed privately; disclosure coordinated with affected backends.
* **EOL:** a MINOR is supported until 90 days after the next MINOR; a MAJOR 12 months after the next MAJOR. EOL dates published in `CHANGELOG.md`. After EOL: no fixes; release gate refuses promotion of EOL versions (future work: gate reads EOL table).
