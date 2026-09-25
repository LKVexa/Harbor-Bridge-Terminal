"""Deterministically regenerate schemas/error_codes.json and the WIT error-code enum
from the stable codes raised in source.  Run: python3 tools/gen_contracts.py [--check]
--check exits 1 if the committed artifacts differ from what would be generated."""
import json, pathlib, re, sys
PKG = pathlib.Path(__file__).resolve().parents[1]
NOT_ERRORS = {"PK_CORE_PATH", "PK_CORE_OK"}


def codes():
    found = set()
    for p in sorted(PKG.glob("*.py")):
        found |= set(re.findall(r'"(PK_[A-Z_]+)"', p.read_text()))
    return sorted(found - NOT_ERRORS)


RETRY = {  # family/code -> (class, caller action)
    "PK_POLL_OVERLOADED": ("transient", "retry with jittered exponential backoff (base 50 ms, cap 5 s)"),
    "PK_POLL_TENANT_QUOTA": ("quota", "reduce concurrent polls for this tenant; retry after an in-flight poll completes"),
    "PK_POLL_CANCELLED": ("caller", "do not retry unless the caller issues a new request"),
    "PK_POLL_DRAINING": ("policy", "do not retry; the legacy path is being disabled -- use INV-15"),
    "PK_POLL_DISABLED": ("policy", "do not retry; use INV-15"),
    "PK_POLL_QUARANTINED": ("policy", "do not retry; escalate to the INV-14 owner"),
    "PK_POLL_FAILED_STATE": ("policy", "do not retry; escalate"),
    "PK_AUDIT_UNAVAILABLE": ("dependency", "retry after audit sink recovery; operation was refused, not performed"),
}
FAMILY = {"POLL": ("permanent", "fix the request; retrying the same request fails identically"),
          "AUDIT": ("dependency", "operator action on the audit sink"), "CLOCK": ("permanent", "fix configuration"),
          "CONFIG": ("permanent", "fix configuration"), "CORE": ("permanent", "pin/install the exact pk_core"),
          "CHECKPOINT": ("permanent", "start from safe defaults; investigate storage"),
          "GOVERNANCE": ("permanent", "fix governance data"), "MIGRATION": ("permanent", "follow migration runbook"),
          "ADJACENT": ("dependency", "supply adjacent layers")}


def classify(c):
    if c in RETRY:
        return RETRY[c]
    if c.startswith("PK_POLL_TOKEN") or c.startswith("PK_POLL_IDENTITY") or c in ("PK_POLL_FOREIGN_OWNER", "PK_POLL_NO_TRUST_ROOT"):
        return ("security", "do not retry; obtain a valid capability for the owning principal")
    if c in ("PK_POLL_UNREGISTERED_CONSUMER", "PK_POLL_MIGRATION_OVERDUE", "PK_POLL_MIGRATION_REGRESSION", "PK_POLL_EOL_REMOVED", "PK_POLL_REGISTRY_CLOSED"):
        return ("governance", "register the consumer, obtain a waiver, or complete migration to INV-15")
    return FAMILY.get(c.split("_")[1], ("permanent", "see error details"))


def wit_name(c):
    return c[3:].lower().replace("_", "-")


def main(check=False):
    cs = codes()
    reg = {"schema": "PK_POLL_ERROR_CODES/1", "version": "4.3.0",
           "details_policy": "details are bounded (16 keys, 256 chars) and tenant-safe: they never name another principal, key material or local paths",
           "codes": [{"code": c, "wit": wit_name(c), "family": c.split("_")[1], "retry_class": classify(c)[0],
                      "caller_action": classify(c)[1]} for c in cs]}
    reg_txt = json.dumps(reg, indent=1, sort_keys=True) + "\n"
    wit_p = PKG / "wit" / "inv14-legacy-poll.wit"
    wit = wit_p.read_text()
    enum = "  enum error-code {\n" + "".join(f"    {wit_name(c)},\n" for c in cs) + "  }"
    new_wit = re.sub(r"  enum error-code \{.*?\n  \}", lambda m: enum, wit, count=1, flags=re.S)
    reg_p = PKG / "schemas" / "error_codes.json"
    err_p = PKG / "schemas" / "pk_poll_error.schema.json"
    err = json.loads(err_p.read_text())
    err["properties"]["code"]["enum"] = cs
    err_txt = json.dumps(err, indent=1, sort_keys=True) + "\n"
    if check:
        ok = (reg_p.exists() and reg_p.read_text() == reg_txt and new_wit == wit and err_p.read_text() == err_txt)
        print("contracts up to date" if ok else "contracts STALE")
        return 0 if ok else 1
    reg_p.write_text(reg_txt)
    wit_p.write_text(new_wit)
    err_p.write_text(err_txt)
    print(f"{len(cs)} codes")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
