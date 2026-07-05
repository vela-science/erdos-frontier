#!/usr/bin/env python3
"""Comprehensive v3-LB sweep over the walled families.

For each (shape, I) and each non-iso internal config, compute lb3's dual LB
on min-holes. The config is KILLED at rung q iff lb3_LB > cap = I + q - d.
Since lb3_LB <= true_min_holes (valid relaxation), lb3_LB > cap proves the
full spec INFEASIBLE -> config killed.

We compute lb3_LB ONCE per config; the per-config "kill threshold" is
  qmax_killed(config) = lb3_LB - I + d - 1     [killed for all q <= this]
(because killed at q iff lb3_LB - I + d > q).
A config is closed for the whole road to 66 iff qmax_killed >= 10.

Output per config: shape, E, I, lb3_LB, qmax_killed, and a FLAG if
qmax_killed < 10 (i.e. NOT closed through q=10 by v3 at this time budget).

Usage: sweep_v3.py SHAPE I_lo I_hi [TL] [conc_k] [workers] [conc_procs]
  SHAPE like 6,5,5,5,5 ; runs I in [I_lo, I_hi].
"""
import sys, json, time, itertools
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617/artifacts/road66/handlemma")
import general_rung as G
from lb_oracle3 import lb3
from concurrent.futures import ProcessPoolExecutor, as_completed


def work(item):
    sizes, E, I, ck, tl, wk = item
    t = time.time()
    st, val, lb, _ = lb3(sizes, E, conc_k=ck, time_limit=tl, workers=wk)
    return (sizes, E, I, st, val, lb, round(time.time() - t))


def main():
    shape = tuple(int(x) for x in sys.argv[1].split(","))
    I_lo, I_hi = int(sys.argv[2]), int(sys.argv[3])
    TL = int(sys.argv[4]) if len(sys.argv) > 4 else 120
    CK = int(sys.argv[5]) if len(sys.argv) > 5 else 4
    WK = int(sys.argv[6]) if len(sys.argv) > 6 else 2
    CC = int(sys.argv[7]) if len(sys.argv) > 7 else 7
    d = G.defect(shape)
    tag = "".join(str(x) for x in shape)
    out = open(f"/Users/williamblair/personal/verified-combinatorics/erdos-617/"
               f"artifacts/road66/handlemma/v3sweep_{tag}.jsonl", "a")
    items = []
    for I in range(I_lo, I_hi + 1):
        for E in G.enumerate_configs(shape, I):
            items.append((shape, E, I, CK, TL, WK))
    print(f"v3 sweep shape={shape} d={d} I in [{I_lo},{I_hi}]: {len(items)} configs, "
          f"TL={TL} CK={CK} WK={WK} CC={CC}", flush=True)
    worst = (99, None)   # smallest qmax_killed
    done = 0
    with ProcessPoolExecutor(max_workers=CC) as ex:
        futs = [ex.submit(work, it) for it in items]
        for fut in as_completed(futs):
            sizes, E, I, st, val, lb, secs = fut.result(); done += 1
            qmax = (lb - I + d - 1) if lb is not None else None
            rec = {"shape": list(sizes), "I": I, "E": E, "status": st,
                   "relax_min": val, "lb": lb, "qmax_killed": qmax, "secs": secs}
            out.write(json.dumps(rec) + "\n"); out.flush()
            if qmax is not None and qmax < worst[0]:
                worst = (qmax, {"I": I, "lb": lb, "E": E, "st": st})
            if qmax is None or qmax < 10:
                print(f"  [NOT closed thru q=10] I={I} lb={lb} qmax_killed={qmax} "
                      f"st={st} E={E} ({secs}s)", flush=True)
            if done % 25 == 0:
                print(f"  ...{done}/{len(items)} worst qmax_killed={worst[0]}", flush=True)
    print(f"\nshape {shape} I in [{I_lo},{I_hi}]: done {done}. "
          f"worst qmax_killed = {worst[0]} at {worst[1]}", flush=True)
    print(f"  => {'ALL closed through q=10' if worst[0] >= 10 else 'NOT all closed (see flags)'}", flush=True)


if __name__ == "__main__":
    main()
