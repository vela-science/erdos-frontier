#!/usr/bin/env python3
"""Independent full-spec checker for the Erdos #617 pass-20 hitset-pair
problem.  Takes a witness JSON (edge list + P + Q + case name) and verifies
every condition of the section-6 spec from scratch.  No pysat, no shared
code with the solver.

Usage: check_witness.py result_<case>.json
"""
import itertools, json, sys

N = 19
VS = range(N)


def main(path):
    data = json.load(open(path))
    if data['verdict'] != 'SAT':
        print(f"{path}: verdict={data['verdict']} — nothing to check")
        return
    E = set(tuple(sorted(e)) for e in data['witness'])
    P, Q = set(data['P']), set(data['Q'])
    case = path.split('result_')[1].split('.json')[0]
    adj = lambda a, b: (min(a, b), max(a, b)) in E
    ind = lambda S: not any(adj(a, b) for a, b in itertools.combinations(S, 2))
    ok = True

    def req(cond, msg):
        nonlocal ok
        print(('PASS' if cond else 'FAIL'), msg)
        ok = ok and cond

    req(len(E) == 40, f"L1 e(B)=40 (got {len(E)})")
    deg = {v: sum(1 for e in E if v in e) for v in VS}
    req(max(deg.values()) <= 6, f"L2 Delta<=6 (got {max(deg.values())})")
    req(all(not ind(S) for S in itertools.combinations(VS, 5)),
        "L3 alpha(B)<=4")
    worst6 = max(sum(adj(a, b) for a, b in itertools.combinations(S, 2))
                 for S in itertools.combinations(VS, 6))
    req(worst6 <= 11, f"L4 max edges on a 6-set = {worst6} <= 11")

    # L5: ~B K5-saturated == for every B-edge uv there is a 3-set T such that
    # T u {u,v} has no B-edge other than uv
    def sat_pair(u, v):
        others = [w for w in VS if w not in (u, v)]
        for T in itertools.combinations(others, 3):
            S = list(T) + [u, v]
            if not any(adj(a, b) and {a, b} != {u, v}
                       for a, b in itertools.combinations(S, 2)):
                return True
        return False
    req(all(sat_pair(u, v) for (u, v) in E), "L5 complement K5-saturated")

    # L6: no partition of V into <=4 B-cliques (exhaustive over part-assignments
    # via backtracking)
    def cover4():
        order = sorted(VS, key=lambda v: deg[v])
        parts = [[] for _ in range(4)]
        def bt(i):
            if i == N:
                return True
            v = order[i]
            seen_empty = False
            for p in parts:
                if not p:
                    if seen_empty:
                        return False
                    seen_empty = True
                if all(adj(v, u) for u in p):
                    p.append(v)
                    if bt(i + 1):
                        return True
                    p.pop()
            return False
        return bt(0)
    req(not cover4(), "L6 complement not 4-partite (no 4-clique-cover of B)")

    # L7: tau_4(B) = 4
    ind4 = [set(S) for S in itertools.combinations(VS, 4) if ind(S)]
    req(len(ind4) > 0, f"independent 4-sets exist ({len(ind4)})")
    tau4 = None
    for k in range(0, 5):
        if any(all(set(H) & S for S in ind4)
               for H in itertools.combinations(VS, k)):
            tau4 = k
            break
    req(tau4 == 4, f"L7 tau_4(B)={tau4} == 4")

    # Case conditions
    req(all(P & S for S in ind4), "P hits all independent 4-sets")
    req(all(Q & S for S in ind4), "Q hits all independent 4-sets")
    eP = sum(1 for a, b in itertools.combinations(sorted(P), 2) if adj(a, b))
    eQ = sum(1 for a, b in itertools.combinations(sorted(Q), 2) if adj(a, b))
    k = len(P & Q)
    if case == 'I':
        req(len(P) == 4 and len(Q) == 5, "case I sizes |P|=4,|Q|=5")
        req(k == 0, "case I: P,Q disjoint")
        ind3 = [set(S) for S in itertools.combinations(VS, 3) if ind(S)]
        req(all((P | Q) & S for S in ind3),
            "case I: P u Q hits all independent 3-sets")
        req(eQ <= 6, f"case I: e_B(Q)={eQ} <= 6")
    else:
        req(len(P) == 4 and len(Q) == 4, "case II sizes |P|=|Q|=4")
        req(eP + k <= 6, f"case II: e_B(P)+|PnQ| = {eP}+{k} <= 6")
        req(eQ + k <= 6, f"case II: e_B(Q)+|PnQ| = {eQ}+{k} <= 6")

    print("OVERALL:", "ALL CHECKS PASS" if ok else "CHECKS FAILED")
    return ok


if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1]) else 1)
