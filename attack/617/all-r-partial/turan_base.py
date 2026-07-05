#!/usr/bin/env python3
"""Rooted surplus reduction + exact-Turán-base lemma (Erdős #617), 2026-06-16.

Root a single-colour counterexample G at a maximum independent set I (|I|=r,
since α(G)=r — α≤r-1 would give >A_r edges by Turán). With O = V minus I (|O|=m=r²-r+1),
F=G[O], and L=#root links, the target e(G)≥A_r+1 becomes the SURPLUS inequality

    (e(F) - y0) + (L - m)  >=  C(r,2)+1 = C_r,

where y0 = C(r,2)+(r-1)C(r-1,2) is the Turán minimum of e(F) (α(F)≤r ⇒ F is r
cliques: Q0 of size r, Q1..Q_{r-1} of size r-1) and m is the minimum # root
links (each x∈O needs one, else {x}∪I is an independent (r+1)-set).

LEMMA (this pass, VERIFIED). e(F) = y0 is impossible: no root-link assignment to
the Turán-extremal F satisfies the local caps. So e(F) >= y0+1 (one unit of the
required C_r surplus). Proof: on Q0 each root links ≤1 vertex (upper cap) and
every Q0-vertex needs a link ⇒ perfect matching x_i↔root i; then each N_k must
hit every transversal of Q1×…×Q_{r-1} ⇒ contains a full small part; a small part
can serve ≤1 root (else C(r-1,2)+2(r-1) ≤ C(r,2)+1 ⟺ 2r-2 ≤ r, false for r≥3);
r roots need r distinct full parts but only r-1 exist. Contradiction.

This script checks (a) the surplus arithmetic and (b) the lemma's finite model
(INFEASIBLE) for r=3,4. Remaining open: the full surplus inequality (≥ C_r),
i.e. the weighted blocker |D|+τ ≥ C(r,2)+1 over the near-Turán range.

Run: python3 turan_base.py
"""
from itertools import combinations
from ortools.sat.python import cp_model
import math


def turan_base_feasible(r, tl=60):
    parts, cur = [], 0
    for p in range(r):
        sz = r if p == 0 else r - 1
        parts.append(list(range(cur, cur + sz))); cur += sz
    O, m = list(range(cur)), cur
    Fe = {(a, b) for part in parts for a, b in combinations(part, 2)}
    md = cp_model.CpModel()
    l = {(x, i): md.NewBoolVar(f"l{x}_{i}") for x in O for i in range(r)}
    Cr = math.comb(r, 2) + 1
    allv = O + [m + i for i in range(r)]
    for S in combinations(allv, r + 1):
        A = [v for v in S if v < m]; B = [v - m for v in S if v >= m]
        eF = sum(1 for a, b in combinations(A, 2) if (a, b) in Fe)
        t = [l[(x, i)] for x in A for i in B]
        md.Add(eF + sum(t) >= 1); md.Add(eF + sum(t) <= Cr)
    s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = tl; s.parameters.num_search_workers = 8
    return s.StatusName(s.Solve(md))


if __name__ == "__main__":
    print("surplus arithmetic  (A_r+1)-(y0+m) == C(r,2)+1:")
    for r in range(3, 7):
        A = r*(r*r+1)//2; y0 = math.comb(r, 2)+(r-1)*math.comb(r-1, 2); m = r*r-r+1
        assert (A+1)-(y0+m) == math.comb(r, 2)+1
        print(f"  r={r}: {(A+1)-(y0+m)} == {math.comb(r,2)+1}  OK")
    print("exact-Turán-base feasibility (expect INFEASIBLE ⇒ e(F)≥y0+1):")
    for r in (3, 4):
        st = turan_base_feasible(r)
        print(f"  r={r}: {st}")
        assert st == "INFEASIBLE"
    print("OK")
