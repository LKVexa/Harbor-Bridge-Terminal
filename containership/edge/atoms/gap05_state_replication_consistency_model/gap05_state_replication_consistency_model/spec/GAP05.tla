---------------------------- MODULE GAP05 ----------------------------
(* GAP-05 causal frontier with bounded active set, quarantine and resolution.     *)
(* Review artifact for MC48.  NOT model-checked with TLC in the v4.3.0 build (no  *)
(* TLC available); the executable bounded checker production/modelcheck.py checks *)
(* the same invariants against the shipped Python code.  Status: NOT_RUN.         *)
EXTENDS Naturals, FiniteSets, Sequences

CONSTANTS Sites, MaxSiblings, Writes   \* Writes: set of records [site, vec, val]

VARIABLES delivered, frontier, active

Dominates(a, b) == /\ \A s \in Sites : a[s] >= b[s]
                   /\ \E s \in Sites : a[s] > b[s]

Rank(S) == CHOOSE f \in [1..Cardinality(S) -> S] : \A i, j \in 1..Cardinality(S) :
             i < j => f[i].vec # f[j].vec   \* deterministic total order (vector-first)

Init == /\ delivered = {} /\ frontier = {} /\ active = {}

Apply(w) ==
  /\ w \in Writes
  /\ delivered' = delivered \cup {w}
  /\ frontier' = IF \E f \in frontier : Dominates(f.vec, w.vec) \/ f = w
                 THEN frontier
                 ELSE {f \in frontier : ~Dominates(w.vec, f.vec)} \cup {w}
  /\ active' = {x \in frontier' : Cardinality({y \in frontier' : y.vec < x.vec}) < MaxSiblings}

Next == \E w \in Writes : Apply(w)

(* ---------------------------- invariants ---------------------------- *)
Antichain  == \A x, y \in frontier : ~Dominates(x.vec, y.vec)
Cover      == \A d \in delivered : d \in frontier \/ \E f \in frontier : Dominates(f.vec, d.vec)
Bound      == Cardinality(active) <= MaxSiblings /\ active \subseteq frontier
(* Convergence (order independence) is a hyperproperty; checked by enumerating  *)
(* all delivery orders in production/modelcheck.py.                             *)

Spec == Init /\ [][Next]_<<delivered, frontier, active>>
THEOREM Spec => [](Antichain /\ Cover /\ Bound)
=============================================================================
