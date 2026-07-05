#!/usr/bin/env python3
"""Compute the TRUE min-holes for the canonical triangle-free hard atoms,
using the full-spec general_rung model (build + Minimize).  This is the
ground-truth oracle the LP-duality bound must be calibrated against:
  if a claimed lower bound EXCEEDS the value printed here, the bound is WRONG.

Atom layout (shape (6,5,5,5,5), global vertex ids):
  P0 = 0..5  (the 6-part; carries the STAR star(P0) = K_{1,4} on {0;1,2,3,4})
  P1 = 6..10, P2 = 11..15, P3 = 16..20, P4 = 21..25  (the four 5-parts)

We place a triangle-free internal graph F across the four 5-parts and
report min-holes at a chosen cap (we set cap large so the Minimize is the
TRUE unconstrained min internal-to-the-spec; we also report at the actual
rung caps to know feasibility).

Usage: oracle_min.py NAME CAP [TL] [WK]
       NAME in the ATOMS dict below.
"""
import sys, time, itertools
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
import general_rung as G
from ortools.sat.python import cp_model

P0 = list(range(0, 6))
P1 = list(range(6, 11)); P2 = list(range(11, 16))
P3 = list(range(16, 21)); P4 = list(range(21, 26))
PARTS5 = [P1, P2, P3, P4]

def star_P0():
    # K_{1,4}: center 0 joined to 1,2,3,4 (leaves); vertex 5 isolated in P0.
    return [(0, 1), (0, 2), (0, 3), (0, 4)]

def inpart(p, local_edges):
    return [(p[a], p[b]) for (a, b) in local_edges]

# triangle-free graphs on 5 local vertices (within ONE 5-part)
MATCH1 = [(0, 1)]
MATCH2 = [(0, 1), (2, 3)]
PATH2  = [(0, 1), (1, 2)]
PATH3  = [(0, 1), (1, 2), (2, 3)]
PATH4  = [(0, 1), (1, 2), (2, 3), (3, 4)]
C4     = [(0, 1), (1, 2), (2, 3), (0, 3)]
C5     = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]
K23    = [(0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4)]  # parts {0,1}|{2,3,4}

ATOMS = {
    # canonical hardest: star(P0) + K_{2,3} in P1 ; I = 4 + 6 = 10
    "star_K23":          star_P0() + inpart(P1, K23),
    # star + C5 in one part ; I = 4 + 5 = 9
    "star_C5":           star_P0() + inpart(P1, C5),
    # star + C4 in one part ; I = 4 + 4 = 8
    "star_C4":           star_P0() + inpart(P1, C4),
    # star + 2-matching in EACH of two parts ; I = 4 + 2 + 2 = 8
    "star_2m_2m":        star_P0() + inpart(P1, MATCH2) + inpart(P2, MATCH2),
    # star + P4 path in one part ; I = 4 + 4 = 8
    "star_path4":        star_P0() + inpart(P1, PATH4),
    # the pure-matching diffuse profile (4,4,0,0,0) wrt edges-in-parts:
    # star(=4 edges in P0) + 4-matching... can't fit 4 disjoint edges on 5 vtx
    # (max matching on 5 vtx = 2).  So "(4,4,0,0,0)" profile means 4 edges in
    # P0 (the star) and 4 edges in P1.  Triangle-free 4-edge graphs on 5 vtx:
    # C4, P4, P3+e(=path3 plus a disjoint edge), star K_{1,3}+? ... we test C4,
    # path4, and "two matchings can't" -> use P4 and C4 above.
    # spread matchings: star + 2m in P1 + 2m in P2 + (nothing) already above.
    # spread across THREE/four parts:
    "star_m_m_m":        star_P0() + inpart(P1, MATCH1) + inpart(P2, MATCH1) + inpart(P3, MATCH1),
    "star_m_m_m_m":      star_P0() + inpart(P1, MATCH1) + inpart(P2, MATCH1) + inpart(P3, MATCH1) + inpart(P4, MATCH1),
    # NO-star variants (P0 empty) collapse to INTRA_INFEAS for a single
    # edge-part (Lemma D) -- but with edges in 2+ parts P0-empty is still
    # interesting at LOW I.  Provide a couple:
    "noP0_m_m":          inpart(P1, MATCH1) + inpart(P2, MATCH1),
    "noP0_C4":           inpart(P1, C4),
    # denser P0 (e0=6 star+? ) not needed; keep star.
}

def full_min(E, cap, tl, wk):
    sizes = (6, 5, 5, 5, 5)
    built = G.build(sizes, E, cap)
    if built is None:
        return ("INTRA_INFEAS", None, None, 0)
    m, h = built
    m.Minimize(sum(h))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = tl
    s.parameters.num_search_workers = wk
    t = time.time()
    st = s.Solve(m)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return (s.StatusName(st), int(round(s.ObjectiveValue())),
                int(round(s.BestObjectiveBound())), round(time.time() - t))
    return (s.StatusName(st), None, int(round(s.BestObjectiveBound())) if st != cp_model.UNKNOWN else None,
            round(time.time() - t))

if __name__ == "__main__":
    name = sys.argv[1]
    cap = int(sys.argv[2])
    tl = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    wk = int(sys.argv[4]) if len(sys.argv) > 4 else 12
    E = ATOMS[name]
    I = len(E)
    print(f"ATOM {name}: I={I} edges, cap={cap}, TL={tl}s WK={wk}", flush=True)
    st, mn, lb, secs = full_min(E, cap, tl, wk)
    print(f"  status={st} min_holes={mn} dualLB={lb} ({secs}s)", flush=True)
    # feasibility statement
    if mn is not None:
        print(f"  => TRUE min-holes (full spec) = {mn}.  "
              f"Config FEASIBLE at any cap >= {mn}, INFEASIBLE at cap < {mn}.", flush=True)
