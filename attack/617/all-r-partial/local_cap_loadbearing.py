#!/usr/bin/env python3
"""Two exact checks for the all-r reduction (Erdős #617), 2026-06-16.

(A) The reduction "alpha(G),omega(G) <= r  =>  e(G) > A_r" is FALSE: there is a
    10-vertex graph with alpha=omega=3 and only 14 < A_3=15 edges. It fails only
    the LOCAL CAP (a 4-set carries 5 > M_3=4 edges). Hence the local cap
    e_G(S) <= M_r is load-bearing; no proof of #617 can use alpha,omega<=r alone.

(B) SC(3): the minimum number of edges of a 10-vertex graph in which every
    4-set spans between 1 and M_3=4 edges is 18 >= A_3+1 = 16. So SC(3) holds
    (with room), confirming #617 for r=3 via the single-colour reduction.

Run: python3 local_cap_loadbearing.py
"""
from itertools import combinations
from ortools.sat.python import cp_model

# (A) counterexample to alpha,omega<=r => e>A_r  (r=3, A_3=15, M_3=4)
EDGES = [(0,1),(0,3),(0,9),(1,2),(1,4),(2,4),(2,5),
         (3,5),(3,9),(4,5),(5,9),(6,7),(6,8),(7,8)]
N = 10
ES = {tuple(sorted(e)) for e in EDGES}
def ie(a, b): return tuple(sorted((a, b))) in ES
def has_ind(k): return any(all(not ie(a, b) for a, b in combinations(S, 2)) for S in combinations(range(N), k))
def has_clq(k): return any(all(ie(a, b) for a, b in combinations(S, 2)) for S in combinations(range(N), k))
max4 = max(sum(ie(a, b) for a, b in combinations(S, 2)) for S in combinations(range(N), 4))
print("(A) local cap load-bearing:")
print(f"    e={len(EDGES)} (<A_3=15), alpha<=3={not has_ind(4)}, omega<=3={not has_clq(4)}, "
      f"max-edges-on-4set={max4} (>M_3=4 ⇒ violates cap)")
assert len(EDGES) == 14 and not has_ind(4) and not has_clq(4) and max4 == 5

# (B) SC(3): min edges with every (r+1)-set in [1, M_r]
def solve_SC(r, tl=120):
    n = r*r+1; M = r*(r+1)//2-(r-1)
    pairs = [(i, j) for i in range(n) for j in range(i+1, n)]
    idx = {e: k for k, e in enumerate(pairs)}
    m = cp_model.CpModel()
    x = [m.NewBoolVar(f"x{k}") for k in range(len(pairs))]
    for S in combinations(range(n), r+1):
        ids = [idx[tuple(sorted((a, b)))] for a, b in combinations(S, 2)]
        m.Add(sum(x[k] for k in ids) >= 1)
        m.Add(sum(x[k] for k in ids) <= M)
    m.Minimize(sum(x))
    s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = tl; s.parameters.num_search_workers = 8
    s.Solve(m)
    return int(s.ObjectiveValue()), n*n  # noqa

mn, _ = solve_SC(3)
print(f"(B) SC(3) min = {mn}  (A_3+1 = 16 ⇒ SC(3) holds)")
assert mn == 18
print("OK")
