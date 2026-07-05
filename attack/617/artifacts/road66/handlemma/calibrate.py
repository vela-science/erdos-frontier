#!/usr/bin/env python3
"""Calibration: true minimum holes for configs the oracle CAN solve, to
understand the adversary's optimal defense and where the budget cap bites.

We minimize holes (not decision-at-cap) on (6,5,5,5,5) configs with various
e(P0) and 5-part edge distributions, at small total I, recording the true
minimum. This tells us, per config family, the slack against cap = I+q.
"""
import sys, time, itertools
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
import general_rung as G
from ortools.sat.python import cp_model

# Build a minimize-holes model from the same full-spec encoding as general_rung,
# but WITHOUT a hole cap (so we get the true minimum). We reuse build() with a
# large cap and then minimize.

ALLPAIRS26 = G.ALLPAIRS26
PIDX26 = G.PIDX26


def min_holes(sizes, E, cap_for_model=40, time_limit=120, workers=8):
    parts, off, part_of = [], 0, {}
    for pi, n in enumerate(sizes):
        for v in range(off, off + n):
            part_of[v] = pi
        off += n
    Eset = set((min(a, b), max(a, b)) for a, b in E)
    cross = [PIDX26[(a, b)] for (a, b) in ALLPAIRS26 if part_of[a] != part_of[b]]
    cset = set(cross); cpos = {pi: i for i, pi in enumerate(cross)}
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(cross))]
    m.Add(sum(h) <= cap_for_model)
    for S in itertools.combinations(range(26), 6):
        cids, intra = [], []
        for a, b in itertools.combinations(S, 2):
            pi = PIDX26[(a, b)]
            if pi in cset:
                cids.append(cpos[pi])
            else:
                intra.append((a, b))
        intraE = sum(1 for p in intra if p in Eset)
        rhs = len(cids) + intraE - 4
        if rhs < 0:
            return ("INTRA_INFEAS", None)
        if rhs < min(len(cids), cap_for_model):
            m.Add(sum(h[i] for i in cids) <= rhs)
        if intraE == len(intra):
            m.AddBoolOr([h[i] for i in cids])
    m.Minimize(sum(h))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = time_limit
    s.parameters.num_search_workers = workers
    st = s.Solve(m)
    name = s.StatusName(st)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return (name, int(round(s.ObjectiveValue())), int(round(s.BestObjectiveBound())))
    return (name, None, int(round(s.BestObjectiveBound())) if st != cp_model.UNKNOWN else None)


if __name__ == "__main__":
    sizes = (6, 5, 5, 5, 5)
    P0 = list(range(6))
    Pj = {1: list(range(6, 11)), 2: list(range(11, 16)),
          3: list(range(16, 21)), 4: list(range(21, 26))}
    # P0 configs
    star = [(0, 1), (0, 2), (0, 3), (0, 4)]
    paw = [(0, 1), (1, 2), (0, 2), (0, 3)]
    K3K2 = [(0, 1), (1, 2), (0, 2), (3, 4)]
    C4 = [(0, 1), (1, 2), (2, 3), (0, 3)]

    def edge(p, k):  # k-th edge inside part p (p in 1..4)
        v = Pj[p]
        pairs = [(v[0], v[1]), (v[2], v[3]), (v[0], v[2]), (v[1], v[3]), (v[0], v[3])]
        return pairs[k]

    tests = []
    # I=4 (Case A, all in P0): true min should be ~ big
    tests.append(("e0=4 star, 5-parts empty (I=4)", star))
    # I=5: one edge in P1
    tests.append(("e0=4 star + 1 edge P1 (I=5)", star + [edge(1, 0)]))
    # I=6: edges in P1,P2
    tests.append(("e0=4 star + edges P1,P2 (I=6)", star + [edge(1, 0), edge(2, 0)]))
    # I=6: two edges in P1
    tests.append(("e0=4 star + 2 edges P1 (I=6)", star + [edge(1, 0), edge(1, 1)]))
    # I=7: edges P1,P2,P3
    tests.append(("e0=4 star + edges P1,P2,P3 (I=7)", star + [edge(1, 0), edge(2, 0), edge(3, 0)]))
    # I=8: edges P1,P2,P3,P4
    tests.append(("e0=4 star + edges P1..P4 (I=8)", star + [edge(1, 0), edge(2, 0), edge(3, 0), edge(4, 0)]))
    # I=8: 2 edges each in P1,P2
    tests.append(("e0=4 star + 2 in P1, 2 in P2 (I=8)", star + [edge(1, 0), edge(1, 1), edge(2, 0), edge(2, 1)]))

    for name, E in tests:
        I = len(E)
        t = time.time()
        res = min_holes(sizes, E, time_limit=90)
        print(f"  {name}: I={I}, min_holes={res} ({round(time.time()-t)}s)", flush=True)
        for q in (8, 9, 10):
            cap = I + q  # defect 0
            print(f"      q={q}: cap={cap}", flush=True)
