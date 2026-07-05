from itertools import combinations, permutations, product
def matchings(a,b):
    out=[]
    for k in range(min(a,b)+1):
        for A in combinations(range(a),k):
            for B in combinations(range(b),k):
                for pi in permutations(B): out.append(frozenset(zip(A,pi)))
    return out
def covers_box(s,M12,M13,M23):
    a,b,c=s
    for x,y,z in product(range(a),range(b),range(c)):
        if (x,y) not in M12 and (x,z) not in M13 and (y,z) not in M23: return False
    return True
def match_block(s):
    a,b,c=s; best=None
    for M12 in matchings(a,b):
        for M13 in matchings(a,c):
            for M23 in matchings(b,c):
                val=len(M12)+len(M13)+len(M23)
                if best is not None and val>=best: continue
                if covers_box(s,M12,M13,M23): best=val
    return best
print('MATCH_BLOCK(2,2,2)=',match_block((2,2,2)))
print('MATCH_BLOCK(3,2,2)=',match_block((3,2,2)))
P0=range(6);P1=range(5);CENTER=0;LEAVES=[1,2,3,4]
F_edges={(a,b) for a in [0,1] for b in [2,3,4]}
def e0(R):
    R=set(R); return sum(1 for l in LEAVES if CENTER in R and l in R)
def e1(S):
    S=set(S); return sum(1 for a,b in F_edges if a in S and b in S)
constraints=[]
for r in range(1,6):
    s=6-r
    if 1<=s<=5:
        for R in combinations(P0,r):
            for S in combinations(P1,s):
                rhs=r*s+e0(R)+e1(S)-4
                if rhs<r*s:
                    mask=0
                    for x in R:
                        for y in S: mask|=1<<(5*x+y)
                    constraints.append((mask,rhs))
cons_by_var=[[] for _ in range(30)]
for i,(mask,rhs) in enumerate(constraints):
    for v in range(30):
        if (mask>>v)&1: cons_by_var[v].append(i)
cur=[0]*len(constraints)
def active_info(mask):
    U=set();active=[]
    for l in LEAVES:
        for y in P1:
            if ((mask>>(5*CENTER+y))&1)==0 and ((mask>>(5*l+y))&1)==0:
                T=(('P0',CENTER),('P0',l),('P1',y));U.update(T);active.append(T)
    for w in P0:
        for a,b in F_edges:
            if ((mask>>(5*w+a))&1)==0 and ((mask>>(5*w+b))&1)==0:
                T=(('P0',w),('P1',a),('P1',b));U.update(T);active.append(T)
    return active,U
best=[10**9];no_active=[0];valid=[0];dist={};best_sols=[]
def dfs(v,mask,h):
    if v==30:
        valid[0]+=1;active,U=active_info(mask)
        if not active: no_active[0]+=1; return
        val=h+3*len(U)+6; dist[val]=dist.get(val,0)+1
        if val<best[0]: best[0]=val; best_sols.clear()
        if val==best[0]: best_sols.append((h,len(U),len(active)))
        return
    dfs(v+1,mask,h); ok=True
    for ci in cons_by_var[v]:
        if cur[ci]+1>constraints[ci][1]: ok=False; break
    if ok:
        for ci in cons_by_var[v]: cur[ci]+=1
        dfs(v+1,mask|(1<<v),h+1)
        for ci in cons_by_var[v]: cur[ci]-=1
dfs(0,0,0)
print('core_valid=',valid[0],'no_active=',no_active[0])
print('core_B=',best[0],'num_B_sols=',len(best_sols),'sol=',best_sols[0] if best_sols else None)
print('next_core_values=',sorted((k,dist[k]) for k in dist)[:5])
# rainbow obstruction
C=0;L=[1,2,3,4];A=[5,6];B=[7,8,9];P1a=[5,6,7,8,9];W=[0,1,2,3,4]
active=[]
for l in L:
    for y in P1a: active.append((C,l,y))
for w in W:
    for a in A:
        for b in B: active.append((w,a,b))
byv=[[] for _ in range(10)]
for e in active:
    for v in e: byv[v].append(e)
order=sorted(range(10),key=lambda v:-len(byv[v]));colors=[None]*10;count=[0]
def edge_ok(e):
    vals=[colors[v] for v in e if colors[v] is not None]; return len(vals)==len(set(vals))
def dfsc(i):
    if i==len(order):
        if len({colors[l] for l in L})==4: count[0]+=1
        return
    v=order[i]
    for c in range(5):
        colors[v]=c
        if all(edge_ok(e) for e in byv[v]):
            a=[colors[l] for l in L if colors[l] is not None]
            if len(a)==len(set(a)): dfsc(i+1)
        colors[v]=None
dfsc(0)
print('rainbow_colorings_with_four_distinct_leaves=',count[0])
