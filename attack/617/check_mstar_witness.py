#!/usr/bin/env python3
"""Independent checker for an m* probe witness (Erdos #617, r=5).

Input: edge-list file, one 'u v' pair per line, vertices 0..25.  Verifies
from scratch (no shared code with probe_mstar.py):

  (A) alpha(G) <= 5   — every 6-set of vertices spans at least one edge
  (B) every 6-set of vertices spans at most 11 edges

and reports e(G).  A verified witness with e(G) <= 65 proves m* <= 65,
i.e. the single-colour-class counting route to #617 r=5 cannot close.

Usage: check_mstar_witness.py witness.txt
"""
import itertools, sys

adj = [0] * 26
ne = 0
for line in open(sys.argv[1]):
    parts = line.split()
    if not parts:
        continue
    u, v = int(parts[0]), int(parts[1])
    assert 0 <= u < v < 26, (u, v)
    assert not (adj[u] >> v) & 1, f"duplicate edge {(u,v)}"
    adj[u] |= 1 << v
    adj[v] |= 1 << u
    ne += 1

badA = badB = 0
for S in itertools.combinations(range(26), 6):
    cnt = 0
    for i in range(6):
        for j in range(i + 1, 6):
            cnt += (adj[S[i]] >> S[j]) & 1
    if cnt == 0:
        badA += 1
        if badA <= 3:
            print("INDEPENDENT 6-SET", S)
    if cnt > 11:
        badB += 1
        if badB <= 3:
            print("OVERFULL 6-SET", S, cnt)

print(f"e(G) = {ne}; six-sets with no edge: {badA}; six-sets over 11 edges: {badB}")
ok = badA == 0 and badB == 0
print(("VERIFIED witness: m* <= %d" % ne) if ok else "INVALID witness")
sys.exit(0 if ok else 1)
