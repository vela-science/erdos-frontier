#!/usr/bin/env python3
"""Efficient LOWER-BOUND oracle on min-holes for a full config.

The full-spec model has 230230 six-set constraints and is intractable at
high budgets. But for a LOWER bound on min-holes we may DROP constraints:
any subset of the true constraints yields a relaxation whose optimum is a
valid lower bound on the true min-holes.

We keep exactly the constraints that the hand proof actually uses:
  (B) Foothold-1 budgets: every vertex w has <= 1+e(P_i) holes into each
      5-part P_i (i != part(w)); and the pair-budget into empty 4-parts.
  (K) K6-blocking clauses for every 6-set that contains a "guaranteed
      clique core": specifically, for every internal edge and the
      transversal completions. We include ALL 6-sets S such that the intra
      edges present in S already number >= (6-set-needs); equivalently we
      keep the AddBoolOr K6 clauses (intraE == n_intra) -- these are the
      pure K6-avoidance clauses -- for 6-sets meeting >= 1 internal edge.

Concretely we reuse general_rung.build's K6 clauses but RESTRICT to 6-sets
that contain at least one internal edge (those are the only ones whose
blocking is forced by clique pressure around the internal structure), and
we ADD the Foothold-1 budget constraints explicitly. Dropping the
"sparse-cross" inequality constraints (rhs bounds) only relaxes further.

This is MUCH smaller (clauses ~ #internal-edges * 5^3) and exact-solvable.
Its optimum LB satisfies LB <= true min-holes, so LB > cap => INFEASIBLE
=> config killed. (One-directional: LB <= cap proves nothing.)
"""
import sys, itertools, time
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
import general_rung as G
from ortools.sat.python import cp_model

ALLPAIRS26 = G.ALLPAIRS26
PIDX26 = G.PIDX26


def lb_min_holes(sizes, E, time_limit=120, workers=2, extra_pair_budget=True,
                 return_witness=False):
    parts, off, part_of, partlist = [], 0, {}, []
    for pi, n in enumerate(sizes):
        block = list(range(off, off + n))
        partlist.append(block)
        for v in block:
            part_of[v] = pi
        off += n
    Eset = set((min(a, b), max(a, b)) for a, b in E)
    # e(P_i)
    eP = [0] * 5
    for a, b in Eset:
        if part_of[a] == part_of[b]:
            eP[part_of[a]] += 1
    cross = [PIDX26[(a, b)] for (a, b) in ALLPAIRS26 if part_of[a] != part_of[b]]
    cset = set(cross); cpos = {pi: i for i, pi in enumerate(cross)}
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(cross))]

    def hv(a, b):
        return h[cpos[PIDX26[(min(a, b), max(a, b))]]]

    # (B) Foothold-1 single-vertex budgets into each 5-part
    for w in range(26):
        for pi in range(5):
            if part_of[w] == pi:
                continue
            P = partlist[pi]
            n = len(P)
            if n == 5:
                m.Add(sum(hv(w, p) for p in P) <= 1 + eP[pi])
            elif n == 4 and eP[pi] == 0:
                # empty 4-part: every outside vertex COMPLETE (0 holes)
                for p in P:
                    m.Add(hv(w, p) == 0)
            elif n == 4:
                m.Add(sum(hv(w, p) for p in P) <= eP[pi])  # n-4+e = e
            # n==6 or n>=7: no single-vertex budget added (weaker, fine)
    # (B') pair-budget into empty 4-parts: for w,w' outside empty 4-part Q,
    #      holes_Q(w)+holes_Q(w') <= 4 + [ww' hole]. (Already implied 0 by above
    #      when e=0; meaningful when e(Q) in {1,2}.)
    if extra_pair_budget:
        for pi in range(5):
            if len(partlist[pi]) == 4 and eP[pi] >= 1:
                Q = partlist[pi]
                outside = [w for w in range(26) if part_of[w] != pi]
                for w, w2 in itertools.combinations(outside, 2):
                    s = sum(hv(w, p) for p in Q) + sum(hv(w2, p) for p in Q)
                    if part_of[w] == part_of[w2]:
                        wwhole = 0  # same part: ww' is intra, not a cross hole;
                        # the 6-set {w,w'}∪Q: ww' may be an internal edge or not.
                        ww_is_edge = (min(w, w2), max(w, w2)) in Eset
                        m.Add(s <= 4 - eP[pi] + (0 if ww_is_edge else 1))
                    else:
                        # ww' is a cross pair; [ww' a hole] = hv(w,w')
                        m.Add(s <= 4 - eP[pi] + hv(w, w2))
    # (K) K6-avoidance clauses for every 6-set whose intra pairs are ALL edges
    #     and that meets >= 1 internal edge (clique pressure). Keep only those.
    for S in itertools.combinations(range(26), 6):
        cids, intra = [], []
        for a, b in itertools.combinations(S, 2):
            pi = PIDX26[(a, b)]
            if pi in cset:
                cids.append(cpos[pi])
            else:
                intra.append((a, b))
        intra_edges = sum(1 for p in intra if p in Eset)
        if intra_edges == 0:
            continue  # no clique core -> drop (relaxation)
        if intra_edges == len(intra):
            # all intra pairs present => the cross pairs must contain a hole
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
    print("LB-oracle sanity: Case A single edge in P0 (6,5,5,5,5), should hit 26-ish")
    # Just one P0 edge, parts empty -> single-edge demand 26 (8 endpoint + 18)
    # but with only ONE edge there is slack; the FULL Case A has e0>=4.
    for name, E in [
        ("1 P0 edge, empty", [(0, 1)]),
        ("e0=4 star, empty 5-parts", [(0, 1), (0, 2), (0, 3), (0, 4)]),
        ("e0=4 star + 1 edge P1", [(0, 1), (0, 2), (0, 3), (0, 4), (6, 7)]),
        ("e0=4 star + edges P1,P2", [(0, 1), (0, 2), (0, 3), (0, 4), (6, 7), (11, 12)]),
    ]:
        t = time.time()
        r = lb_min_holes((6, 5, 5, 5, 5), E, time_limit=60)
        print(f"  {name}: status={r[0]} min={r[1]} LB={r[2]} ({round(time.time()-t)}s)", flush=True)
