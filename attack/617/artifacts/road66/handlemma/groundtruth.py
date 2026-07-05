#!/usr/bin/env python3
"""Full-spec ground truth on the configs where relaxations were weak.
These are the make-or-break tests: if the full model is INFEASIBLE at the
cap, the route closes for that config (and we then need a hand argument);
if FEASIBLE, the route has a genuine gap (a surviving config => m*>=66 is
NOT provable this way at that config).

Runs several configs in parallel, each with a long time limit. Logs verdicts.
"""
import sys, json, time, itertools
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
import general_rung as G
from ortools.sat.python import cp_model
from concurrent.futures import ProcessPoolExecutor, as_completed

parts = [list(range(0, 6)), list(range(6, 11)), list(range(11, 16)),
         list(range(16, 21)), list(range(21, 26))]


def edges_in(pi, k):
    v = parts[pi]
    allp = list(itertools.combinations(range(len(v)), 2))
    return [(v[a], v[b]) for (a, b) in allp[:k]]


star = [(0, 1), (0, 2), (0, 3), (0, 4)]

# (label, E, q) ; cap = I + q (defect 0 for 6,5,5,5,5)
# Decisive high-cap (6,5,5,5,5) configs at q=8 (lowest walled caps).
import os
_SET = os.environ.get("GTSET", "A")
if _SET == "A":
    CONFIGS = [
        ("star+4P1 I8 q8", star + edges_in(1, 4), 8),            # cap 16
        ("star+6P1 I10 q8", star + edges_in(1, 6), 8),           # cap 18
        ("star+3P1+3P2 I10 q8", star + edges_in(1, 3) + edges_in(2, 3), 8),  # cap 18
    ]
else:
    CONFIGS = [
        ("star+5P1 I9 q8", star + edges_in(1, 5), 8),            # cap 17
        ("star+2P1+2P2 I8 q8", star + edges_in(1, 2) + edges_in(2, 2), 8),   # cap 16
        ("Kbipartite23 P1 I10 q8", star + [(6,8),(6,9),(6,10),(7,8),(7,9),(7,10)], 8),  # K23 in P1, cap18
    ]


def work(item):
    label, E, q, tl, wk = item
    sizes = (6, 5, 5, 5, 5)
    I = len(E)
    cap = I + q  # d=0
    t = time.time()
    built = G.build(sizes, E, cap)
    if built is None:
        return (label, I, cap, "BUILD_NONE(intra-infeasible)", 0)
    m, h = built
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = tl
    s.parameters.num_search_workers = wk
    st = s.Solve(m)
    return (label, I, cap, s.StatusName(st), round(time.time() - t))


if __name__ == "__main__":
    TL = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    WK = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    CC = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    out = open("/Users/williamblair/personal/verified-combinatorics/erdos-617/"
               "artifacts/road66/handlemma/groundtruth.jsonl", "a")
    print(f"ground-truth full-spec, TL={TL} WK={WK} CC={CC}, {len(CONFIGS)} configs", flush=True)
    with ProcessPoolExecutor(max_workers=CC) as ex:
        futs = [ex.submit(work, (lab, E, q, TL, WK)) for (lab, E, q) in CONFIGS]
        for fut in as_completed(futs):
            label, I, cap, st, secs = fut.result()
            rec = {"label": label, "I": I, "cap": cap, "status": st, "secs": secs}
            out.write(json.dumps(rec) + "\n"); out.flush()
            flag = ""
            if st in ("OPTIMAL", "FEASIBLE"):
                flag = "  <<<<<< FEASIBLE: CONFIG SURVIVES (route GAP)"
            elif st == "INFEASIBLE":
                flag = "  (killed -> route closes here)"
            else:
                flag = "  (inconclusive, need more time)"
            print(f"  {label}: I={I} cap={cap} -> {st} ({secs}s){flag}", flush=True)
    print("done.", flush=True)
