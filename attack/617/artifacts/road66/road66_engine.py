#!/usr/bin/env python3
"""road66_engine.py — general full-spec CP-SAT engine for the Erdos #617
m* ladder (the "road to 66").

================================  THE PROBLEM  ================================
m* = min e(G) over graphs G on 26 vertices with alpha(G) <= 5 and every 6-set
spanning <= 11 edges.  Pass to the complement H = Gbar: K6-free, every 6-set
spans >= 4 edges, and e(G)+e(H) = C(26,2) = 325, so m* >= M  <=>  e(H) <= 325-M.

================================  THE REDUCTION  =============================
At "rung q" we test, for a fixed 5-partition shape, whether H can have
e(H) = 270 - q.  Furedi stability (Thm 1, arXiv:1501.03129, p=5) on
e(H) = e(T_26,5) - t = 270 - t gives a 5-partition with I <= t = q internal
H-edges.  For a partition with size vector nv = (n0..n4):

    internal_pairs(nv) = sum C(ni,2);   cross_pairs(nv) = 325 - internal_pairs
    defect          d  = internal_pairs(nv) - 55      (55 = ip of (6,5,5,5,5))
    cross_pairs(nv)    = 270 - d
    holes              = cross_pairs - (cross edges present)
    e(H)               = (cross_pairs - holes) + I = (270 - d - holes) + I

Setting e(H) = 270 - q:        holes = q + I - d   =:  BUDGET.

A (size_vector, internal_edge_count I) layout CLOSES rung q iff

        min_holes(layout)  >  q + I - d   ( = BUDGET ),

i.e. H cannot reach e(H) = 270 - q on that shape.  If min_holes <= BUDGET the
layout is FEASIBLE at e(H)=270-q (a witness exists at min_holes); the
single-class counting route cannot close that rung on that shape.

Closing every admissible layout at rung q (and all lower rungs) proves
e(H) <= 269 - q, i.e.  m* >= 56 + q.   Target: q = 10  ->  m* >= 66  (#617 r=5).

ADMISSIBILITY.  Shape census: min internal edges f(m) of an m-part with every
6-subset spanning >= 4 internal edges:  f(<=5)=0, f(6)=4, f(7)=6, f(8)=8,
f(9)=11.  A size vector is admissible at rung q iff sum f(ni) <= q (Furedi caps
I <= q) and the parts sum to 26 with five parts.  For each admissible vector we
sweep I from f_min(nv) up to q (higher I => higher budget => harder to close;
the binding case is the largest feasible I).

==============================  THE MODEL (FULL SPEC)  =======================
Variables:
  * one boolean per cross-pair  (1 = HOLE, i.e. absent in H; 0 = present)
  * one boolean per internal-pair (1 = internal H-edge present; 0 = absent)
Constraints (the REAL 6-set condition, no shortcut):
  * EVERY 6-subset S of the 26 vertices spans >= 4 edges of H.  Edges of S =
    (present cross pairs of S) + (present internal pairs of S).  With cross
    holes h and internal-present b this is:
        sum_{cross pairs (a,c) in S} (1 - h[a,c])
      + sum_{internal pairs (a,c) in S} b[a,c]   >=  4
    <=>  sum h[cross in S] - sum b[internal in S] <= |cross pairs in S| - 4.
    (This single family simultaneously enforces "every 6-set >= 4" AND, because
     a K6 would span 15 > 11... no: K6-freeness is the e(H) side.  K6-freeness
     is enforced separately below since a 6-set spanning all 15 pairs is a K6.)
  * K6-free: no 6-subset spans all 15 pairs.  For every 6-subset, NOT all 15
    pairs present  <=>  (some cross pair is a hole) OR (some internal pair
    absent):  sum h[cross in S] + sum (1-b[internal in S]) >= 1.
  * sum of internal-present booleans == I   (fix the internal edge count)
  * per-part internal validity is IMPLIED by the global 6-set constraint when a
    part has >= 6 vertices (its own 6-subsets are 6-sets of H), so we do not add
    it separately; but we DO pin sum b == I and let the solver place edges.
  * sum of holes <= BUDGET (decision) or minimize sum of holes (optimization).

Soundness of constraint pruning: a 6-set whose constraint RHS is large enough
that it can never bind given the hole cap may be dropped, but ONLY in capped
(decision) mode and ONLY when the cap is enforced.  In minimize mode we keep
every constraint (we pass model_cap = a safe large number).  See build_model.

This file is a library; road66_driver.py runs the rung sweep.  An independent
checker road66_check.py re-verifies any witness from scratch.

Trust base: Furedi 2015 Thm 1 (published, verified verbatim) + the shape census
(elementary) + OR-Tools CP-SAT (solver-trust for INFEASIBLE; witnesses are
independently re-verified, certificate-grade).
"""
import sys
from itertools import combinations
from math import comb
from ortools.sat.python import cp_model

N = 26

# Shape census: min internal edges for an m-part with every 6-subset >= 4 edges.
F_CENSUS = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 4, 7: 6, 8: 8, 9: 11}


def internal_pairs(nv):
    return sum(comb(n, 2) for n in nv)


def cross_pairs(nv):
    return comb(N, 2) - internal_pairs(nv)


def defect(nv):
    return internal_pairs(nv) - 55


def f_min(nv):
    return sum(F_CENSUS[n] for n in nv)


def budget(q, I, nv):
    """holes available to the adversary at rung q with I internal edges."""
    return q + I - defect(nv)


def parts_of(nv):
    """Return (parts list, part_of map) for size vector nv laid out on 0..25."""
    parts, k = [], 0
    for n in nv:
        parts.append(list(range(k, k + n)))
        k += n
    assert k == N, f"size vector {nv} does not sum to {N}"
    part_of = {}
    for pi, P in enumerate(parts):
        for v in P:
            part_of[v] = pi
    return parts, part_of


def classify_pairs(nv):
    """Return (cross_list, cross_index, internal_list, internal_index, part_of)."""
    parts, part_of = parts_of(nv)
    cross, internal = [], []
    for a, b in combinations(range(N), 2):
        if part_of[a] != part_of[b]:
            cross.append((a, b))
        else:
            internal.append((a, b))
    cidx = {e: i for i, e in enumerate(cross)}
    iidx = {e: i for i, e in enumerate(internal)}
    assert len(cross) == cross_pairs(nv)
    assert len(internal) == internal_pairs(nv)
    return cross, cidx, internal, iidx, part_of


def precompute_sixsets(part_of, cidx, iidx):
    """For each 6-subset record (cross-pair indices, internal-pair indices)."""
    data = []
    for S in combinations(range(N), 6):
        cids, iids = [], []
        for a, b in combinations(S, 2):
            if part_of[a] != part_of[b]:
                cids.append(cidx[(a, b)])
            else:
                iids.append(iidx[(a, b)])
        data.append((cids, iids))
    return data


def build_model(nv, I, hole_cap, model_cap, fixed_internal=None,
                six_data=None, classified=None):
    """Build the full-spec CP-SAT model for size vector nv with I internal edges.

    hole_cap   : enforced upper bound on total holes (decision) -- pass a large
                 number (e.g. cross_pairs) in pure minimize mode.
    model_cap  : a 6-set constraint with RHS >= min(#cross-in-S, model_cap) is
                 dropped (sound iff total holes <= model_cap is enforced).  Pass
                 model_cap >= hole_cap; in minimize mode pass cross_pairs (no drop
                 unless RHS >= #cross-in-S, which can never bind anyway).
    fixed_internal : optional explicit set of internal pairs (tuples) to force as
                 present (the rest absent).  When given, I is checked against it
                 and the internal booleans are pinned.  When None, internal edges
                 are free booleans with sum == I (solver explores all structures).

    Returns (model, h_vars, b_vars, cross, internal, stats).
    """
    if classified is None:
        cross, cidx, internal, iidx, part_of = classify_pairs(nv)
    else:
        cross, cidx, internal, iidx, part_of = classified
    if six_data is None:
        six_data = precompute_sixsets(part_of, cidx, iidx)

    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(cross))]      # 1 = hole
    b = [m.NewBoolVar(f"b{i}") for i in range(len(internal))]   # 1 = internal edge

    m.Add(sum(h) <= hole_cap)

    if fixed_internal is not None:
        fset = {tuple(sorted(e)) for e in fixed_internal}
        assert len(fset) == I, f"fixed_internal has {len(fset)} edges, expected I={I}"
        for e, idx in iidx.items():
            if e in fset:
                m.Add(b[idx] == 1)
            else:
                m.Add(b[idx] == 0)
    else:
        m.Add(sum(b) == I)

    n_six, n_k6 = 0, 0
    for (cids, iids) in six_data:
        ncross = len(cids)
        # every 6-set spans >= 4 edges:
        #   sum (1-h) over cross  +  sum b over internal  >= 4
        #   => sum h[cross] - sum b[internal] <= ncross - 4
        rhs = ncross - 4
        # If there are no internal pairs in S, this is the pure-cross form.
        # Drop only if it can never bind under the hole cap AND no internal slack:
        #   max LHS = (sum h) - 0 <= hole_cap; constraint slack present iff
        #   rhs < min(ncross, model_cap) OR there are internal pairs (which can
        #   lower the LHS bound).  Keep whenever internal pairs are involved.
        if iids:
            m.Add(sum(h[i] for i in cids) - sum(b[i] for i in iids) <= rhs)
            n_six += 1
        else:
            if rhs < min(ncross, model_cap):
                m.Add(sum(h[i] for i in cids) <= rhs)
                n_six += 1
        # K6-free: not all 15 pairs present
        #   sum h[cross] + sum (1-b[internal]) >= 1
        #   => sum h[cross] - sum b[internal] >= 1 - |internal in S|
        nint = len(iids)
        m.Add(sum(h[i] for i in cids) - sum(b[i] for i in iids) >= 1 - nint)
        n_k6 += 1

    stats = {"n_cross": len(cross), "n_internal": len(internal),
             "n_six_constraints": n_six, "n_k6_constraints": n_k6,
             "n_sixsets": len(six_data)}
    return m, h, b, cross, internal, stats


# ========================================================================
#  FAST PATH: internal edges FIXED (a concrete H-graph on each part).
#  With the internal structure fixed, intraE per 6-set is a constant, so we
#  prune the >=4 constraint to only the binding 6-sets and post the K6 (no-15)
#  constraint only for 6-sets whose every internal pair is present.  This is
#  the proven-fast encoding of caseB_model.py, generalized to any nv.  Holes
#  are the only variables.  min_holes(nv,I) = min over all valid internal
#  configs of the holes objective.
# ========================================================================

def build_fixed(nv, internal_edges, hole_cap, model_cap,
                six_data=None, classified=None):
    """Full-spec model with internal_edges FIXED (set of present internal pairs).
    Only holes are variables.  Returns (model, h, cross, stats).

    Soundness of pruning (identical to caseB_model.py):
      * >=4 constraint for a 6-set S: sum h[cross in S] <= ncross + intraE - 4.
        If RHS >= min(ncross, model_cap) it can never bind given sum h <=
        model_cap (and ncross is the max possible holes in S), so it is dropped.
        VALID iff sum h <= model_cap is enforced (we Add it).
      * K6 (no-15): only 6-sets with EVERY internal pair present can be a K6;
        for those post OR(holes in S) (at least one cross pair must be a hole).
    """
    if classified is None:
        cross, cidx, internal, iidx, part_of = classify_pairs(nv)
    else:
        cross, cidx, internal, iidx, part_of = classified
    if six_data is None:
        six_data = precompute_sixsets(part_of, cidx, iidx)
    fset = {tuple(sorted(e)) for e in internal_edges}
    # map internal pair -> present? using iidx ordering
    present = [False] * len(internal)
    for e in fset:
        present[iidx[e]] = True

    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(cross))]
    m.Add(sum(h) <= hole_cap)

    n_six = n_k6 = 0
    for (cids, iids) in six_data:
        ncross = len(cids)
        intraE = sum(1 for i in iids if present[i])
        rhs = ncross + intraE - 4
        if rhs < 0:
            raise RuntimeError(f"6-set forces infeasibility independent of holes "
                               f"(ncross={ncross}, intraE={intraE})")
        if rhs < min(ncross, model_cap):
            m.Add(sum(h[i] for i in cids) <= rhs)
            n_six += 1
        if intraE == len(iids):           # all internal pairs present -> potential K6
            m.AddBoolOr([h[i] for i in cids])
            n_k6 += 1
    stats = {"n_cross": len(cross), "n_six_constraints": n_six,
             "n_k6_constraints": n_k6, "n_sixsets": len(six_data),
             "I": len(fset)}
    return m, h, cross, stats


def solve_fixed(m, h, cross, minimize, time_limit, workers, log=False):
    if minimize:
        m.Minimize(sum(h))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.log_search_progress = log
    st = solver.Solve(m)
    name = solver.StatusName(st)
    out = {"status": name, "wall": solver.WallTime()}
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        holes = [cross[i] for i in range(len(cross)) if solver.Value(h[i])]
        out["holes"] = holes
        out["n_holes"] = len(holes)
    if minimize:
        out["bound"] = solver.BestObjectiveBound()
        if st == cp_model.OPTIMAL:
            out["min_holes"] = int(round(solver.ObjectiveValue()))
    return out


def solve_model(m, h, b, cross, internal, minimize, time_limit, workers,
                log=False):
    if minimize:
        m.Minimize(sum(h))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.log_search_progress = log
    st = solver.Solve(m)
    name = solver.StatusName(st)
    out = {"status": name, "wall": solver.WallTime()}
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        holes = [cross[i] for i in range(len(cross)) if solver.Value(h[i])]
        iedges = [internal[i] for i in range(len(internal)) if solver.Value(b[i])]
        out["holes"] = holes
        out["n_holes"] = len(holes)
        out["internal_edges"] = iedges
        out["n_internal"] = len(iedges)
    if minimize:
        out["bound"] = solver.BestObjectiveBound()
        if st == cp_model.OPTIMAL:
            out["min_holes"] = int(round(solver.ObjectiveValue()))
    return out


def min_holes(nv, I, time_limit=600, workers=8, fixed_internal=None,
              six_data=None, classified=None, log=False):
    """Compute min_holes(layout): the minimum number of cross-holes for a
    full-spec H on shape nv with exactly I internal edges (every 6-set >= 4,
    K6-free).  Returns the solver output dict; out['min_holes'] is exact iff
    status == OPTIMAL.  If only FEASIBLE within the time limit, out has
    'n_holes' (an upper bound) and 'bound' (a lower bound)."""
    cap = cross_pairs(nv)
    m, h, b, cross, internal, stats = build_model(
        nv, I, hole_cap=cap, model_cap=cap, fixed_internal=fixed_internal,
        six_data=six_data, classified=classified)
    out = solve_model(m, h, b, cross, internal, minimize=True,
                      time_limit=time_limit, workers=workers, log=log)
    out["stats"] = stats
    return out


def decision_at_budget(nv, I, q, time_limit=600, workers=8,
                       fixed_internal=None, six_data=None, classified=None,
                       log=False):
    """Decision form: does a full-spec H on shape nv with I internal edges and
    holes <= budget(q,I,nv) exist?  INFEASIBLE => layout closes rung q.
    FEASIBLE => layout is a witness (obstruction) at e(H)=270-q."""
    bud = budget(q, I, nv)
    if bud < 0:
        return {"status": "INFEASIBLE", "reason": f"budget {bud} < 0",
                "budget": bud, "n_holes": None}
    m, h, b, cross, internal, stats = build_model(
        nv, I, hole_cap=bud, model_cap=bud + 1, fixed_internal=fixed_internal,
        six_data=six_data, classified=classified)
    out = solve_model(m, h, b, cross, internal, minimize=False,
                      time_limit=time_limit, workers=workers, log=log)
    out["budget"] = bud
    out["stats"] = stats
    return out


# ---- admissibility enumeration -------------------------------------------
def admissible_vectors(q):
    """All 5-part size vectors (sorted desc) summing to 26 with f_min <= q."""
    from itertools import product
    seen = set()
    for c in product(range(0, 10), repeat=5):
        if sum(c) != 26:
            continue
        nv = tuple(sorted(c, reverse=True))
        if nv in seen:
            continue
        seen.add(nv)
    out = [nv for nv in sorted(seen) if f_min(nv) <= q]
    return out


def layouts_for_rung(q):
    """Yield (nv, I) layouts admissible at rung q: f_min(nv) <= I <= q.
    Higher I => higher budget => binding; we sweep the whole range."""
    for nv in admissible_vectors(q):
        fm = f_min(nv)
        for I in range(fm, q + 1):
            yield (nv, I)


if __name__ == "__main__":
    # quick self-report of the admissibility lattice
    for q in range(5, 11):
        print(f"=== rung q={q}  (proves m* >= {56+q}, boundary e(H)={270-q}) ===")
        for nv in admissible_vectors(q):
            d = defect(nv)
            fm = f_min(nv)
            blo, bhi = budget(q, fm, nv), budget(q, q, nv)
            print(f"   {nv}  d={d:2d}  f_min={fm:2d}  I in [{fm},{q}]  "
                  f"budget in [{blo},{bhi}]")
