"""Scope the machine residue for m* >= 66: how many configs actually need
full-spec CP-SAT, and how long do they take?  Free classification (no SAT)
+ a small timed sample.

Categories per walled config (cap = I+q-d > 13):
  HAND   : hand_bound(sizes,E) > cap  (clique/Case-A/Lemma-D; free)
  SPREAD : internal edges touch >= 3 parts  (the packing closes these; free)
  RESID  : concentrated (<= 2 active parts) and NOT hand-covered
           -> the machine residue (upper bound; some may still be packing-free)
"""
import sys, time, itertools, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617/artifacts/road66/handlemma")
import general_rung as G
from hand_coverage import hand_bound

SHAPES_BY_Q = {q: [s for s in G.shapes_for(q)] for q in (8, 9, 10)}


def active_parts(sizes, E):
    blocks, off = [], 0
    for n in sizes:
        blocks.append(set(range(off, off + n))); off += n
    parts = set()
    for a, b in E:
        for pi, blk in enumerate(blocks):
            if a in blk:
                parts.add(pi)
    return len(parts)


def census():
    resid_samples = []
    for q in (8, 9, 10):
        cnt = {"HAND": 0, "SPREAD": 0, "RESID": 0, "total": 0}
        for sizes in SHAPES_BY_Q[q]:
            d = G.defect(sizes)
            for I in range(sum(G.fmin(n) for n in sizes), q + 1):
                cap = I + q - d
                if cap <= 13:
                    continue
                for E in G.enumerate_configs(sizes, I):
                    cnt["total"] += 1
                    bnd, _ = hand_bound(sizes, E)
                    if bnd > cap:
                        cnt["HAND"] += 1
                    elif active_parts(sizes, E) >= 3:
                        cnt["SPREAD"] += 1
                    else:
                        cnt["RESID"] += 1
                        if len(resid_samples) < 12 and cap >= 16:
                            resid_samples.append((sizes, E, cap))
        print(f"q={q}: total walled {cnt['total']:5d} | HAND {cnt['HAND']:5d} "
              f"| SPREAD(packing) {cnt['SPREAD']:5d} | RESID(machine<=2parts) {cnt['RESID']:5d}",
              flush=True)
    return resid_samples


def sample_timing(samples):
    from ortools.sat.python import cp_model
    print(f"\n--- timing {len(samples)} residue configs (decision at cap, 12 workers, 1200s cap) ---", flush=True)
    times = []
    for sizes, E, cap in samples:
        m, h = G.build(sizes, E, cap)
        s = cp_model.CpSolver()
        s.parameters.max_time_in_seconds = 1200
        s.parameters.num_search_workers = 12
        t = time.time()
        st = s.StatusName(s.Solve(m))
        dt = time.time() - t
        times.append((st, dt))
        print(f"  {str(sizes)} cap={cap} active<=2: {st} in {dt:.0f}s", flush=True)
    inf = [dt for st, dt in times if st == "INFEASIBLE"]
    to = [dt for st, dt in times if st not in ("INFEASIBLE",)]
    print(f"\nsample: {len(inf)} solved (avg {sum(inf)/len(inf):.0f}s) "
          f"if any; {len(to)} timed out at 1200s", flush=True)


if __name__ == "__main__":
    print("=== free census (no SAT) ===", flush=True)
    samples = census()
    if "--time" in sys.argv:
        sample_timing(samples)
