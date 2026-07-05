#!/usr/bin/env python3
"""Reproduce the CP-SAT MINIMIZE dual lower bound on min-holes for a chosen
triangle-free config on shape (6,5,5,5,5).  Reads BestObjectiveBound (the
LP/fractional-packing dual certificate) periodically and on completion.

This calibrates the EXPLICIT hand-built fractional packing in LPDUAL.md:
the hand packing value must be <= this dual LB and (we hope) > cap.

Usage: dualLB.py NAME CAP [TL] [WK]
"""
import sys, time
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
import general_rung as G
from ortools.sat.python import cp_model

P0 = list(range(0, 6))
P1 = list(range(6, 11)); P2 = list(range(11, 16))
P3 = list(range(16, 21)); P4 = list(range(21, 26))

def star_P0():
    return [(0, 1), (0, 2), (0, 3), (0, 4)]   # center 0; leaves 1..4; 5 isolated

def inpart(p, local):
    return [(p[a], p[b]) for (a, b) in local]

MATCH1 = [(0, 1)]
MATCH2 = [(0, 1), (2, 3)]
PATH4  = [(0, 1), (1, 2), (2, 3), (3, 4)]
C4     = [(0, 1), (1, 2), (2, 3), (0, 3)]
C5     = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]
K23    = [(0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4)]

ATOMS = {
    "star_K23":     star_P0() + inpart(P1, K23),
    "star_C5":      star_P0() + inpart(P1, C5),
    "star_C4":      star_P0() + inpart(P1, C4),
    "star_2m_2m":   star_P0() + inpart(P1, MATCH2) + inpart(P2, MATCH2),
    "star_path4":   star_P0() + inpart(P1, PATH4),
    "star_m_m_m_m": star_P0() + inpart(P1, MATCH1) + inpart(P2, MATCH1) + inpart(P3, MATCH1) + inpart(P4, MATCH1),
    # pure matching, NO star (P0 empty needs e0>=4 to be Furedi-valid actually;
    # but as a pure combinatorial relaxation of the hardest spread we keep it)
}

class Cb(cp_model.CpSolverSolutionCallback):
    def __init__(self):
        super().__init__(); self.n = 0
    def on_solution_callback(self):
        self.n += 1
        print(f"    [sol {self.n}] obj={self.ObjectiveValue()} bound={self.BestObjectiveBound()} t={self.WallTime():.0f}s", flush=True)

if __name__ == "__main__":
    name = sys.argv[1]; cap = int(sys.argv[2])
    tl = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    wk = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    E = ATOMS[name]; I = len(E)
    print(f"ATOM {name}: I={I}, cap={cap}, TL={tl}s WK={wk}", flush=True)
    built = G.build((6, 5, 5, 5, 5), E, cap)
    if built is None:
        print("  INTRA_INFEAS"); sys.exit()
    m, h = built
    m.Minimize(sum(h))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = tl
    s.parameters.num_search_workers = wk
    cb = Cb()
    t = time.time()
    st = s.Solve(m, cb)
    print(f"  status={s.StatusName(st)} obj={s.ObjectiveValue() if st in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None} "
          f"dualLB={s.BestObjectiveBound()} ({round(time.time()-t)}s)", flush=True)
    print(f"  => min_holes >= {int(s.BestObjectiveBound())} (dual). cap={cap}. "
          f"{'KILLED' if s.BestObjectiveBound() > cap else 'not yet'}", flush=True)
