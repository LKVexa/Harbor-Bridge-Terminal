# Vulnerability, patch and end-of-life policy (G13-MC-048)

* **Intake:** security reports to the security owner (OWNERS.yaml); acknowledge within 2 business days.
* **Severity and response SLA (fix available / deployed):** Critical 72 h / 7 d · High 7 d / 14 d · Medium 30 d / 60 d · Low next minor.
* **Supported branches:** current minor (5.0.x) and previous major's last minor (4.2.x) for security fixes only, until 2027-03-31. 4.2.x is **not** safe for untrusted bundles (caller-asserted verification) and is EOL for new deployments now.
* **Dependencies:** `cryptography` pinned to a supported line; review monthly and on every advisory; dependency/licence scan is a release-gate input.
* **EOL rule:** a minor is EOL 6 months after the next minor ships; EOL is announced in `CHANGELOG.md` one release in advance.
* **Disclosure:** coordinated, 90 days default.
* **Crypto agility:** new algorithms are added only to the verifier allowlist in code, never negotiated from bundle metadata; removal of an algorithm is a minor release with a trust-store migration note.
