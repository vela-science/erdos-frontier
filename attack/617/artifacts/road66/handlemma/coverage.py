#!/usr/bin/env python3
"""Coverage map: for a stratified sample of configs across the walled
shapes, report whether each is closed through q=10, and BY WHICH tool:
  HAND   : a hand lemma certifies it (Case A; triangle/K4/K5 core).
  LB3    : lb3's dual LB > cap for all q<=10 (machine sub-model, valid).
  FULL   : only the full-spec machine decides it (lb3 dual stalls).
  OPEN   : neither lb3 nor (within budget) full-spec resolves -> residue.

For each sampled config we compute:
  - hand_bound: max of applicable hand-lemma bounds (26 if Case A; 15 if a
    5-part triangle + >=3 empty others; 9 if K4 +>=2 empty; 5 if K5 +>=1).
  - lb3_LB (dual), with a generous TL.
  - cap(q) = I + q - d.
Closed-through-q10 iff hand_bound > I+10-d OR lb3_LB > I+10-d.

Usage: coverage.py SHAPE I_lo I_hi [TL] [n_sample_per_I] [workers] [procs]
"""
import sys, json, time, itertools, random
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617/artifacts/road66/handlemma")
import general_rung as G
import networkx as nx
from lb_oracle3 import lb3
from concurrent.futures import ProcessPoolExecutor, as_completed


def part_blocks(sizes):
    blocks, off = [], 0
    for n in sizes:
        blocks.append(list(range(off, off + n))); off += n
    return blocks


def analyze_hand(sizes, E):
    """Return the strongest applicable HAND-lemma lower bound on holes."""
    blocks = part_blocks(sizes)
    part_of = {}
    for pi, b in enumerate(blocks):
        for v in b:
            part_of[v] = pi
    # per-part internal graph
    Gi = {pi: nx.Graph() for pi in range(5)}
    for pi, b in enumerate(blocks):
        Gi[pi].add_nodes_from(b)
    e_in = [0] * 5
    for a, b in E:
        if part_of[a] == part_of[b]:
            Gi[part_of[a]].add_edge(a, b); e_in[part_of[a]] += 1
    # Case A: all internal edges in part 0 AND part0 is the (unique) big part?
    # Theorem A is for (6,5,5,5,5) with empty 5-parts. Generalize: if every
    # 5-part is empty and there is an internal edge in the 6-part with the four
    # 5-parts empty -> 26. We apply only for (6,5,5,5,5).
    bound = 0
    empty5 = [pi for pi in range(5) if sizes[pi] == 5 and e_in[pi] == 0]
    if sizes == (6, 5, 5, 5, 5) and e_in[0] >= 1 and all(e_in[pi] == 0 for pi in range(1, 5)):
        bound = max(bound, 26)
    # clique cores in any part with enough OTHER empty 5-parts
    for pi in range(5):
        if Gi[pi].number_of_edges() == 0:
            continue
        # largest clique in this part
        cl = max((len(c) for c in nx.find_cliques(Gi[pi])), default=1)
        others_empty = sum(1 for pj in range(5) if pj != pi and sizes[pj] == 5 and e_in[pj] == 0)
        # core K_t needs 6-t completion vertices; if >= (6-t) of the OTHER parts
        # are empty 5-parts, the all-empty completion table applies.
        for t, val, need in [(5, 5, 1), (4, 9, 2), (3, 15, 3)]:
            if cl >= t and others_empty >= need:
                bound = max(bound, val)
                break
    return bound, e_in


def work(item):
    sizes, E, I, d, ck, tl, wk = item
    hand, e_in = analyze_hand(sizes, E)
    t = time.time()
    st, val, lb, _ = lb3(sizes, E, conc_k=ck, time_limit=tl, workers=wk)
    secs = round(time.time() - t)
    cap10 = I + 10 - d
    closed_hand = hand > cap10
    closed_lb3 = (lb is not None and lb > cap10)
    return (sizes, E, I, tuple(e_in), hand, st, val, lb, cap10,
            closed_hand, closed_lb3, secs)


def main():
    shape = tuple(int(x) for x in sys.argv[1].split(","))
    I_lo, I_hi = int(sys.argv[2]), int(sys.argv[3])
    TL = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    NS = int(sys.argv[5]) if len(sys.argv) > 5 else 40
    WK = int(sys.argv[6]) if len(sys.argv) > 6 else 2
    CC = int(sys.argv[7]) if len(sys.argv) > 7 else 7
    d = G.defect(shape)
    tag = "".join(str(x) for x in shape)
    random.seed(12345)
    items = []
    for I in range(I_lo, I_hi + 1):
        cfgs = G.enumerate_configs(shape, I)
        # stratify: ensure we include the most concentrated configs (max single
        # e_in) AND a random sample.
        def maxe(E):
            blocks = part_blocks(shape); po = {}
            for pi, b in enumerate(blocks):
                for v in b:
                    po[v] = pi
            ein = [0]*5
            for a, b in E:
                if po[a] == po[b]:
                    ein[po[a]] += 1
            return max(ein)
        cfgs_sorted = sorted(cfgs, key=maxe, reverse=True)
        chosen = cfgs_sorted[:NS//2]  # most concentrated
        rest = cfgs_sorted[NS//2:]
        if rest:
            chosen += random.sample(rest, min(NS - len(chosen), len(rest)))
        for E in chosen:
            items.append((shape, E, I, d, 4, TL, WK))
    out = open(f"/Users/williamblair/personal/verified-combinatorics/erdos-617/"
               f"artifacts/road66/handlemma/coverage_{tag}.jsonl", "a")
    print(f"coverage shape={shape} d={d} I in [{I_lo},{I_hi}]: {len(items)} sampled "
          f"configs, TL={TL} NS={NS}", flush=True)
    nclosed = nopen = 0; opens = []
    with ProcessPoolExecutor(max_workers=CC) as ex:
        futs = [ex.submit(work, it) for it in items]
        for fut in as_completed(futs):
            (sizes, E, I, ein, hand, st, val, lb, cap10,
             ch, cl, secs) = fut.result()
            closed = ch or cl
            tool = "HAND" if ch else ("LB3" if cl else "OPEN")
            rec = {"shape": list(sizes), "I": I, "eprofile": list(ein), "E": E,
                   "hand": hand, "lb3_status": st, "lb3_min": val, "lb3_LB": lb,
                   "cap_q10": cap10, "closed_through_q10": closed, "tool": tool,
                   "secs": secs}
            out.write(json.dumps(rec) + "\n"); out.flush()
            if closed:
                nclosed += 1
            else:
                nopen += 1
                opens.append((I, list(ein), lb, cap10))
                print(f"  [OPEN] I={I} eprofile={list(ein)} hand={hand} "
                      f"lb3_LB={lb} cap_q10={cap10} ({secs}s) E={E}", flush=True)
    print(f"\nshape {shape}: {nclosed} closed-through-q10, {nopen} OPEN (sampled).", flush=True)
    if opens:
        print("OPEN profiles:", opens, flush=True)


if __name__ == "__main__":
    main()
