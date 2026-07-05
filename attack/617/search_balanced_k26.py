#!/usr/bin/env python3
"""Direct SAT search for a counterexample to Erdos #617 at r=5: a 5-colouring
of E(K_26) such that every 6-set of vertices sees all 5 colours.

A model here would DISPROVE the conjecture (problem is marked falsifiable).
UNSAT is not expected to be reachable for a plain solver (huge symmetry), so
this script is only useful in the SAT direction.

Encoding: x[e][c] for each of the 325 edges and 5 colours; exactly-one colour
per edge; for every 6-set S and colour c: OR over the 15 edges of S of
x[e][c].  Mild symmetry breaking: the 5 edges at vertex 0 to 1..5 get colours
1..5; edge (1,2) restricted.

Usage: search_balanced_k26.py [n]   (default n=26; n=25 searches K_25)
"""
import itertools, sys, time
from pysat.solvers import Cadical195

n = int(sys.argv[1]) if len(sys.argv) > 1 else 26
V = list(range(n))
R = 5
EDGES = list(itertools.combinations(V, 2))
eidx = {e: i for i, e in enumerate(EDGES)}


def var(e, c):
    return eidx[e] * R + c + 1


s = Cadical195()
for e in EDGES:
    s.add_clause([var(e, c) for c in range(R)])
    for c1 in range(R):
        for c2 in range(c1 + 1, R):
            s.add_clause([-var(e, c1), -var(e, c2)])
ncl = 0
for S in itertools.combinations(V, 6):
    es = list(itertools.combinations(S, 2))
    for c in range(R):
        s.add_clause([var(e, c) for e in es])
        ncl += 1
# symmetry breaking: colours of the star at vertex 0 to 1..5 are 0..4
for i in range(1, 6):
    s.add_clause([var((0, i), i - 1)])
print(f"n={n}: {len(EDGES)*R} vars, ~{ncl} cover clauses; solving...",
      flush=True)
t0 = time.time()
res = s.solve()
print(f"result: {'SAT' if res else 'UNSAT'} in {time.time()-t0:.0f}s",
      flush=True)
if res:
    m = set(l for l in s.get_model() if l > 0)
    col = {e: c for e in EDGES for c in range(R) if var(e, c) in m}
    with open(f'artifacts/balanced_k{n}_witness.txt', 'w') as f:
        for e, c in sorted(col.items()):
            f.write(f"{e[0]} {e[1]} {c}\n")
    print(f"witness written to artifacts/balanced_k{n}_witness.txt")
