"""Generalized grid, factored enumeration.

Parts/budgets (variant-ii triple, A = subset of the part with an internal
edge, i.e. absorption INTO A's part is 2):
  a in A: <=1 hole into B, <=1 into C
  b in B: <=2 into A,      <=1 into C
  c in C: <=2 into A,      <=1 into B
Question: for which sizes can ALL transversal triangles be blocked, and at
what minimum hole count?
Also re-run the symmetric all-1 matrix as a regression.
"""
from itertools import product

def enum_bipartite(P, Q, dP, dQ):
    """all hole-sets between P,Q with deg_P <= dP, deg_Q <= dQ"""
    sets = []
    # each p picks a subset of Q of size <= dP; then filter q-degrees
    choices = []
    from itertools import combinations
    subs = [frozenset(c) for r in range(dP + 1) for c in combinations(Q, r)]
    for pick in product(subs, repeat=len(P)):
        cnt = {}
        ok = True
        for i, s in enumerate(pick):
            for q in s:
                cnt[q] = cnt.get(q, 0) + 1
                if cnt[q] > dQ:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            sets.append(frozenset((P[i], q) for i, s in enumerate(pick) for q in s))
    return sets

def min_block(nA, nB, nC, dAB, dBA, dAC, dCA, dBC, dCB):
    A = [("A", i) for i in range(nA)]
    B = [("B", i) for i in range(nB)]
    C = [("C", i) for i in range(nC)]
    AB = enum_bipartite(A, B, dAB, dBA)
    AC = enum_bipartite(A, C, dAC, dCA)
    BC = enum_bipartite(B, C, dBC, dCB)
    tris = [(a, b, c) for a, b, c in product(A, B, C)]
    best = None
    for hab in AB:
        for hac in AC:
            for hbc in BC:
                n = len(hab) + len(hac) + len(hbc)
                if best is not None and n >= best:
                    continue
                if all((a, b) in hab or (a, c) in hac or (b, c) in hbc
                       for a, b, c in tris):
                    best = n
    return best

print("regression, all budgets 1:")
for s in [(2,2,2),(3,2,2)]:
    print("  ", s, "->", min_block(*s, 1,1,1,1,1,1), flush=True)

print("variant-ii matrix (absorption into A's part = 2):")
for s in [(2,2,2),(3,2,2),(2,3,2),(2,2,3),(4,2,2),(3,3,2),(3,2,3),(2,3,3),(3,3,3),(5,2,2),(4,3,3),(4,3,2),(4,2,3)]:
    print("  ", s, "->", min_block(*s, 1,2,1,2,1,1), flush=True)
