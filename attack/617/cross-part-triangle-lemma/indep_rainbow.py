import itertools
# Independent brute force. Vertices: 0=center, 1..4=leaves, 5,6=A(deg-3), 7,8,9=B(deg-2)
leaves=[1,2,3,4]; A=[5,6]; B=[7,8,9]
# active triples: star (center,leaf,p1) for every leaf & every P1 vertex; dense (w,a,b) w in P0\{z}, a in A, b in B
triples=[]
for l in leaves:
    for p1 in range(5,10): triples.append((0,l,p1))
for w in range(0,5):          # center + 4 leaves = P0\{z}
    for a in A:
        for b in B: triples.append((w,a,b))
cnt=0
for col in itertools.product(range(5),repeat=10):
    if len(set(col[1:5]))!=4: continue          # leaves must be 4 distinct
    good=True
    for (x,y,z) in triples:
        if col[x]==col[y] or col[x]==col[z] or col[y]==col[z]:
            good=False; break
    if good: cnt+=1
print("independent_rainbow_count =", cnt, " (GPT claims 0)")
print("VERDICT:", "obstruction holds (0)" if cnt==0 else f"REFUTED: {cnt} valid colorings exist")
