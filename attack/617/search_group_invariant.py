#!/usr/bin/env python3
"""Cyclic-group-invariant counterexample search for Erdos #617 (r=5).

Searches 5-colourings of E(K_26) invariant under a given permutation g of
the 26 vertices (i.e. under the cyclic group <g>): edge orbits under <g>
are the colouring variables; balanced means every 6-set sees all 5 colours,
and one representative per <g>-class of 6-sets suffices.

Generator shapes are 'zP-B': B disjoint P-cycles on the first P*B vertices,
the remaining 26-P*B vertices fixed.  Aliases for the PSL_2(25) element
shapes on P^1(F_25): z5 = z5-5 (unipotent), z3 = z3-8 (split torus),
z2 = z2-12 (involution); z13-2 is covered by search_z13_invariant.py.
Sweeping every feasible (P,B) yields: no balanced colouring of K_26 admits
ANY vertex-automorphism of one of the swept prime-order shapes — every
nontrivial automorphism group contains an element of prime order, so this
is a structured-counterexample exclusion theorem, shape by shape.

SAT => witness dumped to artifacts/ and re-verified by check_balanced.py
(independent checker); UNSAT => no balanced colouring invariant under <g>.

Usage: search_group_invariant.py {zP-B|z5|z3|z2} [time_limit_s]
"""
import itertools, sys
from ortools.sat.python import cp_model

name = sys.argv[1]
tlim = int(sys.argv[2]) if len(sys.argv) > 2 else 1800

ALIAS = {"z5": "z5-5", "z3": "z3-8", "z2": "z2-12"}
shape = ALIAS.get(name, name)
try:
    p, nb = (int(x) for x in shape[1:].split("-"))
    assert p >= 2 and nb >= 1 and p * nb <= 26
except Exception:
    sys.exit("unknown shape " + name + " (want zP-B with P*B <= 26)")
g = {v: v for v in range(26)}
for a in range(nb):
    for b in range(p):
        g[p * a + b] = p * a + (b + 1) % p

order = 1
h = dict(g)
while any(h[v] != v for v in range(26)):
    h = {v: g[h[v]] for v in range(26)}
    order += 1

# edge orbits under <g>
eorb, orbs = {}, []
for e in itertools.combinations(range(26), 2):
    if e in eorb:
        continue
    o, cur = len(orbs), e
    members = []
    while cur not in eorb:
        eorb[cur] = o
        members.append(cur)
        cur = tuple(sorted((g[cur[0]], g[cur[1]])))
    orbs.append(members)
print(f"{shape}: <g> order {order}, {len(orbs)} edge orbits "
      f"(sizes {sorted(set(len(m) for m in orbs))})")

# representatives of 6-set classes under <g>
reps, seen = [], set()
for S in itertools.combinations(range(26), 6):
    imgs, cur = [], tuple(S)
    for _ in range(order):
        cur = tuple(sorted(g[v] for v in cur))
        imgs.append(cur)
    key = min(imgs)
    if key in seen:
        continue
    seen.add(key)
    reps.append(frozenset(eorb[e] for e in itertools.combinations(S, 2)))
print(f"{len(reps)} six-set classes; min distinct orbits in a class: "
      f"{min(len(r) for r in reps)}")

m = cp_model.CpModel()
b = [[m.new_bool_var(f"b{o}_{c}") for c in range(5)] for o in range(len(orbs))]
for o in range(len(orbs)):
    m.add_exactly_one(b[o])
for obs in reps:
    for c in range(5):
        m.add_bool_or([b[o][c] for o in obs])
m.add(b[0][0] == 1)                       # colour value-precedence breaking
for o in range(1, len(orbs)):
    for c in range(1, 5):
        m.add_bool_or([b[op][c - 1] for op in range(o)] + [b[o][c].Not()])

solver = cp_model.CpSolver()
solver.parameters.num_search_workers = 4
solver.parameters.max_time_in_seconds = tlim
status = solver.solve(m)
sname = solver.status_name(status)
print("status:", sname)
if sname in ("OPTIMAL", "FEASIBLE"):
    col = {o: next(c for c in range(5) if solver.value(b[o][c]))
           for o in range(len(orbs))}
    path = f"artifacts/{shape}_witness.txt"
    with open(path, "w") as f:
        for u, v in itertools.combinations(range(26), 2):
            f.write(f"{u} {v} {col[eorb[(u, v)]]}\n")
    print(f"witness -> {path} ; verify with check_balanced.py")
    sys.exit(2)
elif sname == "INFEASIBLE":
    print(f"UNSAT: no {name}-invariant balanced 5-colouring of K_26 exists")
else:
    print("UNDECIDED within time limit")
