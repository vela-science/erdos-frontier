#!/usr/bin/env python3
# For each F in {C4,C5,P4}: (1) scan all valid P0-P1 cores, find bound B(F) and the
# binding core X*; (2) pin core=X* in the full model and check cap=B-1 -> UNSAT
# confirms min over X* >= B(F), the same fix-core backing K_{2,3} got.
import itertools
from ortools.sat.python import cp_model

P0=range(6); P1L=range(5); CENTER=0; LEAVES=[1,2,3,4]
FAMS={
 "C4": {(0,1),(1,2),(2,3),(3,0)},
 "C5": {(0,1),(1,2),(2,3),(3,4),(4,0)},
 "P4": {(0,1),(1,2),(2,3)},
}
def scan(Fed):
    Fed={tuple(sorted(e)) for e in Fed}
    e0=lambda R: sum(1 for l in LEAVES if CENTER in R and l in R)
    e1=lambda S: sum(1 for a,b in Fed if a in S and b in S)
    cons=[]
    for r in range(1,6):
        s=6-r
        if 1<=s<=5:
            for R in itertools.combinations(P0,r):
                for S in itertools.combinations(P1L,s):
                    rhs=r*s+e0(set(R))+e1(set(S))-4
                    if rhs<r*s:
                        mask=0
                        for x in R:
                            for y in S: mask|=1<<(5*x+y)
                        cons.append((mask,rhs))
    cbv=[[] for _ in range(30)]
    for i,(mk,_) in enumerate(cons):
        for v in range(30):
            if (mk>>v)&1: cbv[v].append(i)
    cur=[0]*len(cons); best=[10**9]; bmask=[0]
    def U_of(mask):
        U=set()
        for l in LEAVES:
            for y in P1L:
                if not (mask>>(5*CENTER+y))&1 and not (mask>>(5*l+y))&1:
                    U.update([("0",CENTER),("0",l),("1",y)])
        for w in P0:
            for a,b in Fed:
                if not (mask>>(5*w+a))&1 and not (mask>>(5*w+b))&1:
                    U.update([("0",w),("1",a),("1",b)])
        return U
    def dfs(v,mask,h):
        if v==30:
            U=U_of(mask)
            if not U: return
            val=h+3*len(U)+6
            if val<best[0]: best[0]=val; bmask[0]=mask
            return
        dfs(v+1,mask,h)
        ok=all(cur[ci]+1<=cons[ci][1] for ci in cbv[v])
        if ok:
            for ci in cbv[v]: cur[ci]+=1
            dfs(v+1,mask|(1<<v),h+1)
            for ci in cbv[v]: cur[ci]-=1
    dfs(0,0,0)
    return best[0], bmask[0]

sizes=[6,5,5,5,5]; part_of={}; off=0
for pi,n in enumerate(sizes):
    for v in range(off,off+n): part_of[v]=pi
    off+=n
N=26
cross=[p for p in itertools.combinations(range(N),2) if part_of[p[0]]!=part_of[p[1]]]
cidx={p:i for i,p in enumerate(cross)}

for name,Fl in FAMS.items():
    B,bmask=scan(Fl)
    Xstar={(i//5, 6+(i%5)) for i in range(30) if (bmask>>i)&1}   # global P0-P1 holes
    Eglob={(min(6+a,6+b),max(6+a,6+b)) for a,b in Fl}
    E={(0,1),(0,2),(0,3),(0,4)} | Eglob
    cap=B-1
    m=cp_model.CpModel(); h=[m.NewBoolVar(f"h{i}") for i in range(len(cross))]
    for p in cross:
        a,b=p
        if part_of[a]==0 and part_of[b]==1:
            m.Add(h[cidx[p]]==(1 if p in Xstar else 0))
    m.Add(sum(h)<=cap)
    for S in itertools.combinations(range(N),6):
        cids=[]; intra=[]
        for a,b in itertools.combinations(S,2):
            if part_of[a]!=part_of[b]: cids.append(cidx[(a,b)])
            else: intra.append((a,b))
        intraE=sum(1 for p in intra if p in E)
        rhs=len(cids)+intraE-4
        if rhs<0: break
        if rhs<len(cids): m.Add(sum(h[i] for i in cids)<=rhs)
        if intraE==len(intra): m.AddBoolOr([h[i] for i in cids])
    sv=cp_model.CpSolver(); sv.parameters.max_time_in_seconds=600; sv.parameters.num_search_workers=8
    st=sv.StatusName(sv.Solve(m))
    v=("CONFIRMED min>=%d"%B if st=="INFEASIBLE" else "REFUTED" if st in("OPTIMAL","FEASIBLE") else st)
    print(f"star+{name}: B={B} |X*|={len(Xstar)} fix-core cap={cap} -> {st}  => {v}", flush=True)
