"""Operator explain view (MC-063): turns one audit-ledger decision into a readable account.

The view is rendered only from recorded data (ledger entry + the policy digest it names), so what
an operator reads is what was decided, not a re-evaluation against today's state.  If the current
policy digest differs from the recorded one the view says so.
"""
from __future__ import annotations


def render(entry: dict, current_policy=None) -> str:
    p = entry["payload"]
    req = p.get("request", {})
    lines = [f"Decision {p.get('decision_id', '')[:16]}  (ledger #{entry['seq']}, {entry['at']})",
             f"Outcome : {p.get('outcome')}" + (f"  -> {p['toolchain']}" if p.get("toolchain") else f"  code={p.get('code')}"),
             "Request : " + ", ".join(f"{k}={req[k]}" for k in ("environment", "language", "architecture", "runtime",
                                                              "hypervisor", "provider", "abi") if req.get(k)),
             f"          devices={req.get('devices', [])} features={req.get('features', [])}"
             + (f" site={req['site']['site_id']}" if req.get("site") else ""),
             f"Registry: revision {p.get('registry_revision')}",
             f"Policy  : digest {str(p.get('policy_digest'))[:16]}"]
    if current_policy is not None and current_policy.digest != p.get("policy_digest"):
        lines.append("          NOTE: policy has changed since this decision; the account below is as decided.")
    if p.get("certification_id"):
        lines.append(f"GAP-15  : certificate {p['certification_id']}")
    if p.get("waivers"):
        lines.append(f"Waivers : {', '.join(p['waivers'])}")
    elim = p.get("eliminated") or []
    if elim:
        lines.append("Eliminated candidates:")
        for e in elim:
            lines.append(f"  - {e['toolchain']}: {', '.join(e['codes'])}")
    unmet = p.get("unmet") or {}
    if unmet:
        lines.append("Unmet constraints:")
        for code, refs in sorted(unmet.items()):
            lines.append(f"  - {code}: {', '.join(refs)}")
    return "\n".join(lines) + "\n"
