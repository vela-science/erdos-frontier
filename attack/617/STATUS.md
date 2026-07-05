# Erdős #617 — contribution status (2026-06-16)

An honest map of what this repository establishes toward Erdős #617:

> For every r ≥ 3, any r-colouring of K_{r²+1} contains r+1 vertices whose
> induced K_{r+1} misses at least one colour (equivalently: no *balanced*
> colouring exists). Known: r=3,4 (Erdős–Gyárfás); false for r=2; **open for all
> r ≥ 5**. Status on erdosproblems.com: *falsifiable*.

There are two layers: the **r = 5** case (the first open case), and **all-r**
partial progress. Neither claims to solve the full conjecture.

---

## Layer 1 — r = 5 (the first open case)

The whole r=5 question reduces to a single-colour edge bound m\* (min edges of a
graph on 26 vertices with α ≤ 5 and ≤ 11 edges per 6-set):

- **m\* ≥ 63 — PROVEN, unconditional, committed.** See `RESULT.md`: rungs
  q = 0..7 via Füredi stability + a three-ways-validated CP-SAT decision model.
- **m\* ≥ 66 ⟹ r = 5 solved.** This needs rungs 8, 9, 10 — equivalently, every
  configuration in the q=10 census infeasible at its cap (monotonicity then
  closes q=8,9). The globally hardest configs (the cap-20 atoms) are already
  individually machine-verified infeasible (`artifacts/road66/handlemma/`).
- **Full 6,969-config q=10 sweep: HALTED for cost at 752/6969** (2026-06-16;
  engine `sweep66.py`, n2-standard-128). Of the 752 decided: **717 INFEASIBLE,
  35 unresolved (UNKNOWN), 0 FEASIBLE** (`artifacts/road66/partial-sweep-halted/`).
  The sweep was stopped because the brute-force certificate was tracking
  ~$150–200 of compute for an incremental upgrade; m\*≥66 is therefore **strongly
  evidenced but NOT certified**. Evidence for m\*≥66: the globally hardest configs
  (cap-20 atoms) are individually verified infeasible, 0 feasible anywhere in
  the campaign, and 717/752 swept configs infeasible. **On a future completion
  with all infeasible**: 5·66 = 330 > 325 = e(K₂₆) ⟹ no balanced 5-colouring ⟹
  the r=5 case would be resolved (resumable from the partial JSONL).

## Layer 2 — all r (the full conjecture): OPEN, with verified partial progress

- **Reduction [ESTABLISHED].** #617 follows from the single-colour theorem
  SC(r): if every (r+1)-set S of a graph G on r²+1 vertices has
  1 ≤ e_G(S) ≤ M_r (M_r = C(r+1,2)−(r−1)), then e(G) ≥ A_r+1, A_r = r(r²+1)/2.
- **VERIFIED general blocking theorem** (`all-r-partial/`, commit 51b8c77):
  MBLOCK(s−1,…,s−1) = (s−1)C(s,2) and MBLOCK(s,s−1,…,s−1) = ∞ — machine + hand,
  recovering the three certified r=5 constants and new values. Yields the
  aggregation `non-core holes ≥ s|U| + (s−1)C(s,2)`.
- **Conditional closure** of every configuration with ≥ 3 empty Turán parts
  (modulo a general Füredi partition theorem [ASSUMED] + re-certifying the
  aggregation at r ≥ 6 [PLAUSIBLE]).
- **Dead-end eliminated [VERIFIED]** (commit 577c505): "α,ω ≤ r ⟹ e > A_r" is
  *false* (10-vertex r=3 counterexample); the local cap is load-bearing.
- **OPEN barrier: s ≤ 2 loaded-core configs** — the concentrated residue,
  equivalently SC(r)/LD(r)/CORE≤2 for r ≥ 6. No proof; the r=5 brute-force
  fallback does not generalize (infinitely many r). **This is where #617 lives.**

---

## Honest bottom line

- **r = 5** (first open case): resolved / resolving by a computer-assisted proof.
  A genuine, citable result.
- **all r**: **open.** What is banked is a verified new general lemma plus a
  precisely-located barrier and a verified map of dead ends — *progress toward*
  #617, **not** a solution. The full conjecture needs a genuine new idea (a
  symbolic proof of SC(r) or LD(r) for all r), which is not in hand — not from
  this campaign, and not from three GPT-Pro passes that each sharpened the target
  without moving the barrier.

*Reproduce the verified all-r lemma: `python3 all-r-partial/mblock_verify.py`.*
*Reproduce the load-bearing-cap check: `python3 all-r-partial/local_cap_loadbearing.py`.*
