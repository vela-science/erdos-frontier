#!/usr/bin/env python3
"""EXACT fractional covering bound for min-holes, by LP (no Furedi cuts).

min_holes >= LP-min { sum_p x_p : for every potential-K6 set K,
                      sum_{p in cross(K)} x_p >= 1 ;  x >= 0 }
           = max fractional packing { sum_K y_K : sum_{K ni p} y_K <= 1 ; y>=0 }.

A "potential K6" = a 6-subset of the 26 vertices whose every SAME-PART pair is
an internal edge (so it is a clique once all its cross-pairs are present).  Its
cross-pairs are the variables that can block it.  We enumerate all such 6-sets
for a given internal-edge set E on shape (6,5,5,5,5), build the covering LP, and
solve it exactly with scipy.linprog (or report the integer min via CP-SAT for a
cross-check).  We also (optionally) add Foothold budget upper-bounds to see
whether they lift the LP value (they are valid <= constraints on x).

Crucially this is the PURE-COVERING relaxation: its optimum is a rigorous lower
bound on true min-holes, and ANY feasible dual y is a hand-checkable certificate.

Usage: covering_lp.py NAME [--budgets] [--int]
"""
import sys, itertools
import numpy as np

sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")

# ---- geometry ----
SIZES = (6, 5, 5, 5, 5)
PARTS = []
off = 0
for n in SIZES:
    PARTS.append(list(range(off, off + n))); off += n
PART_OF = {}
for pi, P in enumerate(PARTS):
    for v in P:
        PART_OF[v] = pi
ALLPAIRS = list(itertools.combinations(range(26), 2))
CROSS = [(a, b) for (a, b) in ALLPAIRS if PART_OF[a] != PART_OF[b]]
CIDX = {p: i for i, p in enumerate(CROSS)}   # cross-pair -> column

def star_P0():
    P0 = PARTS[0]
    return [(P0[0], P0[1]), (P0[0], P0[2]), (P0[0], P0[3]), (P0[0], P0[4])]

def inpart(pi, local):
    P = PARTS[pi]
    return [(P[a], P[b]) for (a, b) in local]

MATCH1 = [(0, 1)]
MATCH2 = [(0, 1), (2, 3)]
PATH4  = [(0, 1), (1, 2), (2, 3), (3, 4)]
C4     = [(0, 1), (1, 2), (2, 3), (0, 3)]
C5     = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]
K23    = [(0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4)]

ATOMS = {
    "star_K23":     star_P0() + inpart(1, K23),
    "star_C5":      star_P0() + inpart(1, C5),
    "star_C4":      star_P0() + inpart(1, C4),
    "star_2m_2m":   star_P0() + inpart(1, MATCH2) + inpart(2, MATCH2),
    "star_path4":   star_P0() + inpart(1, PATH4),
    "star_m_m_m_m": star_P0() + inpart(1, MATCH1) + inpart(2, MATCH1) + inpart(3, MATCH1) + inpart(4, MATCH1),
    "star_m_m":     star_P0() + inpart(1, MATCH1) + inpart(2, MATCH1),
    "star_2m":      star_P0() + inpart(1, MATCH2),
}

def potential_k6s(E):
    """All 6-subsets whose every same-part pair is in E (an internal edge)."""
    Eset = set((min(a, b), max(a, b)) for a, b in E)
    out = []
    for S in itertools.combinations(range(26), 6):
        ok = True
        cross_cols = []
        for a, b in itertools.combinations(S, 2):
            if PART_OF[a] == PART_OF[b]:
                if (a, b) not in Eset:   # a same-part NON-edge -> not a clique candidate
                    ok = False; break
            else:
                cross_cols.append(CIDX[(a, b)])
        if ok:
            out.append(cross_cols)
    return out

def solve_lp(E, with_budgets=False):
    from scipy.optimize import linprog
    K = potential_k6s(E)
    ncols = len(CROSS)
    # min sum x  s.t.  -sum_{p in K} x_p <= -1  (covering), 0<=x<=1
    A_ub = []
    b_ub = []
    for cols in K:
        row = np.zeros(ncols);
        for c in cols: row[c] = -1.0
        A_ub.append(row); b_ub.append(-1.0)
    if with_budgets:
        # Foothold: for w not in P_i (|P_i|=5), holes(w->P_i) <= 1+e(P_i).
        # Encode for every (vertex w, 5-part P_i not containing w).
        Eset = set((min(a, b), max(a, b)) for a, b in E)
        def epart(pi):
            P = PARTS[pi]
            return sum(1 for a, b in itertools.combinations(P, 2) if (min(a,b),max(a,b)) in Eset)
        for pi, P in enumerate(PARTS):
            if SIZES[pi] != 5: continue
            cap_into = 1 + epart(pi)
            for w in range(26):
                if PART_OF[w] == pi: continue
                row = np.zeros(ncols)
                for u in P:
                    row[CIDX[(min(w,u),max(w,u))]] = 1.0
                A_ub.append(row); b_ub.append(float(cap_into))
    A_ub = np.array(A_ub); b_ub = np.array(b_ub)
    c = np.ones(ncols)
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=[(0, 1)] * ncols, method="highs")
    return res, K

if __name__ == "__main__":
    name = sys.argv[1]
    wb = "--budgets" in sys.argv
    E = ATOMS[name]
    K = potential_k6s(E)
    print(f"ATOM {name}: I={len(E)}, #cross-pairs={len(CROSS)}, #potential-K6={len(K)}", flush=True)
    res, K = solve_lp(E, with_budgets=wb)
    print(f"  covering LP{'+budgets' if wb else ''} min-holes (fractional) = {res.fun:.4f}"
          f"   status={res.message}", flush=True)
    print(f"  => min_holes >= ceil = {int(np.ceil(res.fun - 1e-6))}", flush=True)
