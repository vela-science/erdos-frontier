#!/usr/bin/env python3
"""VALIDATION of the lower-bound certifier lb3 against the full-spec oracle.

lb3 is a SUB-MODEL of the full spec (it keeps a subset of the >=4-edge and
K6 constraints), so lb3_min <= full_min and lb3_dualLB <= full_min ALWAYS
(soundness by construction). What we machine-check here:

 (A) TIGHTNESS on a case with a known/​computable full min: lb3 should
     reproduce it (it does on Case-A C4: both 34).
 (B) KILL-CONSISTENCY: for configs where the full spec has a verdict at a
     cap, confirm  (lb3 certifies kill: lb3_dualLB>cap)  =>  full INFEASIBLE,
     and  (full FEASIBLE at cap)  =>  lb3_dualLB<=cap  (no false kill).

We also expose the full-spec decision so a reviewer can re-run any line.

Run: validate.py [time_limit]
"""
import sys, time, itertools
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617/artifacts/road66/handlemma")
import general_rung as G
from lb_oracle3 import lb3
from ortools.sat.python import cp_model

ALLPAIRS26 = G.ALLPAIRS26
PIDX26 = G.PIDX26
parts = [list(range(0, 6)), list(range(6, 11)), list(range(11, 16)),
         list(range(16, 21)), list(range(21, 26))]


def edges_in(pi, k):
    v = parts[pi]; allp = list(itertools.combinations(range(len(v)), 2))
    return [(v[a], v[b]) for (a, b) in allp[:k]]


def full_decision(sizes, E, cap, tl=300, wk=8):
    built = G.build(sizes, E, cap)
    if built is None:
        return "BUILD_NONE", 0
    m, h = built
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = tl
    s.parameters.num_search_workers = wk
    t = time.time()
    st = s.Solve(m)
    return s.StatusName(st), round(time.time() - t)


def full_min(sizes, E, cap_model, tl=300, wk=8):
    parts_, off, part_of = [], 0, {}
    for pi, n in enumerate(sizes):
        for v in range(off, off + n):
            part_of[v] = pi
        off += n
    Eset = set((min(a, b), max(a, b)) for a, b in E)
    cross = [PIDX26[(a, b)] for (a, b) in ALLPAIRS26 if part_of[a] != part_of[b]]
    cset = set(cross); cpos = {pi: i for i, pi in enumerate(cross)}
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(cross))]
    m.Add(sum(h) <= cap_model)
    for S in itertools.combinations(range(26), 6):
        cids, intra = [], []
        for a, b in itertools.combinations(S, 2):
            pi = PIDX26[(a, b)]
            (cids if pi in cset else intra).append(cpos[pi] if pi in cset else (a, b))
        ie = sum(1 for p in intra if p in Eset)
        rhs = len(cids) + ie - 4
        if rhs < 0:
            return "INTRA_INFEAS", None
        if rhs < min(len(cids), cap_model):
            m.Add(sum(h[i] for i in cids) <= rhs)
        if ie == len(intra):
            m.AddBoolOr([h[i] for i in cids])
    m.Minimize(sum(h))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = tl
    s.parameters.num_search_workers = wk
    st = s.Solve(m)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return s.StatusName(st), int(round(s.ObjectiveValue()))
    return s.StatusName(st), None


star = [(0, 1), (0, 2), (0, 3), (0, 4)]
C4 = [(0, 1), (1, 2), (2, 3), (0, 3)]

if __name__ == "__main__":
    TL = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    print("=== (A) TIGHTNESS: lb3 vs exact full min on Case-A C4 ===", flush=True)
    fst, fm = full_min((6, 5, 5, 5, 5), C4, 40, tl=TL)
    lst, lval, llb, _ = lb3((6, 5, 5, 5, 5), C4, conc_k=4, time_limit=min(TL, 120), workers=8)
    print(f"  Case-A C4: full_min=({fst},{fm})  lb3=({lst},min={lval},LB={llb})  "
          f"[expect all = 34]", flush=True)

    print("\n=== (B) KILL-CONSISTENCY: full-spec decision vs lb3 dual LB ===", flush=True)
    # configs with their cap; we report full verdict + lb3 LB and check agreement.
    CASES = [
        ("star+2xP1 (I6)", star + [(6, 7), (8, 9)], 14),         # full INFEAS@14 known
        ("star+triangleP1 (I7)", star + edges_in(1, 3), 15),     # full INFEAS@15 known
        ("star+P1,P2 (I6)", star + edges_in(1, 1) + edges_in(2, 1), 14),
    ]
    for name, E, cap in CASES:
        fst, fsecs = full_decision((6, 5, 5, 5, 5), E, cap, tl=TL, wk=8)
        lst, lval, llb, _ = lb3((6, 5, 5, 5, 5), E, conc_k=4, time_limit=min(TL, 120), workers=8)
        kill = (llb is not None and llb > cap)
        ok = "OK"
        if kill and fst != "INFEASIBLE":
            ok = "*** FALSE KILL: lb3 says kill but full not INFEASIBLE ***"
        if fst in ("OPTIMAL", "FEASIBLE") and llb is not None and llb > cap:
            ok = "*** lb3 killed a FEASIBLE config ***"
        print(f"  {name} cap={cap}: full={fst}({fsecs}s) lb3_LB={llb} "
              f"lb3_kill={kill}  [{ok}]", flush=True)
    print("\ndone.", flush=True)
