#!/usr/bin/env python3
"""Single P0-edge demand as a function of the 5-part internal-edge profile.

Fix an internal edge uv inside P0 (the 6-part), shape (6,5,5,5,5). The four
5-parts P1..P4 carry e_i internal edges each (profile (e1,e2,e3,e4)). We
compute the MINIMUM number of holes that must be "charged to this edge":
namely the holes incident to u or v (endpoint holes) PLUS the between-5-part
holes needed to block the U-grid, where U_i = P_i ∩ N(u) ∩ N(v).

Foothold 1: u (and v) each have <= 1 + e_i holes into P_i, so
|U_i| >= 5 - 2(1+e_i) = 3 - 2 e_i in the worst case... but that can go
negative. The right statement: holes(u into P_i)+holes(v into P_i) costs
endpoint holes, and shrinks |U_i|. We do NOT fix |U_i|; we let the solver
choose the endpoint-hole pattern and the U_i, paying for everything.

This is a LOCAL model around one edge: parts are empty except for the
budget LOOSENING e_i (we do NOT here add the OTHER parts' internal edges as
K6 pressure -- that only ADDS holes, so the number we get is a valid LOWER
bound on the true per-edge charge). The between-part holes here are the
holes among P1..P4; we ALSO count the endpoint holes u,v -> P_i.

Returns: min over admissible (endpoint holes + grid-blocking holes).
With e_i loosened, a vertex of P_i may have up to 1+e_i holes into another
part -- but WAIT: the budget 1+e_i is into P_i (incoming), governs how many
holes land ON a P_i vertex from outside. The matching constraint on the
U-grid between P_i and P_j: a P_i vertex has <= 1+e_i holes into P_j? NO --
Foothold 1 is {w}∪P_j: a P_i vertex w has <= 1+e_j holes into P_j. So the
column budget (into P_j) is 1+e_j, the row budget (into P_i) is 1+e_i.
"""
import itertools
from ortools.sat.python import cp_model


def single_edge_demand(profile, time_limit=120, workers=8, full_endpoints=True):
    """profile = (e1,e2,e3,e4): internal edges in P1..P4.
    Returns min holes charged to one P0-edge uv: endpoint holes (u,v into
    P1..P4) + between-part holes blocking the U-grid.

    Model: vertices of P1..P4 indexed 0..4 each. u,v are apexes.
    var hu[i][a] = 1 if u-a(i) is a hole (a in P_i). Similarly hv.
    U_i = { a : not hu[i][a] and not hv[i][a] }.
    var hh[(i,j,a,b)] = hole between a in P_i and b in P_j.
    K6 block: for every transversal a1..a4 with all ai in U_i (i.e. neither
    u nor v misses ai) AND all cross pairs present -> forbidden. Encode:
    for each transversal, OR over [ hu[i][ai], hv[i][ai] (i=1..4),
    hh among the pairs ].
    Budgets: u into P_i <= 1+e_i; v into P_i <= 1+e_i.
             a in P_i, holes into P_j (the hh): row a sum_b hh <= 1+e_j;
             col b sum_a hh <= 1+e_i.  (Foothold 1, both directions.)
    Minimize sum hu + sum hv + sum hh.
    """
    SZ = 5
    parts = list(range(4))  # P1..P4 as 0..3
    e = list(profile)
    m = cp_model.CpModel()
    hu = [[m.new_bool_var(f"hu_{i}_{a}") for a in range(SZ)] for i in parts]
    hv = [[m.new_bool_var(f"hv_{i}_{a}") for a in range(SZ)] for i in parts]
    hh = {}
    for (i, j) in itertools.combinations(parts, 2):
        for a in range(SZ):
            for b in range(SZ):
                hh[(i, j, a, b)] = m.new_bool_var(f"hh_{i}_{j}_{a}_{b}")
    # endpoint budgets
    for i in parts:
        m.add(sum(hu[i]) <= 1 + e[i])
        m.add(sum(hv[i]) <= 1 + e[i])
    # between-part matching budgets (Foothold 1 both directions)
    for (i, j) in itertools.combinations(parts, 2):
        for a in range(SZ):  # row a in P_i: holes into P_j  <= 1+e_j
            m.add(sum(hh[(i, j, a, b)] for b in range(SZ)) <= 1 + e[j])
        for b in range(SZ):  # col b in P_j: holes into P_i  <= 1+e_i
            m.add(sum(hh[(i, j, a, b)] for a in range(SZ)) <= 1 + e[i])
    # K6 blocking over all transversals
    for t in itertools.product(range(SZ), repeat=4):
        lits = []
        for i in parts:
            lits.append(hu[i][t[i]])
            lits.append(hv[i][t[i]])
        for (i, j) in itertools.combinations(parts, 2):
            lits.append(hh[(i, j, t[i], t[j])])
        m.add_bool_or(lits)
    obj = sum(sum(hu[i]) for i in parts) + sum(sum(hv[i]) for i in parts) \
        + sum(hh.values())
    m.minimize(obj)
    s = cp_model.CpSolver()
    s.parameters.num_search_workers = workers
    s.parameters.max_time_in_seconds = time_limit
    st = s.solve(m)
    if st == cp_model.INFEASIBLE:
        return None
    assert st in (cp_model.OPTIMAL, cp_model.FEASIBLE), s.status_name(st)
    return int(round(s.objective_value)), (st == cp_model.OPTIMAL)


if __name__ == "__main__":
    print("Single P0-edge demand vs 5-part edge-profile (6,5,5,5,5):")
    print("(endpoint holes into P1..P4 + between-5-part grid-blocking holes)")
    profiles = [
        (0, 0, 0, 0),  # Case A: empty 5-parts -> expect 8+18 = 26
        (1, 0, 0, 0),  # one part carries an edge
        (1, 1, 0, 0),
        (1, 1, 1, 0),
        (1, 1, 1, 1),
        (2, 0, 0, 0),
        (2, 1, 0, 0),
        (2, 2, 0, 0),
        (3, 0, 0, 0),
        (2, 2, 1, 0),
        (2, 2, 1, 1),
        (2, 2, 2, 0),
    ]
    for p in profiles:
        r = single_edge_demand(p)
        if r is None:
            print(f"  profile {p}: INFEASIBLE (no valid hole pattern!?)")
        else:
            val, opt = r
            tag = "" if opt else " (not proven optimal -- LOWER bound may be loose)"
            print(f"  profile {p}: single-edge demand = {val}{tag}")
