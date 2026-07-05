#!/usr/bin/env python3
"""road66_check.py — independent, from-scratch verifier for a road66 witness.

Reads a JSON {size_vector, internal_edges, holes} (the latter two as lists of
[a,b] pairs on labels 0..25 laid out left-to-right by size_vector) and rebuilds
H, then checks WITHOUT any code shared with the CP-SAT model:
  * cross pairs are partitioned: each cross pair is present unless it is a hole
  * internal pairs are present iff listed in internal_edges
  * e(H) = cross_pairs - holes + internal_edges
  * EVERY 6-subset of the 26 vertices spans >= 4 edges of H   (the real cond.)
  * NO K6: no 6-subset spans all 15 pairs
Prints the 6-set edge-count range and PASS/FAIL.  Usage: road66_check.py x.json
"""
import sys, json
from itertools import combinations
from math import comb


def parts_from_vector(nv):
    parts, k = [], 0
    for n in nv:
        parts.append(list(range(k, k + n)))
        k += n
    assert k == 26
    pof = {}
    for i, P in enumerate(parts):
        for v in P:
            pof[v] = i
    return parts, pof


def main(path):
    with open(path) as f:
        data = json.load(f)
    nv = tuple(data["size_vector"])
    holes = {tuple(sorted(e)) for e in data["holes"]}
    internal = {tuple(sorted(e)) for e in data.get("internal_edges", [])}
    parts, pof = parts_from_vector(nv)

    # sanity: every internal edge is within a part; every hole is cross
    for (a, b) in internal:
        assert pof[a] == pof[b], f"internal edge {(a,b)} crosses parts!"
    for (a, b) in holes:
        assert pof[a] != pof[b], f"hole {(a,b)} is not a cross pair!"

    cross_pairs = sum(len(parts[i]) * len(parts[j])
                      for i in range(5) for j in range(i + 1, 5))
    adj = [0] * 26
    edges = 0
    for a, b in combinations(range(26), 2):
        if pof[a] != pof[b]:
            present = (a, b) not in holes
        else:
            present = (a, b) in internal
        if present:
            adj[a] |= 1 << b
            adj[b] |= 1 << a
            edges += 1

    exp = cross_pairs - len(holes) + len(internal)
    print(f"size_vector = {nv}")
    print(f"cross_pairs = {cross_pairs}, holes = {len(holes)}, "
          f"internal_edges = {len(internal)}")
    print(f"e(H) = {edges}  (expected {exp})")
    assert edges == exp, "edge count mismatch"

    min_e, max_e = 99, -1
    bad_lo = bad_hi = 0
    for S in combinations(range(26), 6):
        cnt = 0
        for i in range(6):
            ai = S[i]
            row = adj[ai]
            for j in range(i + 1, 6):
                cnt += (row >> S[j]) & 1
        if cnt < min_e:
            min_e = cnt
        if cnt > max_e:
            max_e = cnt
        if cnt < 4:
            bad_lo += 1
        if cnt == 15:
            bad_hi += 1
    print(f"6-set edge range: [{min_e},{max_e}]  "
          f"violations: (<4): {bad_lo}, (K6=15): {bad_hi}")
    ok = (bad_lo == 0 and bad_hi == 0)
    print("VALID H (K6-free, every 6-set >= 4)" if ok else "INVALID")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
