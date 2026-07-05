#!/usr/bin/env python3
"""Exact holes forced by an edge-graph F1 inside ONE 5-part P1, with P0 and
the other 5-parts EMPTY (shape 6,5,5,5,5). This isolates the 'W-system'
demand of a single edge-bearing 5-part.

K6 sources (with P0,P2,P3,P4 internally empty so each contributes an
independent set => at most one vertex per such part to a clique):
 - any edge/clique of F1 in P1 + completion vertices across {P0,P2,P3,P4}.
   A K6 = (clique S in P1) ∪ (clique T across other parts, |S|+|T|=6, all
   cross pairs present). Since P0,P2,P3,P4 are independent, T has <=1 vertex
   per part, so |T| <= 4, hence |S| >= 2: S is an EDGE/clique of F1.

We DON'T fix the structure; we just build the exact local model over the 26
vertices (P1 has F1 edges; all other parts empty) keeping ALL K6-blocking
clauses + Foothold budgets, and minimize holes. This is a valid LOWER bound
on the contribution of F1, and EXACT for the 'one edge-bearing part'
subproblem (since with all other parts empty, the only intra edges are F1).

Budgets (Foothold-1):
 - w -> empty 5-part: <=1.   w -> P1 (e1 edges): <= 1+e1, but tighter via
   5-subsets: w -> P1\{z}: <= 1 + e1 - deg_{P1}(z).
 - w -> P0 (size6, empty): the 6-set {w}∪(5 of P0) has 0 intra edges =>
   w has <=1 hole into every 5-subset of P0 => <=1 hole into P0 total
   (if it had 2 holes into P0, some 5-subset would have 2 holes -> the
   6-set {w}∪that-5-subset spans 5-2=3<4 edges). So w -> P0: <= 1.
   [P0 empty 6-part behaves like a 5-part for budgets: <=1 hole.]
"""
import sys, itertools
from math import comb
from ortools.sat.python import cp_model


def one_part_demand(F1_edges, time_limit=120, workers=8, n0=6):
    """F1_edges: edges inside P1 (vertices 0..4 local). Build the local
    full-spec model with P1 = F1, all other parts empty. Return min holes."""
    # parts: P0 size n0, P1..P4 size 5
    sizes = [n0, 5, 5, 5, 5]
    parts, off, part_of = [], 0, {}
    for pi, n in enumerate(sizes):
        blk = list(range(off, off + n)); parts.append(blk)
        for v in blk:
            part_of[v] = pi
        off += n
    N = off
    # P1 global vertices:
    P1 = parts[1]
    Eset = set()
    for a, b in F1_edges:
        Eset.add((P1[a], P1[b]) if P1[a] < P1[b] else (P1[b], P1[a]))
    allpairs = list(itertools.combinations(range(N), 2))
    pidx = {e: i for i, e in enumerate(allpairs)}
    cross = [pidx[(a, b)] for (a, b) in allpairs if part_of[a] != part_of[b]]
    cset = set(cross); cpos = {pi: i for i, pi in enumerate(cross)}
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(cross))]
    # full-spec 6-sets over these N vertices
    for S in itertools.combinations(range(N), 6):
        cids, intra = [], []
        for a, b in itertools.combinations(S, 2):
            p = pidx[(a, b)]
            if p in cset:
                cids.append(cpos[p])
            else:
                intra.append((a, b))
        ie = sum(1 for p in intra if p in Eset)
        rhs = len(cids) + ie - 4
        if rhs < 0:
            return ("INTRA_INFEAS", None, None)
        if rhs < len(cids):
            m.Add(sum(h[i] for i in cids) <= rhs)
        if ie == len(intra):
            m.AddBoolOr([h[i] for i in cids])
    m.Minimize(sum(h))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = time_limit
    s.parameters.num_search_workers = workers
    st = s.Solve(m)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return (s.StatusName(st), int(round(s.ObjectiveValue())),
                int(round(s.BestObjectiveBound())))
    return (s.StatusName(st), None, int(round(s.BestObjectiveBound())))


if __name__ == "__main__":
    # F1 graphs on 5 vertices by edge count; pick representative structures
    G5 = {
        "1 edge": [(0, 1)],
        "2 edges (matching)": [(0, 1), (2, 3)],
        "2 edges (path)": [(0, 1), (1, 2)],
        "triangle K3": [(0, 1), (1, 2), (0, 2)],
        "P4 path": [(0, 1), (1, 2), (2, 3)],
        "K3+e": [(0, 1), (1, 2), (0, 2), (3, 4)],
        "C4": [(0, 1), (1, 2), (2, 3), (0, 3)],
        "K_{2,3}": [(0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4)],  # 6 edges, bipartite
        "K4": [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)],       # 6 edges
        "K4+e (book)": [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3), (0, 4)],
        "K5 minus": [(0, 1), (0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4), (2, 3)],
    }
    print("Holes forced by an edge-graph F1 in ONE 5-part (P0,P2,P3,P4 empty):")
    print("(this is the W-system demand of a single edge-bearing 5-part)\n")
    import os
    WK = int(os.environ.get("OPD_WK", "2"))
    TL = int(os.environ.get("OPD_TL", "60"))
    for name, F in G5.items():
        st, val, lb = one_part_demand(F, time_limit=TL, workers=WK)
        print(f"  F1 = {name:18s} (e1={len(F)}): min holes = {val}  [{st}, LB={lb}]", flush=True)
