#!/usr/bin/env python3
"""m* probe for Erdos #617 (r=5 case): minimise e(G) over graphs G on 26
vertices satisfying the two single-colour-class consequences of balancedness:

  (A) alpha(G) <= 5            (every 6-set of vertices spans >= 1 edge)
  (B) every 6-set spans <= 11 edges

Both are unconditional facts about every colour class of a balanced
5-colouring of K_26 (NOTES.md section 1).  Write m* for the minimum.

Why this single number is decisive for the whole campaign:

  * m* >= 66  =>  every colour class has >= 66 edges, so the five classes
    carry >= 330 > 325 = e(K_26) edges: NO balanced colouring exists and
    the r=5 case of #617 is PROVED, with no dependence on the imported
    pass-1..20 ladder.
  * m* <= 65  =>  single-colour-class constraints alone can never close
    r=5 (the counting route needs 66); multi-class interaction is then
    mandatory at whatever rung the ladder reaches m*.

CP-SAT minimise with the valid Turan cut e >= 55 and degree-sorted symmetry
breaking.  Every incumbent is dumped to artifacts/ as an edge list and must
be re-verified by the independent checker check_mstar_witness.py (no shared
code).  The internal lower bound reported by CP-SAT is informative but NOT
certificate-grade; a certified UNSAT pass (pysat + DRAT, as in
solve_hitset_pair.py) is the follow-up once the target threshold is known.

Usage: probe_mstar.py [time_limit_s] [workers] [target]
  With target: pure decision run "does a witness with e(G) <= target exist?"
  (the fork question is target = 65).  Without: minimise e(G).
"""
import itertools, sys, time
from ortools.sat.python import cp_model

N, TIME, WORKERS = 26, int(sys.argv[1]) if len(sys.argv) > 1 else 10800, \
    int(sys.argv[2]) if len(sys.argv) > 2 else 14
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else None
V = range(N)
EDGES = list(itertools.combinations(V, 2))
EIDX = {e: i for i, e in enumerate(EDGES)}

m = cp_model.CpModel()
x = [m.new_bool_var(f"e{u}_{v}") for u, v in EDGES]

t0 = time.time()
nsix = 0
for S in itertools.combinations(V, 6):
    lits = [x[EIDX[e]] for e in itertools.combinations(S, 2)]
    m.add_bool_or(lits)                      # (A) at least one edge
    m.add(sum(lits) <= 11)                   # (B) cap
    nsix += 1
total = sum(x)
m.add(total >= 55)                           # Turan: alpha<=5 => e >= 325-T(26,5)
deg = [sum(x[EIDX[tuple(sorted((u, v)))]] for v in V if v != u) for u in V]
for u in range(N - 1):                       # WLOG sorted degrees
    m.add(deg[u] >= deg[u + 1])
if TARGET is not None:
    m.add(total <= TARGET)
else:
    m.minimize(total)
print(f"model built: {nsix} six-sets, {len(EDGES)} edge vars, "
      f"mode={'decision<=%d' % TARGET if TARGET is not None else 'minimise'}, "
      f"{time.time()-t0:.1f}s", flush=True)


class Incumbent(cp_model.CpSolverSolutionCallback):
    def __init__(self):
        super().__init__()
        self.best = None

    def on_solution_callback(self):
        es = [EDGES[i] for i in range(len(EDGES)) if self.value(x[i])]
        k = len(es)
        if self.best is not None and k >= self.best:
            return
        self.best = k
        path = f"artifacts/mstar_witness_E{k}.txt"
        with open(path, "w") as f:
            for u, v in es:
                f.write(f"{u} {v}\n")
        bound = "" if TARGET is not None else f"  bound={self.best_objective_bound:.0f}"
        print(f"[{self.wall_time:8.1f}s] incumbent e={k}{bound}  -> {path}", flush=True)


solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = TIME
solver.parameters.num_search_workers = WORKERS
solver.parameters.log_search_progress = False
cb = Incumbent()
status = solver.solve(m, cb)
name = solver.status_name(status)
print(f"status={name}  best_incumbent={cb.best}  wall={solver.wall_time:.0f}s", flush=True)
if TARGET is not None:
    print("VERDICT:",
          f"m* <= {cb.best} — single-class route CANNOT reach 66" if cb.best else
          f"m* > {TARGET} — single-class counting PROVES #617 r=5 (certify next!)"
          if name == "INFEASIBLE" else "UNDECIDED within budget", flush=True)
else:
    print("VERDICT: m* =", cb.best if name == "OPTIMAL" else
          f"in [{solver.best_objective_bound:.0f}, {cb.best}]" if cb.best else
          f">= {solver.best_objective_bound:.0f} (no incumbent)", flush=True)
