#!/usr/bin/env python3
"""Complete the hardest CONCENTRATED family: e_0=4 (star) + a 6-edge graph
in ONE 5-part (I=10), shape (6,5,5,5,5). There are exactly 6 non-iso 6-edge
graphs on 5 vertices. Confirm full-spec INFEASIBLE at q (cap = 10+q).

These are the configs where lb3's dual stalls; full-spec settles them.
"""
import sys, json, time, itertools
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
import general_rung as G
import networkx as nx
from ortools.sat.python import cp_model
from concurrent.futures import ProcessPoolExecutor, as_completed

P1 = list(range(6, 11))
star = [(0, 1), (0, 2), (0, 3), (0, 4)]


def six_edge_graphs():
    V = range(5); allp = list(itertools.combinations(V, 2))
    reps = []
    for es in itertools.combinations(allp, 6):
        Gg = nx.Graph(); Gg.add_nodes_from(V); Gg.add_edges_from(es)
        if any(nx.is_isomorphic(Gg, H) for H, _ in reps):
            continue
        reps.append((Gg, es))
    out = []
    for Gg, es in reps:
        E1 = [(P1[a], P1[b]) for a, b in es]
        tri = sum(nx.triangles(Gg).values()) // 3
        deg = sorted([d for _, d in Gg.degree()], reverse=True)
        out.append((f"deg{deg}_tri{tri}", E1))
    return out


def work(item):
    name, E1, q, tl, wk = item
    E = star + E1
    I = len(E); cap = I + q
    sizes = (6, 5, 5, 5, 5)
    t = time.time()
    built = G.build(sizes, E, cap)
    if built is None:
        return (name, q, cap, "BUILD_NONE", 0)
    m, h = built
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = tl
    s.parameters.num_search_workers = wk
    st = s.Solve(m)
    return (name, q, cap, s.StatusName(st), round(time.time() - t))


if __name__ == "__main__":
    q = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    TL = int(sys.argv[2]) if len(sys.argv) > 2 else 2400
    WK = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    CC = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    graphs = six_edge_graphs()
    items = [(name, E1, q, TL, WK) for name, E1 in graphs]
    print(f"hardest family: star + 6-edge-graph in P1 (I=10), q={q} cap={10+q}, "
          f"{len(items)} graphs, TL={TL} WK={WK} CC={CC}", flush=True)
    out = open("/Users/williamblair/personal/verified-combinatorics/erdos-617/"
               "artifacts/road66/handlemma/hardest_family.jsonl", "a")
    nbad = 0
    with ProcessPoolExecutor(max_workers=CC) as ex:
        futs = [ex.submit(work, it) for it in items]
        for fut in as_completed(futs):
            name, q, cap, st, secs = fut.result()
            out.write(json.dumps({"graph": name, "q": q, "cap": cap,
                                  "status": st, "secs": secs}) + "\n"); out.flush()
            flag = ""
            if st in ("OPTIMAL", "FEASIBLE"):
                flag = "  <<<<<< FEASIBLE: SURVIVES"; nbad += 1
            elif st != "INFEASIBLE":
                flag = "  (inconclusive)"; nbad += 1
            print(f"  {name}: q={q} cap={cap} -> {st} ({secs}s){flag}", flush=True)
    print(f"\nq={q}: {len(items)-nbad}/{len(items)} INFEASIBLE. "
          f"{'ALL dense single-part configs killed' if nbad==0 else 'SOME not killed'}", flush=True)
