#!/usr/bin/env python3
"""Independent checker for a claimed balanced r-colouring of K_n
(Erdos #617 counterexample format): each line 'u v c' with 0<=u<v<n,
c in 0..r-1.  Verifies that every (r+1)-set of vertices sees all r colours.

Usage: check_balanced.py witness.txt [n] [r]
"""
import itertools, sys

path = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 26
r = int(sys.argv[3]) if len(sys.argv) > 3 else 5

col = {}
for line in open(path):
    u, v, c = map(int, line.split())
    assert 0 <= u < v < n and 0 <= c < r, (u, v, c)
    assert (u, v) not in col, f"duplicate edge {(u,v)}"
    col[(u, v)] = c
assert len(col) == n * (n - 1) // 2, f"missing edges: {len(col)}"

bad = 0
for S in itertools.combinations(range(n), r + 1):
    seen = set(col[e] for e in itertools.combinations(S, 2))
    if len(seen) < r:
        bad += 1
        if bad <= 5:
            print("BAD", S, sorted(seen))
print(f"n={n} r={r}: checked all {r+1}-sets; violations: {bad}")
print("BALANCED" if bad == 0 else "NOT BALANCED")
sys.exit(0 if bad == 0 else 1)
