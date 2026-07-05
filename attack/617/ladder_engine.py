"""General rung engine for Erdos #617 m* lower bound (2026-06-13).

Proves m* >= 56 + q by killing rung q: no graph H on 26 vertices that is
K6-free, has every 6-set spanning >= 4 edges, e(H) = 270 - q, and whose
Furedi 5-partition has shape `sizes` (with <= q internal edges).

Encoding per shape (internal edges are VARIABLES, so NO config is missed):
  x[pair] in {0,1} for all 325 pairs;
  every 6-set S:  4 <= sum_{pairs in S} x <= 14   (>=4 balanced; <=14 K6-free);
  sum_all x = 270 - q                              (e(H) = 270 - q);
  sum_{intra-part pairs} x <= q                    (Furedi: <= q internal edges).
INFEASIBLE for every admissible shape  =>  rung q killed  =>  m* >= 56 + q.

m* >= 66 (rungs q=6..10 all killed) proves the r=5 case of Erdos #617.

Usage: ladder_engine.py q [time_limit_s] [workers]
"""
import sys, itertools, json
from ortools.sat.python import cp_model

V = range(26)
PAIRS = list(itertools.combinations(V, 2))
PIDX = {e: i for i, e in enumerate(PAIRS)}
assert len(PAIRS) == 325

# per-6-set: the 15 pair-indices (shape-independent)
SIX_PAIRIDX = []
for S in itertools.combinations(V, 6):
    SIX_PAIRIDX.append([PIDX[p] for p in itertools.combinations(S, 2)])
assert len(SIX_PAIRIDX) == 230230


def f_min(n):                       # min internal edges of an n-part
    return {0:0,1:0,2:0,3:0,4:0,5:0,6:4,7:6,8:8,9:11,10:12}[n]


def shapes_for_rung(q):
    """All size-vectors (5 positive parts summing to 26) with sum f <= q,
    up to sorting (descending)."""
    out = []
    for c in itertools.combinations_with_replacement(range(1, 11), 5):
        if sum(c) != 26:
            continue
        sizes = tuple(sorted(c, reverse=True))
        if sizes in out:
            continue
        if sum(f_min(n) for n in sizes) <= q:
            out.append(sizes)
    return sorted(set(out), reverse=True)


def part_assignment(sizes):
    parts, v = [], 0
    for n in sizes:
        parts.append(list(range(v, v + n))); v += n
    return parts


def run_shape(sizes, q, time_limit=900, workers=8):
    parts = part_assignment(sizes)
    part_of = {v: pi for pi, P in enumerate(parts) for v in P}
    intra_idx = [PIDX[(a, b)] for (a, b) in PAIRS if part_of[a] == part_of[b]]
    m = cp_model.CpModel()
    x = [m.NewBoolVar(f"x{i}") for i in range(325)]
    for pidx in SIX_PAIRIDX:
        s = sum(x[i] for i in pidx)
        m.Add(s >= 4)
        m.Add(s <= 14)
    m.Add(sum(x) == 270 - q)
    m.Add(sum(x[i] for i in intra_idx) <= q)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    st = solver.StatusName(solver.Solve(m))
    witness = None
    if st in ("OPTIMAL", "FEASIBLE"):
        witness = [PAIRS[i] for i in range(325) if solver.Value(x[i])]
    return st, witness


def main():
    q = int(sys.argv[1])
    tl = int(sys.argv[2]) if len(sys.argv) > 2 else 900
    wk = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    shapes = shapes_for_rung(q)
    print(f"rung q={q}: e(H)={270-q}, {len(shapes)} admissible shapes: {shapes}", flush=True)
    allinf = True
    results = {}
    for sizes in shapes:
        st, witness = run_shape(sizes, q, time_limit=tl, workers=wk)
        results[str(sizes)] = st
        print(f"  {str(sizes):20s}: {st}", flush=True)
        if st in ("OPTIMAL", "FEASIBLE"):
            allinf = False
            with open(f"artifacts/road66/ladder_witness_q{q}_{'_'.join(map(str,sizes))}.txt", "w") as fo:
                for a, b in witness:
                    fo.write(f"{a} {b}\n")
            print(f"    !! FEASIBLE — witness saved; rung {q} NOT killed by this shape", flush=True)
        elif st not in ("INFEASIBLE",):
            allinf = False
            print(f"    ?? {st} (timeout/unknown) — inconclusive, needs more time", flush=True)
    verdict = (f"rung {q} KILLED => m* >= {56+q}" if allinf
               else f"rung {q} NOT fully killed (see above)")
    print(f"\nVERDICT q={q}: {verdict}", flush=True)
    with open(f"artifacts/road66/ladder_q{q}_results.json", "w") as fo:
        json.dump({"q": q, "results": results, "all_infeasible": allinf}, fo, indent=1)


if __name__ == "__main__":
    main()
