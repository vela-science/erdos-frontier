#!/usr/bin/env python3
"""Machine confirmation of the aggregation lemma / equality obstruction, directly
against the FULL model (no reliance on the hand argument).

Pin the P0-P1 core pattern, then ask CP-SAT whether the config admits a completion
with <= CAP holes. UNSAT at cap 38 confirms min_holes >= 39 for that core.

Usage:  python3 fix_core_check.py [xstar|empty] [CAP]
  xstar : core X* = {(z,a0),(z,a1)} (the unique pattern with aggregation LB = 38)
  empty : core = {} (all P0-P1 pairs present; aggregation LB = 39)
Both return UNSAT at CAP=38, confirming min_holes >= 39.
"""
import itertools, sys
from ortools.sat.python import cp_model

mode = sys.argv[1] if len(sys.argv) > 1 else "xstar"
CAP  = int(sys.argv[2]) if len(sys.argv) > 2 else 38

# parts P0=0..5 (center 0, leaves 1-4, isolated z=5); P1=6..10 (K_{2,3}: A={6,7} deg3, B={8,9,10} deg2)
sizes=[6,5,5,5,5]; part_of={}; off=0
for pi,n in enumerate(sizes):
    for v in range(off,off+n): part_of[v]=pi
    off+=n
N=26
E={(0,1),(0,2),(0,3),(0,4),(6,8),(6,9),(6,10),(7,8),(7,9),(7,10)}
E={(min(a,b),max(a,b)) for a,b in E}
Xstar = set() if mode=="empty" else {(5,6),(5,7)}

cross=[p for p in itertools.combinations(range(N),2) if part_of[p[0]]!=part_of[p[1]]]
cidx={p:i for i,p in enumerate(cross)}
m=cp_model.CpModel()
h=[m.NewBoolVar(f"h{i}") for i in range(len(cross))]
for p in cross:                                  # pin the core (all P0-P1 cross pairs)
    a,b=p
    if part_of[a]==0 and part_of[b]==1:
        m.Add(h[cidx[p]] == (1 if p in Xstar else 0))
m.Add(sum(h)<=CAP)
for S in itertools.combinations(range(N),6):
    cids=[]; intra=[]
    for a,b in itertools.combinations(S,2):
        if part_of[a]!=part_of[b]: cids.append(cidx[(a,b)])
        else: intra.append((a,b))
    intraE=sum(1 for p in intra if p in E)
    rhs=len(cids)+intraE-4
    if rhs<0: print("INFEASIBLE OUTRIGHT"); raise SystemExit
    if rhs<len(cids): m.Add(sum(h[i] for i in cids)<=rhs)   # every 6-set spans >= 4 edges
    if intraE==len(intra): m.AddBoolOr([h[i] for i in cids]) # K6-free

sv=cp_model.CpSolver(); sv.parameters.max_time_in_seconds=600; sv.parameters.num_search_workers=8
st=sv.Solve(m); name=sv.StatusName(st)
print(f"core={mode}, cap={CAP}: STATUS {name}")
if st in (cp_model.OPTIMAL,cp_model.FEASIBLE):
    nh=sum(int(sv.Value(x)) for x in h)
    print(f"  SAT -> completion with {nh} holes exists -> aggregation/obstruction REFUTED")
elif st==cp_model.INFEASIBLE:
    print(f"  UNSAT -> no <= {CAP}-hole completion -> min_holes >= {CAP+1} for this core: CONFIRMED")
else:
    print("  UNKNOWN (timeout)")
