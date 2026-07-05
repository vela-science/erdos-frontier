#!/usr/bin/env python3
"""Second-engine pure-spec cross-check of search_z13_invariant.py.

Independent encoding choices on purpose: CaDiCaL (not CP-SAT), ALL C(26,6)
six-sets constrained explicitly (no rotation-class dedup), no colour
symmetry breaking, no exactly-5-classes cut — just the raw spec:

  * each of the 25 Z_13 edge orbits gets exactly one of 5 colours;
  * every 6-set of vertices sees every colour on its 15 edges.

UNSAT here independently confirms: no Z_13-invariant balanced 5-colouring.

Usage: crosscheck_z13_pysat.py
"""
import itertools, time
from pysat.solvers import Cadical195


def orbit(u, v):
    i, s = u % 13, u // 13
    j, t = v % 13, v // 13
    if s == t:
        d = (j - i) % 13
        d = min(d, 13 - d)
        return s * 6 + d - 1
    return 12 + ((j - i) % 13)


def var(o, c):
    return o * 5 + c + 1


s = Cadical195()
for o in range(25):
    s.add_clause([var(o, c) for c in range(5)])
    for c1 in range(5):
        for c2 in range(c1 + 1, 5):
            s.add_clause([-var(o, c1), -var(o, c2)])

t0, ncl = time.time(), 0
for S in itertools.combinations(range(26), 6):
    obs = set(orbit(*e) for e in itertools.combinations(S, 2))
    for c in range(5):
        s.add_clause([var(o, c) for o in obs])
        ncl += 1
print(f"{ncl} coverage clauses built in {time.time()-t0:.1f}s; solving...")
res = s.solve()
print("SAT" if res else
      "UNSAT: confirmed — no Z_13-invariant balanced 5-colouring of K_26")
