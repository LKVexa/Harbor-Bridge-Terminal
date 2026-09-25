"""Multi-dimensional gravity planner (G14-P2-28..36).

Hard constraints are evaluated first and eliminate options outright (legality,
convergence, compute compatibility, quota, thermal headroom, route
availability).  Only surviving options are scored by an explicit objective:

    score = money + time_value_per_hour * transfer_hours + carbon_price_per_kg * kg_co2

where every term is reported per option, so the choice is explainable.
Energy/carbon is modelled for compute at the execution site only; network transfer
energy is deliberately excluded (no validated per-route energy model) rather than
estimated with false precision (G14-P2-32 A09).

With no ``WorkloadProfile`` supplied the planner reduces *exactly* to the v4.2.0
engine semantics (two options, money only, tie -> move-compute); a property test
(tests/test_property_fuzz.py) checks the equivalence on random inputs.

Options
-------
move-compute     relocate compute to the data site (warm-up amortised over runs)
move-data        transfer the full dataset
move-data-partial transfer only the shards the workload reads (P2-28)
replicate        keep a synchronised replica at the compute site (P2-30)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Any, Callable, Mapping, Sequence

from .errors import G14Error
from .trust import exact_fields, ident, number

ORDER = {"move-compute": 0, "move-data-partial": 1, "move-data": 2, "replicate": 3}


@dataclass(frozen=True)
class Shard:
    name: str
    size_gb: float
    needed: bool
    converged: bool = True


@dataclass(frozen=True)
class SiteEconomics:
    """Per-site economics (P2-32 carbon/power/thermal, P2-34 storage/IOPS)."""
    carbon_g_per_kwh: float = 0.0
    power_price_per_kwh: float = 0.0
    thermal_headroom_kw: float = float("inf")
    storage_per_gb_month: float = 0.0
    read_per_gb: float = 0.0
    write_per_gb: float = 0.0
    per_million_iops: float = 0.0
    min_charge: float = 0.0
    rounding_gb: float = 0.0          # provider bills in increments (0 = exact)


@dataclass(frozen=True)
class WorkloadProfile:
    runs: int = 1                            # P2-29 repeated-job amortisation horizon
    compute_warmup_cost: float = 0.0         # one-off at a new site, amortised over runs
    cache_reuse_fraction: float = 0.0        # fraction of transfer reused across runs
    read_gb_per_run: float = 0.0
    write_gb_per_run: float = 0.0
    iops_per_run: float = 0.0
    compute_kwh_per_run: float = 0.0
    compute_kw: float = 0.0
    shards: tuple[Shard, ...] = ()
    replica_months: float = 0.0              # >0 enables replicate option
    replica_sync_gb_per_run: float = 0.0
    time_value_per_hour: float = 0.0
    carbon_price_per_kg: float = 0.0

    @classmethod
    def parse(cls, raw: Mapping[str, Any] | None) -> "WorkloadProfile | None":
        if raw is None:
            return None
        names = [f for f in cls.__dataclass_fields__ if f != "shards"]
        exact_fields(raw, "profile", [], names + ["shards"])
        kw: dict[str, Any] = {}
        for n in names:
            if n in raw:
                kw[n] = number(raw[n], f"profile.{n}", maximum=1e12)
        if "runs" in kw:
            kw["runs"] = int(kw["runs"])
            if kw["runs"] < 1:
                raise G14Error("G14_INVALID_REQUEST", "profile.runs must be >= 1")
        if kw.get("cache_reuse_fraction", 0) > 1:
            raise G14Error("G14_INVALID_REQUEST", "cache_reuse_fraction must be <= 1")
        shards = []
        for s in raw.get("shards", []) or []:
            exact_fields(s, "profile.shard", ["name", "size_gb", "needed"], ["converged"])
            if not isinstance(s["needed"], bool) or not isinstance(s.get("converged", True), bool):
                raise G14Error("G14_INVALID_REQUEST", "shard flags must be bool")
            shards.append(Shard(ident(s["name"], "shard.name"), number(s["size_gb"], "shard.size_gb"), s["needed"], s.get("converged", True)))
        if len(shards) > 10_000:
            raise G14Error("G14_PAYLOAD_TOO_LARGE", "too many shards")
        return cls(shards=tuple(shards), **kw)


@dataclass(frozen=True)
class Route:
    locality_multiplier: float
    egress_per_gb: float
    available: bool = True
    bandwidth_gbps: float = 1.0
    congestion: float = 0.0

    def transfer_hours(self, gb: float) -> float:
        """P2-33: effective throughput = bandwidth * (1 - congestion)."""
        eff = self.bandwidth_gbps * (1.0 - self.congestion)
        return 0.0 if gb == 0 else (gb * 8.0) / eff / 3600.0


@dataclass
class PlanInputs:
    dataset: str
    data_site: str
    compute_site: str
    size_gb: float
    classification: str
    converged: bool
    legal: Callable[[str], tuple[bool, str]]             # site -> (ok, reason)
    routes: Mapping[tuple[str, str], Route]
    compute_ok: Callable[[str], tuple[bool, str]]          # site -> (ok, reason)
    quota_ok: Callable[[str, float], tuple[bool, str]]     # (site, gb) -> (ok, reason)
    compute_relocation_cost: float
    economics: Mapping[str, SiteEconomics] = field(default_factory=dict)
    profile: WorkloadProfile | None = None


def _billable(gb: float, econ: SiteEconomics) -> float:
    if econ.rounding_gb > 0 and gb > 0:
        return ceil(gb / econ.rounding_gb) * econ.rounding_gb
    return gb


def plan(inp: PlanInputs) -> dict[str, Any]:
    """Return {options, eliminated, best} with full per-dimension breakdowns."""
    from .engine import CostModelError, NoLegalOption  # local: keep planner importable standalone

    p = inp.profile
    runs = p.runs if p else 1
    options: list[dict[str, Any]] = []
    eliminated: list[dict[str, str]] = []

    def elim(direction: str, code: str, reason: str) -> None:
        eliminated.append({"direction": direction, "code": code, "reason": reason})

    def route(a: str, b: str, direction: str) -> Route | None:
        if a == b:
            return Route(0.0, 0.0)
        r = inp.routes.get((a, b))
        if r is None:
            raise CostModelError(f"missing locality multiplier for {a}->{b}",
                                 details={"from_site": a, "to_site": b, "field": "distance"})
        if not r.available:
            elim(direction, "ROUTE_UNAVAILABLE", f"route {a}->{b} unavailable")
            return None
        return r

    def site_econ(s: str) -> SiteEconomics:
        return inp.economics.get(s, SiteEconomics())

    def run_costs(site: str) -> dict[str, float]:
        """Per-run storage IOPS/read/write, energy and carbon at the execution site."""
        if not p:
            return {"storage_io": 0.0, "energy": 0.0, "kg_co2": 0.0}
        e = site_econ(site)
        io = (_billable(p.read_gb_per_run, e) * e.read_per_gb + _billable(p.write_gb_per_run, e) * e.write_per_gb
              + p.iops_per_run / 1e6 * e.per_million_iops)
        io = max(io, e.min_charge) if io > 0 else 0.0
        return {"storage_io": io, "energy": p.compute_kwh_per_run * e.power_price_per_kwh,
                "kg_co2": p.compute_kwh_per_run * e.carbon_g_per_kwh / 1000.0}

    def thermal_ok(site: str) -> bool:
        return not p or p.compute_kw <= site_econ(site).thermal_headroom_kw

    def finalize(direction: str, to: str, money_once: float, gb_moved: float, r: Route, extra: dict[str, Any]) -> None:
        exec_site = to if direction == "move-compute" else inp.compute_site
        rc = run_costs(exec_site)
        reuse = p.cache_reuse_fraction if p else 0.0
        hours = r.transfer_hours(gb_moved)
        per_run_money = money_once / runs + rc["storage_io"] + rc["energy"] + extra.pop("recurring_money", 0.0)
        per_run_hours = hours / runs if direction != "move-compute" else 0.0
        if p and direction in ("move-data", "move-data-partial") and reuse < 1.0 and runs > 1:
            # cache reuse: fraction (1-reuse) of the transfer recurs each subsequent run
            per_run_money += (1 - reuse) * money_once * (runs - 1) / runs
            per_run_hours += (1 - reuse) * hours * (runs - 1) / runs
        score = per_run_money
        if p:
            score += p.time_value_per_hour * per_run_hours + p.carbon_price_per_kg * rc["kg_co2"]
        breakdown = {"kind": direction, "from": inp.data_site if direction != "move-compute" else inp.compute_site,
                     "to": to, "one_time_money": money_once, "runs": runs, "per_run_money": per_run_money,
                     "transfer_hours": hours, "per_run_kg_co2": rc["kg_co2"], "storage_io_per_run": rc["storage_io"],
                     "energy_per_run": rc["energy"], "locality_multiplier": r.locality_multiplier, **extra}
        options.append({"direction": direction, "to": to, "cost": score, "cost_breakdown": breakdown})

    # --- A: move compute to the data
    ok, why = inp.legal(inp.data_site)
    if not ok:
        elim("move-compute", "RESIDENCY_FORBIDDEN", why)
    else:
        cok, cwhy = inp.compute_ok(inp.data_site)
        if not cok:
            elim("move-compute", "COMPUTE_UNAVAILABLE" if ("capacity" in cwhy or "free" in cwhy) else "COMPUTE_INCOMPATIBLE", cwhy)
        elif not thermal_ok(inp.data_site):
            elim("move-compute", "THERMAL_LIMIT", f"{inp.data_site} thermal headroom below {p.compute_kw:g} kW")  # type: ignore[union-attr]
        else:
            r = route(inp.compute_site, inp.data_site, "move-compute")
            if r is not None:
                money = inp.compute_relocation_cost * r.locality_multiplier + (p.compute_warmup_cost if p else 0.0)
                finalize("move-compute", inp.data_site, money, 0.0, r, {"base_compute_move_cost": inp.compute_relocation_cost})

    # --- B/C/D: bring data to the compute
    ok, why = inp.legal(inp.compute_site)
    data_dirs = ["move-data"] + (["move-data-partial"] if p and p.shards else []) + (["replicate"] if p and p.replica_months > 0 else [])
    if not ok:
        for d in data_dirs:
            elim(d, "RESIDENCY_FORBIDDEN", why)
    elif not thermal_ok(inp.compute_site):
        for d in data_dirs:
            elim(d, "THERMAL_LIMIT", f"{inp.compute_site} thermal headroom below {p.compute_kw:g} kW")  # type: ignore[union-attr]
    else:
        r = route(inp.data_site, inp.compute_site, "move-data")
        if r is not None:
            econ_dst = site_econ(inp.compute_site)
            # full move
            if not inp.converged:
                elim("move-data", "DATASET_NOT_CONVERGED", f"{inp.dataset} has unresolved replication conflicts")
            else:
                qok, qwhy = inp.quota_ok(inp.compute_site, inp.size_gb)
                if not qok:
                    elim("move-data", "QUOTA_EXCEEDED", qwhy)
                else:
                    gb = _billable(inp.size_gb, econ_dst)
                    finalize("move-data", inp.compute_site, gb * r.egress_per_gb * r.locality_multiplier, inp.size_gb, r,
                             {"size_gb": inp.size_gb, "egress_per_gb": r.egress_per_gb})
            # partial (P2-28): only needed shards; each needed shard must itself be converged
            if p and p.shards:
                needed = [s for s in p.shards if s.needed]
                if not needed:
                    elim("move-data-partial", "NOTHING_NEEDED", "profile marks no shard as needed")
                elif any(not s.converged for s in needed):
                    elim("move-data-partial", "DATASET_NOT_CONVERGED", "a needed shard has unresolved conflicts")
                elif sum(s.size_gb for s in p.shards) - inp.size_gb > 1e-9 * max(1.0, inp.size_gb):
                    elim("move-data-partial", "SHARD_MODEL_INCONSISTENT", "shard sizes exceed dataset size")
                else:
                    gb = sum(s.size_gb for s in needed)
                    qok, qwhy = inp.quota_ok(inp.compute_site, gb)
                    if not qok:
                        elim("move-data-partial", "QUOTA_EXCEEDED", qwhy)
                    else:
                        finalize("move-data-partial", inp.compute_site, _billable(gb, econ_dst) * r.egress_per_gb * r.locality_multiplier,
                                 gb, r, {"size_gb": gb, "shards": [s.name for s in needed], "egress_per_gb": r.egress_per_gb})
            # replicate (P2-30): requires convergence; storage + sync lifecycle cost
            if p and p.replica_months > 0:
                if not inp.converged:
                    elim("replicate", "DATASET_NOT_CONVERGED", f"{inp.dataset} has unresolved replication conflicts")
                else:
                    qok, qwhy = inp.quota_ok(inp.compute_site, inp.size_gb)
                    if not qok:
                        elim("replicate", "QUOTA_EXCEEDED", qwhy)
                    else:
                        seed = _billable(inp.size_gb, econ_dst) * r.egress_per_gb * r.locality_multiplier
                        storage = inp.size_gb * econ_dst.storage_per_gb_month * p.replica_months
                        sync = p.replica_sync_gb_per_run * r.egress_per_gb * r.locality_multiplier
                        finalize("replicate", inp.compute_site, seed + storage, inp.size_gb, r,
                                 {"size_gb": inp.size_gb, "replica_storage": storage, "sync_per_run": sync,
                                  "recurring_money": sync, "consistency": "GAP-05 async replica; reads bounded by replica lag"})

    if not options:
        raise NoLegalOption(f"{inp.dataset}: no legal way to co-locate with compute at {inp.compute_site}",
                            details={"dataset": inp.dataset, "compute_site": inp.compute_site, "eliminated": eliminated})
    best = min(options, key=lambda o: (o["cost"], ORDER[o["direction"]]))
    options.sort(key=lambda o: ORDER[o["direction"]])
    return {"options": options, "eliminated": eliminated, "best": best}


# ---------------------------------------------------------------- DAG (P2-31)
@dataclass(frozen=True)
class Stage:
    name: str
    inputs: tuple[str, ...]              # dataset names or upstream stage names
    output_gb: float = 0.0


def optimize_dag(stages: Sequence[Stage], datasets: Mapping[str, Mapping[str, Any]], candidate_sites: Sequence[str],
                 pair_cost: Callable[[str, float, str, str, str], float | None], relocation: Callable[[str], float],
                 *, max_assignments: int = 200_000) -> dict[str, Any]:
    """Assign each stage a compute site minimising total movement cost.

    ``datasets[name]`` = {"site", "size_gb", "classification"}.  ``pair_cost(name,
    gb, classification, from, to)`` returns the legal move cost or ``None`` if the
    move is illegal (residency/convergence/quota).  Exhaustive search when the
    assignment space is small enough (exact optimum); otherwise greedy in
    topological order (method reported, never silently).
    """
    names = [s.name for s in stages]
    if len(set(names)) != len(names):
        raise G14Error("G14_INVALID_REQUEST", "duplicate stage names")
    by_name = {s.name: s for s in stages}
    order: list[str] = []
    state: dict[str, int] = {}

    def visit(n: str) -> None:
        if state.get(n) == 1:
            raise G14Error("G14_INVALID_REQUEST", "stage graph has a cycle", details={"stage": n})
        if state.get(n) == 2:
            return
        state[n] = 1
        for i in by_name[n].inputs:
            if i in by_name:
                visit(i)
            elif i not in datasets:
                raise G14Error("G14_INVALID_REQUEST", f"unknown input {i}")
        state[n] = 2
        order.append(n)
    for n in names:
        visit(n)

    cls_of: dict[str, str] = {}
    for n in order:  # derived outputs carry every upstream classification (strictest-wins)
        acc: set[str] = set()
        for i in by_name[n].inputs:
            acc.update((datasets[i]["classification"],) if i in datasets else cls_of[i].split("+"))
        cls_of[n] = "+".join(sorted(acc))

    def stage_cost(n: str, site: str, assign: Mapping[str, str]) -> float | None:
        total = relocation(site)
        for i in by_name[n].inputs:
            if i in datasets:
                d = datasets[i]
                c = pair_cost(i, d["size_gb"], d["classification"], d["site"], site)
            else:
                up = by_name[i]
                c = pair_cost(i, up.output_gb, cls_of[i], assign[i], site)
            if c is None:
                return None
            total += c
        return total

    space = len(candidate_sites) ** len(order)
    best: tuple[float, dict[str, str]] | None = None
    method = "exhaustive" if space <= max_assignments else "greedy-topological"
    if method == "exhaustive":
        import itertools
        for combo in itertools.product(candidate_sites, repeat=len(order)):
            assign = dict(zip(order, combo))
            total = 0.0
            for n in order:
                c = stage_cost(n, assign[n], assign)
                if c is None:
                    break
                total += c
            else:
                if best is None or total < best[0] - 1e-12:
                    best = (total, assign)
    else:
        assign: dict[str, str] = {}
        total = 0.0
        for n in order:
            costs = [(c, s) for s in candidate_sites if (c := stage_cost(n, s, assign)) is not None]
            if not costs:
                best = None
                break
            c, s = min(costs)
            assign[n], total = s, total + c
        else:
            best = (total, assign)
    if best is None:
        from .engine import NoLegalOption
        raise NoLegalOption("no legal assignment for DAG", details={"stages": order})
    return {"method": method, "total_cost": best[0], "assignment": best[1], "order": order}
