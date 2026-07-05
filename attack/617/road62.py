"""Rung q=6, shape (7,5,5,5,4): the last layout for m* >= 62 (Erdos #617).

Adapted directly from the validated artifacts/caseB/caseB_model.py (same
full-spec encoding: H = complete 5-partite on parts of sizes (7,5,5,5,4),
MINUS a hole set, PLUS 6 internal edges inside the 7-part P0; enforce every
6-set spans >= 4 edges, and block every K6).

e(H) = (268 cross pairs - holes) + 6 internal = 274 - holes.  Proving
m* >= 62 means e(H) <= 263; assume e(H) >= 264 for contradiction <=> holes
<= 10.  If the decision "exists hole set, |holes| <= 10, H valid (every
6-set >= 4) and K6-free" is INFEASIBLE for all six 7-part structures, then
the (7,5,5,5,4) shape cannot achieve e(H)=264.  Combined with the
(6,5,5,5,5) shape (already INFEASIBLE 27/27, artifacts/caseB), this closes
rung 62: m* >= 62, unconditional modulo Furedi.

The 7-part has max-degree <= 2 (every 6-subset >= 4 => deg <= 2), so its 6
edges form a union of paths/cycles with exactly one path component: the six
structures below exhaust them.
"""
import sys
from itertools import combinations
from ortools.sat.python import cp_model

P0 = list(range(0, 7))     # the 7-part
P1 = list(range(7, 12))    # empty 5-part
P2 = list(range(12, 17))   # empty 5-part
P3 = list(range(17, 22))   # empty 5-part
Q  = list(range(22, 26))   # the 4-part (empty)
PARTS = [P0, P1, P2, P3, Q]
part_of = {}
for pi, P in enumerate(PARTS):
    for v in P:
        part_of[v] = pi

# six valid 6-edge max-degree-2 structures on the 7 vertices 0..6
CONFIGS = {
    "C6+K1":    [(0,1),(1,2),(2,3),(3,4),(4,5),(0,5)],
    "C3+C3+K1": [(0,1),(1,2),(0,2),(3,4),(4,5),(3,5)],
    "C5+P2":    [(0,1),(1,2),(2,3),(3,4),(0,4),(5,6)],
    "C4+P3":    [(0,1),(1,2),(2,3),(0,3),(4,5),(5,6)],
    "C3+P4":    [(0,1),(1,2),(0,2),(3,4),(4,5),(5,6)],
    "P7":       [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6)],
}
for name, edges in CONFIGS.items():
    assert len(edges) == 6
    deg = {}
    for a, b in edges:
        deg[a] = deg.get(a, 0) + 1; deg[b] = deg.get(b, 0) + 1
    assert max(deg.values()) <= 2, (name, deg)

CROSS = [(a, b) for a, b in combinations(range(26), 2) if part_of[a] != part_of[b]]
CIDX = {e: i for i, e in enumerate(CROSS)}
assert len(CROSS) == 268, len(CROSS)

SIXSETS = list(combinations(range(26), 6))
assert len(SIXSETS) == 230230
SIX_DATA = []
for S in SIXSETS:
    cross_ids, intraP0 = [], []
    for a, b in combinations(S, 2):
        if part_of[a] != part_of[b]:
            cross_ids.append(CIDX[(a, b)])
        elif part_of[a] == 0:
            intraP0.append((a, b))
        # intra pairs in empty parts contribute no edges
    SIX_DATA.append((cross_ids, intraP0))


def build_full(config_edges, hole_cap=10, model_cap=11):
    E = set((min(a, b), max(a, b)) for a, b in config_edges)
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(CROSS))]
    m.Add(sum(h) <= hole_cap)
    n_six = n_k6 = 0
    for (cross_ids, intraP0) in SIX_DATA:
        intraE = sum(1 for p in intraP0 if p in E)
        n_intra = len(intraP0)
        rhs = len(cross_ids) + intraE - 4
        if rhs < 0:
            raise RuntimeError("6-set infeasible independent of holes (bad config)")
        if rhs < min(len(cross_ids), model_cap):
            m.Add(sum(h[i] for i in cross_ids) <= rhs)
            n_six += 1
        if intraE == n_intra:                 # all intra pairs are edges => potential K6
            m.AddBoolOr([h[i] for i in cross_ids])
            n_k6 += 1
    return m, h, n_six, n_k6


def main():
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(f"(7,5,5,5,4) decision at holes <= {cap}  (INFEASIBLE all => m* >= 62)\n")
    allinf = True
    for name, edges in CONFIGS.items():
        m, h, n_six, n_k6 = build_full(edges, hole_cap=cap, model_cap=cap + 1)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 600
        solver.parameters.num_search_workers = 4
        st = solver.StatusName(solver.Solve(m))
        if st in ("OPTIMAL", "FEASIBLE"):
            allinf = False
            holes = [CROSS[i] for i in range(len(CROSS)) if solver.Value(h[i])]
            print(f"  {name:10s}: {st}  (witness, {len(holes)} holes) -> SAVING")
            with open(f"artifacts/road66/witness62_{name}.txt", "w") as f:
                for a, b in holes:
                    f.write(f"{a} {b}\n")
        else:
            print(f"  {name:10s}: {st}  ({n_six} six-cuts, {n_k6} K6-blocks)")
    print("\nVERDICT:", "all INFEASIBLE => (7,5,5,5,4) dead at e(H)=264 => m* >= 62"
          if allinf else "a layout is FEASIBLE — rung 62 NOT closed by this shape")


if __name__ == "__main__":
    main()
