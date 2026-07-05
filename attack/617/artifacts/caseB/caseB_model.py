"""Case B of rung q=5 (Erdos #617 m* hand attack), exact finite model.

H on 26 vertices = complete 5-partite K(6,5,5,5,5) on parts
P0(6),P1..P4(5)  MINUS a set of cross 'holes'  PLUS 5 internal edges:
a 4-edge configuration inside P0 and the edge xy inside P1.

Case B hypothesis space: does there exist a hole set with |holes| <= 10
such that H is K6-free and every 6-set spans >= 4 edges?
(holes <= 10  <=>  e(H) = 275 - holes >= 265.)

Models:
  F  : full spec (all 6-set >=4 conditions + all K6 blocking clauses)
  R0 : per-(vertex,5-set) budget caps + S1 blocking only (P0-edge systems)
  R1 : R0 + S2 blocking (xy system)

For each of the 9 nonisomorphic 4-edge P0 configs:
  decision F at <=10 (expect INFEASIBLE), then minimum holes for F, R1, R0.
Any SAT model is re-verified by an independent checker (check_caseB.py).
"""
import sys, json
from itertools import combinations, product
from ortools.sat.python import cp_model

P0 = list(range(0, 6))
P1 = list(range(6, 11))   # x=6, y=7
P2 = list(range(11, 16))
P3 = list(range(16, 21))
P4 = list(range(21, 26))
PARTS = [P0, P1, P2, P3, P4]
part_of = {}
for pi, P in enumerate(PARTS):
    for v in P:
        part_of[v] = pi
X, Y = 6, 7

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

CROSS = [(a, b) for a, b in combinations(range(26), 2) if part_of[a] != part_of[b]]
CIDX = {e: i for i, e in enumerate(CROSS)}
assert len(CROSS) == 270

SIXSETS = list(combinations(range(26), 6))
assert len(SIXSETS) == 230230
# precompute per 6-set: cross pair ids, intra-P0 pairs, intra-5part pairs
SIX_DATA = []
for S in SIXSETS:
    cross_ids, intraP0, intra5 = [], [], []
    for a, b in combinations(S, 2):
        if part_of[a] != part_of[b]:
            cross_ids.append(CIDX[(a, b)])
        elif part_of[a] == 0:
            intraP0.append((a, b))
        else:
            intra5.append((a, b))
    SIX_DATA.append((cross_ids, intraP0, intra5))


def internal_edge_set(config_edges):
    E = set()
    for a, b in config_edges:
        E.add((min(a, b), max(a, b)))
    E.add((X, Y))
    return E


def build_full(config_edges, hole_cap, model_cap_for_constraints):
    """Full-spec model.  Soundness note: omitting a 6-set constraint whose
    RHS >= model_cap_for_constraints is valid as long as total holes <=
    model_cap_for_constraints is enforced."""
    E = internal_edge_set(config_edges)
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(CROSS))]
    tot = sum(h)
    m.Add(tot <= hole_cap)
    n_six, n_k6 = 0, 0
    for (cross_ids, intraP0, intra5) in SIX_DATA:
        intraE = sum(1 for p in intraP0 if p in E) + sum(1 for p in intra5 if p == (X, Y))
        n_intra = len(intraP0) + len(intra5)
        rhs = len(cross_ids) + intraE - 4
        if rhs < 0:
            raise RuntimeError("infeasible 6-set independent of holes?!")
        if rhs < min(len(cross_ids), model_cap_for_constraints):
            m.Add(sum(h[i] for i in cross_ids) <= rhs)
            n_six += 1
        if intraE == n_intra:  # potential K6: all intra pairs are edges
            m.AddBoolOr([h[i] for i in cross_ids])
            n_k6 += 1
    return m, h, n_six, n_k6


def add_budgets(m, h, config_edges):
    E = internal_edge_set(config_edges)
    eP = [4, 1, 0, 0, 0]
    degP0 = {v: 0 for v in P0}
    for a, b in config_edges:
        degP0[a] += 1
        degP0[b] += 1
    def hv(a, b):
        return h[CIDX[(min(a, b), max(a, b))]]
    for w in range(26):
        for pi in range(1, 5):
            if part_of[w] == pi: continue
            m.Add(sum(hv(w, p) for p in PARTS[pi]) <= 1 + eP[pi])
        if part_of[w] != 0:
            for zp in P0:
                m.Add(sum(hv(w, p) for p in P0 if p != zp) <= 5 - degP0[zp])


def add_S1(m, h, config_edges):
    def hv(a, b):
        return h[CIDX[(min(a, b), max(a, b))]]
    n = 0
    for (u, v) in config_edges:
        for w1, w2, w3, w4 in product(P1, P2, P3, P4):
            ws = [w1, w2, w3, w4]
            lits = [hv(u, w) for w in ws] + [hv(v, w) for w in ws] + \
                   [hv(a, b) for a, b in combinations(ws, 2)]
            m.AddBoolOr(lits)
            n += 1
    return n


def add_S2(m, h):
    def hv(a, b):
        return h[CIDX[(min(a, b), max(a, b))]]
    n = 0
    for z in P0:
        for w2, w3, w4 in product(P2, P3, P4):
            ws = [w2, w3, w4]
            lits = [hv(X, z), hv(Y, z)] + [hv(X, w) for w in ws] + [hv(Y, w) for w in ws] + \
                   [hv(z, w) for w in ws] + [hv(a, b) for a, b in combinations(ws, 2)]
            m.AddBoolOr(lits)
            n += 1
    return n


def solve(m, h, minimize=False, time_limit=300, workers=8):
    if minimize:
        m.Minimize(sum(h))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    st = solver.Solve(m)
    name = solver.StatusName(st)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        holes = [CROSS[i] for i in range(len(CROSS)) if solver.Value(h[i])]
        return name, len(holes), holes, solver.BestObjectiveBound() if minimize else None
    return name, None, None, solver.BestObjectiveBound() if minimize else None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "decision"
    results = {}
    for cname, cedges in CONFIGS.items():
        if mode == "decision":
            m, h, n_six, n_k6 = build_full(cedges, hole_cap=10, model_cap_for_constraints=11)
            st, nh, holes, _ = solve(m, h, minimize=False, time_limit=600)
            print(f"[F<=10] {cname}: {st}" + (f" holes={nh}" if nh is not None else ""), flush=True)
            results[cname] = {"status": st, "holes": holes}
            if holes is not None:
                with open(f"/tmp/caseB/witness_F_{cname}.json", "w") as f:
                    json.dump({"config": cedges, "holes": holes}, f)
        elif mode == "minF":
            CAP = 60
            m, h, n_six, n_k6 = build_full(cedges, hole_cap=CAP, model_cap_for_constraints=CAP)
            st, nh, holes, bound = solve(m, h, minimize=True, time_limit=600)
            print(f"[minF] {cname}: {st} min={nh} bound={bound}", flush=True)
            results[cname] = {"status": st, "min": nh, "bound": bound}
            if holes is not None:
                with open(f"/tmp/caseB/witness_minF_{cname}.json", "w") as f:
                    json.dump({"config": cedges, "holes": holes}, f)
        elif mode in ("minR0", "minR1"):
            m = cp_model.CpModel()
            h = [m.NewBoolVar(f"h{i}") for i in range(len(CROSS))]
            add_budgets(m, h, cedges)
            add_S1(m, h, cedges)
            if mode == "minR1":
                add_S2(m, h)
            st, nh, holes, bound = solve(m, h, minimize=True, time_limit=600)
            print(f"[{mode}] {cname}: {st} min={nh} bound={bound}", flush=True)
            results[cname] = {"status": st, "min": nh, "bound": bound}
            if holes is not None:
                with open(f"/tmp/caseB/witness_{mode}_{cname}.json", "w") as f:
                    json.dump({"config": cedges, "holes": holes}, f)
    with open(f"/tmp/caseB/results_{mode}.json", "w") as f:
        json.dump(results, f, indent=1)


if __name__ == "__main__":
    main()
