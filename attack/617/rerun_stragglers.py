"""Re-run the UNKNOWN (timed-out) configs from a rung sweep at a long limit.

The dense (cap=14, I=7) configs of rung 63 are INFEASIBLE but need ~2400s
(confirmed: one cap=14 config INFEASIBLE at 2400s, was UNKNOWN at 600s).
This collects every status=UNKNOWN config from the sweep jsonl and re-runs
it at the long limit, fanned out.  All INFEASIBLE => those stragglers
close => rung fully closed.

Usage: rerun_stragglers.py <sweep.jsonl> [time_limit=2400] [workers=4] [conc=8]
"""
import sys, json, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import rung_general as R
from ortools.sat.python import cp_model

JSONL = sys.argv[1]
TL = int(sys.argv[2]) if len(sys.argv) > 2 else 2400
WK = int(sys.argv[3]) if len(sys.argv) > 3 else 4
CC = int(sys.argv[4]) if len(sys.argv) > 4 else 8

stragglers = []
for line in open(JSONL):
    rec = json.loads(line)
    if rec["status"] not in ("INFEASIBLE", "SKIP"):
        stragglers.append((tuple(map(tuple, rec["E"])), rec["cap"]))
stragglers = list(dict.fromkeys(stragglers))   # dedupe, keep order


def work(item):
    E, cap = item
    t0 = time.time()
    built = R.build([tuple(e) for e in E], cap)
    if built is None:
        return (E, cap, "SKIP", 0)
    m, h = built
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = TL
    s.parameters.num_search_workers = WK
    st = s.StatusName(s.Solve(m))
    return (E, cap, st, round(time.time() - t0))


def main():
    print(f"{len(stragglers)} stragglers from {JSONL}; TL={TL} WK={WK} CC={CC}", flush=True)
    bad = 0
    with ProcessPoolExecutor(max_workers=CC) as ex:
        futs = [ex.submit(work, s) for s in stragglers]
        for fut in as_completed(futs):
            E, cap, st, secs = fut.result()
            tag = "INFEASIBLE" if st == "INFEASIBLE" else st
            if st not in ("INFEASIBLE", "SKIP"):
                bad += 1
                print(f"  [{st}] cap={cap} E={list(E)} ({secs}s)"
                      + ("  <<< FEASIBLE — route caps!" if st in ("OPTIMAL", "FEASIBLE")
                         else "  <<< STILL hard at %ds" % TL), flush=True)
            else:
                print(f"  [INFEASIBLE] cap={cap} ({secs}s)", flush=True)
    print(f"\n{len(stragglers)} stragglers: {bad} not closed. "
          + ("ALL INFEASIBLE => rung closes" if bad == 0 else "some still open"), flush=True)


if __name__ == "__main__":
    main()
