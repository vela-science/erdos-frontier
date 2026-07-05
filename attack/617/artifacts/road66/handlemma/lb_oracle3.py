#!/usr/bin/env python3
"""STRONG valid lower-bound oracle, v3.

Relaxation of the full "every 6-set spans >=4 edges + K6-free" model that
keeps exactly the 6-sets likely to bind, and ALL K6 clauses. Its min is a
valid lower bound on true min-holes; if min > cap, the config is killed.

Kept constraint families (all VALID -> relaxation):
  (CONC) every 6-set with >= CONC_K (default 4) vertices in a single part.
         These are the "hole-concentration limiters": (>=4 in one part) ∪
         (rest). For each such 6-set S:  sum(cross holes in S) <= rhs,
         rhs = (#cross pairs) + (#intra edges) - 4.
         [These were the binding ones missing from v2 -- including P0-subsets
          {5 of P0} ∪ {w} which forced extra holes in the triangle case.]
  (K6)   every 6-set whose intra pairs are ALL edges -> OR of cross holes.
  (BUD)  Foothold-1 single-vertex budgets (implied by CONC with full-part
         6-sets, but cheap and helps the solver).

Returns (status, relax_min, dual_LB, witness?). dual_LB <= relax_min <=
true_min_holes, so dual_LB > cap  =>  config infeasible (killed).
"""
import sys, itertools
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
import general_rung as G
from ortools.sat.python import cp_model

ALLPAIRS26 = G.ALLPAIRS26
PIDX26 = G.PIDX26


def lb3(sizes, E, conc_k=4, time_limit=120, workers=2, return_witness=False,
        extra_k6_only=False):
    parts, off, part_of, partlist = [], 0, {}, []
    for pi, n in enumerate(sizes):
        blk = list(range(off, off + n)); partlist.append(blk)
        for v in blk:
            part_of[v] = pi
        off += n
    Eset = set((min(a, b), max(a, b)) for a, b in E)
    eP = [0] * 5
    for a, b in Eset:
        if part_of[a] == part_of[b]:
            eP[part_of[a]] += 1
    cross = [PIDX26[(a, b)] for (a, b) in ALLPAIRS26 if part_of[a] != part_of[b]]
    cset = set(cross); cpos = {pi: i for i, pi in enumerate(cross)}
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(cross))]

    def add_sixset(S):
        cids, intra = [], []
        for a, b in itertools.combinations(S, 2):
            p = PIDX26[(a, b)]
            if p in cset:
                cids.append(cpos[p])
            else:
                intra.append((a, b))
        ie = sum(1 for p in intra if p in Eset)
        # K6 clause
        if ie == len(intra):
            m.AddBoolOr([h[i] for i in cids])
        # >=4 edge inequality
        if not extra_k6_only:
            rhs = len(cids) + ie - 4
            if rhs < 0:
                return False
            if rhs < len(cids):
                m.Add(sum(h[i] for i in cids) <= rhs)
        return True

    seen = set()
    # (CONC) 6-sets with >= conc_k vertices in one part
    for pi, P in enumerate(partlist):
        n = len(P)
        for kk in range(conc_k, min(n, 6) + 1):
            for T in itertools.combinations(P, kk):
                rest = [w for w in range(26) if part_of[w] != pi]
                for comp in itertools.combinations(rest, 6 - kk):
                    S = tuple(sorted(T + comp))
                    if S in seen:
                        continue
                    seen.add(S)
                    if not add_sixset(S):
                        return ("INTRA_INFEAS", None, None, None)
    # (K6-ALL) every 6-set meeting an internal edge whose intra pairs are ALL
    # edges => OR of cross holes (these FORCE holes to exist). Add the ones
    # not already covered above. This is the essential K6-avoidance pressure.
    for S in itertools.combinations(range(26), 6):
        if S in seen:
            continue
        cids, intra = [], []
        for a, b in itertools.combinations(S, 2):
            p = PIDX26[(a, b)]
            if p in cset:
                cids.append(cpos[p])
            else:
                intra.append((a, b))
        ie = sum(1 for p in intra if p in Eset)
        if ie == 0:
            continue  # no clique core -> drop (relaxation)
        if ie == len(intra):
            m.AddBoolOr([h[i] for i in cids])
    m.Minimize(sum(h))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = time_limit
    s.parameters.num_search_workers = workers
    st = s.Solve(m)
    name = s.StatusName(st)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        lb = int(round(s.BestObjectiveBound()))
        val = int(round(s.ObjectiveValue()))
        wit = None
        if return_witness:
            wit = [ALLPAIRS26[cross[i]] for i in range(len(cross)) if s.Value(h[i])]
        return name, val, lb, wit
    if st == cp_model.INFEASIBLE:
        return name, None, None, None
    return name, None, int(round(s.BestObjectiveBound())), None


if __name__ == "__main__":
    import time
    parts = [list(range(0, 6)), list(range(6, 11)), list(range(11, 16)),
             list(range(16, 21)), list(range(21, 26))]

    def edges_in(pi, k):
        v = parts[pi]; allp = list(itertools.combinations(range(len(v)), 2))
        return [(v[a], v[b]) for (a, b) in allp[:k]]
    star = [(0, 1), (0, 2), (0, 3), (0, 4)]
    cases = [
        ("star Case A I=4 (true>=38)", star),
        ("star+triangleP1 I=7 (true>=16)", star + edges_in(1, 3)),
        ("star+2xP1 I=6 (true>=15)", star + [(6, 7), (8, 9)]),
        ("star+P1,P2 I=6 (true=19)", star + [(6, 7), (11, 12)]),
        ("star+4P1 I=8", star + edges_in(1, 4)),
        ("star+3P1+3P2 I=10", star + edges_in(1, 3) + edges_in(2, 3)),
    ]
    for ck in (4,):
        print(f"=== CONC_K={ck} ===", flush=True)
        for name, E in cases:
            t = time.time()
            r = lb3((6, 5, 5, 5, 5), E, conc_k=ck, time_limit=120, workers=8)
            print(f"  {name}: status={r[0]} relax_min={r[1]} LB={r[2]} ({round(time.time()-t)}s)", flush=True)
