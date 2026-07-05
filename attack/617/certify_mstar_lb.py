#!/usr/bin/env python3
"""Certified lower bounds for m* (Erdos #617, r=5 single-class problem).

Target statement, per MSTAR-PROBE.md: no graph G on 26 vertices has
  (A) alpha(G) <= 5,  (B) every 6-set spans <= 11 edges,  e(G) <= TARGET.
Certifying TARGET = 65 proves the r=5 case of #617 outright (counting).
Smaller TARGETs are certified m* lower bounds (m* >= TARGET+1) and validate
the pipeline end to end.

Soundness design (key point): a CNF built from a SUBSET of the spec's
constraints that is UNSAT certifies the full spec UNSAT a fortiori.  So we
grow the expensive cap family (B) lazily:

  core = (A) one clause per 6-set  +  totalizer[ e(G) <= TARGET ]
  loop: solve with CaDiCaL;
        SAT  -> find 6-sets violating (B) in the model, add their
                CardEnc.atmost(11) blocks (counterexample-guided);
        UNSAT -> dump the grown CNF; re-solve it with Glucose 4.2 producing
                a DRAT proof; verify with drat-trim (s VERIFIED).

The dumped CNF + DRAT certificate is the auditable artifact; its clauses are
each spec-implied (witnessed by construction maps logged alongside).  Any
SAT model passing all caps would instead be a witness m* <= TARGET (checked
independently by check_mstar_witness.py) — both exits are decisive.

Usage: certify_mstar_lb.py TARGET [max_rounds] [--seed]
  --seed: pre-cap every 6-set spanning >= 10 edges in any verified witness
          artifacts/mstar_witness_E*.txt (the dense regions of near-optimal
          graphs are where low-edge models overflow; caps are spec-implied
          for EVERY 6-set, so seeding any subset is sound).
Artifacts: artifacts/mstar_lb_T{T}.cnf(.gz), .drat, certs in
artifacts/mstar_lb_summary.txt; requires glucose + drat-trim on PATH for the
certificate leg (CaDiCaL CEGAR leg runs regardless).
"""
import glob, itertools, subprocess, sys, time
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from pysat.solvers import Cadical195

TARGET = int(sys.argv[1])
MAXROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 4000
SEED = "--seed" in sys.argv

V = range(26)
EDGES = list(itertools.combinations(V, 2))
EIDX = {e: i + 1 for i, e in enumerate(EDGES)}        # vars 1..325
pool = IDPool(start_from=326)
SIXES = list(itertools.combinations(V, 6))

clauses = []
for S in SIXES:                                        # (A) alpha <= 5
    clauses.append([EIDX[e] for e in itertools.combinations(S, 2)])
tot = CardEnc.atmost([EIDX[e] for e in EDGES], bound=TARGET,
                     vpool=pool, encoding=EncType.totalizer)
clauses.extend(tot.clauses)

capped = set()


def cap_clauses(S):
    enc = CardEnc.atmost([EIDX[e] for e in itertools.combinations(S, 2)],
                         bound=11, vpool=pool, encoding=EncType.seqcounter)
    return enc.clauses


if SEED:
    dense = set()
    for path in glob.glob("artifacts/mstar_witness_E*.txt"):
        adj = [0] * 26
        for line in open(path):
            u, v = map(int, line.split())
            adj[u] |= 1 << v; adj[v] |= 1 << u
        for S in SIXES:
            if S in dense:
                continue
            cnt = sum((adj[S[i]] >> S[j]) & 1
                      for i in range(6) for j in range(i + 1, 6))
            if cnt >= 10:
                dense.add(S)
    for S in dense:
        capped.add(S)
        clauses.extend(cap_clauses(S))
    print(f"seeded {len(dense)} caps from witnesses", flush=True)

s = Cadical195(bootstrap_with=clauses)
t0 = time.time()
rounds = 0
while True:
    rounds += 1
    if rounds > MAXROUNDS:
        print(f"round cap {MAXROUNDS} hit; aborting"); sys.exit(3)
    if not s.solve():
        print(f"UNSAT after {rounds-1} cap additions ({len(capped)} capped "
              f"6-sets), {time.time()-t0:.1f}s")
        break
    model = set(l for l in s.get_model() if 0 < l <= 325)
    adj = [0] * 26
    for (u, v) in EDGES:
        if EIDX[(u, v)] in model:
            adj[u] |= 1 << v; adj[v] |= 1 << u
    viol = []
    for S in SIXES:
        if S in capped:
            continue
        cnt = sum((adj[S[i]] >> S[j]) & 1 for i in range(6) for j in range(i+1, 6))
        if cnt > 11:
            viol.append(S)
            if len(viol) >= 200:                       # batch caps per round
                break
    if not viol:
        es = sorted(e for e in EDGES if EIDX[e] in model)
        path = f"artifacts/mstar_witness_T{TARGET}_E{len(es)}.txt"
        with open(path, "w") as f:
            for u, v in es:
                f.write(f"{u} {v}\n")
        print(f"SAT — genuine witness, m* <= {len(es)}: {path} "
              f"(verify with check_mstar_witness.py)")
        sys.exit(2)
    for S in viol:
        capped.add(S)
        for c in cap_clauses(S):
            clauses.append(c)
            s.add_clause(c)
    if rounds % 25 == 0:
        print(f"  round {rounds}: {len(capped)} capped six-sets, "
              f"{time.time()-t0:.0f}s", flush=True)

cnf_path = f"artifacts/mstar_lb_T{TARGET}.cnf"
nv = pool.top
with open(cnf_path, "w") as f:
    f.write(f"p cnf {nv} {len(clauses)}\n")
    for c in clauses:
        f.write(" ".join(map(str, c)) + " 0\n")
print(f"grown CNF dumped: {cnf_path} ({nv} vars, {len(clauses)} clauses)")
print(f"next: glucose -certified -certified-output={cnf_path}.drat {cnf_path} ; "
      f"drat-trim {cnf_path} {cnf_path}.drat  (expect: s VERIFIED)")
