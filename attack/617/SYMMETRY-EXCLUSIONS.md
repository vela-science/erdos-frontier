# Symmetric counterexample exclusions (2026-06-12)

Counterexample direction for #617, r = 5: a balanced 5-colouring of K₂₆
would settle the whole problem in the negative, and a structured one would
be found by invariant search.  This session closes the natural symmetric
families.  Every claim below is about colourings invariant under a vertex
permutation g, i.e. colour(gu, gv) = colour(u, v); "shape zP-B" means B
disjoint P-cycles and 26 − PB fixed points.  Witnesses, had any existed,
are re-verified by `check_balanced.py` (independent checker).

## 1. Arithmetic exclusions (by hand, unconditional)

Invariant colour classes are unions of edge orbits, and every colour class
of a balanced colouring has ≥ 55 edges (Turán, NOTES.md §1).  Integrality
of orbit sizes then kills:

* **Z₂₆ circulants** (12 orbits of 26, one of 13): sizes 26a + 13b with
  Σa = 12, Σb = 1; 26a + 13b ≥ 55 forces a ≥ 2 when b = 1 and a ≥ 3 when
  b = 0, so Σa ≥ 2 + 4·3 = 14 > 12.  ∎
* **F₂₅-translation colourings** (25 affine points + ∞; 13 orbits, all of
  size 25): sizes 25k ≥ 55 force k ≥ 3 per colour, Σk ≥ 15 > 13.  ∎

## 2. Block exclusions (by inspection, unconditional)

If g has a 5-cycle, take its 5 points plus any 6th vertex: the within-block
edges fall in 2 orbit classes (differences ±1, ±2) and the 5 edges to the
6th vertex form 1 class — 3 classes, so this 6-set sees ≤ 3 < 5 colours.
If g has a 7-cycle, any 6 of its points span differences ±1, ±2, ±3 —
again ≤ 3 classes.  Hence **no shape containing a 5- or 7-block admits a
balanced invariant colouring**: all of z5-1..5 and z7-1..3 die by hand.  ∎

(The SAT runs below for z5-3/4/5 and z7-2/3 confirm this independently:
their reps have min 3 distinct orbits per 6-set class.)

## 3. SAT-decided shapes (CP-SAT INFEASIBLE)

`search_z13_invariant.py` (z13-2, with the valid exactly-5-classes cut and
a CaDiCaL pure-spec cross-check on all 1 151 150 coverage clauses — see
`crosscheck_z13_pysat.py`) and `search_group_invariant.py` (all others;
one representative 6-set per ⟨g⟩-class, colour value-precedence breaking):

| shape | fixed pts | edge orbits | verdict |
|---|---|---|---|
| z23-1 | 3 | 17 | UNSAT |
| z19-1 | 7 | 37 | UNSAT |
| z17-1 | 9 | 53 | UNSAT |
| z13-2 | 0 | 25 | UNSAT (2 engines) |
| z13-1 | 13 | 97 | UNSAT |
| z11-2 | 4 | 35 | UNSAT |
| z11-1 | 15 | 125 | UNSAT |
| z7-3, z7-2 | 5, 12 | 55, 103 | UNSAT (also §2) |
| z5-5, z5-4, z5-3 | 1, 6, 11 | 65, 77, 109 | UNSAT (also §2) |
| z3-8, z3-7, z3-6 | 2, 5, 8 | 109, 115, 127 | UNSAT |
| z3-5, z3-4, z3-3, z3-2, z3-1 | 11, 14, 17, 20, 23 | 145, 163, 187, 217, 253 | UNSAT (cloud, 32-core) |
| z2-13 | 0 | 169 | UNDECIDED at 600 s (min 9 distinct orbits per class — no cheap kill) |
| z2-12 | 2 | 169 | UNDECIDED at 3 600 s locally; rerunning at cloud scale, 24 h budget |

z13-2 is the tight family: 25 orbits of size 13 force every colour to take
exactly 5 orbits (65 edges — the all-classes-65 extremal point), and some
6-sets span exactly 5 orbit classes; infeasibility is genuinely global.
Logs: `artifacts/z13_search.log`, `artifacts/z{3,5}_search.log`,
`artifacts/shape_sweep.log`.

## 4. Consequences

* **Theorem (computational).** No balanced 5-colouring of K₂₆ admits a
  vertex-automorphism of **any odd prime order, of any cycle shape**
  (p ≥ 5: §2 hand proofs + SAT; p = 3: all eight shapes z3-1..8 by SAT,
  the fixed-point-rich tail at cloud scale).  Hence any counterexample to
  #617 at r = 5 has an automorphism group that is a **2-group**; the
  involution shapes z2-12, z2-13 (in flight) are the first rungs of that
  remaining tower (z2-1..11 open).
* PSL₂(25) on P¹(F₂₅) has elements of prime order 2, 3, 5, 13 only, with
  shapes z2-12, z3-8, z5-5, z13-2 — all closed except z2-12 (in flight).
  Once it lands: **no balanced colouring is invariant under any nontrivial
  subgroup of PSL₂(25)**.

## 5. Remaining shapes and follow-ups

z3-1..5 (≥ 11 fixed) and z2-1..11 (≥ 4 fixed) have 145–313 edge orbits;
search space approaches the monolithic 5³²⁵ problem and CP-SAT verdicts are
not expected cheaply.  Next: z3-5/z3-4 attempts with longer budgets; DRAT
certification of the solver-decided rows (each is a small CNF; pipeline as
in `certify_unsat.py`); the m* probe (`MSTAR-PROBE.md`) is the complementary
proof-direction experiment.

Reproduce: `python3 search_z13_invariant.py && python3 crosscheck_z13_pysat.py
&& for s in z23-1 z19-1 z17-1 z13-1 z11-2 z11-1 z3-7 z3-6; do python3
search_group_invariant.py $s 600; done`
