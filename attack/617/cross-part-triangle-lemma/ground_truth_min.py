import itertools
from ortools.sat.python import cp_model

# Parts P0=0..5 (size6), P1=6..10, P2=11..15, P3=16..20, P4=21..25
sizes=[6,5,5,5,5]; part_of={}; off=0
for pi,n in enumerate(sizes):
    for v in range(off,off+n): part_of[v]=pi
    off+=n
N=26

# star K_{1,4} in P0 (center 0, leaves 1-4, isolated 5) + K_{2,3} in P1 ({6,7}x{8,9,10})
E={(0,1),(0,2),(0,3),(0,4),(6,8),(6,9),(6,10),(7,8),(7,9),(7,10)}
E={(min(a,b),max(a,b)) for a,b in E}

cross=[p for p in itertools.combinations(range(N),2) if part_of[p[0]]!=part_of[p[1]]]
cidx={p:i for i,p in enumerate(cross)}
m=cp_model.CpModel()
h=[m.NewBoolVar(f"h{i}") for i in range(len(cross))]

outright=False
for S in itertools.combinations(range(N),6):
    cids=[]; intra=[]
    for a,b in itertools.combinations(S,2):
        if part_of[a]!=part_of[b]: cids.append(cidx[(a,b)])
        else: intra.append((a,b))
    intraE=sum(1 for p in intra if p in E)
    rhs=len(cids)+intraE-4
    if rhs<0: outright=True; break
    if rhs<len(cids): m.Add(sum(h[i] for i in cids)<=rhs)   # every 6-set >=4 edges
    if intraE==len(intra): m.AddBoolOr([h[i] for i in cids]) # K6-free

if outright:
    print("INFEASIBLE OUTRIGHT")
else:
    m.Minimize(sum(h))
    class CB(cp_model.CpSolverSolutionCallback):
        def __init__(self): super().__init__()
        def on_solution_callback(self):
            print(f"  incumbent {int(self.ObjectiveValue())} holes  (lower bound {self.BestObjectiveBound():.1f})",flush=True)
    sv=cp_model.CpSolver()
    sv.parameters.max_time_in_seconds=300
    sv.parameters.num_search_workers=8
    st=sv.Solve(m,CB())
    print(f"\nSTATUS {sv.StatusName(st)}   true min_holes in [{sv.BestObjectiveBound():.1f}, {sv.ObjectiveValue():.0f}]")
    print(f"GPT claimed lower bound: 38")
    print("VERDICT:", "REFUTED (feasible < 38 exists)" if sv.ObjectiveValue()<38 else
          ("CONFIRMED >=38" if sv.BestObjectiveBound()>=38 else "INCONCLUSIVE (gap not closed)"))
