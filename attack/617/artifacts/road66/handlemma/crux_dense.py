#!/usr/bin/env python3
"""DECISIVE test: full-spec feasibility of the hardest family --
e_0=4 (star) + e_1=6 (dense single 5-part), shape (6,5,5,5,5), I=10.
cap = I + q = 10 + q. Test q=8 (cap18) and q=10 (cap20).

If INFEASIBLE at cap20: route closes at q<=10 for this config.
If FEASIBLE at cap20 (or 18): a surviving config => the route to m*>=66
has a genuine gap here (this config is NOT killed).

We test several 6-edge P1 graphs (the structurally distinct ones) to find
the WEAKEST (most likely to survive).
"""
import sys, time, itertools, json
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
import general_rung as G
from ortools.sat.python import cp_model

P1 = list(range(6, 11))  # 6,7,8,9,10
star = [(0, 1), (0, 2), (0, 3), (0, 4)]

# 6-edge graphs on P1 (5 vertices), structurally distinct:
DENSE6 = {
    "hub(21~all)+2": [(6, 7), (6, 8), (6, 9), (6, 10), (7, 8), (9, 10)],  # two triangles sharing hub
    "K_{2,3}": [(6, 8), (6, 9), (6, 10), (7, 8), (7, 9), (7, 10)],        # bipartite, triangle-free
    "K4+isolated-edge?": [(6, 7), (6, 8), (6, 9), (7, 8), (7, 9), (8, 9)],  # K4 on {6,7,8,9}, 10 isolated
    "bull/house": [(6, 7), (7, 8), (8, 9), (9, 6), (6, 8), (7, 9)],       # K4-ish on 4 vtx (C4+diagonals)
    "wheel-ish": [(6, 7), (7, 8), (8, 6), (6, 9), (7, 9), (8, 10)],
}


def test(E, cap, tl=2000, wk=14):
    sizes = (6, 5, 5, 5, 5)
    t = time.time()
    built = G.build(sizes, E, cap)
    if built is None:
        return ("BUILD_NONE", round(time.time() - t))
    m, h = built
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = tl
    s.parameters.num_search_workers = wk
    st = s.Solve(m)
    return (s.StatusName(st), round(time.time() - t))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "K_{2,3}"
    q = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    tl = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
    F = DENSE6[which]
    E = star + F
    I = len(E); cap = I + q
    print(f"CRUX: star + [{which}] in P1, I={I}, q={q}, cap={cap}", flush=True)
    st, secs = test(E, cap, tl=tl)
    flag = "  <<<<<< FEASIBLE: SURVIVES (route GAP!)" if st in ("OPTIMAL", "FEASIBLE") else \
           ("  (INFEASIBLE: killed)" if st == "INFEASIBLE" else "  (inconclusive)")
    print(f"  => {st} ({secs}s){flag}", flush=True)
    with open("/Users/williamblair/personal/verified-combinatorics/erdos-617/"
              "artifacts/road66/handlemma/crux_dense.jsonl", "a") as f:
        f.write(json.dumps({"graph": which, "I": I, "q": q, "cap": cap,
                            "status": st, "secs": secs}) + "\n")
