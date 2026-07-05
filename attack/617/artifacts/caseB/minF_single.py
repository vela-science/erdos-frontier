"""Full-spec minimisation for a single P0 config; validates the encoding
end-to-end: the returned witness must pass check_caseB.py."""
import sys, json
from caseB_model import build_full, solve, CONFIGS, CROSS

cname = sys.argv[1]
CAP = int(sys.argv[2]) if len(sys.argv) > 2 else 60
tl = int(sys.argv[3]) if len(sys.argv) > 3 else 900
m, h, n_six, n_k6 = build_full(CONFIGS[cname], hole_cap=CAP, model_cap_for_constraints=CAP)
print(f"{cname}: {n_six} six-set constraints, {n_k6} K6 clauses", flush=True)
st, nh, holes, bound = solve(m, h, minimize=True, time_limit=tl)
print(f"[minF] {cname}: {st} min={nh} bound={bound}", flush=True)
if holes is not None:
    with open(f"/tmp/caseB/witness_minF_{cname}.json", "w") as f:
        json.dump({"config": CONFIGS[cname], "holes": holes}, f)
