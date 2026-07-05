"""Fan out all (shape, rung) variable-internal models across cores.

For each rung q in 6..10 and each admissible Furedi shape, run the complete
variable-internal decision (ladder_engine.run_shape).  INFEASIBLE => that
shape contributes to killing rung q; SAT => a feasible witness (the route
caps below 56+q); TIMEOUT => inconclusive (hard model).

m* >= 66 (r=5 case of #617) iff every shape at every rung 6..10 is INFEASIBLE.
Results stream to artifacts/road66/ladder_parallel.jsonl as they finish.
"""
import sys, json, time
from concurrent.futures import ProcessPoolExecutor, as_completed
import ladder_engine as L

TL = int(sys.argv[1]) if len(sys.argv) > 1 else 2400     # per-model time limit
WK = int(sys.argv[2]) if len(sys.argv) > 2 else 4        # workers per model
CONC = int(sys.argv[3]) if len(sys.argv) > 3 else 8      # concurrent models

pairs = []
seen = set()
for q in range(6, 11):
    for shape in L.shapes_for_rung(q):
        if (shape, q) not in seen:
            seen.add((shape, q)); pairs.append((shape, q))
# easiest (smallest budget = I+q-d, hardest-to-be-feasible) first is not obvious;
# do lower q first (cheaper, fail-fast)
pairs.sort(key=lambda sq: (sq[1], sq[0]))


def work(shape, q):
    t0 = time.time()
    st, wit = L.run_shape(shape, q, time_limit=TL, workers=WK)
    return shape, q, st, (len(wit) if wit else None), round(time.time() - t0)


def main():
    print(f"{len(pairs)} (shape,rung) models; TL={TL}s WK={WK} CONC={CONC}", flush=True)
    out = open("artifacts/road66/ladder_parallel.jsonl", "a")
    with ProcessPoolExecutor(max_workers=CONC) as ex:
        futs = {ex.submit(work, s, q): (s, q) for (s, q) in pairs}
        for fut in as_completed(futs):
            shape, q, st, witn, secs = fut.result()
            rec = {"q": q, "m_star_ge": 56 + q, "shape": list(shape),
                   "status": st, "witness_edges": witn, "secs": secs}
            out.write(json.dumps(rec) + "\n"); out.flush()
            flag = ""
            if st in ("OPTIMAL", "FEASIBLE"):
                flag = "  <<< FEASIBLE — rung NOT killed, route caps at m*<%d" % (56 + q)
            elif st != "INFEASIBLE":
                flag = "  <<< %s (inconclusive)" % st
            print(f"[q={q} m*>= {56+q}] {str(shape):20s} {st} ({secs}s){flag}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
