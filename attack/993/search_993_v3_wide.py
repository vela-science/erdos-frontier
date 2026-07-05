#!/usr/bin/env python3
"""
Erdős #993 — broadened search. Generalize the Kadrawi–Levit non-log-concave
family T_{3,m,n} to a parametric class of rooted "bush" trees, harvest a rich,
SEVERE non-log-concave seed set, check every generated tree for non-unimodality
(the single-tree prize), then sweep the FOREST surface (products / powers /
smoothings) where Hoggar's theorem says any forest counterexample must live.

Generalized builder G(branches):
  root r; for each branch (c, pls) in `branches`:
      r — b   (one node per branch)
      b has `c` children; child j carries a pendant PATH of pls[j] extra vertices.
  T_{3,m,n} = G([(3,[1,1,1]), (m,[1]*m), (n,[1]*n)]).
  T*_{3,m,n} = same but one child of the first branch has pendant length 2.
The structural knobs (root degree, per-branch child count, pendant depths) are
exactly what controls the log-concavity break, so scanning them yields many more
non-log-concave trees — and more severe ones — than the original two families.
"""
import sys, itertools
from itertools import combinations_with_replacement as cwr
import networkx as nx
from verify_993_kernel import (
    indpoly_tree, indpoly_forest, is_unimodal, is_logconcave, valley,
)


def build_bush(branches):
    """branches: list of (c, [pendant_len_0,...,pendant_len_{c-1}]). Returns adj, order."""
    g = nx.Graph()
    nid = [0]
    def new():
        v = nid[0]; nid[0] += 1; g.add_node(v); return v
    r = new()
    for (c, pls) in branches:
        b = new(); g.add_edge(r, b)
        for j in range(c):
            ch = new(); g.add_edge(b, ch)
            prev = ch
            for _ in range(pls[j]):          # pendant path of pls[j] extra vertices
                nxt = new(); g.add_edge(prev, nxt); prev = nxt
    return {v: list(g.neighbors(v)) for v in g.nodes()}, g.number_of_nodes()


def poly_of(adj):
    return indpoly_tree(adj, root=0)


def lc_severity(p):
    worst = 0.0
    for k in range(1, len(p) - 1):
        d = p[k] * p[k] - p[k - 1] * p[k + 1]
        denom = p[k] * p[k] if p[k] else 1
        r = d / denom
        if r < worst:
            worst = r
    return worst


def gen_library(order_cap=60, verbose=True):
    """
    Scan generalized bushes. Branch types: child-count c in 2..6, uniform pendant
    length L in 1..3 (plus a few mixed-pendant variants on one branch). Root degree
    a in 2..5. Collect distinct non-log-concave polynomials; flag non-unimodal.
    """
    # branch "types": (c, uniform L) plus a 'starred' variant (one child L+1)
    btypes = []
    for c in range(2, 8):
        for L in range(1, 5):
            btypes.append(("u", c, L))         # uniform pendant length L
            btypes.append(("s", c, L))         # one child gets pendant L+1 ("star")
    def make_branch(bt):
        kind, c, L = bt
        pls = [L] * c
        if kind == "s":
            pls[0] = L + 1
        return (c, pls)

    lib = {}            # poly-tuple -> (label, order, poly)
    prizes = []         # non-unimodal single trees
    scanned = 0
    for a in range(2, 7):                       # root degree (widened)
        for combo in cwr(range(len(btypes)), a):
            branches = [make_branch(btypes[i]) for i in combo]
            adj, o = build_bush(branches)
            if o > order_cap:
                continue
            p = poly_of(adj)
            scanned += 1
            if not is_unimodal(p):
                lbl = "bush(" + ",".join(f"{btypes[i][0]}{btypes[i][1]}p{btypes[i][2]}" for i in combo) + f")|n={o}"
                prizes.append((lbl, o, p))
                if verbose:
                    print(f"  *** SINGLE-TREE NON-UNIMODAL: {lbl}  valley={valley(p)}", flush=True)
            if not is_logconcave(p):
                key = tuple(p)
                if key not in lib:
                    lbl = "bush(" + ",".join(f"{btypes[i][0]}{btypes[i][1]}p{btypes[i][2]}" for i in combo) + f")|n={o}"
                    lib[key] = (lbl, o, p)
    libl = sorted(lib.values(), key=lambda t: lc_severity(t[2]))   # most severe first
    if verbose:
        print(f"  scanned {scanned} bushes; {len(libl)} distinct non-log-concave; "
              f"{len(prizes)} non-unimodal single trees", flush=True)
        if libl:
            print(f"  worst severity {lc_severity(libl[0][2]):.4f} at {libl[0][0]} "
                  f"(orders {min(o for _,o,_ in libl)}..{max(o for _,o,_ in libl)})", flush=True)
    return libl, prizes


def path_polys(nmax=16):
    out = []
    for nn in range(1, nmax + 1):
        g = {i: [] for i in range(nn)}
        for i in range(nn - 1):
            g[i].append(i + 1); g[i + 1].append(i)
        out.append((nn, indpoly_tree(g, root=0)))
    return out


def forest_surface(lib, smoothers, core=80, max_powers=20):
    """Cheap high-value checks: pairs+triples over core, powers, smoothings."""
    found = []
    tested = 0
    core_lib = lib[:min(core, len(lib))]
    N = len(core_lib)
    print(f"  forest surface over core={N} most-severe seeds", flush=True)

    def test(polys, tag):
        nonlocal tested
        prod = indpoly_forest(polys)
        tested += 1
        if not is_unimodal(prod):
            found.append((tag, prod, valley(prod)))
            print(f"  *** FOREST COUNTEREXAMPLE ({tag})", flush=True)

    for i, j in cwr(range(N), 2):
        test([core_lib[i][2], core_lib[j][2]], f"pair[{core_lib[i][0]} | {core_lib[j][0]}]")
    print(f"  [pairs over core] total {tested}", flush=True)
    for i, j, k in cwr(range(N), 3):
        test([core_lib[i][2], core_lib[j][2], core_lib[k][2]], "triple")
    print(f"  [triples over core] total {tested}", flush=True)

    for (lab, o, p) in lib:                       # powers over the FULL severe library
        acc = p
        for k in range(2, max_powers + 1):
            acc = indpoly_forest([acc, p])
            tested += 1
            if not is_unimodal(acc):
                found.append((f"{lab}^{k}", acc, valley(acc)))
                print(f"  *** POWER COUNTEREXAMPLE: {lab}^{k}", flush=True)
    print(f"  [powers] total {tested}", flush=True)

    for (lab, o, p) in core_lib:                  # severe seed x 1..3 paths
        for k in range(1, 4):
            for combo in cwr(range(len(smoothers)), k):
                prod = indpoly_forest([p] + [smoothers[i][1] for i in combo])
                tested += 1
                if not is_unimodal(prod):
                    found.append((lab + " + paths", prod, valley(prod)))
                    print(f"  *** SMOOTHED COUNTEREXAMPLE: {lab} + paths", flush=True)
    print(f"  [seed x paths] total {tested}", flush=True)
    return found, tested


def main():
    print("=== broadened non-log-concave library (generalized bushes) ===", flush=True)
    lib, prizes = gen_library(order_cap=60)
    if prizes:
        print(f"\n  *** {len(prizes)} NON-UNIMODAL SINGLE TREES — Erdős #993 DISPROVED ***")
        for lbl, o, p in prizes[:5]:
            print(f"    {lbl}: valley {valley(p)}\n      {p}")
        return prizes
    print("\n=== building path smoothers (P_1..P_16) ===", flush=True)
    smoothers = path_polys(16)
    print("\n=== FOREST SURFACE SWEEP ===", flush=True)
    found, tested = forest_surface(lib, smoothers, core=80, max_powers=20)
    print(f"\n  tested {tested} forest objects.", flush=True)
    if found:
        print(f"  *** {len(found)} NON-UNIMODAL FORESTS — Erdős #993 DISPROVED ***")
        for lbl, prod, v in found[:10]:
            print(f"    {lbl}: valley {v}")
    else:
        print("  no non-unimodal tree OR forest found across the broadened surface.")
    return found


if __name__ == "__main__":
    main()
