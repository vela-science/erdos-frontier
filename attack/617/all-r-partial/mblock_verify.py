#!/usr/bin/env python3
"""Machine verification of the all-r DP/matching blocking theorem (2026-06-16).

THEOREM (Erdos #617, all-r aggregation kernel).
Let s >= 2 and take s parts E_1,...,E_s. Between every ordered pair of parts the
"blocker" edges form a matching (each vertex has <= 1 blocker into each other
part). MBLOCK(sizes) = the minimum number of blocker edges that hit every
transversal (x_1,...,x_s) in E_1 x ... x E_s (i.e. leave no independent
transversal).  Then

    MBLOCK_s(s-1) := MBLOCK(s-1, s-1, ..., s-1)  =  (s-1) * C(s,2),
    MBLOCK(s, s-1, ..., s-1)                     =  infinity.

This recovers the three constants certified for r=5
    MBLOCK(2,2,2)=6,  MBLOCK(3,2,2)=inf,  BLOCK(3,3,3,3)=18
and predicts new ones (s=5: 40, etc.).  This script confirms the formula by
exact CP-SAT minimisation (infeasible model == infinity).

Run: python3 mblock_verify.py
"""
from itertools import combinations, product
from ortools.sat.python import cp_model
import math, time, sys


def mblock(sizes, tl=300):
    s = len(sizes)
    parts = [list(range(z)) for z in sizes]
    m = cp_model.CpModel()
    edge = {}
    for i, j in combinations(range(s), 2):
        for u in parts[i]:
            for v in parts[j]:
                edge[(i, u, j, v)] = m.NewBoolVar(f"e{i}_{u}_{j}_{v}")
    # matching constraint: each vertex has <= 1 blocker into each other part
    for i, j in combinations(range(s), 2):
        for u in parts[i]:
            m.Add(sum(edge[(i, u, j, v)] for v in parts[j]) <= 1)
        for v in parts[j]:
            m.Add(sum(edge[(i, u, j, v)] for u in parts[i]) <= 1)
    # every transversal must contain at least one blocked pair
    for tr in product(*parts):
        m.AddBoolOr([edge[(i, tr[i], j, tr[j])] for i, j in combinations(range(s), 2)])
    m.Minimize(sum(edge.values()))
    sv = cp_model.CpSolver()
    sv.parameters.max_time_in_seconds = tl
    sv.parameters.num_search_workers = 8
    st = sv.Solve(m)
    if st == cp_model.INFEASIBLE:
        return ("inf", None)
    if st == cp_model.OPTIMAL:
        return ("opt", int(round(sv.ObjectiveValue())))
    if st == cp_model.FEASIBLE:
        return ("feas", int(round(sv.ObjectiveValue())))
    return (sv.StatusName(st), None)


def pred(s):
    return (s - 1) * math.comb(s, 2)


CASES = [
    # (sizes, expected): all-(s-1) cases -> (s-1)C(s,2); one-part-s cases -> inf
    ((2, 2, 2),          6),
    ((3, 2, 2),          "inf"),
    ((3, 3, 3, 3),       18),
    ((4, 3, 3, 3),       "inf"),
    ((4, 4, 4, 4, 4),    40),
    ((5, 4, 4, 4, 4),    "inf"),
]

if __name__ == "__main__":
    ok = True
    for sizes, exp in CASES:
        t = time.time()
        kind, val = mblock(sizes)
        got = "inf" if kind == "inf" else val
        match = (got == exp) if kind in ("inf", "opt") else False
        ok &= match
        print(f"  {str(sizes):16s} -> {str(got):4s}  expected {str(exp):4s}  "
              f"[{'OK' if match else 'MISMATCH'}]  ({time.time()-t:.0f}s)", flush=True)
    print("\nALL MATCH GPT's formula (s-1)C(s,2) / infinity." if ok
          else "\n*** MISMATCH -- formula refuted ***")
    sys.exit(0 if ok else 1)
