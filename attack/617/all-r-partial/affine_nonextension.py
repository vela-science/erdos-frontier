#!/usr/bin/env python3
"""Affine non-extension lemma (Erdős #617, disproof side), 2026-06-16.

LEMMA. The standard affine-plane balanced q-colouring of K_{q²} (q prime power;
q-1 singleton colours = one parallel class each, one doubleton colour = two
classes) cannot be extended to a balanced q-colouring of K_{q²+1} by adding one
vertex.  Proof: each singleton colour c forces its preimage f^{-1}(c) under the
new vertex's edge-colouring to hit every transversal of c's parallel class
(q blocks of size q), which forces it to contain a full line; two singleton
lines of different directions meet in a point needing two colours -- impossible
(q ≥ 3).  This kills the most obvious counterexample route (it does NOT prove
#617: not every balanced K_{q²} colouring is known to be affine, and this is
one-vertex extension only).

This script brute-force confirms the lemma for q=3 (the full claim, not just the
subclaim) and checks the transversal subclaim for q=2,3.

Run: python3 affine_nonextension.py
"""
from itertools import combinations, product

# AG(2,3): points (i,j) in Z3 x Z3; 4 parallel classes V,S0,S1,S2 -> colours
# {V:0, S0:1, S1:2, S2:2} (two singletons + one doubleton).
PTS = [(i, j) for i in range(3) for j in range(3)]
INV3 = {1: 1, 2: 2}
def _cls(a, b):
    (i1, j1), (i2, j2) = PTS[a], PTS[b]
    di = (i2 - i1) % 3
    return 'V' if di == 0 else f"S{((j2 - j1) * INV3[di]) % 3}"
_COL = {'V': 0, 'S0': 1, 'S1': 2, 'S2': 2}
def ecol(a, b): return _COL[_cls(a, b)]

if __name__ == "__main__":
    bal9 = all(len({ecol(a, b) for a, b in combinations(S, 2)}) == 3
               for S in combinations(range(9), 4))
    print("K_9 affine colouring balanced:", bal9)
    assert bal9

    triples = list(combinations(range(9), 3))
    tri = [{ecol(a, b) for a, b in combinations(T, 2)} for T in triples]
    found = next((f for f in product(range(3), repeat=9)
                  if all(len(tc | {f[t] for t in T}) == 3 for T, tc in zip(triples, tri))),
                 None)
    print(f"one-vertex balanced extension exists: {found is not None}  "
          f"(searched all 3^9 = {3**9})")
    assert found is None

    def sub(q):
        bad = 0
        for mask in range(1 << (q * q)):
            S = {(k // q, k % q) for k in range(q * q) if (mask >> k) & 1}
            hits = all(any((i, t[i]) in S for i in range(q)) for t in product(range(q), repeat=q))
            full = any(all((i, j) in S for j in range(q)) for i in range(q))
            bad += hits and not full
        return bad
    subs = [sub(q) for q in (2, 3)]
    print("transversal subclaim counterexamples (q=2,3):", subs)
    assert subs == [0, 0]
    print("OK -- affine K_9 does not extend to a balanced K_10.")
