#!/usr/bin/env python3
"""EXACT LP relaxation of the full general_rung spec, solved by HiGHS, with
dual extraction.  This is the LP whose CP-SAT integer optimum is the true
min-holes; its LP value is a rigorous lower bound (and matches the CP-SAT
BestObjectiveBound).  We solve it directly so we can (a) confirm the value
> cap and (b) READ OFF a fractional-packing dual certificate.

Model (variables x_p in [0,1], one per cross-pair p):
  minimize  sum_p x_p
  s.t. for every 6-set S:
       (COVER)  sum_{p in cross(S)} x_p >= 1                  if intraE(S)=#intra(S)
       (FUR)    sum_{p in cross(S)} x_p <= |cross(S)|+intraE(S)-4   [the >=4-edge cut]
  These are EXACTLY general_rung.build's two constraint families (build adds
  the FUR cut only when its rhs < min(|cross|,cap+1); for the LP lower bound we
  may add ALL of them -- more constraints only tighten -- but to MATCH build we
  replicate its guard with a large cap).

Dual (max):  sum_S yCov_S  -  sum_S rFur_S * zFur_S  -  sum_p s_p
  s.t. for every cross-pair p:
       sum_{S: p in cover(S)} yCov_S - sum_{S: p in fur(S)} zFur_S - s_p <= 1
  yCov,zFur,s >= 0.  A feasible dual with objective > cap CERTIFIES min>cap.

Usage: full_lp.py NAME [bigcap]   (bigcap default 99 = add all FUR cuts)
"""
import sys, itertools, time
import numpy as np
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
    P0 = PARTS[0]
    return [(P0[0], P0[1]), (P0[0], P0[2]), (P0[0], P0[3]), (P0[0], P0[4])]
def inpart(pi, local):
    P = PARTS[pi]; return [(P[a], P[b]) for (a, b) in local]
MATCH1=[(0,1)]; MATCH2=[(0,1),(2,3)]; PATH4=[(0,1),(1,2),(2,3),(3,4)]
C4=[(0,1),(1,2),(2,3),(0,3)]; C5=[(0,1),(1,2),(2,3),(3,4),(0,4)]
K23=[(0,2),(0,3),(0,4),(1,2),(1,3),(1,4)]
ATOMS = {
    "star_K23": star_P0()+inpart(1,K23),
    "star_C5":  star_P0()+inpart(1,C5),
    "star_C4":  star_P0()+inpart(1,C4),
    "star_2m_2m": star_P0()+inpart(1,MATCH2)+inpart(2,MATCH2),
    "star_path4": star_P0()+inpart(1,PATH4),
    "star_m_m_m_m": star_P0()+inpart(1,MATCH1)+inpart(2,MATCH1)+inpart(3,MATCH1)+inpart(4,MATCH1),
}

def build_rows(E, bigcap=99):
    Eset = set((min(a,b),max(a,b)) for a,b in E)
    cover_rows = []   # list of (cols)         -> sum >= 1
    fur_rows   = []   # list of (cols, rhs)    -> sum <= rhs
    for S in itertools.combinations(range(26), 6):
        cols, intra = [], []
        for a, b in itertools.combinations(S, 2):
            if PART_OF[a] != PART_OF[b]:
                cols.append(CIDX[(a,b)])
            else:
                intra.append((min(a,b),max(a,b)))
        intraE = sum(1 for p in intra if p in Eset)
        rhs = len(cols) + intraE - 4
        if rhs < 0:
            return None
        if rhs < min(len(cols), bigcap + 1):
            fur_rows.append((tuple(cols), rhs))
        if intraE == len(intra):
            cover_rows.append(tuple(cols))
    return cover_rows, fur_rows

def solve(E, bigcap=99):
    br = build_rows(E, bigcap)
    if br is None:
        return None
    cover_rows, fur_rows = br
    # Build A_ub x <= b_ub.  COVER as -sum<=-1 ; FUR as sum<=rhs.
    data, ri, ci, b = [], [], [], []
    r = 0
    for cols in cover_rows:
        for c in cols:
            data.append(-1.0); ri.append(r); ci.append(c)
        b.append(-1.0); r += 1
    for cols, rhs in fur_rows:
        for c in cols:
            data.append(1.0); ri.append(r); ci.append(c)
        b.append(float(rhs)); r += 1
    A = csr_matrix((data, (ri, ci)), shape=(r, NCOL))
    c = np.ones(NCOL)
    t = time.time()
    res = linprog(c, A_ub=A, b_ub=np.array(b), bounds=[(0,1)]*NCOL, method="highs")
    return res, cover_rows, fur_rows, round(time.time()-t)

if __name__ == "__main__":
    name = sys.argv[1]
    bigcap = int(sys.argv[2]) if len(sys.argv) > 2 else 99
    E = ATOMS[name]
    print(f"ATOM {name}: I={len(E)}, NCOL={NCOL}, bigcap={bigcap}", flush=True)
    out = solve(E, bigcap)
    if out is None:
        print("  INTRA_INFEAS"); sys.exit()
    res, cover_rows, fur_rows, secs = out
    print(f"  #cover={len(cover_rows)} #fur={len(fur_rows)}  LP solved in {secs}s", flush=True)
    print(f"  FULL-LP min-holes (fractional) = {res.fun:.4f}  ({res.message})", flush=True)
    print(f"  => min_holes >= ceil = {int(np.ceil(res.fun-1e-6))}", flush=True)
    # dump dual (marginals).  scipy: res.ineqlin.marginals are the duals of A_ub x<=b.
    try:
        m = res.ineqlin.marginals
        ncov = len(cover_rows)
        ycov = -m[:ncov]          # cover was multiplied by -1, dual sign flip
        zfur = -m[ncov:]          # <= constraint duals are <=0 in scipy convention
        print(f"  sum yCov={ycov.sum():.3f}  sum zFur={zfur.sum():.3f}  "
              f"nz_yCov={(ycov>1e-6).sum()} nz_zFur={(zfur>1e-6).sum()}", flush=True)
        np.savez(f"/Users/williamblair/personal/verified-combinatorics/erdos-617/artifacts/road66/lpdual/dual_{name}.npz",
                 ycov=ycov, zfur=zfur, value=res.fun)
        print(f"  dual saved to dual_{name}.npz", flush=True)
    except Exception as ex:
        print("  (dual extraction failed:", ex, ")", flush=True)
