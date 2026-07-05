#!/usr/bin/env python3
"""
Erdős #993 — frozen, fast, deterministic verifier for the banked result.
Asserts the headline facts of the broadened search WITHOUT re-running the full
112,916-tree scan (that lives in search_993_v2.py). Checks:

  1. Kernel correctness: tree-DP independence polynomial == brute force on all
     trees up to order 9 (fast subset of the full 436-tree self-test).
  2. Literature reproduction: the two order-26 trees T_3,4,4 and T*_3,3,4 are
     non-log-concave AND unimodal (Kadrawi–Levit–Yosef–Mizrachi 2023).
  3. Forest surface (bounded resweep): a deterministic family of products /
     powers / smoothings of the order-26 non-log-concave seeds is unimodal —
     i.e. no counterexample on the sampled forest surface.
  4. Self-test of the unimodality scanner against a hand-built valley.

Exit 0 iff all hold. Registered in scripts/reproduce.py.
"""
import sys
from itertools import combinations_with_replacement as cwr
import networkx as nx
from verify_993_kernel import (
    indpoly_tree, indpoly_forest, is_unimodal, is_logconcave, valley,
    indpoly_bruteforce, tree_adj,
)
from search_993 import build_T, path_polys


def check_kernel():
    bad = 0
    for n in range(1, 10):
        for T in nx.nonisomorphic_trees(n):
            got = indpoly_tree(tree_adj(T), root=next(iter(T.nodes())))
            exp = indpoly_bruteforce(T)
            while len(got) > 1 and got[-1] == 0:
                got.pop()
            bad += (got != exp)
    return bad == 0


def check_seeds():
    a1, o1 = build_T(4, 4, star=False)   # T_3,4,4
    p1 = indpoly_tree(a1, root=0)
    a2, o2 = build_T(3, 4, star=True)    # T*_3,3,4
    p2 = indpoly_tree(a2, root=0)
    ok = (o1 == 26 and not is_logconcave(p1) and is_unimodal(p1)
          and o2 == 26 and not is_logconcave(p2) and is_unimodal(p2))
    return ok, (o1, p1, o2, p2)


def check_forest_surface(p1, p2):
    """Bounded deterministic resweep over the two order-26 seeds."""
    seeds = [p1, p2]
    paths = path_polys(nmax=12)
    nonuni = []
    # products of 2..4 seed copies
    for k in range(2, 5):
        for combo in cwr(range(len(seeds)), k):
            prod = indpoly_forest([seeds[i] for i in combo])
            if not is_unimodal(prod):
                nonuni.append(("prod", combo))
    # powers to 12
    for s in seeds:
        acc = s
        for _ in range(2, 13):
            acc = indpoly_forest([acc, s])
            if not is_unimodal(acc):
                nonuni.append(("pow", None))
    # seed x 1..2 paths
    for s in seeds:
        for k in range(1, 3):
            for combo in cwr(range(len(paths)), k):
                prod = indpoly_forest([s] + [paths[i][1] for i in combo])
                if not is_unimodal(prod):
                    nonuni.append(("smooth", combo))
    return len(nonuni) == 0


def check_scanner():
    return (not is_unimodal([1, 5, 2, 5, 1])) and valley([1, 5, 2, 5, 1]) is not None \
        and is_unimodal([1, 3, 5, 4, 2])


def main():
    r1 = check_kernel()
    print(f"[1] kernel vs brute force (trees n<=9): {'PASS' if r1 else 'FAIL'}")
    r2, (o1, p1, o2, p2) = check_seeds()
    print(f"[2] order-26 seeds T_3,4,4 & T*_3,3,4 non-log-concave + unimodal: {'PASS' if r2 else 'FAIL'}")
    r3 = check_forest_surface(p1, p2)
    print(f"[3] forest surface (products/powers/smoothings of seeds) all unimodal: {'PASS' if r3 else 'FAIL'}")
    r4 = check_scanner()
    print(f"[4] unimodality scanner self-test: {'PASS' if r4 else 'FAIL'}")
    ok = r1 and r2 and r3 and r4
    print(f"\n#993 result verifier: {'ALL PASS' if ok else 'FAILED'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
