#!/usr/bin/env python3
"""
Erdős #993 — Unimodality of independence polynomials of trees/forests
(Alavi–Erdős–Malde–Schwenk 1987). FROZEN VERIFIER + self-tests.

A graph G's independence polynomial is I(G;x) = sum_k i_k x^k where i_k = number
of independent sets of size k (i_0 = 1). The conjecture: for every forest (in
particular every tree), the coefficient sequence (i_k) is UNIMODAL. A single
forest whose (i_k) has a strict interior valley DISPROVES it — a real solve.

This module is the shared, exact, deterministic kernel for the search:
  - indpoly_tree(adj, root): exact big-int independence polynomial of a tree via
    the standard in/out tree DP. O(n^2) integer ops, no floating point.
  - indpoly_forest(components): product (convolution) of component polynomials.
  - is_unimodal(coeffs): True iff the sequence is unimodal (ascend then descend,
    plateaus allowed).
  - valley(coeffs): the witnessing (j,k,l) strict valley or None.

SELF-TESTS (run as main): the tree DP is cross-checked against a brute-force
independent-set enumerator on every small graph, and the unimodality scanner is
checked against its definition. Corrupt-the-witness style: we also confirm a
hand-built non-unimodal sequence is flagged.
"""
import sys
from itertools import combinations
import networkx as nx


# ---------- exact polynomial arithmetic (coefficient lists, big-int) ----------
def pmul(a, b):
    """Multiply two polynomials given as coefficient lists (index = degree)."""
    res = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai:
            for j, bj in enumerate(b):
                res[i + j] += ai * bj
    return res


# ---------- exact independence polynomial of a TREE via in/out DP ----------
def indpoly_tree(adj, root=0):
    """
    adj: dict v -> iterable of neighbors (an undirected tree).
    Returns coefficient list of I(T;x). Iterative post-order to avoid recursion
    limits on large trees.
    For each subtree at v we track:
      A[v] = ind. poly of subtree with v EXCLUDED
      B[v] = ind. poly of subtree with v INCLUDED
    Leaf: A=[1], B=[0,1].
    Internal: A[v] = prod_c (A[c]+B[c]); B[v] = x * prod_c A[c].
    I(T) = A[root] + B[root].
    """
    parent = {root: None}
    order = [root]
    stack = [root]
    while stack:
        u = stack.pop()
        for w in adj[u]:
            if w not in parent:
                parent[w] = u
                order.append(w)
                stack.append(w)
    A = {}
    B = {}
    for v in reversed(order):  # children processed before parents
        children = [w for w in adj[v] if w != parent[v]]
        if not children:
            A[v] = [1]
            B[v] = [0, 1]
        else:
            pa = [1]          # prod (A[c]+B[c])
            pb = [1]          # prod A[c]
            for c in children:
                ic = [x + y for x, y in zip_pad(A[c], B[c])]
                pa = pmul(pa, ic)
                pb = pmul(pb, A[c])
            A[v] = pa
            B[v] = [0] + pb   # multiply by x
    return [x + y for x, y in zip_pad(A[root], B[root])]


def zip_pad(a, b):
    n = max(len(a), len(b))
    return [(a[i] if i < len(a) else 0, b[i] if i < len(b) else 0) for i in range(n)]


def indpoly_forest(comp_polys):
    """Product of component independence polynomials = forest ind. poly."""
    res = [1]
    for p in comp_polys:
        res = pmul(res, p)
    return res


# ---------- unimodality ----------
def is_unimodal(c):
    """Unimodal iff sequence ascends (non-strict) then descends (non-strict)."""
    n = len(c)
    i = 0
    while i + 1 < n and c[i] <= c[i + 1]:
        i += 1
    while i + 1 < n and c[i] >= c[i + 1]:
        i += 1
    return i == n - 1


def valley(c):
    """Return a witnessing strict interior valley (j,k,l) with c[j]>c[k]<c[l], or None."""
    n = len(c)
    for k in range(1, n - 1):
        # nearest higher value to the left and to the right
        jL = next((j for j in range(k - 1, -1, -1) if c[j] > c[k]), None)
        jR = next((l for l in range(k + 1, n) if c[l] > c[k]), None)
        if jL is not None and jR is not None:
            return (jL, k, jR)
    return None


def is_logconcave(c):
    """c_k^2 >= c_{k-1} c_{k+1} for all interior k (no internal zeros assumed)."""
    return all(c[k] * c[k] >= c[k - 1] * c[k + 1] for k in range(1, len(c) - 1))


# ---------- brute-force ground truth (for self-test only) ----------
def indpoly_bruteforce(G):
    """Count independent sets of each size by direct enumeration. Small graphs only."""
    nodes = list(G.nodes())
    adj = {v: set(G.neighbors(v)) for v in nodes}
    counts = {}
    # iterative subset DP would be cleaner; for tiny n just enumerate by size
    n = len(nodes)
    counts[0] = 1
    for k in range(1, n + 1):
        c = 0
        for S in combinations(nodes, k):
            ok = True
            Sset = set(S)
            for v in S:
                if adj[v] & Sset:
                    ok = False
                    break
            if ok:
                c += 1
        if c == 0:
            break
        counts[k] = c
    deg = max(counts)
    return [counts.get(k, 0) for k in range(deg + 1)]


def tree_adj(G):
    return {v: list(G.neighbors(v)) for v in G.nodes()}


def _selftest():
    print("=== #993 kernel self-tests ===")
    # 1. tree DP vs brute force on every tree up to n=11
    bad = 0
    total = 0
    for n in range(1, 12):
        for T in nx.nonisomorphic_trees(n):
            total += 1
            got = indpoly_tree(tree_adj(T), root=next(iter(T.nodes())))
            exp = indpoly_bruteforce(T)
            # strip trailing zeros
            while len(got) > 1 and got[-1] == 0:
                got.pop()
            if got != exp:
                bad += 1
                if bad <= 3:
                    print(f"  MISMATCH n={n}: got {got} exp {exp}")
    print(f"tree DP vs brute force: {total-bad}/{total} trees match  ->  {'PASS' if bad==0 else 'FAIL'}")

    # 2. forest product vs brute force on a few disjoint unions
    bad2 = 0
    tcase = 0
    trees5 = list(nx.nonisomorphic_trees(5))
    trees4 = list(nx.nonisomorphic_trees(4))
    for t1 in trees5:
        for t2 in trees4:
            tcase += 1
            F = nx.disjoint_union(t1, t2)
            p1 = indpoly_tree(tree_adj(t1), root=next(iter(t1.nodes())))
            p2 = indpoly_tree(tree_adj(t2), root=next(iter(t2.nodes())))
            got = indpoly_forest([p1, p2])
            exp = indpoly_bruteforce(F)
            while len(got) > 1 and got[-1] == 0:
                got.pop()
            if got != exp:
                bad2 += 1
    print(f"forest product vs brute force: {tcase-bad2}/{tcase} match  ->  {'PASS' if bad2==0 else 'FAIL'}")

    # 3. unimodality scanner sanity
    checks = [
        ([1, 3, 5, 4, 2], True, None),
        ([1, 2, 3, 3, 1], True, None),
        ([1, 5, 2, 5, 1], False, True),   # strict valley at index 2
        ([1, 4, 4, 4, 1], True, None),
        ([1, 2, 1, 2, 1], False, True),
    ]
    ok3 = True
    for seq, uni, hasvalley in checks:
        if is_unimodal(seq) != uni:
            ok3 = False
            print(f"  unimodal MISMATCH {seq}: got {is_unimodal(seq)} exp {uni}")
        v = valley(seq)
        if (v is not None) != bool(hasvalley):
            ok3 = False
            print(f"  valley MISMATCH {seq}: got {v}")
    print(f"unimodality scanner: {'PASS' if ok3 else 'FAIL'}")

    # 4. known fact: the path P_n and star are unimodal (spot check), and a known
    #    non-log-concave-but-unimodal example exists. Confirm logconcave!=unimodal logic.
    star = nx.star_graph(10)  # K_{1,10}
    ps = indpoly_tree(tree_adj(star), root=0)
    print(f"star K(1,10) I(x) = {ps}  unimodal={is_unimodal(ps)} logconcave={is_logconcave(ps)}")

    allpass = (bad == 0 and bad2 == 0 and ok3)
    print(f"\n=== {'ALL SELF-TESTS PASS' if allpass else 'SELF-TESTS FAILED'} ===")
    return allpass


if __name__ == "__main__":
    ok = _selftest()
    sys.exit(0 if ok else 1)
