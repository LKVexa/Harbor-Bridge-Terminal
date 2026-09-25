"""Dependency-free INV-41 security smoke check."""
from __future__ import annotations

from .capabilities import Authority, Forged, Membrane, Revoked, Widening


def run() -> dict:
    authority = Authority({"store": {"read", "write"}}, authority_id="inv41-selfcheck")
    holder = authority.bind_holder("api", {"store": authority.grant("store")})
    narrowed = holder.delegate("store", {"read"})
    checks = {"narrow_read": narrowed.invoke("read")["permitted"]}

    try:
        holder.delegate("store", {"read", "write", "admin"})
    except Widening:
        checks["widening_refused"] = True
    else:
        checks["widening_refused"] = False

    try:
        holder.use("missing", "read")
    except Forged:
        checks["ambient_lookup_refused"] = True
    else:
        checks["ambient_lookup_refused"] = False

    membrane = Membrane("selfcheck")
    wrapped = membrane.wrap(narrowed)
    membrane.revoke()
    try:
        wrapped.invoke("read")
    except Revoked:
        checks["revocation_enforced"] = True
    else:
        checks["revocation_enforced"] = False

    return {"schema": "INV41_SELFCHECK/1", "passing": all(checks.values()), "checks": checks}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), sort_keys=True))
