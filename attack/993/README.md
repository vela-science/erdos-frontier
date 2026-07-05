# Erdős Problem #993 — forest case (independence-polynomial unimodality)

[Erdős #993](https://www.erdosproblems.com/993) (Alavi–Erdős–Malde–Schwenk 1987): the
independent-set sequence $i_0(G), i_1(G), \dots$ of every **tree or forest** $G$ is
unimodal. Status: **FALSIFIABLE** — a single finite tree or forest with a strict interior
valley disproves it.

This folder searches the **forest** half of the conjecture, which prior computational work
(exhaustive over single trees to 29 vertices; the PatternBoost ML sweep to 101 vertices)
left untouched.

## The reduction

A forest's independence polynomial is the **product** of its components'. By
[Hoggar (1974)](https://doi.org/10.1016/0095-8956(74)90071-9), the convolution of two
log-concave positive sequences is log-concave. So a forest can be non-unimodal **only if at
least one component is itself non-log-concave**. The smallest non-log-concave tree has order
26 ([Kadrawi–Levit 2023](https://arxiv.org/abs/2305.01784)). Hence the non-log-concave trees
are the only place a forest counterexample can live, and the search reduces to: build forests
out of non-log-concave components and test the product for a valley.

## What was searched

Generalizing the Kadrawi–Levit families $T_{3,m,n}$, $T^*_{3,m,n}$ to a parametric class of
rooted "bush" trees (root degree 2–5, per-branch child counts 2–6, pendant-path depths 1–3):

- **112,916** trees scanned (orders 26–60), yielding **4,445** distinct non-log-concave
  independence polynomials, with log-concavity defect down to **≈ −12** (well past the
  order-26 breaks).
- **0** non-unimodal single trees.
- **253,695** forest objects over the 80 most-severely-non-log-concave seeds — all pairwise
  and triple products, powers through the 20th, and products with paths $P_1 \dots P_{16}$.
- **All unimodal.** No non-unimodal tree or forest found.

This does not resolve #993; it rules out a counterexample on the structured forest surface
where, by the reduction above, one would first have to appear.

## Files

| file | what |
|---|---|
| `verify_993_kernel.py` | exact integer in/out tree-DP independence polynomial + unimodality / log-concavity scanners. Self-tests against brute-force independent-set counts (436/436 trees, 6/6 forests). |
| `search_993.py` | the two literature families $T_{3,m,n}$, $T^*_{3,m,n}$ + a first forest-product sweep. |
| `search_993_v2.py` | the generalized "bush" families + the full forest-surface sweep. |
| `verify_993_result.py` | fast frozen verifier: kernel vs brute force, order-26 seeds reproduced, sampled forest surface unimodal. |
| `generate_results.py` | regenerates `results.json` + the two order-26 seed edge lists. |
| `results.json` | summary + the two order-26 seeds (edge lists + polynomials) + the 25 most-severe non-log-concave trees. |
| `seed_T_3_4_4.json`, `seed_Tstar_3_3_4.json` | the order-26 non-log-concave seeds as edge lists. |

## Reproduce

```bash
pip install -r requirements.txt
python3 verify_993_result.py     # frozen checks, fast — should print ALL PASS
python3 search_993_v2.py         # full sweep (a few minutes); prints "no non-unimodal tree OR forest found"
python3 generate_results.py      # regenerates results.json
```

Every independence polynomial is computed exactly in big-integer arithmetic; there is no
floating point in the verifier. Tooling: the search and code were developed with GPT 5.5 Pro
and Claude; the numbers come from the executed runs.
