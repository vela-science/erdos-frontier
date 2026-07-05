#!/usr/bin/env python3
"""Stronger LOWER-BOUND oracle: relaxation that ADDS more valid constraints
than lb_oracle.py so its minimum rises closer to the true full-spec min,
while staying far cheaper than the 230230-constraint full model.

Valid constraint families (each is a genuine consequence of "every 6-set
spans >= 4 edges" + K6-freeness, so the relaxation min is a true lower
bound on holes):

 (B1) single-vertex budgets: w has <= (n_i-4)+e(P_i) holes into P_i.
 (BK) K6 clauses: 6-sets with ALL intra pairs being edges => OR of cross holes.
 (BS) "subset 6-set" >=4 constraints for 6-sets that are cheap to enumerate
      and bound hole concentration. We add 6-sets of the form
      {w, w'} ∪ T  where w,w' are two vertices (any parts) and T is a
      4-subset of one 5-part P_i, requiring
         (#edges inside the 6-set) >= 4,
      i.e. (e among w,w',T) + (#cross present) >= 4, equivalently
         (#cross HOLES in the 6-set) <= (#cross pairs) + (intra edges) - 4.
      These directly cap how many holes can pile onto a 5-part locally.
 (BP) full-part 6-sets {w} ∪ P_i (already in B1) and the pair-budget
      {w,w'}∪Q for 4-parts (handled in lb_oracle; replicated).

We parametrize WHICH families to include so we can find the minimal set
that matches the full spec on the calibration cases.
"""
import sys, itertools, time
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
import general_rung as G
from ortools.sat.python import cp_model

ALLPAIRS26 = G.ALLPAIRS26
PIDX26 = G.PIDX26


def lb2(sizes, E, families=("B1", "BK", "BS4"), time_limit=120, workers=2,
        return_witness=False):
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

    def hid(a, b):
        return cpos[PIDX26[(min(a, b), max(a, b))]]

    def hv(a, b):
        return h[hid(a, b)]

    def edge(a, b):
        return (min(a, b), max(a, b)) in Eset

    # (B1) single-vertex budgets
    if "B1" in families:
        for w in range(26):
            for pi in range(5):
                if part_of[w] == pi:
                    continue
                P = partlist[pi]; n = len(P)
                cap = (n - 4) + eP[pi]
                if cap < n:  # nontrivial
                    m.Add(sum(hv(w, p) for p in P) <= cap)
    # (BK) K6 clauses
    if "BK" in families:
        for S in itertools.combinations(range(26), 6):
            cids, intra = [], []
            for a, b in itertools.combinations(S, 2):
                pi = PIDX26[(a, b)]
                if pi in cset:
                    cids.append(cpos[pi])
                else:
                    intra.append((a, b))
            ie = sum(1 for p in intra if p in Eset)
            if ie == 0:
                continue
            if ie == len(intra):
                m.AddBoolOr([h[i] for i in cids])
    # (BS4) 6-sets {w,w'} ∪ T, T a 4-subset of a 5-part: >=4 edges.
    #       cross-holes <= (#cross pairs in 6set) + (intra edges) - 4.
    if "BS4" in families:
        seen = set()
        for pi in range(5):
            P = partlist[pi]
            if len(P) != 5:
                continue
            for T in itertools.combinations(P, 4):
                rest = [w for w in range(26) if part_of[w] != pi]
                for w, w2 in itertools.combinations(rest, 2):
                    S = tuple(sorted(T + (w, w2)))
                    if S in seen:
                        continue
                    seen.add(S)
                    cids, intra = [], []
                    for a, b in itertools.combinations(S, 2):
                        p = PIDX26[(a, b)]
                        if p in cset:
                            cids.append(cpos[p])
                        else:
                            intra.append((a, b))
                    ie = sum(1 for p in intra if p in Eset)
                    rhs = len(cids) + ie - 4
                    if rhs < 0:
                        return ("INTRA_INFEAS", None, None, None)
                    if rhs < len(cids):
                        m.Add(sum(h[i] for i in cids) <= rhs)
    # (BS3) 6-sets {w,w',w''} ∪ T, T a 3-subset of a 5-part
    if "BS3" in families:
        seen = set()
        for pi in range(5):
            P = partlist[pi]
            if len(P) != 5:
                continue
            for T in itertools.combinations(P, 3):
                rest = [w for w in range(26) if part_of[w] != pi]
                for trip in itertools.combinations(rest, 3):
                    S = tuple(sorted(T + trip))
                    if S in seen:
                        continue
                    seen.add(S)
                    cids, intra = [], []
                    for a, b in itertools.combinations(S, 2):
                        p = PIDX26[(a, b)]
                        if p in cset:
                            cids.append(cpos[p])
                        else:
                            intra.append((a, b))
                    ie = sum(1 for p in intra if p in Eset)
                    rhs = len(cids) + ie - 4
                    if rhs < 0:
                        return ("INTRA_INFEAS", None, None, None)
                    if rhs < len(cids):
                        m.Add(sum(h[i] for i in cids) <= rhs)
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
    star = [(0, 1), (0, 2), (0, 3), (0, 4)]
    cases = [
        ("star+2xP1 (e0=4,e1=2) I=6", star + [(6, 7), (8, 9)]),
        ("star+P1,P2 (e0=4,e1=e2=1) I=6", star + [(6, 7), (11, 12)]),
        ("star (Case A) I=4", star),
    ]
    for fam in [("B1", "BK"), ("B1", "BK", "BS4"), ("B1", "BK", "BS4", "BS3")]:
        print(f"=== families {fam} ===", flush=True)
        for name, E in cases:
            t = time.time()
            r = lb2((6, 5, 5, 5, 5), E, families=fam, time_limit=90, workers=4)
            print(f"  {name}: status={r[0]} min={r[1]} LB={r[2]} ({round(time.time()-t)}s)", flush=True)
