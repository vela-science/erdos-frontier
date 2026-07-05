"""Two-pass q=10 sweep for Erdos #617 m* >= 66 (2026-06-15).

Reuses general_rung's trusted encoding (build / enumerate_configs) verbatim --
soundness is identical to the rung-62-validated engine.  The only additions are
(a) a cheap first pass that clears the easy majority at low workers, then a
second pass that concentrates all workers on the survivors, and (b) resumable
JSONL + a hard FEASIBLE tripwire (a single satisfiable config would DISPROVE
m* >= 66, so it is logged to a separate CRITICAL file and printed loudly).

q=10 is the binding rung: closing it (every walled config INFEASIBLE at
cap = I + q - d) closes q=8,9 too, giving m* >= 66 and the r=5 solve.

Usage:
  python3 sweep66.py enumerate                 # build + cache the config list
  python3 sweep66.py run [shape] [P1_TL P1_WK P1_CC] [P2_TL P2_WK P2_CC]
Defaults: P1 = 60s/4w/CC=cores//4 ; P2 = 900s/AllCores/CC=1 .
"""
import sys, os, json, time, pickle, itertools, hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed
sys.argv_backup = sys.argv
sys.argv = ['x']                       # neutralize engine __main__ parsing
import general_rung as G
from ortools.sat.python import cp_model
sys.argv = sys.argv_backup

Q = 10
ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts", "road66")
os.makedirs(ART, exist_ok=True)
CACHE = os.path.join(ART, f"configs_q{Q}.pkl")
RESULTS = os.path.join(ART, f"sweep_q{Q}.jsonl")
CRITICAL = os.path.join(ART, f"FEASIBLE_q{Q}.jsonl")


def ckey(sizes, E, cap):
    payload = json.dumps([list(sizes), sorted(map(list, E)), cap], sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()


def enumerate_all():
    """All q=10 configs across every machine-tractable shape, cached."""
    targets = G.shapes_for(Q)
    items = []
    t0 = time.time()
    for sizes in targets:
        d = G.defect(sizes)
        lo = sum(G.fmin(n) for n in sizes)
        for I in range(lo, Q + 1):
            cap = I + Q - d
            for E in G.enumerate_configs(sizes, I):
                items.append((tuple(sizes), [tuple(e) for e in E], cap))
        print(f"  {sizes}: cumulative {len(items)} ({time.time()-t0:.0f}s)", flush=True)
    pickle.dump(items, open(CACHE, "wb"))
    print(f"enumerated {len(items)} q={Q} configs across {len(targets)} shapes "
          f"in {time.time()-t0:.0f}s -> {CACHE}", flush=True)
    return items


def solve(sizes, E, cap, tl, wk):
    built = G.build(list(sizes), E, cap)
    if built is None:
        return ("SKIP", 0.0)
    m, h = built
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = tl
    s.parameters.num_search_workers = wk
    s.parameters.symmetry_level = 4          # max symmetry (sound; no added constraints)
    t0 = time.time()
    st = s.StatusName(s.Solve(m))
    return (st, round(time.time() - t0, 1))


def _worker(args):
    sizes, E, cap, tl, wk = args
    st, secs = solve(sizes, E, cap, tl, wk)
    return (sizes, E, cap, st, secs)


def load_done():
    done = {}
    if os.path.exists(RESULTS):
        for ln in open(RESULTS):
            try:
                r = json.loads(ln)
            except Exception:
                continue
            done[r["key"]] = r["status"]
    return done


def run_pass(items, tl, wk, cc, label, out):
    """Solve items; return list of (sizes,E,cap) that are not yet INFEASIBLE/SKIP."""
    survivors, feas = [], []
    n = len(items)
    done = 0
    with ProcessPoolExecutor(max_workers=cc) as ex:
        futs = {ex.submit(_worker, (s, E, c, tl, wk)): (s, E, c) for (s, E, c) in items}
        for fut in as_completed(futs):
            sizes, E, cap, st, secs = fut.result()
            done += 1
            rec = {"key": ckey(sizes, E, cap), "shape": list(sizes), "E": [list(e) for e in E],
                   "cap": cap, "status": st, "secs": secs, "pass": label}
            out.write(json.dumps(rec) + "\n"); out.flush()
            if st in ("OPTIMAL", "FEASIBLE"):
                feas.append((sizes, E, cap))
                with open(CRITICAL, "a") as cf:
                    cf.write(json.dumps(rec) + "\n")
                print(f"  <<<<<< FEASIBLE!! {sizes} cap={cap} E={E}  ({secs}s) "
                      f"-- m*>=66 WOULD BE FALSE, STOP", flush=True)
            elif st not in ("INFEASIBLE", "SKIP"):
                survivors.append((sizes, E, cap))
            if done % 100 == 0:
                print(f"  [{label}] {done}/{n}  survivors={len(survivors)} feas={len(feas)}", flush=True)
    return survivors, feas


def run(shape_filter=None, p1=(60, 4, None), p2=(900, None, 1)):
    cores = os.cpu_count() or 8
    items = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else enumerate_all()
    if shape_filter:
        items = [it for it in items if it[0] == shape_filter]
    done = load_done()
    todo = [it for it in items if done.get(ckey(*it)) not in ("INFEASIBLE", "SKIP")]
    print(f"total={len(items)} already_infeasible={len(items)-len(todo)} todo={len(todo)}", flush=True)
    p1_tl, p1_wk, p1_cc = p1[0], p1[1], (p1[2] or max(1, cores // p1[1]))
    p2_tl, p2_wk, p2_cc = p2[0], (p2[1] or cores), p2[2]
    out = open(RESULTS, "a")
    t0 = time.time()
    print(f"=== PASS 1: TL={p1_tl} WK={p1_wk} CC={p1_cc} on {len(todo)} ===", flush=True)
    survivors, feas1 = run_pass(todo, p1_tl, p1_wk, p1_cc, "p1", out)
    print(f"pass1 done in {time.time()-t0:.0f}s: survivors={len(survivors)} feasible={len(feas1)}", flush=True)
    feas2, still = [], []
    if survivors:
        print(f"=== PASS 2: TL={p2_tl} WK={p2_wk} CC={p2_cc} on {len(survivors)} ===", flush=True)
        still, feas2 = run_pass(survivors, p2_tl, p2_wk, p2_cc, "p2", out)
        print(f"pass2 done: still_unknown={len(still)} feasible={len(feas2)}", flush=True)
        if still:
            print(f"  !!! {len(still)} configs STILL UNKNOWN after pass2 -- need more time:", flush=True)
            for s, E, c in still[:20]:
                print(f"     {s} cap={c} E={E}", flush=True)
    feas = feas1 + feas2
    out.close()
    print(f"\n=== SWEEP q={Q} {'['+str(shape_filter)+']' if shape_filter else 'ALL'} "
          f"in {time.time()-t0:.0f}s ===", flush=True)
    if feas:
        print(f"  *** {len(feas)} FEASIBLE configs -- m*>=66 IS FALSE. See {CRITICAL}", flush=True)
    elif still:
        print("  INCOMPLETE: some configs unresolved (UNKNOWN). Re-run pass2 with more time.", flush=True)
    else:
        print(f"  ALL RESOLVED INFEASIBLE -> rung q={Q} closed -> m* >= 66 (for swept shapes).", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "enumerate":
        enumerate_all()
    elif cmd == "run":
        shp = None
        rest = sys.argv[2:]
        if rest and "," in rest[0]:
            shp = tuple(int(x) for x in rest[0].split(",")); rest = rest[1:]
        p1 = tuple(int(x) for x in rest[0:3]) if len(rest) >= 3 else (60, 4, None)
        p2 = tuple(int(x) for x in rest[3:6]) if len(rest) >= 6 else (900, None, 1)
        run(shp, p1, p2)
