"""Regenerate reference fixtures (MC-019).  Valid fixtures come from real code paths
(PK_SANDBOX_APPLIED/2 from a real kernel-verified launch with a *fixture-only* key);
each invalid fixture is a valid one with exactly one defect, named in the file."""
from __future__ import annotations

import copy
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))
pkg = __import__(HERE.name)
from importlib import import_module
att = import_module(HERE.name + ".attestation")
ctl = import_module(HERE.name + ".control")
rt = import_module(HERE.name + ".runtime")
errors = import_module(HERE.name + ".errors")
profiles = import_module(HERE.name + ".profiles")

FIXTURE_KEY = b"inv39-fixture-key-not-for-production-use!!"
V, I = HERE / "fixtures" / "valid", HERE / "fixtures" / "invalid"


def dump(d, name, obj):
    (d / name).write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")


def main():
    V.mkdir(parents=True, exist_ok=True)
    I.mkdir(parents=True, exist_ok=True)
    prof = pkg.SandboxProfile("svc", frozenset({"read", "write", "exit_group"}))
    dump(V, "profile-1.json", prof.as_dict())
    box = pkg.Sandbox("p1", prof)
    dump(V, "applied-1.json", box.start(readback=box.requested_state()))
    dump(V, "error-1.json", errors.SandboxError("E_QUOTA_EXCEEDED", "tenant t1 at quota").payload(trace_id="0" * 31 + "1"))
    authz = ctl.Authorizer()
    authz.grant("fixture-op", "tenant-operator", "t1")
    svc = rt.SandboxService(identity=att.NodeIdentity("node-fixture", FIXTURE_KEY),
                            principal_keys={"fixture-op": FIXTURE_KEY}, authz=authz)
    out = svc.launch(rt.LaunchRequest(token=ctl.issue_token(FIXTURE_KEY, "fixture-op", svc.AUDIENCE, 60),
                                      tenant="t1", workload="w1", profile=profiles.load_profile("posix-minimal"),
                                      argv=("/bin/true",)))
    a2 = out["evidence"]
    dump(V, "applied-2.json", a2)
    negatives = {
        "profile-1.missing-digest.json": (prof.as_dict(), lambda d: d.pop("digest")),
        "profile-1.extra-field.json": (prof.as_dict(), lambda d: d.__setitem__("privileged", True)),
        "profile-1.bad-digest.json": (prof.as_dict(), lambda d: d.__setitem__("digest", "md5:abc")),
        "applied-1.claims-os-proof.json": (json.loads((V / "applied-1.json").read_text()),
                                           lambda d: d.__setitem__("os_enforcement_proven", True)),
        "applied-2.not-verified.json": (a2, lambda d: d.__setitem__("verified", False)),
        "applied-2.caller-supplied.json": (a2, lambda d: d.__setitem__("evidence_source", "caller_supplied")),
        "applied-2.unsigned.json": (a2, lambda d: d.pop("signature")),
        "applied-2.bad-namespace.json": (a2, lambda d: d.__setitem__("namespaces", ["host"])),
        "error-1.bad-outcome.json": (json.loads((V / "error-1.json").read_text()), lambda d: d.__setitem__("outcome", "fine")),
        "error-1.bool-as-code.json": (json.loads((V / "error-1.json").read_text()), lambda d: d.__setitem__("code", True)),
    }
    for name, (base, mut) in negatives.items():
        d = copy.deepcopy(base)
        mut(d)
        dump(I, name, d)
    print(f"wrote {len(list(V.iterdir()))} valid and {len(list(I.iterdir()))} invalid fixtures")


if __name__ == "__main__":
    main()
