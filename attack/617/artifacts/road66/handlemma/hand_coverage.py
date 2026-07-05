#!/usr/bin/env python3
"""Pure-combinatorial HAND-lemma coverage census (no SAT): for every
non-iso config of each walled shape at q=8,9,10, decide whether a HAND
lemma proves holes > cap. Reports the fraction covered by hand vs the
residue that needs the machine.

Hand lemmas applied (all rigorous, see LEMMAS.md):
 - Theorem A (Case A): (6,5,5,5,5) with internal edge in P0 and all four
   5-parts empty  => holes >= 26.
 - Triangle Lemma: a 5-part with a triangle and >=3 OTHER empty 5-parts
   => holes >= 15.
 - K4 Lemma: a part with K4 and >=2 other empty 5-parts => holes >= 9.
 - K5 Lemma: a part with K5 and >=1 other empty 5-part => holes >= 5.
 - 18-lemma (edge core): a P0-edge with all four 5-parts empty => 26 (subset
   of Case A; covered there).
A config is HAND-COVERED at rung q iff hand_bound > cap = I+q-d.
"""
import sys, itertools
sys.path.insert(0, "/Users/williamblair/personal/verified-combinatorics/erdos-617")
import general_rung as G
import networkx as nx


def part_blocks(sizes):
    blocks, off = [], 0
    for n in sizes:
        blocks.append(list(range(off, off + n))); off += n
    return blocks


def hand_bound(sizes, E):
    blocks = part_blocks(sizes); po = {}
    for pi, b in enumerate(blocks):
        for v in b:
            po[v] = pi
    Gi = {pi: nx.Graph() for pi in range(5)}
    for pi, b in enumerate(blocks):
        Gi[pi].add_nodes_from(b)
    e_in = [0] * 5
    for a, b in E:
        if po[a] == po[b]:
            Gi[po[a]].add_edge(a, b); e_in[po[a]] += 1
    bnd = 0
    INF = 9999  # "K6 forced" => infeasible at ANY cap
    if sizes == (6, 5, 5, 5, 5) and e_in[0] >= 1 and all(e_in[pi] == 0 for pi in range(1, 5)):
        bnd = max(bnd, 26)
    # ---- Lemma D (empty-4-part forces K6) ----
    # If some part P_a has an internal edge, AND among the OTHER parts there is
    # an empty 4-part, AND the remaining 3 parts are all empty 5-parts, then for
    # any edge uv in P_a the completion grid U_b over the other 4 parts has the
    # full empty 4-part as one coordinate (|U|=4, since outside vertices are
    # COMPLETE to an empty 4-part) and the three empty 5-parts give |U|>=3; by
    # Lemma B4 (max coord >=4 => UNBLOCKABLE) {u,v}+transversal is a K6. =>
    # INFEASIBLE at any cap.
    for pa in range(5):
        if e_in[pa] == 0:
            continue
        others = [pj for pj in range(5) if pj != pa]
        empty4 = [pj for pj in others if sizes[pj] == 4 and e_in[pj] == 0]
        empty5 = [pj for pj in others if sizes[pj] == 5 and e_in[pj] == 0]
        if empty4 and len(empty5) >= 3:
            bnd = max(bnd, INF)
    # ---- clique-core lemmas (Lemma C) over empty 5-part completions ----
    for pi in range(5):
        if Gi[pi].number_of_edges() == 0:
            continue
        cl = max((len(c) for c in nx.find_cliques(Gi[pi])), default=1)
        oth = sum(1 for pj in range(5) if pj != pi and sizes[pj] == 5 and e_in[pj] == 0)
        for t, val, need in [(5, 5, 1), (4, 9, 2), (3, 15, 3)]:
            if cl >= t and oth >= need:
                bnd = max(bnd, val); break
    return bnd, e_in


SHAPES = [(6, 5, 5, 5, 5), (6, 6, 5, 5, 4), (7, 5, 5, 5, 4),
          (8, 5, 5, 5, 3), (8, 5, 5, 4, 4), (7, 6, 5, 5, 3), (7, 6, 5, 4, 4)]

if __name__ == "__main__":
    import warnings; warnings.filterwarnings("ignore")
    for q in (8, 9, 10):
        print(f"\n========== rung q={q} ==========", flush=True)
        tot_cov = tot_all = 0
        for shape in SHAPES:
            d = G.defect(shape); fsum = sum(G.fmin(n) for n in shape)
            cov = all_ = 0
            residue_profiles = {}
            for I in range(fsum, q + 1):
                cap = I + q - d
                for E in G.enumerate_configs(shape, I):
                    all_ += 1
                    hb, ein = hand_bound(shape, E)
                    if hb > cap:
                        cov += 1
                    else:
                        key = (I, tuple(sorted(ein, reverse=True)))
                        residue_profiles[key] = residue_profiles.get(key, 0) + 1
            tot_cov += cov; tot_all += all_
            pct = (100 * cov / all_) if all_ else 100
            print(f"  {shape} d={d}: {cov}/{all_} hand-covered ({pct:.0f}%). "
                  f"residue by (I,eprofile): "
                  f"{dict(sorted(residue_profiles.items())[:6])}{' ...' if len(residue_profiles)>6 else ''}",
                  flush=True)
        print(f"  TOTAL q={q}: {tot_cov}/{tot_all} hand-covered "
              f"({100*tot_cov/tot_all:.0f}%); residue {tot_all-tot_cov} need machine.", flush=True)
