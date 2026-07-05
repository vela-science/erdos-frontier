#!/usr/bin/env python3
"""Parallel sweep of (6,5,5,5,5) configs via the LB-oracle, finding the
true min-holes and the slack (min_holes - cap) at each rung q in {8,9,10}.

We compute min_holes ONCE per config (it does not depend on q); cap = I + q.
A config is killed at q iff min_holes >= cap+1 = I+q+1.
The WORST config at q is the one minimizing (min_holes - I) = (min_holes - I);
since cap-min_holes = I+q-min_holes, the config survives at q iff
min_holes <= I+q, i.e. min_holes - I <= q. So the critical quantity per
config is  SLACKBASE := min_holes - I.  Config killed at rung q iff
SLACKBASE >= q+1, i.e. min_holes - I > q.

Smallest SLACKBASE across all configs of the shape => the binding case.
If min(SLACKBASE) >= 11 then ALL configs killed through q=10. """
import sys, json, time, itertools
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617/artifacts/road66/handlemma")
import general_rung as G
from lb_oracle import lb_min_holes
from concurrent.futures import ProcessPoolExecutor, as_completed

SIZES = (6, 5, 5, 5, 5)
TL = int(sys.argv[2]) if len(sys.argv) > 2 else 90


def e_profile(E):
    parts = [list(range(0, 6)), list(range(6, 11)), list(range(11, 16)),
             list(range(16, 21)), list(range(21, 26))]
    po = {}
    for pi, P in enumerate(parts):
        for v in P:
            po[v] = pi
    ep = [0] * 5
    for a, b in E:
        if po[a] == po[b]:
            ep[po[a]] += 1
    return tuple(ep)


def work(item):
    idx, I, E = item
    t = time.time()
    name, val, lb, _ = lb_min_holes(SIZES, E, time_limit=TL, return_witness=False)
    return (idx, I, E, e_profile(E), name, val, lb, round(time.time() - t))


def main():
    I_target = int(sys.argv[1])
    cfgs = G.enumerate_configs(SIZES, I_target)
    items = [(i, I_target, E) for i, E in enumerate(cfgs)]
    print(f"(6,5,5,5,5) I={I_target}: {len(items)} configs, TL={TL}", flush=True)
    out = open(f"/Users/williamblair/personal/verified-combinatorics/erdos-617/"
               f"artifacts/road66/handlemma/sweep655_I{I_target}.jsonl", "w")
    worst = (99, None)
    done = 0
    with ProcessPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(work, it) for it in items]
        for fut in as_completed(futs):
            idx, I, E, ep, name, val, lb, secs = fut.result()
            done += 1
            rec = {"I": I, "E": E, "eprofile": ep, "status": name,
                   "min_holes": val, "lb": lb, "secs": secs}
            out.write(json.dumps(rec) + "\n"); out.flush()
            # SLACKBASE uses a VALID LOWER BOUND on min_holes:
            #  if status OPTIMAL: lb==val is exact.
            #  else: lb is a valid lower bound on min_holes -> use lb.
            mh_lb = lb if lb is not None else None
            if mh_lb is not None:
                sb = mh_lb - I
                if sb < worst[0]:
                    worst = (sb, (I, ep, name, val, lb))
            if done % 20 == 0:
                print(f"  ...{done}/{len(items)}  worst SLACKBASE so far={worst[0]} {worst[1]}", flush=True)
    print(f"\nI={I_target}: done. worst SLACKBASE(min_holes_lb - I) = {worst[0]} at {worst[1]}", flush=True)
    print(f"  => configs with this I killed through q < SLACKBASE; "
          f"need SLACKBASE>=11 for all-of-q<=10.", flush=True)


if __name__ == "__main__":
    main()
