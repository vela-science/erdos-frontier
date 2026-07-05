"""Parallel fixed-config rung runner for the (6,5,5,5,5) shape.

Uses the validated rung_general enumerators + full-spec build(), fans every
internal configuration across cores with a generous per-config time limit
(dense configs need ~600s, confirmed: I=6 cap=13 config is INFEASIBLE at
600s though UNKNOWN at 110s).  INFEASIBLE for all => (6,5,5,5,5) dead at
e(H)=270-q.  Any FEASIBLE => route caps.  Streams to a jsonl.

Usage: run_655_parallel.py q [time_limit] [workers_per] [concurrency]
"""
import sys, json, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import rung_general as R
from ortools.sat.python import cp_model

q   = int(sys.argv[1])
TL  = int(sys.argv[2]) if len(sys.argv) > 2 else 600
WK  = int(sys.argv[3]) if len(sys.argv) > 3 else 4
CC  = int(sys.argv[4]) if len(sys.argv) > 4 else 8

configs = []
for I in range(4, q + 1):
    cap = I + q
    for e0 in range(4, I + 1):
        k = I - e0
        if k > 3:
            continue
        for P0 in R.noniso_P0(e0):
            for fp in R.fivepart_dists(k):
                configs.append((list(P0) + list(fp), cap, I, e0, k))


def work(item):
    E, cap, I, e0, k = item
    t0 = time.time()
    built = R.build(E, cap)
    if built is None:
        return (E, cap, "SKIP", round(time.time() - t0))
    m, h = built
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = TL
    s.parameters.num_search_workers = WK
    st = s.StatusName(s.Solve(m))
    return (E, cap, st, round(time.time() - t0))


def main():
    print(f"(6,5,5,5,5) q={q}: {len(configs)} configs, TL={TL} WK={WK} CC={CC}", flush=True)
    out = open(f"artifacts/road66/rung_{q}_655_parallel.jsonl", "a")
    bad = 0; done = 0
    with ProcessPoolExecutor(max_workers=CC) as ex:
        futs = [ex.submit(work, c) for c in configs]
        for fut in as_completed(futs):
            E, cap, st, secs = fut.result()
            done += 1
            out.write(json.dumps({"E": E, "cap": cap, "status": st, "secs": secs}) + "\n")
            out.flush()
            if st not in ("INFEASIBLE", "SKIP"):
                bad += 1
                print(f"  [{st}] cap={cap} E={E} ({secs}s)"
                      + ("  <<< FEASIBLE — route caps!" if st in ("OPTIMAL", "FEASIBLE")
                         else "  <<< inconclusive"), flush=True)
            if done % 25 == 0:
                print(f"  ...{done}/{len(configs)} done, {bad} non-infeasible", flush=True)
    print(f"\nq={q} (6,5,5,5,5): {done} configs, {bad} non-infeasible. "
          + (f"ALL INFEASIBLE => contributes m* >= {56+q}" if bad == 0
             else "NOT all closed (see above)"), flush=True)


if __name__ == "__main__":
    main()
