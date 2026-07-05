#!/usr/bin/env python3
"""Independent recheck of the multiedge agent's "18-lemma" (artifacts lost).

Single internal edge uv in P0, all four 5-parts empty.  U_i = common
H-neighbours of u,v in part i, |U_i| = 3 (pinned).  K6-avoidance: every
transversal (w1,w2,w3,w4) in U1xU2xU3xU4 with all six cross pairs present
is a K6 (with u,v) and is forbidden.  So the between-5-part "holes" must
hit every transversal.

Foothold 1 (empty parts): each vertex has <= 1 hole into each other part,
so between U_i and U_j the holes form a PARTIAL MATCHING (<=3 per pair).

QUESTION: minimum number of between-part holes to block all 81 transversals?
  agent claims 18 (all six pair-matchings perfect).
  pure covering volume bound is 81/9 = 9.
We compute the exact minimum (a) with the matching constraint, (b) without,
by exact CP-SAT.  Total single-edge demand = 8 endpoint holes + this.
"""
import itertools
from ortools.sat.python import cp_model

PARTS = 4
SZ = 3
pairs = list(itertools.combinations(range(PARTS), 2))


def solve(matching_constraint):
    m = cp_model.CpModel()
    # hole[(i,j,a,b)] : missing edge between vertex a of part i and b of part j
    hole = {}
    for (i, j) in pairs:
        for a in range(SZ):
            for b in range(SZ):
                hole[(i, j, a, b)] = m.new_bool_var(f"h_{i}_{j}_{a}_{b}")
    # block every transversal
    for t in itertools.product(range(SZ), repeat=PARTS):
        lits = []
        for (i, j) in pairs:
            lits.append(hole[(i, j, t[i], t[j])])
        m.add_bool_or(lits)
    if matching_constraint:
        for (i, j) in pairs:
            for a in range(SZ):                      # i-side: vertex a <=1 hole into part j
                m.add(sum(hole[(i, j, a, b)] for b in range(SZ)) <= 1)
            for b in range(SZ):                      # j-side: vertex b <=1 hole into part i
                m.add(sum(hole[(i, j, a, b)] for a in range(SZ)) <= 1)
    m.minimize(sum(hole.values()))
    s = cp_model.CpSolver()
    s.parameters.num_search_workers = 8
    st = s.solve(m)
    return s.status_name(st), int(s.objective_value)


for mc in (True, False):
    name, val = solve(mc)
    label = "with matching constraint" if mc else "pure covering (no matching)"
    print(f"{label:32s}: {name}, min between-part holes = {val}")
    print(f"   => single-edge demand = 8 (endpoints) + {val} = {8+val}")
