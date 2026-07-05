#!/usr/bin/env python3
"""CP-SAT (OR-Tools) attack on the same hitset-pair spec as
solve_hitset_pair.py — an independent second solver for cross-verification.

Differences from the CNF version: cardinalities are native linear
constraints; the FULL spec is encoded eagerly here, including all 27132
six-set bounds (cheap as linear constraints) — only non-4-partiteness is
CEGAR (it quantifies over partitions).  Verdicts:
  INFEASIBLE -> no B exists for the case;
  FEASIBLE   -> witness re-verified by check_witness.py.

Usage: solve_hitset_pair_cpsat.py <case> [workers]
"""
import itertools, json, sys, time
from ortools.sat.python import cp_model

N = 19
VS = list(range(N))
PAIRS = list(itertools.combinations(VS, 2))


def pairs_in(S):
    return itertools.combinations(sorted(S), 2)


def build(case_name, P, Q, hit3, ePmax, eQmax):
    m = cp_model.CpModel()
    x = {}
    for (i, j) in PAIRS:
        x[(i, j)] = m.NewBoolVar(f'e{i}_{j}')
    ev = lambda a, b: x[(min(a, b), max(a, b))]
    # L1
    m.Add(sum(x.values()) == 40)
    # L2
    for v in VS:
        m.Add(sum(ev(v, u) for u in VS if u != v) <= 6)
    # L3 alpha<=4
    for S in itertools.combinations(VS, 5):
        m.AddBoolOr([ev(a, b) for (a, b) in pairs_in(S)])
    # L4 all six-sets <= 11 edges
    for S in itertools.combinations(VS, 6):
        m.Add(sum(ev(a, b) for (a, b) in pairs_in(S)) <= 11)
    # hitting conditions
    for S in itertools.combinations([v for v in VS if v not in P], 4):
        m.AddBoolOr([ev(a, b) for (a, b) in pairs_in(S)])
    for S in itertools.combinations([v for v in VS if v not in Q], 4):
        m.AddBoolOr([ev(a, b) for (a, b) in pairs_in(S)])
    if hit3:
        R = [v for v in VS if v not in P and v not in Q]
        for S in itertools.combinations(R, 3):
            m.AddBoolOr([ev(a, b) for (a, b) in pairs_in(S)])
    if ePmax is not None:
        m.Add(sum(ev(a, b) for (a, b) in pairs_in(P)) <= ePmax)
    if eQmax is not None:
        m.Add(sum(ev(a, b) for (a, b) in pairs_in(Q)) <= eQmax)
    # L5 saturation of ~B, eager.  Sound T-range restriction: any valid T
    # makes T u {u} and T u {v} independent 4-sets, which P and Q must hit;
    # hence T meets P unless u,v both lie in P, likewise for Q.
    sP, sQ = set(P), set(Q)
    for (u, v) in PAIRS:
        others = [w for w in VS if w != u and w != v]
        needP = not (u in sP and v in sP)
        needQ = not (u in sQ and v in sQ)
        ts = []
        for T in itertools.combinations(others, 3):
            tset = set(T)
            if (needP and not tset & sP) or (needQ and not tset & sQ):
                continue
            t = m.NewBoolVar(f's{u}_{v}_{T[0]}_{T[1]}_{T[2]}')
            ts.append(t)
            lits = [ev(a, b).Not() for (a, b) in pairs_in(T)]
            lits += [ev(u, w).Not() for w in T]
            lits += [ev(v, w).Not() for w in T]
            m.AddBoolAnd(lits).OnlyEnforceIf(t)
        m.AddBoolOr([ev(u, v).Not()] + ts)
    # structural cuts implied by the spec (case1_structure.md /
    # case2_structure.md): Turan-stability lower bounds
    notP = [v for v in VS if v not in P]
    notQ = [v for v in VS if v not in Q]
    if hit3:  # Case I
        m.Add(sum(ev(a, b) for (a, b) in pairs_in(notP)) >= 31)  # Lemma 1
        m.Add(sum(ev(a, b) for (a, b) in pairs_in(notQ)) >= 27)  # Lemma 2
        R = [v for v in VS if v not in P and v not in Q]
        m.Add(sum(ev(a, b) for (a, b) in pairs_in(R)) >= 20)
    else:     # Case II
        m.Add(sum(ev(a, b) for (a, b) in pairs_in(notP)) >= 31)  # Lemma 3
        m.Add(sum(ev(a, b) for (a, b) in pairs_in(notQ)) >= 31)  # Lemma 3
    # Symmetry breaking: all constraints are invariant under permuting
    # vertices within P, within Q\P, and within the rest; every orbit has a
    # representative with non-decreasing degrees inside each class, so
    # requiring that is sound.
    classes = [sorted(set(P) & set(Q)), sorted(set(P) - set(Q)),
               sorted(set(Q) - set(P)),
               sorted(v for v in VS if v not in P and v not in Q)]
    for cls in classes:
        for (u, w) in zip(cls, cls[1:]):
            m.Add(sum(ev(u, t) for t in VS if t != u)
                  <= sum(ev(w, t) for t in VS if t != w))
    # L7 lower half: tau4 >= 4 via aux independence indicators
    i4 = {}
    for S4 in itertools.combinations(VS, 4):
        s = m.NewBoolVar(f'i{S4}')
        i4[S4] = s
        for (a, b) in pairs_in(S4):
            m.AddImplication(s, ev(a, b).Not())
    for H in itertools.combinations(VS, 3):
        hs = set(H)
        m.AddBoolOr([i4[S4] for S4 in i4 if not hs & set(S4)])
    return m, x


def four_clique_cover(adj):
    order = sorted(VS, key=lambda v: sum(not adj[v][u] for u in VS if u != v),
                   reverse=True)
    parts = [[] for _ in range(4)]

    def bt(idx):
        if idx == N:
            return True
        v = order[idx]
        seen_empty = False
        for p in parts:
            if not p:
                if seen_empty:
                    return False
                seen_empty = True
            if all(adj[v][u] for u in p):
                p.append(v)
                if bt(idx + 1):
                    return True
                p.pop()
        return False

    return [list(p) for p in parts] if bt(0) else None


CASES = {'I': (list(range(4)), list(range(4, 9)), True, None, 6)}
for k in range(5):
    CASES[f'II.k{k}'] = (list(range(4)),
                         list(range(k)) + list(range(4, 8 - k)),
                         False, 6 - k, 6 - k)


def main():
    name = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    P, Q, hit3, ePmax, eQmax = CASES[name]
    t0 = time.time()
    m, x = build(name, P, Q, hit3, ePmax, eQmax)
    print(f"[{name}] cp-sat model built in {time.time()-t0:.0f}s", flush=True)
    it = 0
    while True:
        it += 1
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = workers
        st = solver.Solve(m)
        if st == cp_model.INFEASIBLE:
            print(f"[{name}] INFEASIBLE (iter {it}, {time.time()-t0:.0f}s)",
                  flush=True)
            json.dump({'verdict': 'UNSAT', 'witness': None, 'P': sorted(P),
                       'Q': sorted(Q), 'solver': 'cp-sat', 'iters': it},
                      open(f'artifacts/result_cpsat_{name}.json', 'w'),
                      indent=1)
            return
        assert st in (cp_model.FEASIBLE, cp_model.OPTIMAL), st
        adj = [[False] * N for _ in range(N)]
        E = []
        for (i, j) in PAIRS:
            if solver.Value(x[(i, j)]):
                adj[i][j] = adj[j][i] = True
                E.append([i, j])
        part = four_clique_cover(adj)
        if part is None:
            print(f"[{name}] WITNESS (iter {it}, {time.time()-t0:.0f}s)",
                  flush=True)
            json.dump({'verdict': 'SAT', 'witness': E, 'P': sorted(P),
                       'Q': sorted(Q), 'solver': 'cp-sat', 'iters': it},
                      open(f'artifacts/result_cpsat_{name}.json', 'w'),
                      indent=1)
            return
        # block this clique cover (sound: spec forbids every 4-clique-cover)
        m.AddBoolOr([x[(a, b)].Not() for cls in part for (a, b) in
                     pairs_in(cls)])
        print(f"[{name}] iter {it}: blocked a 4-clique-cover "
              f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == '__main__':
    main()
