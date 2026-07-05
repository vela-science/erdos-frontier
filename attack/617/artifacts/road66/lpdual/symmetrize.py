#!/usr/bin/env python3
"""Symmetrize the optimal fractional packing into ORBIT classes so the
certificate becomes hand-presentable: a single weight per orbit-type of K6.

For a config with automorphism group Aut (part-permutations fixing the
internal graph + intra-part symmetries), averaging a feasible packing y over
Aut yields a feasible packing of the SAME value whose weight is constant on
each Aut-orbit of potential-K6s.  We approximate Aut-orbits by a structural
SIGNATURE of each K6 that is invariant under the obvious automorphisms, sum the
optimal y over each signature class, and report (class, count, total weight,
per-member weight).  This exposes the structure of the certificate.

Usage: symmetrize.py NAME
"""
import sys, itertools
import numpy as np
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617/artifacts/road66/lpdual")
import verify_packing as V

def signature(S, E):
    """Structural type of a potential-K6 S, invariant under config automorphisms.
    Encodes: for each part, (part-role, #vertices-of-S-in-it, local internal-edge
    pattern among them, and whether a special vertex like the star-center is used).
    Roles: P0 (star part), Pi (matching/dense parts), all symmetric among equals."""
    P0 = set(V.PARTS[0])
    center = V.PARTS[0][0]   # star center
    leaves = set(V.PARTS[0][1:5])  # 4 leaves
    Eset = set((min(a,b),max(a,b)) for a,b in E)
    # describe occupancy per part as a canonical tuple; parts P1..P4 are
    # interchangeable so we SORT their descriptors.
    def part_desc(P):
        verts = [v for v in S if v in set(P)]
        k = len(verts)
        ie = sum(1 for a,b in itertools.combinations(verts,2) if (min(a,b),max(a,b)) in Eset)
        return (k, ie)
    p0verts = [v for v in S if v in P0]
    p0 = (len([v for v in p0verts if v==center]),         # center used?
          len([v for v in p0verts if v in leaves]),       # #leaves
          len([v for v in p0verts if v not in leaves and v != center]),  # isolated z
          sum(1 for a,b in itertools.combinations(p0verts,2) if (min(a,b),max(a,b)) in Eset))
    others = tuple(sorted(part_desc(P) for P in V.PARTS[1:]))
    return ("P0", p0, "rest", others)

def recover_set(cols):
    """Recover the 6-set from its list of cross-pair columns. cols are indices
    into V.CROSS; the union of endpoints, restricted to a 6-set, is the K6."""
    verts = set()
    for c in cols:
        a, b = V.CROSS[c]; verts.add(a); verts.add(b)
    return verts

if __name__ == "__main__":
    name = sys.argv[1]
    E = V.ATOMS[name]
    y, val, K = V.max_packing(E)
    # recover sets; for cols that don't pin all 6 (a K6 fully inside cross has
    # all 15 pairs cross only if 6 parts -- impossible with 5 parts, so >=1 intra
    # edge: the two endpoints of an intra edge share a part and may be missing a
    # cross col connecting only to others -- but every vertex has cross pairs to
    # the other >=4 occupied parts, so the union of endpoints == the 6-set).
    from collections import defaultdict
    classw = defaultdict(float); classn = defaultdict(int)
    bad = 0
    for k, cols in enumerate(K):
        S = recover_set(cols)
        if len(S) != 6:
            bad += 1; continue
        sig = signature(S, E)
        classw[sig] += y[k]; classn[sig] += 1
    print(f"ATOM {name}: packing value = {val:.4f}  (support {int((y>1e-6).sum())}, recover-bad {bad})", flush=True)
    print(f"  {len(classw)} orbit-classes; weight per class:", flush=True)
    tot = 0.0
    for sig in sorted(classw, key=lambda s: -classw[s]):
        w = classw[sig]; n = classn[sig]; tot += w
        if w > 1e-4:
            print(f"    w={w:7.4f}  ({n:4d} K6s, {w/n:.4f} each)  type={sig}", flush=True)
    print(f"  total weight (symmetrized) = {tot:.4f}", flush=True)
