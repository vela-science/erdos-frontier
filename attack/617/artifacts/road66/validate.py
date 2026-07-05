#!/usr/bin/env python3
"""validate.py — reproduce the known facts before trusting any new result.

(1) Case A: (6,5,5,5,5), all 5-parts empty, I=4 internal edges pinned into P0.
    Claim (18-lemma): min_holes >= 26.  At e(H)=264 (q=6, I=4) budget=10, and
    at e(H)=265 (q=5,I=4) budget=9 -> INFEASIBLE either way (26 >> 10).
    We compute min_holes exactly (free P0 4-edge structure, 5-parts forced
    empty) and also a decision at budget 10.
(2) Case B: (6,5,5,5,5), I=5 = 4-edge P0 config + one edge in a 5-part, at
    q=5 (budget = 5+5-0 = 10).  Claim: INFEASIBLE.  We use the FREE-internal
    model with I=5 and check the decision at budget 10 (this is STRONGER than
    Case B: it lets the solver place all 5 edges anywhere, including all in P0).
    To match Case B exactly we also pin one edge into P1.
(3) (7,5,5,5,4) at q=6, I=6: report exact min_holes vs budget 10.  Settles
    whether m* >= 62 closes on the hard shape.

Run: validate.py <which>   where which in {A, A_pin, B, B_pin, 7554, all_fast}
"""
import sys, json, time
from itertools import combinations
sys.path.insert(0, ".")
import road66_engine as E


def case_A_pinned(time_limit=1200, workers=8):
    """(6,5,5,5,5), 4 internal edges all in P0 (5-parts empty), min holes."""
    nv = (6, 5, 5, 5, 5)
    classified = E.classify_pairs(nv)
    cross, cidx, internal, iidx, part_of = classified
    six = E.precompute_sixsets(part_of, cidx, iidx)
    # P0 = {0..5}; force all internal edges inside P0 by pinning every internal
    # pair NOT in P0 to absent, and letting the 6 P0-pairs be free with sum==4.
    # Easiest: use free-internal but add constraint that internal edges outside
    # P0 are zero.  We do this via a custom build.
    cap = E.cross_pairs(nv)
    m, h, b, cross, internal, stats = E.build_model(
        nv, I=4, hole_cap=cap, model_cap=cap, six_data=six, classified=classified)
    P0 = set(range(6))
    for e, idx in iidx.items():
        a, c = e
        if not (a in P0 and c in P0):
            m.Add(b[idx] == 0)          # all internal edges live in P0
    out = E.solve_model(m, h, b, cross, internal, minimize=True,
                        time_limit=time_limit, workers=workers)
    out["stats"] = stats
    return nv, 4, out


def case_A_decision(q, time_limit=900, workers=8):
    """Decision at budget(q,4) for Case A (5-parts empty)."""
    nv = (6, 5, 5, 5, 5)
    classified = E.classify_pairs(nv)
    cross, cidx, internal, iidx, part_of = classified
    six = E.precompute_sixsets(part_of, cidx, iidx)
    bud = E.budget(q, 4, nv)
    m, h, b, cross, internal, stats = E.build_model(
        nv, I=4, hole_cap=bud, model_cap=bud + 1, six_data=six, classified=classified)
    P0 = set(range(6))
    for e, idx in iidx.items():
        a, c = e
        if not (a in P0 and c in P0):
            m.Add(b[idx] == 0)
    out = E.solve_model(m, h, b, cross, internal, minimize=False,
                        time_limit=time_limit, workers=workers)
    out["budget"] = bud
    return nv, 4, out


def case_B_decision(q=5, pin=True, time_limit=900, workers=8):
    """(6,5,5,5,5), I=5 at budget(q,5). pin=True forces 4 edges in P0 + 1 in P1
    (exactly Case B); pin=False lets the solver place all 5 freely (stronger)."""
    nv = (6, 5, 5, 5, 5)
    classified = E.classify_pairs(nv)
    cross, cidx, internal, iidx, part_of = classified
    six = E.precompute_sixsets(part_of, cidx, iidx)
    bud = E.budget(q, 5, nv)
    if pin:
        fixed = [(0, 1), (0, 2), (0, 3), (0, 4), (6, 7)]   # star in P0 + xy in P1
        m, h, b, cross, internal, stats = E.build_model(
            nv, I=5, hole_cap=bud, model_cap=bud + 1, fixed_internal=fixed,
            six_data=six, classified=classified)
    else:
        m, h, b, cross, internal, stats = E.build_model(
            nv, I=5, hole_cap=bud, model_cap=bud + 1,
            six_data=six, classified=classified)
    out = E.solve_model(m, h, b, cross, internal, minimize=False,
                        time_limit=time_limit, workers=workers)
    out["budget"] = bud
    return nv, 5, out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all_fast"
    t0 = time.time()
    if which == "A_pin":
        nv, I, out = case_A_pinned()
        print(json.dumps({"case": "A_pinned_minholes", "nv": nv, "I": I,
                          "status": out["status"],
                          "min_holes": out.get("min_holes"),
                          "n_holes": out.get("n_holes"),
                          "bound": out.get("bound"),
                          "wall": round(out["wall"], 1)}, indent=1))
        if "internal_edges" in out:
            print("internal edges placed:", out["internal_edges"])
    elif which == "A_dec5":
        nv, I, out = case_A_decision(5)
        print(json.dumps({"case": "A_decision_q5", "nv": nv, "budget": out["budget"],
                          "status": out["status"], "wall": round(out["wall"], 1)}, indent=1))
    elif which == "A_dec6":
        nv, I, out = case_A_decision(6)
        print(json.dumps({"case": "A_decision_q6", "nv": nv, "budget": out["budget"],
                          "status": out["status"], "wall": round(out["wall"], 1)}, indent=1))
    elif which == "B_pin":
        nv, I, out = case_B_decision(5, pin=True)
        print(json.dumps({"case": "B_decision_q5_pinned", "nv": nv, "budget": out["budget"],
                          "status": out["status"], "wall": round(out["wall"], 1)}, indent=1))
    elif which == "B_free":
        nv, I, out = case_B_decision(5, pin=False)
        print(json.dumps({"case": "B_decision_q5_free", "nv": nv, "budget": out["budget"],
                          "status": out["status"], "wall": round(out["wall"], 1)}, indent=1))
        if out.get("holes") is not None:
            with open("witness_B_free_q5.json", "w") as f:
                json.dump({"size_vector": list(nv), "internal_edges": out["internal_edges"],
                           "holes": out["holes"]}, f)
    elif which == "7554":
        nv = (7, 5, 5, 5, 4)
        out = E.min_holes(nv, I=6, time_limit=1800, workers=8)
        rec = {"case": "7554_minholes_I6", "nv": nv, "status": out["status"],
               "min_holes": out.get("min_holes"), "n_holes": out.get("n_holes"),
               "bound": out.get("bound"), "budget_q6": E.budget(6, 6, nv),
               "wall": round(out["wall"], 1)}
        print(json.dumps(rec, indent=1))
        if out.get("holes") is not None:
            with open("witness_7554_I6.json", "w") as f:
                json.dump({"size_vector": list(nv), "internal_edges": out["internal_edges"],
                           "holes": out["holes"]}, f)
    print(f"[elapsed {time.time()-t0:.1f}s]")


if __name__ == "__main__":
    main()
