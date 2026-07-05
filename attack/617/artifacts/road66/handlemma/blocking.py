#!/usr/bin/env python3
"""Exact blocking numbers for transversal grids under per-vertex budgets.

CORE COMBINATORIAL OBJECT.  We have r "parts" (each an internally-empty
5-part of H, or a subset thereof).  Part i contributes a set U_i of size
n_i.  A "transversal" is a choice (w_1,...,w_r) in U_1 x ... x U_r.  A
"hole" is a missing cross H-edge between w in U_i and w' in U_j (i != j).
A transversal is BLOCKED if at least one of its C(r,2) cross-pairs is a
hole.  We must block EVERY transversal (else u,v + the transversal form a
K6, given u,v are joined to all of every U_i).

CONSTRAINT (Foothold 1 / matching): a vertex w in U_i may have at most
bud[i][j] holes into U_j.  For internally-empty parts the per-part cap is
1, and budgets only shrink under the subset restriction, so bud=1 is the
correct adversarial premise (the adversary gets the MOST blocking power
when caps are largest; using cap=1 when the true cap could be 0 only HELPS
the adversary, so a lower bound proved with cap=1 is valid).

We compute, by exact CP-SAT, the MINIMUM number of holes to block all
transversals.  This is BLOCK(n_1,...,n_r ; bud).  If BLOCK > available
budget for a config, that config is infeasible.

Functions:
  block(sizes, bud=None, get_witness=False) -> min holes (int) or (int, holes)
  block_pure(sizes) -> covering bound ignoring matching (calibration)
"""
import itertools
from ortools.sat.python import cp_model


def block(sizes, bud=None, time_limit=120, workers=8):
    """Minimum between-part holes to block all transversals of the grid
    prod U_i, where |U_i| = sizes[i], under per-vertex matching budgets.

    bud: optional r x r matrix; bud[i][j] = max holes a vertex of part i
         may have into part j.  Default: all 1 (internally-empty parts).
    Returns the exact minimum (int)."""
    r = len(sizes)
    if bud is None:
        bud = [[1] * r for _ in range(r)]
    pairs = list(itertools.combinations(range(r), 2))
    m = cp_model.CpModel()
    hole = {}
    for (i, j) in pairs:
        for a in range(sizes[i]):
            for b in range(sizes[j]):
                hole[(i, j, a, b)] = m.new_bool_var(f"h_{i}_{j}_{a}_{b}")
    # block every transversal
    for t in itertools.product(*[range(s) for s in sizes]):
        lits = [hole[(i, j, t[i], t[j])] for (i, j) in pairs]
        m.add_bool_or(lits)
    # matching/budget constraints
    for (i, j) in pairs:
        for a in range(sizes[i]):
            m.add(sum(hole[(i, j, a, b)] for b in range(sizes[j])) <= bud[i][j])
        for b in range(sizes[j]):
            m.add(sum(hole[(i, j, a, b)] for a in range(sizes[i])) <= bud[j][i])
    m.minimize(sum(hole.values()))
    s = cp_model.CpSolver()
    s.parameters.num_search_workers = workers
    s.parameters.max_time_in_seconds = time_limit
    st = s.solve(m)
    if st == cp_model.INFEASIBLE:
        return None  # UNBLOCKABLE under the budgets
    assert st in (cp_model.OPTIMAL, cp_model.FEASIBLE), s.status_name(st)
    return int(round(s.objective_value))


def block_pure(sizes):
    """Pure covering bound (no matching constraint): a hole between parts
    i,j kills prod_{k != i,j} n_k transversals; LP/ceil bound is
    total / max_kill.  Returns ceil(prod n / max over pairs of prod_{!=i,j})."""
    r = len(sizes)
    total = 1
    for s in sizes:
        total *= s
    best_kill = 0
    for (i, j) in itertools.combinations(range(r), 2):
        kill = 1
        for k in range(r):
            if k != i and k != j:
                kill *= sizes[k]
        best_kill = max(best_kill, kill)
    return -(-total // best_kill)  # ceil


if __name__ == "__main__":
    print("=== Calibration: 4-part grids, internally-empty (bud=1) ===")
    print("    (None = UNBLOCKABLE => K6 forced, infinite demand)")
    for sz in [(3, 3, 3, 3), (2, 2, 2, 2), (3, 3, 3, 2), (3, 3, 2, 2),
               (4, 3, 3, 3), (5, 5, 5, 5), (4, 4, 4, 4), (5, 4, 3, 3),
               (4, 4, 3, 3), (4, 3, 3, 2), (2, 2, 2, 1), (3, 3, 3, 1)]:
        b = block(list(sz))
        bp = block_pure(list(sz))
        bs = "UNBLOCKABLE" if b is None else f"{b:3d}"
        print(f"  {sz}: matching-block = {bs}   (pure cover = {bp})")
    print("=== 3-part grids (Lemma G regime) ===")
    for sz in [(3, 2, 2), (2, 2, 2), (3, 3, 2), (3, 3, 3), (5, 5, 5),
               (4, 3, 3), (5, 4, 4)]:
        b = block(list(sz))
        print(f"  {sz}: matching-block = {b}   (None==unblockable if huge)")
