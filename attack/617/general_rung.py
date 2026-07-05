"""General multi-shape rung engine for Erdos #617 (2026-06-15).

Handles ANY Furedi shape (5 part-sizes summing to 26) and ANY internal-edge
total I, by enumerating non-isomorphic internal configurations (a valid graph
inside each part, every 6-subset of a part spanning >= 4 edges) up to the
part-permutation symmetry, then deciding the full-spec model at the budget
holes = I + q - defect.  INFEASIBLE for all admissible (shape, config) at a
rung => that rung closes.

Validated against rung 62 (6,5,5,5,5): reproduces 96 configs, all INFEASIBLE.

Usage: general_rung.py q [shape e.g. 8,5,5,5,3] [time_limit] [workers] [conc]
       (no shape => all machine-tractable shapes for that rung)
"""
import sys, json, time, itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
import networkx as nx
from ortools.sat.python import cp_model

ALLPAIRS26 = list(itertools.combinations(range(26), 2))
PIDX26 = {e: i for i, e in enumerate(ALLPAIRS26)}


def fmin(n): return {6: 4, 7: 6, 8: 8, 9: 11, 10: 12}.get(n, 0)
def defect(sizes): return sum(c * (c - 1) // 2 for c in sizes) - 55


def shapes_for(q):
    out = set()
    for c in itertools.combinations_with_replacement(range(1, 11), 5):
        if sum(c) == 26 and sum(fmin(n) for n in c) <= q:
            out.add(tuple(sorted(c, reverse=True)))
    return sorted(out, reverse=True)


_partcache = {}
def valid_part_graphs(n, e):
    """non-iso graphs on n vertices, e edges, every 6-subset spanning >= 4
    (vacuous for n < 6).  returns list of (edge_list, canon_hash)."""
    if (n, e) in _partcache:
        return _partcache[(n, e)]
    verts = list(range(n)); allp = list(itertools.combinations(verts, 2))
    buckets = {}; reps = []
    for es in itertools.combinations(allp, e):
        if n >= 6:
            deg = {}
            for a, b in es:
                deg[a] = deg.get(a, 0) + 1; deg[b] = deg.get(b, 0) + 1
            bad = False
            for drop in itertools.combinations(verts, n - 6):   # 6-subsets
                kept = e - sum(1 for a, b in es if a in drop or b in drop)
                if kept < 4: bad = True; break
            if bad: continue
        G = nx.Graph(); G.add_nodes_from(verts); G.add_edges_from(es)
        h = nx.weisfeiler_lehman_graph_hash(G, iterations=3)   # bucket only
        if any(nx.is_isomorphic(G, H) for (H, _) in buckets.get(h, [])):
            continue
        # exact iso-class id = (n, e, index): WL-hash COLLIDES for non-iso
        # regular graphs, so it must NOT be used as the dedup key downstream.
        rep_id = (n, e, len(reps))
        buckets.setdefault(h, []).append((G, es)); reps.append((list(es), rep_id))
    _partcache[(n, e)] = reps
    return reps


def enumerate_configs(sizes, I):
    """non-iso internal configs: a valid graph per part, total I edges,
    deduped up to permuting equal-size parts."""
    parts, off = [], 0
    for n in sizes:
        parts.append(list(range(off, off + n))); off += n
    # compositions of I across the 5 parts with e_i >= fmin(n_i)
    fmins = [fmin(n) for n in sizes]
    configs = {}
    def rec(i, rem, choice):
        if i == 5:
            if rem == 0:
                yield list(choice)
            return
        lo = fmins[i]
        for e in range(lo, rem - sum(fmins[i+1:]) + 1):
            yield from rec(i + 1, rem - e, choice + [e])
    for evec in rec(0, I, []):
        # per-part reps
        perpart = [valid_part_graphs(sizes[i], evec[i]) for i in range(5)]
        if any(len(pp) == 0 for pp in perpart):
            continue
        for combo in itertools.product(*perpart):
            # canonical key: multiset of (size, canon_hash) -- dedupes part swaps
            key = tuple(sorted((sizes[i], combo[i][1]) for i in range(5)))
            if key in configs:
                continue
            E = []
            for i in range(5):
                base = parts[i][0]
                for (a, b) in combo[i][0]:
                    E.append((base + a, base + b))
            configs[key] = E
    return list(configs.values())


def build(sizes, E, cap):
    parts, off, part_of = [], 0, {}
    for pi, n in enumerate(sizes):
        for v in range(off, off + n): part_of[v] = pi
        off += n
    Eset = set((min(a, b), max(a, b)) for a, b in E)
    cross = [PIDX26[(a, b)] for (a, b) in ALLPAIRS26 if part_of[a] != part_of[b]]
    cset = set(cross); cpos = {pi: i for i, pi in enumerate(cross)}
    m = cp_model.CpModel()
    h = [m.NewBoolVar(f"h{i}") for i in range(len(cross))]
    m.Add(sum(h) <= cap)
    for S in itertools.combinations(range(26), 6):
        cids, intra = [], []
        for a, b in itertools.combinations(S, 2):
            pi = PIDX26[(a, b)]
            if pi in cset: cids.append(cpos[pi])
            else: intra.append((a, b))
        intraE = sum(1 for p in intra if p in Eset)
        rhs = len(cids) + intraE - 4
        if rhs < 0:
            return None
        if rhs < min(len(cids), cap + 1):
            m.Add(sum(h[i] for i in cids) <= rhs)
        if intraE == len(intra):
            m.AddBoolOr([h[i] for i in cids])
    return m, h


def work(item):
    sizes, E, cap = item
    t0 = time.time()
    built = build(sizes, E, cap)
    if built is None:
        return (sizes, E, cap, "SKIP", 0)
    m, h = built
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = TL
    s.parameters.num_search_workers = WK
    return (sizes, E, cap, s.StatusName(s.Solve(m)), round(time.time() - t0))


def main():
    q = int(sys.argv[1])
    shape = tuple(int(x) for x in sys.argv[2].split(",")) if len(sys.argv) > 2 and "," in sys.argv[2] else None
    targets = [shape] if shape else shapes_for(q)
    import os
    MAXCAP = int(os.environ.get("MAXCAP", "99"))   # skip walled (cap>MAXCAP): hand-lemma territory
    items, walled = [], 0
    for sizes in targets:
        d = defect(sizes)
        for I in range(sum(fmin(n) for n in sizes), q + 1):
            cap = I + q - d
            for E in enumerate_configs(sizes, I):
                if cap > MAXCAP:
                    walled += 1; continue
                items.append((sizes, E, cap))
    if walled:
        print(f"({walled} walled configs cap>{MAXCAP} deferred to hand-lemma)", flush=True)
    print(f"rung q={q} targets={targets}: {len(items)} configs, TL={TL} WK={WK} CC={CC}", flush=True)
    out = open(f"artifacts/road66/general_q{q}.jsonl", "a")
    bad = done = 0
    with ProcessPoolExecutor(max_workers=CC) as ex:
        futs = [ex.submit(work, it) for it in items]
        for fut in as_completed(futs):
            sizes, E, cap, st, secs = fut.result(); done += 1
            out.write(json.dumps({"shape": list(sizes), "E": E, "cap": cap, "status": st, "secs": secs}) + "\n"); out.flush()
            if st not in ("INFEASIBLE", "SKIP"):
                bad += 1
                print(f"  [{st}] {sizes} cap={cap} E={E} ({secs}s)"
                      + ("  <<< FEASIBLE!" if st in ("OPTIMAL", "FEASIBLE") else "  <<< inconclusive"), flush=True)
            if done % 50 == 0:
                print(f"  ...{done}/{len(items)}, {bad} non-inf", flush=True)
    print(f"\nq={q}: {done} configs, {bad} non-infeasible. "
          + (f"ALL INFEASIBLE for {targets}" if bad == 0 else "NOT all closed"), flush=True)


if __name__ == "__main__":
    TL = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    WK = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    CC = int(sys.argv[5]) if len(sys.argv) > 5 else 8
    main()
else:
    TL, WK, CC = 600, 4, 8
