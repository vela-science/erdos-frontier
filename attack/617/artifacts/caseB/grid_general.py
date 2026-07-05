"""Generalized grid: parts X (=A's part), Y, Z with per-direction budgets.
budget[(P,Q)] = max holes a vertex of part P may have into part Q
(restricted to the chosen subsets; full-part budgets only strengthen this).
Question: can all transversal triangles of A x B x C be blocked?
Report blockable sizes and min holes for the relevant budget matrices.
"""
from itertools import product

def blockable(nA, nB, nC, bud):
    A = [("A", i) for i in range(nA)]
    B = [("B", i) for i in range(nB)]
    C = [("C", i) for i in range(nC)]
    pairs = [(x, y) for x, y in product(A, B)] + \
            [(x, y) for x, y in product(A, C)] + \
            [(x, y) for x, y in product(B, C)]
    n = len(pairs)
    best = None
    for mask in range(1 << n):
        holes = [pairs[i] for i in range(n) if mask >> i & 1]
        cnt = {}
        ok = True
        for (x, y) in holes:
            cnt[(x, y[0])] = cnt.get((x, y[0]), 0) + 1
            cnt[(y, x[0])] = cnt.get((y, x[0]), 0) + 1
        for (v, tgt), c in cnt.items():
            if c > bud[(v[0], tgt)]:
                ok = False
                break
        if not ok:
            continue
        hs = set(holes)
        if all((a, b) in hs or (a, c) in hs or (b, c) in hs
               for a, b, c in product(A, B, C)):
            if best is None or len(holes) < best:
                best = len(holes)
    return best

# Case B (q=5) budget matrix: all 1 (parts P2,P3,P4 pairwise empty)
bud1 = {(p, q): 1 for p in "ABC" for q in "ABC" if p != q}
print("q=5 symmetric budgets (all 1):")
for sizes in [(2,2,2),(3,2,2),(2,3,2),(2,2,3)]:
    print("  sizes", sizes, "-> min holes to block:", blockable(*sizes, bud1))

# q=6 variant ii triple (P2 has an edge): A in P2 (budget INTO P2 = 2
# for B,C vertices; P2 vertices have budget 1 into P3,P4):
bud2 = dict(bud1)
bud2[("B", "A")] = 2   # P3 -> P2
bud2[("C", "A")] = 2   # P4 -> P2
print("q=6 variant ii budgets (into A's part = 2):")
for sizes in [(2,2,2),(3,2,2),(2,3,2),(2,2,3),(4,2,2),(3,3,2),(3,2,3),(2,3,3),(5,2,2),(4,3,2)]:
    print("  sizes", sizes, "-> min holes to block:", blockable(*sizes, bud2))

# q=6 variant i: pivot may sit in P1 (budget 3) but triple is still
# P2,P3,P4 all-1 -> same as bud1.  Also check pivot-z grids vs P0:
# triple with one part being P0-subset: A in P0 (budget 1 outward),
# but B,C vertices have budget into P0 up to 6-Delta >= 2:
bud3 = dict(bud1)
bud3[("B", "A")] = 2
bud3[("C", "A")] = 2
# same as bud2 by symmetry of roles
print("(P0-as-A with absorption 2 is the same matrix as variant ii)")
