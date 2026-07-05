"""Brute-force check of the Grid Lemma.

Claim: Let A,B,C be sets in three distinct internally-empty 5-parts,
|A|=3, |B|=|C|=2.  Suppose every vertex has at most 1 hole into each of
the other two parts (the empty-part budget, restricted to these sets --
NOTE: budgets cap holes into the WHOLE part, so a fortiori into the
subset; using the subset-restricted cap <=1 is the weaker premise, so a
brute-force over subset-restricted patterns is the right adversarial
test: if no subset-restricted pattern blocks everything, no real one
does).
Then some transversal triangle (a,b,c) in A x B x C has all three pairs
present (i.e. it is IMPOSSIBLE to block all 12 triangles).

Also: for |A|=|B|=|C|=2 blocking IS possible, with minimum exactly 6
holes (the double-triangle pattern).
"""
from itertools import combinations, product

def check(nA, nB, nC):
    A = [("a", i) for i in range(nA)]
    B = [("b", i) for i in range(nB)]
    C = [("c", i) for i in range(nC)]
    pairs = [(x, y) for x, y in product(A, B)] + \
            [(x, y) for x, y in product(A, C)] + \
            [(x, y) for x, y in product(B, C)]
    n = len(pairs)
    best = None
    # enumerate all hole subsets
    for mask in range(1 << n):
        holes = {pairs[i] for i in range(n) if mask >> i & 1}
        # budget: each vertex <=1 hole into each other part
        def holes_from(v, part):
            return sum(1 for (x, y) in holes if (x == v and y[0] == part) or (y == v and x[0] == part))
        ok = True
        for v in A:
            if holes_from(v, "b") > 1 or holes_from(v, "c") > 1: ok = False; break
        if ok:
            for v in B:
                if holes_from(v, "a") > 1 or holes_from(v, "c") > 1: ok = False; break
        if ok:
            for v in C:
                if holes_from(v, "a") > 1 or holes_from(v, "b") > 1: ok = False; break
        if not ok:
            continue
        # does it block every transversal triangle?
        blocked_all = True
        for a, b, c in product(A, B, C):
            if (a, b) not in holes and (a, c) not in holes and (b, c) not in holes:
                blocked_all = False
                break
        if blocked_all:
            if best is None or len(holes) < best[0]:
                best = (len(holes), sorted(holes))
    return best

r322 = check(3, 2, 2)
print("(3,2,2) blockable under budgets:", r322)  # expect None
r222 = check(2, 2, 2)
print("(2,2,2) minimum blocking:", r222[0] if r222 else None, r222[1] if r222 else "")
assert r322 is None, "GRID LEMMA FALSIFIED for (3,2,2)!"
assert r222 is not None and r222[0] == 6
print("Grid lemma verified: (3,2,2) unblockable; (2,2,2) needs exactly 6.")
