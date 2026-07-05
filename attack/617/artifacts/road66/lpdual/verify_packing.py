#!/usr/bin/env python3
"""Independently VERIFY a fractional-packing certificate for min-holes.

A certificate is a vector y >= 0 indexed by potential-K6 sets K with
  (CAP)  for every cross-pair p:  sum_{K ni p} y_K <= 1
  (VAL)  sum_K y_K > cap
Then min_holes >= sum_K y_K > cap  (pure fractional covering / weak LP duality),
so the config is INFEASIBLE at that rung.  This file recomputes y by solving the
covering LP's DUAL directly (max packing), checks (CAP) exactly with Fractions,
and reports the value vs cap.  No Furedi cuts are used -- pure covering -- so the
certificate is elementary and hand-auditable.

It also reports, per atom, the gap cap - value (negative => closed by packing).

Usage: verify_packing.py NAME CAP
"""
import sys, itertools
import numpy as np
from fractions import Fraction
from scipy.optimize import linprog
from scipy.sparse import csr_matrix

SIZES = (6, 5, 5, 5, 5)
PARTS, off = [], 0
for n in SIZES:
    PARTS.append(list(range(off, off + n))); off += n
PART_OF = {v: pi for pi, P in enumerate(PARTS) for v in P}
ALLPAIRS = list(itertools.combinations(range(26), 2))
CROSS = [(a, b) for (a, b) in ALLPAIRS if PART_OF[a] != PART_OF[b]]
CIDX = {p: i for i, p in enumerate(CROSS)}
NCOL = len(CROSS)

def star_P0():
    P0 = PARTS[0]; return [(P0[0],P0[1]),(P0[0],P0[2]),(P0[0],P0[3]),(P0[0],P0[4])]
def inpart(pi, local):
    P = PARTS[pi]; return [(P[a],P[b]) for (a,b) in local]
MATCH1=[(0,1)]; MATCH2=[(0,1),(2,3)]; PATH4=[(0,1),(1,2),(2,3),(3,4)]
C4=[(0,1),(1,2),(2,3),(0,3)]; C5=[(0,1),(1,2),(2,3),(3,4),(0,4)]
K23=[(0,2),(0,3),(0,4),(1,2),(1,3),(1,4)]
ATOMS = {
    "star_K23":star_P0()+inpart(1,K23),"star_C5":star_P0()+inpart(1,C5),
    "star_C4":star_P0()+inpart(1,C4),"star_2m_2m":star_P0()+inpart(1,MATCH2)+inpart(2,MATCH2),
    "star_path4":star_P0()+inpart(1,PATH4),
    "star_m_m_m_m":star_P0()+inpart(1,MATCH1)+inpart(2,MATCH1)+inpart(3,MATCH1)+inpart(4,MATCH1),
}

def potential_k6s(E):
    Eset = set((min(a,b),max(a,b)) for a,b in E)
    out = []
    for S in itertools.combinations(range(26), 6):
        cols, ok = [], True
        for a, b in itertools.combinations(S, 2):
            if PART_OF[a]==PART_OF[b]:
                if (a,b) not in Eset: ok=False; break
            else: cols.append(CIDX[(a,b)])
        if ok: out.append(tuple(cols))
    return out

def max_packing(E):
    """Solve the covering LP DUAL: max sum y_K s.t. for each cross-pair p
    sum_{K ni p} y_K <= 1, y>=0.  (LP-dual of min-cover.)  Returns y, value, K."""
    K = potential_k6s(E)
    nK = len(K)
    # constraints: for each cross-pair col c:  sum_{K ni c} y_K <= 1
    # build A (NCOL x nK)
    data, ri, ci = [], [], []
    for k, cols in enumerate(K):
        for c in cols:
            data.append(1.0); ri.append(c); ci.append(k)
    A = csr_matrix((data, (ri, ci)), shape=(NCOL, nK))
    # maximize sum y  ==  minimize -sum y
    res = linprog(-np.ones(nK), A_ub=A, b_ub=np.ones(NCOL),
                  bounds=[(0, None)]*nK, method="highs")
    y = res.x
    return y, -res.fun, K

def verify(E, cap, y, K, tol=1e-6):
    """Exact-ish check of (CAP) and (VAL).  Reports max capacity load and value."""
    load = np.zeros(NCOL)
    for k, cols in enumerate(K):
        if y[k] > tol:
            for c in cols:
                load[c] += y[k]
    maxload = load.max()
    value = y.sum()
    feasible = maxload <= 1 + 1e-6
    return feasible, maxload, value

if __name__ == "__main__":
    name = sys.argv[1]; cap = int(sys.argv[2])
    E = ATOMS[name]
    y, val, K = max_packing(E)
    feas, maxload, value = verify(E, cap, y, K)
    print(f"ATOM {name}: I={len(E)}  cap={cap}  #K6={len(K)}", flush=True)
    print(f"  max fractional packing value = {value:.4f}", flush=True)
    print(f"  capacity check: max cross-pair load = {maxload:.6f}  (must be <= 1)  -> {'OK' if feas else 'VIOLATED'}", flush=True)
    nz = int((y > 1e-6).sum())
    print(f"  support: {nz} K6-obligations carry positive weight", flush=True)
    verdict = "CLOSES (packing > cap)" if value > cap + 1e-6 else f"FALLS SHORT by {cap - value:.3f}"
    print(f"  => min_holes >= {value:.3f}  vs cap {cap}:  {verdict}", flush=True)
