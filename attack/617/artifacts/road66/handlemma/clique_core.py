#!/usr/bin/env python3
"""Holes forced by a CLIQUE CORE in a part, in isolation.

A "clique core" of size t in part P_i is a set of t mutually-adjacent
vertices (a K_t inside P_i). With u,v + ... we have seen single edges
(K_2 cores). Here we isolate the pure pressure of a K_t core.

LOCAL MODEL: K_t core = {c_1..c_t} in part 0 (role of an edge-bearing
part). To avoid K6 we must block every way to extend the core to a K6,
i.e. every set of (6-t) further vertices, pairwise adjacent and each
adjacent to all core vertices. The cheapest blocking is via cross-holes
among the OTHER parts and from the core to the other parts.

We model: core K_t in part 0 (size n0). Remaining 6-t vertices come from
the OTHER parts (each internally empty, Foothold-1 budget 1 per part).
Compute min holes (core->other + other<->other) to block all K6
completions, under matching budgets. This is BLOCK_core(t).

Specifically for t and a target: enumerate placements of the 6-t outside
vertices across the empty parts P_1..P_{r}. For (6,5,5,5,5): core in P0,
the 6-t=4 outside vertices spread over P1..P4 (one each is the densest
completion, but they could cluster). The K6 needs the 4 outside vertices
mutually adjacent AND adjacent to all core vertices.

We compute exactly: min #(cross holes) so that NO choice of 4 outside
vertices (w1,w2,w3,w4), w_i free to be in ANY of P1..P4 (>=1 per part not
required), forms with the core a K6. Equivalently block every 4-subset of
(P1 ∪..∪ P4) that is (a) pairwise adjacent, (b) fully adjacent to core,
and lies in <=4 parts with the per-6-set rule... but a K6 just needs 6
mutually adjacent vertices total. The 4 outside ones may even share a part
ONLY if that part has internal edges; empty parts contribute an
independent set, so at most ONE outside vertex per empty part.

=> the 4 outside vertices occupy 4 DISTINCT empty parts (one each), exactly
the transversal picture. So BLOCK_core(t) over (6,5,5,5,5) with core in P0:
block every transversal (w1,w2,w3,w4) in P1xP2xP3xP4 such that all
C(4,2)=6 cross pairs present AND all 4*t core-cross pairs present.
Holes available: core_i <-> w_j (t*5 per part, budget: w_j has <=1 hole
into core's... no, core is in P0 size6: w_j has <= 2 holes into P0 if e0=...).

This is getting subtle; we just feed it to CP-SAT with the honest budgets:
 - core vertices c in P0: a 5-part vertex w has <=1 hole into each EMPTY
   5-part; into P0 (size 6) Foothold gives <= 2 + e0 ... we use the SAFE
   (adversary-favoring) budget: w has <= (6-4)+e0 = 2+e0 holes into P0.
   For a lower bound on holes we want to give the adversary the LARGEST
   budgets (most blocking power) -> use the loosest valid caps.
"""
import sys, itertools
from ortools.sat.python import cp_model


def block_core(t, e0, time_limit=120, workers=8):
    """Min cross-holes forced by a K_t core in P0 (size 6, e(P0)=e0).
    Completion size = 6 - t, placed across the empty 5-parts (>=2 parts when
    6-t<=4), one vertex per empty part (empty parts are independent). We use
    the 6-t completion vertices spread over the FIRST (6-t) empty parts (the
    densest single-transversal picture). Budgets as Foothold-1."""
    SZ = 5
    comp = 6 - t                  # completion vertices needed
    cparts = list(range(comp))    # use empty parts 0..comp-1 (each size 5)
    core = list(range(t))
    m = cp_model.CpModel()
    hc = {}                       # core_c <-> w(part pi, vertex a)
    for c in core:
        for pi in cparts:
            for a in range(SZ):
                hc[(c, pi, a)] = m.new_bool_var(f"hc_{c}_{pi}_{a}")
    he = {}                       # between two completion parts
    for (i, j) in itertools.combinations(cparts, 2):
        for a in range(SZ):
            for b in range(SZ):
                he[(i, j, a, b)] = m.new_bool_var(f"he_{i}_{j}_{a}_{b}")
    # w into P0 (size6): cap = 2+e0 (Foothold), restricted to core subset
    for pi in cparts:
        for a in range(SZ):
            m.add(sum(hc[(c, pi, a)] for c in core) <= 2 + e0)
    # core vertex c into empty part pi: <=1
    for c in core:
        for pi in cparts:
            m.add(sum(hc[(c, pi, a)] for a in range(SZ)) <= 1)
    for (i, j) in itertools.combinations(cparts, 2):
        for a in range(SZ):
            m.add(sum(he[(i, j, a, b)] for b in range(SZ)) <= 1)
        for b in range(SZ):
            m.add(sum(he[(i, j, a, b)] for a in range(SZ)) <= 1)
    for tt in itertools.product(range(SZ), repeat=comp):
        lits = []
        for c in core:
            for k, pi in enumerate(cparts):
                lits.append(hc[(c, pi, tt[k])])
        for (i, j) in itertools.combinations(cparts, 2):
            ki, kj = cparts.index(i), cparts.index(j)
            lits.append(he[(i, j, tt[ki], tt[kj])])
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
    print("BLOCK_core(t): min cross-holes forced by a K_t core in P0 (e0)")
    print("  over the four empty 5-parts (blocking all K6 completions).")
    for e0 in (4, 5, 6):
        for t in (2, 3, 4):
            r = block_core(t, e0, time_limit=60)
            if r is None:
                print(f"  K_{t} core, e0={e0}: UNBLOCKABLE (forces K6 outright)")
            else:
                val, opt = r
                print(f"  K_{t} core, e0={e0}: min holes = {val}{'' if opt else ' (LB only)'}")
