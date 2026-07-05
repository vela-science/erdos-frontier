#!/usr/bin/env python3
"""Z_13-invariant counterexample search for Erdos #617 (r=5).

Vertex set: Z_13 x {0,1} (vertex id = i + 13s).  We search 5-colourings of
E(K_26) invariant under the simultaneous rotation (i,s) -> (i+1, s).  Edge
orbits (all of size 13):

  W(s,d)  within-copy edges, copy s, circular difference d in 1..6   (12 orbits)
  X(d)    cross edges {(i,0),(i+d,1)}, shift d in 0..12              (13 orbits)

25 orbits x 13 = 325 = e(K_26).  A Z_13-invariant colouring is an assignment
of the 25 orbits to 5 colours; balanced means every 6-set sees all 5 colours,
and by invariance it suffices to constrain one representative per rotation
class of 6-sets.

Why this family is the live one: Z_26-circulants and F_25-translation
colourings are dead by unconditional arithmetic (orbit sizes vs the Turan
bound e_c >= 55 — see NOTES), while here 25 classes of 13 split as 5 colours
x 5 classes x 13 edges = 65 edges per colour exactly: the all-classes-65
extremal point.  The constraint sum_o [colour(o)=c] = 5 is therefore a VALID
cut, not an assumption.  An order-13 element of PSL_2(25) acts on the 26
points of P^1(F_25) with two 13-orbits and no fixed points, so this search
also covers the projective-line torus candidates.

SAT => witness dumped and re-verified by check_balanced.py (independent);
UNSAT => no Z_13-invariant (hence no D_13-, Z_26-refined) balanced colouring.

Usage: search_z13_invariant.py
"""
import itertools, sys
from ortools.sat.python import cp_model

NORB = 25


def orbit(u, v):
    i, s = u % 13, u // 13
    j, t = v % 13, v // 13
    if s == t:
        d = (j - i) % 13
        d = min(d, 13 - d)
        return s * 6 + d - 1
    return 12 + ((j - i) % 13)        # u<v forces s=0,t=1


def rot(S, r):
    return tuple(sorted((v % 13 + r) % 13 + 13 * (v // 13) for v in S))


# one representative per rotation class of 6-sets
reps, seen = [], set()
min_orbits = 99
for S in itertools.combinations(range(26), 6):
    key = min(rot(S, r) for r in range(13))
    if key in seen:
        continue
    seen.add(key)
    obs = frozenset(orbit(*e) for e in itertools.combinations(S, 2))
    reps.append(obs)
    min_orbits = min(min_orbits, len(obs))
print(f"{len(seen)} rotation classes of 6-sets; min distinct orbits in a 6-set: {min_orbits}")

m = cp_model.CpModel()
b = [[m.new_bool_var(f"b{o}_{c}") for c in range(5)] for o in range(NORB)]
for o in range(NORB):
    m.add_exactly_one(b[o])
for c in range(5):
    m.add(sum(b[o][c] for o in range(NORB)) == 5)      # valid cut (see docstring)
for obs in reps:
    for c in range(5):
        m.add_bool_or([b[o][c] for o in obs])
# colour-symmetry: value precedence (colour c appears only after c-1 has)
m.add(b[0][0] == 1)
for o in range(1, NORB):
    for c in range(1, 5):
        m.add_bool_or([b[op][c - 1] for op in range(o)] + [b[o][c].Not()])

solver = cp_model.CpSolver()
solver.parameters.num_search_workers = 2
solver.parameters.max_time_in_seconds = 600
status = solver.solve(m)
name = solver.status_name(status)
print("status:", name)
if name == "OPTIMAL" or name == "FEASIBLE":
    col = {o: next(c for c in range(5) if solver.value(b[o][c])) for o in range(NORB)}
    print("orbit colours:", [col[o] for o in range(NORB)])
    with open("artifacts/z13_witness.txt", "w") as f:
        for u, v in itertools.combinations(range(26), 2):
            f.write(f"{u} {v} {col[orbit(u, v)]}\n")
    print("witness -> artifacts/z13_witness.txt ; verify with check_balanced.py")
    sys.exit(2)
print("UNSAT: no Z_13-invariant balanced 5-colouring of K_26 exists")
