"""Migration from traditional IaC -- INV-06 -> INV-07 (component 31).

Resource authority moves through explicit, audited states per resource
partition (e.g. a namespace)::

    iac_owned -> dual_observe -> dual_run -> gitops_owned
         ^            |              |
         +------------+--------------+   (rollback boundary: any state before
                                          gitops_owned may return to iac_owned)

* ``dual_observe`` -- INV-07 renders and diffs but never mutates; the dual-run
  detector compares IaC-planned state with Git desired state.
* ``dual_run`` -- INV-07 applies only objects whose ownership annotation it
  already holds; IaC applies the rest; any object both would change is a
  **conflict** that blocks cutover.
* ``gitops_owned`` -- cutover is allowed only when the stabilisation criteria
  hold: N consecutive clean dual-run comparisons, zero conflicts, zero
  unowned objects in the partition, and a named approver.  After cutover the
  IaC pipeline for the partition must be disabled (recorded, not enforced
  here).

Lineage (previous owner, IaC state digest, first GitOps OID) is kept on every
transition so the history of each resource survives the move.
"""
from __future__ import annotations

from .errors import Conflict, Unauthorized

STATES = ("iac_owned", "dual_observe", "dual_run", "gitops_owned")
ALLOWED = {("iac_owned", "dual_observe"), ("dual_observe", "dual_run"), ("dual_run", "gitops_owned"),
           ("dual_observe", "iac_owned"), ("dual_run", "iac_owned"), ("dual_run", "dual_observe")}


def compare(iac: dict, gitops: dict) -> dict:
    """Dual-run detector over {rid: digest} maps."""
    only_iac = sorted(set(iac) - set(gitops))
    only_git = sorted(set(gitops) - set(iac))
    diff = sorted(r for r in set(iac) & set(gitops) if iac[r] != gitops[r])
    return {"clean": not (only_iac or only_git or diff), "only_iac": only_iac, "only_gitops": only_git,
            "conflicts": diff}


class Partition:
    def __init__(self, name: str, *, audit=None, required_clean_runs: int = 3) -> None:
        self.name, self.audit, self.need = name, audit, required_clean_runs
        self.state, self.clean_runs, self.lineage = "iac_owned", 0, []

    def observe(self, result: dict) -> None:
        self.clean_runs = self.clean_runs + 1 if result["clean"] else 0

    def transition(self, to: str, *, actor: str, approver: str | None = None, iac_digest: str | None = None,
                   first_oid: str | None = None) -> dict:
        if (self.state, to) not in ALLOWED:
            raise Conflict("illegal migration transition", frm=self.state, to=to)
        if to == "gitops_owned":
            if self.clean_runs < self.need:
                raise Conflict("stabilisation criteria not met", clean_runs=self.clean_runs, need=self.need)
            if not approver or approver == actor:
                raise Unauthorized("cutover requires a distinct named approver")
        rec = {"partition": self.name, "from": self.state, "to": to, "actor": actor, "approver": approver,
               "iac_digest": iac_digest, "first_oid": first_oid, "clean_runs": self.clean_runs}
        self.lineage.append(rec)
        self.state = to
        if self.audit:
            self.audit.append("migration.transition", rec, actor=actor)
        return rec

    def may_mutate(self, owned_by_us: bool) -> bool:
        return self.state == "gitops_owned" or (self.state == "dual_run" and owned_by_us)
