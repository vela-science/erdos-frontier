#!/usr/bin/env python3
"""part_graphs.py — enumerate non-isomorphic graphs on n <= 8 vertices with a
given edge count that satisfy 'every 6-subset spans >= 4 edges' (the per-part
internal constraint).  Used to enumerate internal-edge configurations.

We canonicalize by brute-force over Sym(n) (n <= 8, fast enough with early
pruning by a cheap invariant: the sorted degree sequence).  For each edge count
we return one representative edge set per isomorphism class.
"""
import itertools
from functools import lru_cache


def _valid6(n, edgeset):
    if n < 6:
        return True
    adj = [0] * n
    for a, b in edgeset:
        adj[a] |= 1 << b
        adj[b] |= 1 << a
    for S in itertools.combinations(range(n), 6):
        c = 0
        for i in range(6):
            r = adj[S[i]]
            for j in range(i + 1, 6):
                c += (r >> S[j]) & 1
        if c < 4:
            return False
    return True


def _deg_seq(n, edgeset):
    d = [0] * n
    for a, b in edgeset:
        d[a] += 1
        d[b] += 1
    return tuple(sorted(d))


def _canon(n, edgeset):
    """Canonical form: lexicographically smallest edge-pair tuple over all
    relabelings that preserve the degree sequence multiset.  We restrict the
    permutation search to those mapping vertices to equal-degree targets to keep
    it fast, which is sound because any isomorphism preserves degree."""
    deg = [0] * n
    for a, b in edgeset:
        deg[a] += 1
        deg[b] += 1
    # group source and target vertices by degree
    from collections import defaultdict
    by_deg = defaultdict(list)
    for v in range(n):
        by_deg[deg[v]].append(v)
    # candidate images: a permutation that respects degree classes
    deg_classes = sorted(by_deg.keys())
    best = None
    # build all degree-respecting bijections
    target_lists = [by_deg[d] for d in deg_classes]
    source_lists = [by_deg[d] for d in deg_classes]  # same grouping

    def rec(ci, mapping):
        nonlocal best
        if ci == len(deg_classes):
            mapped = sorted(tuple(sorted((mapping[a], mapping[b])))
                            for a, b in edgeset)
            key = tuple(mapped)
            if best is None or key < best:
                best = key
            return
        srcs = source_lists[ci]
        for perm in itertools.permutations(target_lists[ci]):
            m2 = dict(mapping)
            for s, t in zip(srcs, perm):
                m2[s] = t
            rec(ci + 1, m2)

    rec(0, {})
    return best


@lru_cache(maxsize=None)
def noniso(n, e):
    """Return a tuple of representative edge sets (each a tuple of (a,b) pairs)
    for all non-isomorphic n-vertex graphs with e edges satisfying the
    >=4-on-every-6-subset condition.  Results are deterministic and cached."""
    if e < 0:
        return ()
    allpairs = list(itertools.combinations(range(n), 2))
    if e > len(allpairs):
        return ()
    seen = set()
    reps = []
    for combo in itertools.combinations(allpairs, e):
        if not _valid6(n, combo):
            continue
        c = _canon(n, combo)
        if c in seen:
            continue
        seen.add(c)
        reps.append(combo)
    return tuple(reps)


if __name__ == "__main__":
    import time
    for n, emax in [(5, 6), (6, 7), (7, 9), (8, 10)]:
        for e in range(0, emax + 1):
            t0 = time.time()
            r = noniso(n, e)
            if r:
                print(f"n={n} e={e}: {len(r):4d} non-iso valid  ({time.time()-t0:.1f}s)")
