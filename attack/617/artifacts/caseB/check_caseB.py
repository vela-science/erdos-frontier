"""Independent checker: rebuild H from (config, holes) and verify from scratch:
   - e(H) = 275 - |holes|
   - every 6-set spans >= 4 edges
   - no K6 (every 6-set spans <= 14 edges)
Bitset adjacency; no code shared with the CP-SAT model beyond vertex labels.
"""
import sys, json
from itertools import combinations

def main(path):
    with open(path) as f:
        data = json.load(f)
    config = [tuple(e) for e in data["config"]]
    part_edges = [tuple(e) for e in data.get("part_edges", [(6,7)])]
    holes = {tuple(sorted(e)) for e in data["holes"]}
    parts = [list(range(0,6)), list(range(6,11)), list(range(11,16)),
             list(range(16,21)), list(range(21,26))]
    pof = {}
    for i,P in enumerate(parts):
        for v in P: pof[v] = i
    internal = {tuple(sorted(e)) for e in config} | {tuple(sorted(e)) for e in part_edges}
    nI = len(internal)
    adj = [0]*26
    edges = 0
    for a,b in combinations(range(26),2):
        e = (a,b)
        if pof[a] != pof[b]:
            present = e not in holes
        else:
            present = e in internal
        if present:
            adj[a] |= 1<<b; adj[b] |= 1<<a; edges += 1
    print(f"e(H) = {edges}, holes = {len(holes)}, internal = {nI}")
    assert edges == 270 + nI - len(holes)
    min_e, max_e = 99, -1
    bad_lo = bad_hi = 0
    for S in combinations(range(26),6):
        cnt = 0
        for i in range(6):
            a = S[i]
            for j in range(i+1,6):
                if adj[a] >> S[j] & 1: cnt += 1
        if cnt < min_e: min_e = cnt
        if cnt > max_e: max_e = cnt
        if cnt < 4: bad_lo += 1
        if cnt == 15: bad_hi += 1
    print(f"6-set edge range: [{min_e},{max_e}]  violations: <4: {bad_lo}, K6: {bad_hi}")
    ok = bad_lo == 0 and bad_hi == 0
    print("VALID Case-B H" if ok else "INVALID")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
