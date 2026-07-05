"""Verify the exact relaxation used by the hand proof of Case B:
premises = per-vertex hole caps into the four 5-parts ONLY
           (<=2 into P1, <=1 into P2,P3,P4; NO P0-direction budgets)
         + S1 blocking clauses (P0-edge transversal K6s) ONLY.
Hand claim: min holes >= 12 (proof gives exactly the 3-per-non-isolated-
P0-vertex count).  Report the solver's true min of this relaxation.
"""
import sys, json
from itertools import combinations, product
from ortools.sat.python import cp_model

P0 = list(range(0,6)); P1 = list(range(6,11)); P2 = list(range(11,16))
P3 = list(range(16,21)); P4 = list(range(21,26))
PARTS = [P0,P1,P2,P3,P4]
part_of = {v:i for i,P in enumerate(PARTS) for v in P}
CROSS = [(a,b) for a,b in combinations(range(26),2) if part_of[a]!=part_of[b]]
CIDX = {e:i for i,e in enumerate(CROSS)}
CONFIGS = {
    "star":  [(0,1),(0,2),(0,3),(0,4)],
    "C4":    [(0,1),(1,2),(2,3),(0,3)],
    "paw":   [(0,1),(1,2),(0,2),(0,3)],
    "P3P3":  [(0,1),(1,2),(3,4),(4,5)],
}
for cname, cedges in CONFIGS.items():
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(CROSS))]
    def hv(a,b): return h[CIDX[(min(a,b),max(a,b))]]
    caps = {1:2, 2:1, 3:1, 4:1}
    for w in range(26):
        for pi in (1,2,3,4):
            if part_of[w]==pi: continue
            m.Add(sum(hv(w,p) for p in PARTS[pi]) <= caps[pi])
    for (u,v) in cedges:
        for ws in product(P1,P2,P3,P4):
            lits=[hv(u,w) for w in ws]+[hv(v,w) for w in ws]+[hv(a,b) for a,b in combinations(ws,2)]
            m.AddBoolOr(lits)
    m.Minimize(sum(h))
    s = cp_model.CpSolver(); s.parameters.max_time_in_seconds=600; s.parameters.num_search_workers=8
    st = s.Solve(m)
    nh = sum(s.Value(x) for x in h) if st in (cp_model.OPTIMAL,cp_model.FEASIBLE) else None
    print(f"[hand-premises] {cname}: {s.StatusName(st)} min={nh} bound={s.BestObjectiveBound()}", flush=True)
