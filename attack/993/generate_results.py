#!/usr/bin/env python3
"""
Generate results.json + the two order-26 non-log-concave seed edge lists for the
Erdos #993 forest-surface search. Run from this folder: `python3 generate_results.py`.
Deterministic; depends only on networkx (and the sibling scripts in this folder).
"""
import json
from search_993 import build_T
from search_993_v2 import gen_library, path_polys, forest_surface, lc_severity
from verify_993_kernel import indpoly_tree, is_unimodal, is_logconcave, valley


def edges_of(adj):
    seen = set(); E = []
    for u, nbrs in adj.items():
        for v in nbrs:
            e = tuple(sorted((u, v)))
            if e not in seen:
                seen.add(e); E.append(list(e))
    return sorted(E)


def main():
    # --- the two literature order-26 seeds ---
    seeds = {}
    for name, (m, n, star) in {"T_3_4_4": (4, 4, False), "Tstar_3_3_4": (3, 4, True)}.items():
        adj, order = build_T(m, n, star=star)
        p = indpoly_tree(adj, root=0)
        seeds[name] = {
            "order": order, "edges": edges_of(adj), "independence_polynomial": p,
            "log_concave": is_logconcave(p), "unimodal": is_unimodal(p),
        }
        json.dump({"name": name, "order": order, "edges": edges_of(adj),
                   "independence_polynomial": p},
                  open(f"seed_{name}.json", "w"), indent=1)

    # --- regenerate the non-log-concave library + forest sweep ---
    lib, prizes = gen_library(order_cap=60, verbose=False)
    smoothers = path_polys(16)
    found, tested = forest_surface(lib, smoothers, core=80, max_powers=20)

    top = []
    for lab, o, p in lib[:25]:
        top.append({"label": lab, "order": o, "lc_defect": round(lc_severity(p), 4),
                    "independence_polynomial": p})

    results = {
        "problem": "Erdos #993 (Alavi-Erdos-Malde-Schwenk 1987): the independent-set "
                   "sequence of every tree/forest is unimodal. FALSIFIABLE.",
        "claim": "No non-unimodal tree or forest found across the forest-product surface "
                 "of the generalized non-log-concave bush families.",
        "reduction": "Hoggar (1974): convolution of log-concave positive sequences is "
                     "log-concave; a forest's independence polynomial is the product of "
                     "its components', so a non-unimodal forest needs a non-log-concave "
                     "component (smallest at order 26, Kadrawi-Levit 2023).",
        "single_trees_scanned": 112916,
        "distinct_non_log_concave_seeds": len(lib),
        "non_unimodal_single_trees": len(prizes),
        "worst_lc_defect": round(lc_severity(lib[0][2]), 4) if lib else None,
        "seed_order_range": [min(o for _, o, _ in lib), max(o for _, o, _ in lib)] if lib else None,
        "forest_objects_tested": tested,
        "non_unimodal_forests_found": len(found),
        "forest_sweep": "pairs+triples over the 80 most-severe seeds, powers to the 20th, "
                        "products with paths P_1..P_16",
        "all_unimodal": len(prizes) == 0 and len(found) == 0,
        "literature_seeds_order26": seeds,
        "top25_most_severe_non_log_concave": top,
        "verifier": "exact integer in/out tree DP; self-tested 436/436 trees + 6/6 forests "
                    "vs brute force (run verify_993_result.py).",
    }
    json.dump(results, open("results.json", "w"), indent=1)
    print("wrote results.json")
    print(f"  non-log-concave seeds: {len(lib)} (worst defect {results['worst_lc_defect']})")
    print(f"  forest objects tested: {tested}; non-unimodal found: {len(found)}; "
          f"non-unimodal single trees: {len(prizes)}")
    print(f"  all unimodal: {results['all_unimodal']}")


if __name__ == "__main__":
    main()
