#!/usr/bin/env python3
"""Replay a dumped DIMACS CNF with Glucose 4.2 (DRAT proof logging) and
verify the proof with drat-trim.  Produces artifacts/<base>.drat and runs
the verifier on it.

Usage: certify_unsat.py artifacts/final_<case>.cnf [path-to-drat-trim]
"""
import subprocess, sys, time
from pysat.formula import CNF
from pysat.solvers import Glucose42

cnf_path = sys.argv[1]
drat_trim = sys.argv[2] if len(sys.argv) > 2 else '/tmp/drat-trim/drat-trim'

print(f"loading {cnf_path} ...", flush=True)
cnf = CNF(from_file=cnf_path)
print(f"{cnf.nv} vars, {len(cnf.clauses)} clauses", flush=True)
s = Glucose42(bootstrap_with=cnf.clauses, with_proof=True)
t0 = time.time()
res = s.solve()
print(f"glucose42: {'SAT' if res else 'UNSAT'} in {time.time()-t0:.0f}s",
      flush=True)
if res:
    sys.exit("unexpected SAT — no certificate to produce")
proof = s.get_proof()
drat_path = cnf_path.replace('.cnf', '.drat')
with open(drat_path, 'w') as f:
    for line in proof:
        f.write(line + ' 0\n' if not line.endswith(' 0') else line + '\n')
print(f"proof: {len(proof)} lemmas -> {drat_path}", flush=True)
out = subprocess.run([drat_trim, cnf_path, drat_path], capture_output=True,
                     text=True, timeout=36000)
print(out.stdout[-2000:])
ok = 's VERIFIED' in out.stdout
print("DRAT VERIFIED" if ok else "DRAT VERIFICATION FAILED")
sys.exit(0 if ok else 1)
