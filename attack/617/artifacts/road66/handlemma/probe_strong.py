#!/usr/bin/env python3
"""Run the STRONG relaxation (B1+BK+BS3) on the apparent worst-case configs
to get genuine lower bounds on full min-holes, and compare to caps.

SLACKBASE = LB(full min_holes) - I. Config killed at rung q iff
true_min_holes >= I+q+1; using the relaxation's dual LB (a valid lower
bound on true min) we get: killed at q if LB - I >= q+1, i.e. LB-I > q.
"""
import sys, time, itertools
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617/artifacts/road66/handlemma")
import general_rung as G
from lb_oracle2 import lb2

parts = [list(range(0, 6)), list(range(6, 11)), list(range(11, 16)),
         list(range(16, 21)), list(range(21, 26))]


def edges_in(pi, k):
    """k edges inside part pi, chosen to be 'dense' (consecutive)."""
    v = parts[pi]
    allp = list(itertools.combinations(range(len(v)), 2))
    return [(v[a], v[b]) for (a, b) in allp[:k]]


star = [(0, 1), (0, 2), (0, 3), (0, 4)]
paw = [(0, 1), (1, 2), (0, 2), (0, 3)]  # has a triangle

# Worst-case candidates: minimal e0=4, edges concentrated in few 5-parts.
cases = []
for k in (2, 3, 4, 5, 6):
    cases.append((f"star + {k} edges in P1 (e0=4,e1={k}) I={4+k}", star + edges_in(1, k)))
cases.append(("star + 3 in P1 + 3 in P2 (I=10)", star + edges_in(1, 3) + edges_in(2, 3)))
cases.append(("star + 2 in P1 + 2 in P2 (I=8)", star + edges_in(1, 2) + edges_in(2, 2)))
cases.append(("paw(triangle) + 6 in P1 (I=10)", paw + edges_in(1, 6)))

FAM = ("B1", "BK", "BS3")
if __name__ == "__main__":
    TL = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    print(f"STRONG relaxation {FAM}, TL={TL}", flush=True)
    for name, E in cases:
        I = len(E)
        t = time.time()
        st, val, lb, _ = lb2((6, 5, 5, 5, 5), E, families=FAM, time_limit=TL, workers=6)
        secs = round(time.time() - t)
        if lb is None:
            print(f"  {name}: {st} (infeasible/err) ({secs}s)", flush=True)
            continue
        sb = lb - I
        kq = sb - 1  # killed through q <= kq
        verdict = "ALL q<=10 KILLED" if kq >= 10 else f"killed only q<={kq}  <<< GAP at q in [{max(8,kq+1)}..10]" if kq < 10 else ""
        print(f"  {name}: I={I} relax_min={val} LB={lb}  SLACKBASE>={sb}  -> {verdict}  ({secs}s)", flush=True)
