# Erdős Problem #617 — the r = 5 case (K_26)

**Problem** ([erdosproblems.com/617](https://www.erdosproblems.com/617),
Erdős–Gyárfás [ErGy99]): let r ≥ 3. If the edges of K_{r²+1} are r-coloured,
must there exist r+1 vertices whose induced K_{r+1} misses at least one
colour?  Proved for r = 3, 4 by Erdős–Gyárfás; **open for r ≥ 5**.  The first
open case is r = 5: does K_26 admit a *balanced* 5-colouring, i.e. one in
which every 6-set of vertices sees all 5 colours on its 15 edges?  The
conjecture says no.

## Current result — see [`RESULT.md`](RESULT.md)

The headline result of this directory is now **unconditional**: in any
balanced 5-colouring of K₂₆ every colour class has **≥ 63 edges**
(equivalently m\* ≥ 63), proved in [`RESULT.md`](RESULT.md) by a finite
Füredi-stability rung argument with a validated full-spec solver. The full
r = 5 case needs m\* ≥ 66; `RESULT.md` §5 localizes the remaining gap to a
concentrated triangle-free residue that provably resists cheap methods.

The sections below describe an **earlier, conditional** route (the 61-edge
hitset-pair decision) that the `RESULT.md` argument supersedes; they are
kept for provenance. The pass-1..20 imports they rely on are *not* in the
trust base of the m\* ≥ 63 result.

## Status of this directory

This directory attacks the single sharpest control point left in the
"61-edge colour class" route, namely the **pass-20 hitset-pair finite
decision problem** (see `NOTES.md` for the full provenance and the
conditional structure):

> Find or rule out a graph B on 19 vertices with e(B)=40, Δ(B)≤6, α(B)≤4,
> at most 11 edges on every 6-set, complement K₅-saturated and not
> 4-partite, τ₄(B)=4, together with the Case I or Case II hitset pair
> (P,Q) — see `solve_hitset_pair.py` docstring for the exact spec.

**IMPORTANT — what is and is not proven.**  The reduction of the 61-edge
colour-class boundary to this finite problem was produced across ~20 earlier
working passes whose artifacts were never committed to this repository.
Those reductions are **imported, unverified claims** here (itemised in
`NOTES.md`).  Consequences derived in this directory that depend on them are
marked *conditional*.  Unconditional facts (the elementary balanced-colouring
constraints, witness checks, SAT/UNSAT verdicts about the stated finite
problem itself) are verifiable from the code and certificates in
`artifacts/`.

Erdős #617 itself remains **open** in both directions; nothing here claims a
full solution.

## RESULT

**The finite problem is UNSAT in all six cases** (Case I; Case II for
k = 0..4): no 19-vertex graph B with the required properties exists.

* 24/24 CDCL runs UNSAT (CaDiCaL via PySAT), including ablations that
  remove the hand-proved lemma cuts and the saturation T-restriction, and
  a "pure spec" variant whose trust base is only the direct constraint
  encoding + lex-leader symmetry breaking.
* DRAT proofs produced by Glucose 4.2 (an independent second solver) and
  machine-verified by drat-trim.
* OR-Tools CP-SAT (a third engine, different encoding and symmetry
  handling) independently returns INFEASIBLE on the cases checked.
* Encoder semantics validated end-to-end against independently written
  checking code; the relaxed instance (cap removed) is SAT and reproduces
  the pass-20 near-miss family, so the encoding is not vacuously strong.

**Conditional corollary** (assuming the *unverified* imported pass-1..20
reductions, see `NOTES.md` §2): every colour class of a balanced
5-colouring of K₂₆ has ≥ 62 edges.  **Erdős #617 itself remains open.**

See `NOTES.md` §5 for the full verdict matrix and trust-base discussion;
`case1_structure.md` / `case2_structure.md` for the new unconditional
structural lemmas (Turán-stability) proved along the way.

## Files

| file | purpose |
|---|---|
| `solve_hitset_pair.py` | CNF encoder + CaDiCaL CEGAR solver for the finite problem (Case I, Case II k=0..4) |
| `check_witness.py` | independent full-spec checker for any SAT witness (no pysat, no shared code) |
| `certify_unsat.py` | replays a dumped CNF with Glucose 4.2 proof logging and verifies the DRAT proof with drat-trim |
| `search_balanced_k26.py` | direct SAT search for a balanced 5-colouring of K_26 (counterexample hunt; SAT direction only) |
| `check_balanced.py` | independent checker for a claimed balanced colouring |
| `NOTES.md` | provenance, imported claims, independent verification of the pass-20 §3 derivations, results |
| `artifacts/` | logs, result JSONs, dumped CNFs, DRAT certificates, SHA256 manifest |
