"""q=6 Case-B variants (budget <= 12), full spec, decision + min.

Variants (e(P0)=4 fixed at 4-edge config; I5 = 2):
  i-m : two-edge MATCHING in P1: edges (6,7),(8,9)
  i-p : two-edge PATH in P1:     edges (6,7),(7,8)
  ii  : one edge in P1 and one in P2: (6,7),(11,12)

holes <= 12  <=>  e(H) = 270 + 6 - holes >= 264.
"""
import sys, json
from itertools import combinations
from ortools.sat.python import cp_model

P0 = list(range(0, 6))
PARTS = [P0, list(range(6,11)), list(range(11,16)), list(range(16,21)), list(range(21,26))]
part_of = {}
for pi, P in enumerate(PARTS):
    for v in P: part_of[v] = pi

CONFIGS = {
    "star":  [(0,1),(0,2),(0,3),(0,4)],
    "chair": [(0,1),(0,2),(0,3),(3,4)],
    "K13K2": [(0,1),(0,2),(0,3),(4,5)],
    "P5":    [(0,1),(1,2),(2,3),(3,4)],
    "P4K2":  [(0,1),(1,2),(2,3),(4,5)],
    "P3P3":  [(0,1),(1,2),(3,4),(4,5)],
    "C4":    [(0,1),(1,2),(2,3),(0,3)],
    "K3K2":  [(0,1),(1,2),(0,2),(3,4)],
    "paw":   [(0,1),(1,2),(0,2),(0,3)],
}
VARIANTS = {
    "i-m": [(6,7),(8,9)],
    "i-p": [(6,7),(7,8)],
    "ii":  [(6,7),(11,12)],
}

CROSS = [(a,b) for a,b in combinations(range(26),2) if part_of[a]!=part_of[b]]
CIDX = {e:i for i,e in enumerate(CROSS)}

SIX_DATA = []
for S in combinations(range(26),6):
    cross_ids, intra = [], []
    for a,b in combinations(S,2):
        if part_of[a]!=part_of[b]: cross_ids.append(CIDX[(a,b)])
        else: intra.append((a,b))
    SIX_DATA.append((cross_ids, intra))

def build(config_edges, part_edges, hole_cap, ccap):
    E = {tuple(sorted(e)) for e in config_edges} | {tuple(sorted(e)) for e in part_edges}
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(CROSS))]
    m.Add(sum(h) <= hole_cap)
    for cross_ids, intra in SIX_DATA:
        intraE = sum(1 for p in intra if p in E)
        rhs = len(cross_ids) + intraE - 4
        if rhs < 0: raise RuntimeError("bad")
        if rhs < min(len(cross_ids), ccap):
            m.Add(sum(h[i] for i in cross_ids) <= rhs)
        if intraE == len(intra):
            m.AddBoolOr([h[i] for i in cross_ids])
    return m, h

def main():
    mode = sys.argv[1]          # decision | min
    variant = sys.argv[2]       # i-m | i-p | ii
    results = {}
    for cname, cedges in CONFIGS.items():
        if mode == "decision":
            m, h = build(cedges, VARIANTS[variant], 12, 13)
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 900
            solver.parameters.num_search_workers = 8
            st = solver.Solve(m)
            name = solver.StatusName(st)
            out = f"[q6 {variant} <=12] {cname}: {name}"
            if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                holes = [CROSS[i] for i in range(len(CROSS)) if solver.Value(h[i])]
                out += f" holes={len(holes)}"
                with open(f"/tmp/caseB/witness_q6{variant}_{cname}.json","w") as f:
                    json.dump({"config":cedges,"part_edges":VARIANTS[variant],"holes":holes},f)
            print(out, flush=True)
            results[cname] = name
        else:
            CAP = 60
            m, h = build(cedges, VARIANTS[variant], CAP, CAP)
            m.Minimize(sum(h))
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 900
            solver.parameters.num_search_workers = 8
            st = solver.Solve(m)
            name = solver.StatusName(st)
            nh = None
            if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                nh = sum(solver.Value(x) for x in h)
                holes = [CROSS[i] for i in range(len(CROSS)) if solver.Value(h[i])]
                with open(f"/tmp/caseB/witness_q6min{variant}_{cname}.json","w") as f:
                    json.dump({"config":cedges,"part_edges":VARIANTS[variant],"holes":holes},f)
            print(f"[q6min {variant}] {cname}: {name} min={nh} bound={solver.BestObjectiveBound()}", flush=True)
            results[cname] = (name, nh)
    with open(f"/tmp/caseB/results_q6_{mode}_{variant}.json","w") as f:
        json.dump(results,f,indent=1)

if __name__ == "__main__":
    main()
