#!/usr/bin/env python3
"""
Erdős #993 search driver — non-log-concave tree families (Kadrawi–Levit–Yosef–
Mizrachi) as seeds, then the genuinely-unsearched FOREST-PRODUCT surface.

Math that focuses the search (Hoggar): the convolution of two log-concave
positive sequences is log-concave. A forest's independence polynomial is the
product of its components'. Hence a forest can be NON-unimodal only if it has a
NON-log-concave component. The smallest non-log-concave tree is order 26, and the
only known supply is the families T_{3,m,n} and T*_{3,m,n}. So the unsearched
counterexample surface = products/powers built from these non-log-concave trees.
A single forest with a strict interior valley DISPROVES Alavi–Erdős–Malde–Schwenk.

Families (from arXiv:2305.01784 / 2603.03025):
  T_{3,m,n}:  root r -> v1,v2,v3.
              v1 has 3 children; v2 has m children; v3 has n children;
              EVERY one of those (3+m+n) children has exactly one further child.
              order = 1 + 3 + 2*(3+m+n) = 10 + 2m + 2n.  T_{3,4,4} = 26.
  T*_{3,m,n}: same, but ONE of v1's three branches is lengthened by one extra
              vertex (a pendant P4 tail instead of P3). order = 12 + 2m + 2n.
              T*_{3,3,4} = 26.
"""
import sys
from itertools import combinations_with_replacement
import networkx as nx
from verify_993_kernel import (
    indpoly_tree, indpoly_forest, is_unimodal, is_logconcave, valley, tree_adj,
)


def build_T(m, n, star=False):
    """Build T_{3,m,n} (star=False) or T*_{3,m,n} (star=True). Returns adj dict."""
    g = nx.Graph()
    nid = [0]
    def new():
        v = nid[0]; nid[0] += 1; g.add_node(v); return v
    r = new()
    branches = [3, m, n]
    for bi, deg in enumerate(branches):
        v = new(); g.add_edge(r, v)
        for j in range(deg):
            ch = new(); g.add_edge(v, ch)
            gch = new(); g.add_edge(ch, gch)        # each child has one further child
            # T*: replace edge (child,grandchild) by a P4 tail -> add TWO vertices
            #     so branch v1-child-grandchild-x-y  (paper: v13-v13'-x-y)
            if star and bi == 0 and j == 0:
                x = new(); g.add_edge(gch, x)
                y = new(); g.add_edge(x, y)
    return {v: list(g.neighbors(v)) for v in g.nodes()}, g.number_of_nodes()


def poly_of(adj):
    return indpoly_tree(adj, root=0)


def report(label, p):
    lc = is_logconcave(p); uni = is_unimodal(p); v = valley(p)
    flag = ""
    if not uni:
        flag = "  *** NON-UNIMODAL — COUNTEREXAMPLE ***"
    elif not lc:
        flag = "  [non-log-concave, unimodal]"
    print(f"{label}: order? deg={len(p)-1} logconcave={lc} unimodal={uni}{flag}")
    if not uni:
        print(f"    valley {v}  coeffs={p}")
    return uni, lc


def validate_seeds():
    print("=== validate against literature: order-26 non-log-concave trees ===")
    adj1, o1 = build_T(4, 4, star=False)   # T_{3,4,4}
    p1 = poly_of(adj1)
    u1, lc1 = report(f"T_3,4,4 (order {o1})", p1)
    adj2, o2 = build_T(3, 4, star=True)    # T*_{3,3,4}
    p2 = poly_of(adj2)
    u2, lc2 = report(f"T*_3,3,4 (order {o2})", p2)
    ok = (o1 == 26 and not lc1 and u1 and o2 == 26 and not lc2 and u2)
    print(f"  -> seeds reproduce literature (order 26, non-log-concave, unimodal): "
          f"{'PASS' if ok else 'FAIL'}\n")
    return ok


def nlc_library(mmax=14, nmax=14):
    """All non-log-concave trees from both families with m,n in range, deduped by poly."""
    lib = []          # list of (label, order, poly)
    seen = set()
    for star in (False, True):
        for m in range(2, mmax + 1):
            for n in range(2, nmax + 1):
                if n < m:
                    continue  # symmetry in m,n
                adj, o = build_T(m, n, star=star)
                p = poly_of(adj)
                if not is_logconcave(p):
                    if not is_unimodal(p):
                        print(f"  *** single-tree COUNTEREXAMPLE: "
                              f"{'T*' if star else 'T'}_3,{m},{n} order {o}")
                    key = tuple(p)
                    if key not in seen:
                        seen.add(key)
                        lib.append((f"{'T*' if star else 'T'}_3,{m},{n}", o, p))
    return lib


def path_polys(nmax=20):
    """Independence polynomials of paths P_1..P_nmax (log-concave smoothers)."""
    out = []
    for nn in range(1, nmax + 1):
        g = {i: [] for i in range(nn)}
        for i in range(nn - 1):
            g[i].append(i + 1); g[i + 1].append(i)
        out.append((nn, indpoly_tree(g, root=0)))
    return out


def lc_severity(p):
    """Most negative normalized log-concavity defect min_k (c_k^2 - c_{k-1}c_{k+1})."""
    worst = 0.0
    for k in range(1, len(p) - 1):
        d = p[k] * p[k] - p[k - 1] * p[k + 1]
        denom = p[k] * p[k] if p[k] else 1
        r = d / denom
        if r < worst:
            worst = r
    return worst   # <0 means non-log-concave; more negative = more severe


def product_search(lib, smoothers, max_powers=16, core_size=50):
    """
    Forest-product surface, restricted to where a counterexample can live:
      (1) PAIRS and TRIPLES among ALL non-log-concave trees (bumps reinforce);
      (2) QUADS and QUINTS among the most-severely non-log-concave 'core' subset;
      (3) powers I(T)^k, k=2..max_powers (does a power develop a valley?);
      (4) one non-log-concave tree x up to 3 path smoothers.
    Any non-unimodal product DISPROVES Erdős #993.
    """
    found = []
    tested = 0
    nlc = lib                       # [(label, order, poly)]
    N = len(nlc)
    # rank by severity; core = most severe
    order_by_sev = sorted(range(N), key=lambda i: lc_severity(nlc[i][2]))
    core = order_by_sev[:min(core_size, N)]
    print(f"  core (most-severe) = {len(core)} trees; "
          f"worst defect {lc_severity(nlc[order_by_sev[0]][2]):.4f}", flush=True)

    def test(idxs, tag):
        nonlocal tested
        prod = indpoly_forest([nlc[i][2] for i in idxs])
        tested += 1
        if not is_unimodal(prod):
            labels = " + ".join(nlc[i][0] for i in idxs)
            found.append((labels, prod, valley(prod)))
            print(f"  *** FOREST COUNTEREXAMPLE ({tag}): {labels}", flush=True)

    # (1) pairs & triples over ALL nlc
    for combo in combinations_with_replacement(range(N), 2):
        test(combo, "pair")
    print(f"  [pairs over all {N}] tested, running total {tested}", flush=True)
    for combo in combinations_with_replacement(range(N), 3):
        test(combo, "triple")
    print(f"  [triples over all {N}] running total {tested}", flush=True)

    # (2) quads & quints over core
    for combo in combinations_with_replacement(core, 4):
        test(combo, "quad")
    print(f"  [quads over core] running total {tested}", flush=True)
    for combo in combinations_with_replacement(core, 5):
        test(combo, "quint")
    print(f"  [quints over core] running total {tested}", flush=True)

    # (3) pure powers
    for (lab, o, p) in nlc:
        acc = p
        for k in range(2, max_powers + 1):
            acc = indpoly_forest([acc, p])
            tested += 1
            if not is_unimodal(acc):
                found.append((f"{lab}^{k}", acc, valley(acc)))
                print(f"  *** POWER COUNTEREXAMPLE: {lab}^{k}", flush=True)
    print(f"  [powers up to {max_powers}] running total {tested}", flush=True)

    # (4) non-log-concave tree x 1..3 path smoothers
    for (lab, o, p) in nlc:
        for k in range(1, 4):
            for combo in combinations_with_replacement(range(len(smoothers)), k):
                prod = indpoly_forest([p] + [smoothers[i][1] for i in combo])
                tested += 1
                if not is_unimodal(prod):
                    lbl = lab + " + " + " + ".join(f"P{smoothers[i][0]}" for i in combo)
                    found.append((lbl, prod, valley(prod)))
                    print(f"  *** FOREST COUNTEREXAMPLE (smoothed): {lbl}", flush=True)
    print(f"  [nlc x paths] running total {tested}", flush=True)
    return found, tested


def main():
    if not validate_seeds():
        print("seed validation failed — aborting"); sys.exit(1)

    print("=== building non-log-concave tree library (families T, T*) ===", flush=True)
    lib = nlc_library(mmax=16, nmax=16)
    print(f"  {len(lib)} distinct non-log-concave tree polynomials "
          f"(orders {min(o for _,o,_ in lib)}..{max(o for _,o,_ in lib)})\n", flush=True)

    print("=== building path smoother pool (P_1..P_20) ===", flush=True)
    smoothers = path_polys(nmax=20)
    print(f"  {len(smoothers)} path polynomials\n", flush=True)

    print("=== FOREST-PRODUCT SEARCH (>=1 non-log-concave component) ===", flush=True)
    found, tested = product_search(lib, smoothers, max_powers=16, core_size=50)
    print(f"\n  tested {tested} forest products.")
    if found:
        print(f"  *** {len(found)} NON-UNIMODAL FORESTS FOUND — Erdős #993 DISPROVED ***")
        for lbl, prod, v in found[:10]:
            print(f"    {lbl}: valley {v}\n      {prod}")
    else:
        print("  no non-unimodal forest found in this surface (conjecture survives here).")
    return found


if __name__ == "__main__":
    main()
