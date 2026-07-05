#!/usr/bin/env python3
"""Holes forced by a K_t core inside a 5-PART P1 (not P0), for shape
(6,5,5,5,5). The K6 completions use 6-t further vertices drawn from
P0 (size 6) and the other empty 5-parts P2,P3,P4 (size 5).

This is the structure in 'star + triangle in P1': the triangle (K_3) in P1
plus 3 completion vertices, one each from three of {P0,P2,P3,P4}. Since P0
has 6 vertices and is internally NON-empty (e0 edges), and P2,P3,P4 are
empty, the completion picture differs from the P0-core case.

We count ALL holes that the core can be charged: core<->completion-part and
completion-part<->completion-part, blocking every K6 completion. The
completion vertices occupy DISTINCT parts among {P0,P2,P3,P4} (P2,P3,P4
empty => 1 each; P0 may host up to ... well a single completion vertex from
P0 unless P0's internal edges allow 2 — but 2 completion vertices in P0
must be P0-adjacent, which is possible; we allow the SAFE over-approx of 1
per part for a LOWER bound, i.e. transversal completions only).

Budgets (Foothold-1, adversary-favoring = loosest valid):
 - completion vertex w in empty part (P2/P3/P4) -> P1: <=1 hole (P1 has the
   core but e1=t-choose-2... for K_t e(P1)>=C(t,2); cap into P1 = 1+e(P1)).
   We use cap = 1 + C(t,2) for w->P1 (loosest). Restricted to the t-core
   subset, still <= 1+C(t,2) but also <= t trivially.
 - completion vertex in P0 -> P1: same, <= 1 + e(P1).
 - core vertex (in P1) -> empty part P_j: <=1.   core vertex -> P0: <= 2+e0.
 - among completion parts: matching/budget per Foothold-1 between the
   specific parts (empty<->empty:1; empty<->P0: into P0 is 2+e0, into empty
   is 1; we encode both directions).
"""
import sys, itertools
from ortools.sat.python import cp_model
from math import comb


def block_core_in5(t, e0, completion_parts, time_limit=120, workers=8):
    """core K_t in P1 (size5). completion_parts: list of ('P0' or 'e') of
    length 6-t, the parts hosting completion vertices (sizes 6 or 5)."""
    e1 = comb(t, 2)
    comp = 6 - t
    assert len(completion_parts) == comp
    sizes = [6 if p == 'P0' else 5 for p in completion_parts]
    core = list(range(t))
    m = cp_model.CpModel()
    # core_c <-> completion vertex (part k, vertex a)
    hc = {}
    for c in core:
        for k in range(comp):
            for a in range(sizes[k]):
                hc[(c, k, a)] = m.new_bool_var(f"hc_{c}_{k}_{a}")
    he = {}  # between completion parts k<l
    for (k, l) in itertools.combinations(range(comp), 2):
        for a in range(sizes[k]):
            for b in range(sizes[l]):
                he[(k, l, a, b)] = m.new_bool_var(f"he_{k}_{l}_{a}_{b}")
    # budgets
    # completion vertex (k,a) -> P1 (has core, e1): cap = 1+e1, restricted to core
    for k in range(comp):
        for a in range(sizes[k]):
            m.add(sum(hc[(c, k, a)] for c in core) <= 1 + e1)
    # core vertex c (in P1) -> completion part k:
    #   if part is empty 5-part: <=1 ; if P0(size6): <= 2+e0
    for c in core:
        for k in range(comp):
            cap = (2 + e0) if completion_parts[k] == 'P0' else 1
            m.add(sum(hc[(c, k, a)] for a in range(sizes[k])) <= cap)
    # between completion parts: row/col budgets per part types
    for (k, l) in itertools.combinations(range(comp), 2):
        # vertex in part k -> part l
        cap_kl = (2 + e0) if completion_parts[l] == 'P0' else 1
        cap_lk = (2 + e0) if completion_parts[k] == 'P0' else 1
        for a in range(sizes[k]):
            m.add(sum(he[(k, l, a, b)] for b in range(sizes[l])) <= cap_kl)
        for b in range(sizes[l]):
            m.add(sum(he[(k, l, a, b)] for a in range(sizes[k])) <= cap_lk)
    # block every completion transversal
    for tt in itertools.product(*[range(s) for s in sizes]):
        lits = []
        for c in core:
            for k in range(comp):
                lits.append(hc[(c, k, tt[k])])
        for (k, l) in itertools.combinations(range(comp), 2):
            lits.append(he[(k, l, tt[k], tt[l])])
        m.add_bool_or(lits)
    m.minimize(sum(hc.values()) + sum(he.values()))
    s = cp_model.CpSolver()
    s.parameters.num_search_workers = workers
    s.parameters.max_time_in_seconds = time_limit
    st = s.solve(m)
    if st == cp_model.INFEASIBLE:
        return None
    return int(round(s.objective_value)), (st == cp_model.OPTIMAL)


if __name__ == "__main__":
    print("Holes forced by a K_t core inside a 5-PART P1 (shape 6,5,5,5,5).")
    print("Completion vertices across distinct parts (P0 size6 / empty size5).\n")
    # K_3 (triangle) in P1: 3 completion vertices. The DENSEST (worst for
    # adversary) completion uses P0 + two empty parts, OR three empty parts.
    # We must block ALL placements; the MIN over placements that the adversary
    # can 'choose' is wrong -- the adversary must block EVERY placement, so the
    # true forced holes >= max over completion-part-choices of the block# ...
    # NO: holes are shared. We report each placement's isolated block number to
    # see which is binding; the real config blocks the UNION.
    for t in (2, 3, 4):
        comp = 6 - t
        print(f"K_{t} core in P1 (e1={comb(t,2)}), {comp} completion vertices:")
        # placements: how many of the completion parts are P0 (0 or 1; only one P0)
        for nP0 in (0, 1):
            if nP0 == 1 and comp < 1:
                continue
            cps = (['P0'] if nP0 else []) + ['e'] * (comp - nP0)
            if len(cps) != comp:
                continue
            # need enough empty parts: we have P2,P3,P4 = 3 empty parts available
            n_empty_needed = comp - nP0
            if n_empty_needed > 3:
                print(f"   completion {cps}: needs {n_empty_needed} empty parts > 3 available -> SKIP")
                continue
            for e0 in (4,):
                r = block_core_in5(t, e0, cps, time_limit=60)
                tag = "UNBLOCKABLE" if r is None else f"{r[0]}{'' if r[1] else ' (LB)'}"
                print(f"   completion parts {cps} (e0={e0}): min holes = {tag}")
        print()
