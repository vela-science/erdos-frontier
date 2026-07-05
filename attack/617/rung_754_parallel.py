"""Parallel fixed-config runner for the (7,5,5,5,4) shape at rung q.

Generalizes road62.py (validated: reproduces it at q=6) to arbitrary rung
and to I=7 configs.  Parts P0=7 (the dense part, e(P0)=e0 in {6,7}),
P1,P2,P3 = empty 5-parts, Q = empty 4-part.  defect d=2, budget = I+q-2.
I=6: e0=6 (six max-deg-2 structures).  I=7: e0=6 + one extra edge (in a
5-part or Q), or e0=7 (valid 7-edge 7-part structures).  All internal
configs enumerated up to isomorphism; INFEASIBLE for all => (7,5,5,5,4)
contributes to killing rung q.

Usage: rung_754_parallel.py q [time_limit] [workers_per] [concurrency]
"""
import sys, json, time, itertools
from concurrent.futures import ProcessPoolExecutor, as_completed
from ortools.sat.python import cp_model

q  = int(sys.argv[1]) if len(sys.argv) > 1 else 7
TL = int(sys.argv[2]) if len(sys.argv) > 2 else 600
WK = int(sys.argv[3]) if len(sys.argv) > 3 else 4
CC = int(sys.argv[4]) if len(sys.argv) > 4 else 8

P0 = list(range(0,7)); P1=list(range(7,12)); P2=list(range(12,17))
P3 = list(range(17,22)); Q=list(range(22,26))
PARTS=[P0,P1,P2,P3,Q]
part_of={v:pi for pi,P in enumerate(PARTS) for v in P}
CROSS=[(a,b) for a,b in itertools.combinations(range(26),2) if part_of[a]!=part_of[b]]
CIDX={e:i for i,e in enumerate(CROSS)}
assert len(CROSS)==268
SIX=[]
for S in itertools.combinations(range(26),6):
    cids,intra=[],[]
    for a,b in itertools.combinations(S,2):
        (cids if part_of[a]!=part_of[b] else intra).append((a,b))
    SIX.append(([CIDX[p] for p in cids],intra))


def valid_7part(e0, n=7):
    """non-iso graphs on the 7 vertices 0..6 with e0 edges, every 6-subset
    spanning >= 4 edges (=> max-degree <= 3).  Exact iso-dedup via networkx
    WL-hash buckets + is_isomorphic (validated: e0=6 -> 6 structs = road62)."""
    import networkx as nx
    verts=list(range(n)); allp=list(itertools.combinations(verts,2))
    buckets={}; reps=[]
    for es in itertools.combinations(allp,e0):
        deg={}
        for a,b in es: deg[a]=deg.get(a,0)+1; deg[b]=deg.get(b,0)+1
        if deg and max(deg.values())>3: continue
        if any(e0-deg.get(d,0)<4 for d in verts): continue
        G=nx.Graph(); G.add_nodes_from(verts); G.add_edges_from(es)
        hsh=nx.weisfeiler_lehman_graph_hash(G, iterations=3)
        if any(nx.is_isomorphic(G,H) for (H,_) in buckets.get(hsh,[])): continue
        buckets.setdefault(hsh,[]).append((G,es)); reps.append(list(es))
    return reps


def configs_for(q):
    """list of (E, cap, tag)."""
    out=[]
    base6 = valid_7part(6)
    # I=6: e0=6, no extra
    cap6 = 6 + q - 2
    for c in base6:
        out.append((list(c), cap6, f"I6_e06"))
    # I=7: e0=6 + 1 extra edge (in a 5-part P1, or in Q)
    cap7 = 7 + q - 2
    for c in base6:
        out.append((list(c)+[(P1[0],P1[1])], cap7, "I7_e06_5part"))
        out.append((list(c)+[(Q[0],Q[1])],   cap7, "I7_e06_Qpart"))
    import os
    if os.environ.get("E07_ONLY") == "1":
        return [(list(c), cap7, "I7_e07") for c in valid_7part(7)]
    if os.environ.get("SKIP_E07") != "1":
        for c in valid_7part(7):
            out.append((list(c), cap7, "I7_e07"))
    return out


def build(E, cap):
    Eset=set((min(a,b),max(a,b)) for a,b in E)
    m=cp_model.CpModel(); h=[m.NewBoolVar(f"h{i}") for i in range(268)]
    m.Add(sum(h)<=cap)
    for cids,intra in SIX:
        intraE=sum(1 for p in intra if p in Eset)
        rhs=len(cids)+intraE-4
        if rhs<0: return None
        if rhs<min(len(cids),cap+1): m.Add(sum(h[i] for i in cids)<=rhs)
        if intraE==len(intra): m.AddBoolOr([h[i] for i in cids])
    return m,h


def work(item):
    E,cap,tag=item; t0=time.time()
    built=build(E,cap)
    if built is None: return (E,cap,tag,"SKIP",0)
    m,h=built; s=cp_model.CpSolver()
    s.parameters.max_time_in_seconds=TL; s.parameters.num_search_workers=WK
    st=s.StatusName(s.Solve(m))
    return (E,cap,tag,st,round(time.time()-t0))


def main():
    cfgs=configs_for(q)
    print(f"(7,5,5,5,4) q={q}: {len(cfgs)} configs, TL={TL} WK={WK} CC={CC}",flush=True)
    out=open(f"artifacts/road66/rung_{q}_754_parallel.jsonl","a")
    bad=done=0
    with ProcessPoolExecutor(max_workers=CC) as ex:
        futs=[ex.submit(work,c) for c in cfgs]
        for fut in as_completed(futs):
            E,cap,tag,st,secs=fut.result(); done+=1
            out.write(json.dumps({"E":E,"cap":cap,"tag":tag,"status":st,"secs":secs})+"\n"); out.flush()
            if st not in ("INFEASIBLE","SKIP"):
                bad+=1
                print(f"  [{st}] {tag} cap={cap} E={E} ({secs}s)"+
                      ("  <<< FEASIBLE — route caps!" if st in("OPTIMAL","FEASIBLE") else "  <<< inconclusive"),flush=True)
    print(f"\nq={q} (7,5,5,5,4): {done} configs, {bad} non-infeasible. "+
          (f"ALL INFEASIBLE => contributes m* >= {56+q}" if bad==0 else "NOT all closed"),flush=True)


if __name__=="__main__":
    main()
