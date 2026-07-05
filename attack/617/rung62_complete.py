"""Complete rung 62 (Erdos #617): (6,5,5,5,5) shape, all internal configs.

(7,5,5,5,4) is already INFEASIBLE (road62.py, validated).  Here we finish
the other q=6 shape, (6,5,5,5,5), by the fast fixed-config full-spec model
(the validated road62/caseB encoding generalized to an arbitrary internal
edge set).  At rung q=6, e(H)=264, holes = I + 6 (defect d=0), I = total
internal edges.  Enumerate every non-isomorphic internal configuration with
I in {4,5,6}: a graph on P0 (6 vtx, e0 in {4,5,6} edges) plus (I-e0) edges
distributed in the 5-parts.  INFEASIBLE for all => (6,5,5,5,5) dead at
e(H)=264 => (with (7,5,5,5,4)) m* >= 62.
"""
import sys, itertools
from ortools.sat.python import cp_model

PARTS = [list(range(0,6)), list(range(6,11)), list(range(11,16)),
         list(range(16,21)), list(range(21,26))]
part_of = {v: pi for pi, P in enumerate(PARTS) for v in P}
CROSS = [(a,b) for a,b in itertools.combinations(range(26),2) if part_of[a]!=part_of[b]]
CIDX = {e:i for i,e in enumerate(CROSS)}
assert len(CROSS) == 270
SIX = []
for S in itertools.combinations(range(26),6):
    cids, intra = [], []
    for a,b in itertools.combinations(S,2):
        (cids if part_of[a]!=part_of[b] else intra).append((a,b))
    SIX.append(([CIDX[p] for p in cids], intra))


def noniso_P0(e0):
    """non-isomorphic graphs on the 6 vertices 0..5 with e0 edges, every
    6-subset (=the whole set) spanning >= 4 edges i.e. e0>=4."""
    verts = list(range(6)); allpairs = list(itertools.combinations(verts,2))
    seen, reps = set(), []
    for es in itertools.combinations(allpairs, e0):
        best = None  # canonical form = min over the 720 relabelings of sorted edge tuple
        for perm in itertools.permutations(verts):
            mapped = tuple(sorted((min(perm[a],perm[b]),max(perm[a],perm[b])) for a,b in es))
            if best is None or mapped < best: best = mapped
        if best in seen: continue
        seen.add(best); reps.append(list(es))
    return reps


def fivepart_dists(k):
    """non-isomorphic ways to place k internal edges in the (symmetric) 5-parts.
    returns list of edge-lists (using vertices of P1,P2 as needed)."""
    P1, P2 = PARTS[1], PARTS[2]
    if k == 0: return [[]]
    if k == 1: return [[(P1[0],P1[1])]]
    if k == 2:
        return [
            [(P1[0],P1[1]),(P1[2],P1[3])],   # 2 disjoint in one part (matching)
            [(P1[0],P1[1]),(P1[1],P1[2])],   # 2 sharing a vertex in one part (path)
            [(P1[0],P1[1]),(P2[0],P2[1])],   # 1 in each of two parts
        ]
    raise ValueError(k)


def build(E, hole_cap):
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(270)]
    m.Add(sum(h) <= hole_cap)
    Eset = set((min(a,b),max(a,b)) for a,b in E)
    for cids, intra in SIX:
        intraE = sum(1 for p in intra if p in Eset)
        rhs = len(cids) + intraE - 4
        if rhs < 0:
            return None  # this 6-set can't be satisfied -> config invalid (e.g. e0<4 subset)
        if rhs < min(len(cids), hole_cap+1):
            m.Add(sum(h[i] for i in cids) <= rhs)
        if intraE == len(intra):
            m.AddBoolOr([h[i] for i in cids])
    return m, h


def main():
    tl = int(sys.argv[1]) if len(sys.argv) > 1 else 180
    allinf = True; ncfg = 0
    for I in (4,5,6):
        cap = I + 6
        for e0 in range(4, I+1):
            k = I - e0
            if k > 2: continue
            for P0cfg in noniso_P0(e0):
                for fp in fivepart_dists(k):
                    E = list(P0cfg) + list(fp)
                    ncfg += 1
                    built = build(E, cap)
                    if built is None:
                        continue
                    m, h = built
                    s = cp_model.CpSolver()
                    s.parameters.max_time_in_seconds = tl
                    s.parameters.num_search_workers = 6
                    st = s.StatusName(s.Solve(m))
                    tag = f"I={I} e0={e0} k={k} cap={cap} P0={P0cfg} fp={fp}"
                    if st != "INFEASIBLE":
                        allinf = False
                        print(f"  [{st}] {tag}", flush=True)
                        if st in ("OPTIMAL","FEASIBLE"):
                            print("    !! FEASIBLE witness — rung 62 NOT killed by this config", flush=True)
                    else:
                        print(f"  [INFEASIBLE] {tag}", flush=True)
    print(f"\n{ncfg} configs tested. VERDICT:",
          "(6,5,5,5,5) dead at e(H)=264 => m* >= 62" if allinf
          else "NOT all infeasible (see above)")


if __name__ == "__main__":
    main()
