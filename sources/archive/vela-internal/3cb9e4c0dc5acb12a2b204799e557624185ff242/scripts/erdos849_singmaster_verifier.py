# Smart exact search to very high B: enumerate k>=3 only (O(B^{1/3}) entries), and for
# triangular (k=2) test by closed form. Also test k=1 always present.
# t(a) = 1[k=1] + 1[triangular and the triangular n has k=2<=n/2] + (#k>=3 reps).
import sys
from math import comb, isqrt
B = int(sys.argv[1])
from collections import defaultdict

def is_triangular_rep(a):
    # a = C(m,2)=m(m-1)/2 with k=2<=m/2 => m>=4. m=(1+sqrt(1+8a))/2
    d = 1+8*a
    s = isqrt(d)
    if s*s!=d: return False
    m = (1+s)
    if m%2: return False
    m//=2
    return m>=4   # need k=2<=n/2 => n=m>=4

# collect k>=3 reps
seen = defaultdict(list)
k = 3
while comb(2*k,k) <= B:
    n = 2*k
    while True:
        c = comb(n,k)
        if c > B: break
        seen[c].append((n,k))
        n += 1
    k += 1

# now compute t for every a that has a k>=3 rep OR is triangular-with-k=2.
# We care about t>=4 (since t>=4 already extremely rare). t = 1 + tri + (#k>=3).
results = defaultdict(list)
for a, r in seen.items():
    t = 1 + (1 if is_triangular_rep(a) else 0) + len(r)
    if t>=4:
        results[t].append((a, r, is_triangular_rep(a)))
print(f"B={B}; #values with a k>=3 rep: {len(seen)}")
for t in sorted(results):
    print(f" t={t}: {len(results[t])} values")
    for a,r,tri in sorted(results[t])[:12]:
        print(f"    a={a} k>=3reps={r} triangular={tri}")
# Also: values with >=3 reps among k>=3 alone (no k=2 needed) would be huge t. report max interior
maxint = max((len(r) for r in seen.values()), default=0)
print("max # of k>=3 reps for a single value:", maxint)

# --- Verifier provenance (Erdos #849 / Singmaster's conjecture) ---
# N(a) = #{(n,k): C(n,k)=a, 1<=k<=n/2}. Question: for every t>=1 is there a with N(a)=t exactly?
# This is Singmaster's conjecture (Erdos credits Erdos-Gordon). Both Erdos and Singmaster
# believed the answer is NO (a uniform bound on N(a) exists).
# Exact exhaustive search (this script) to B=10^18: only N(a)=4 value is 3003;
#   NO value has N(a)>=5; max # of k>=3 reps for any value is 2 (only 3003).
# Cross-validated by an independent per-Pascal-row method up to 2*10^6 (identical t=3/t=4 sets).
# Known t<=4 witnesses: t=1 any prime; t=2 e.g. 6=C(4,2); t=3 in {120,210,1540,7140,11628,24310};
#   t=4 uniquely 3003 = C(78,2)=C(15,5)=C(14,6)=C(3003,1).
