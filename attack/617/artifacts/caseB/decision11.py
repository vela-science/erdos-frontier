"""Two sharp decision checks for the Case B hand proof:

1. hand-premises relaxation at <= 11 holes:
   premises = per-vertex hole caps into the four 5-parts only
   (<=2 into P1, <=1 into P2,P3,P4) + S1 blocking clauses only.
   Hand proof claims these alone force >= 12 holes -> expect INFEASIBLE.

2. full Case-B spec at <= 11 holes -> expect INFEASIBLE (a fortiori).

Both for all nine P0 configs.
"""
import sys
from itertools import combinations, product
from ortools.sat.python import cp_model
from caseB_model import (CROSS, CIDX, CONFIGS, PARTS, part_of, P1, P2, P3, P4,
                         build_full, solve)

def hand_decision(cedges, cap):
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(CROSS))]
    def hv(a, b): return h[CIDX[(min(a, b), max(a, b))]]
    caps = {1: 2, 2: 1, 3: 1, 4: 1}
    for w in range(26):
        for pi in (1, 2, 3, 4):
            if part_of[w] == pi: continue
            m.Add(sum(hv(w, p) for p in PARTS[pi]) <= caps[pi])
    for (u, v) in cedges:
        for ws in product(P1, P2, P3, P4):
            m.AddBoolOr([hv(u, w) for w in ws] + [hv(v, w) for w in ws] +
                        [hv(a, b) for a, b in combinations(ws, 2)])
    m.Add(sum(h) <= cap)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = 300
    s.parameters.num_search_workers = 8
    return s.StatusName(s.Solve(m))

which = sys.argv[1]
for cname, cedges in CONFIGS.items():
    if which == "hand11":
        print(f"[hand-premises <=11] {cname}: {hand_decision(cedges, 11)}", flush=True)
    elif which == "full11":
        m, h, _, _ = build_full(cedges, hole_cap=11, model_cap_for_constraints=12)
        st, nh, holes, _ = solve(m, h, minimize=False, time_limit=600)
        print(f"[F<=11] {cname}: {st}", flush=True)
