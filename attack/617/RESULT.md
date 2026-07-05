# A single-colour-class lower bound for Erdős #617 (r = 5)

*W. Blair, 2026. Code and certificates:
`verified-combinatorics/erdos-617`. Verification: `general_rung.py`,
`rung62_complete.py`, `rung_754_parallel.py`.*

**Abstract.** The first open case of the Erdős–Gyárfás generalized Ramsey
problem [ErGy97] asks whether K₂₆ admits a balanced 5-colouring (one in
which every 6 vertices see all 5 colours). A counting argument reduces a
proof of impossibility to the single-class bound m\* ≥ 66, where m\* is the
least number of edges of a graph on 26 vertices with independence number
≤ 5 in which every 6 vertices span at most 11 edges. We prove **m\* ≥ 63**,
unconditional, improving the elementary Turán bound m\* ≥ 55 by eight. The
proof is a finite Füredi-stability "rung" argument whose case analysis is
discharged by a full-spec SAT/CP decision model, independently validated
(§3). Section 5 localizes the remaining gap to m\* ≥ 66 and shows it
provably resists the cheap (fractional/clique) methods.

---

**Result.** In any balanced 5-colouring of K₂₆, every colour class has at
least **63 edges**, i.e. m\* ≥ 63 (m\* as in the abstract).

The bound is unconditional, resting only on Füredi's stability theorem
(2015) and a finite, machine-checked case analysis. It is verified by an
independently validated solver pipeline; §4 records the trust base and how
to reproduce it.

---

## 1. The problem and the reduction

Erdős–Gyárfás [ErGy97] ask, for r ≥ 3: if the edges of K_{r²+1} are
r-coloured, must some r+1 vertices induce a K_{r+1} missing a colour? The
cases r = 3, 4 are theirs; r ≥ 5 is open. The first open case is r = 5, on
K₂₆: a colouring is *balanced* if every 6 vertices see all 5 colours on
their 15 edges, and the conjecture is that none exists.

Fix a colour c and let G = G_c be its colour class. Balancedness restricted
to one class says exactly two things:

- **(A)** α(G) ≤ 5: every 6-set carries a c-edge, so no independent 6-set;
- **(B)** every 6-set spans ≤ 11 edges of colour c (it must leave room for
  the other four colours on its 15 pairs).

Write **m\*** for the minimum of e(G) over all G on 26 vertices satisfying
(A) and (B). The five colour classes partition the 325 edges of K₂₆, so if
**m\* ≥ 66** then 5·66 = 330 > 325, no balanced colouring exists, and the
r = 5 case is settled. This note proves m\* ≥ 63, four short of that goal;
§5 explains precisely what the remaining gap requires.

The naive bound is m\* ≥ 55 (Turán applied to the complement). The content
here is the 8-edge improvement to 63.

## 2. The complement and the rung method

Pass to the complement H = Ḡ on the same 26 vertices. Conditions (A), (B)
become:

- H is **K₆-free** (a 6-clique in H is an independent 6-set in G);
- **every 6-set spans ≥ 4 edges** in H (15 − 11 = 4).

Since e(G) + e(H) = 325, proving m\* ≥ 63 is proving **e(H) ≤ 262** for
every such H.

Suppose e(H) = 270 − q. By Füredi's theorem ([Fü15], Theorem 1: for a
K_{p+1}-free graph with e(T_{n,p}) − t edges there is a p-chromatic
subgraph within t edges), H has a 5-partition whose number of internal
(within-part) edges I is at most q. For a partition with part sizes
(n₀,…,n₄), set the defect d = Σ C(nᵢ,2) − 55. Counting cross-pairs against
e(H) = 270 − q gives the exact identity

        (number of absent cross-pairs)  =  I + q − d  =:  cap.

So each rung q is a finite question: over the partition shapes admissible
at that q (those with Σ f(nᵢ) ≤ q, where f(n) is the least number of
internal edges a part of size n must carry so that its own 6-subsets each
span ≥ 4) and over every internal configuration, is there a placement of
≤ cap absent cross-pairs that keeps H both K₆-free and ≥ 4 on every 6-set?
If the answer is **no** at every admissible (shape, configuration) for a
rung, that rung is impossible.

Killing rungs q = 0,1,…,7 forces e(H) ≤ 262, hence m\* ≥ 63.

- q ≤ 3: the size-6 part forced by the partition needs f(6) = 4 internal
  edges, but only I ≤ q < 4 are available. Immediate.
- q = 4,5,6,7: each admissible shape and internal configuration is decided
  by the finite full-spec model of §3. The shapes are (6,5,5,5,5) at every
  rung and, from q = 6, (7,5,5,5,4); their internal configurations are
  enumerated up to isomorphism (96 of (6,5,5,5,5) at q = 6; 249 + 52 across
  both shapes at q = 7). Every one is infeasible.

The lower rungs were also obtained by hand: the elementary "hole-budget +
grid + pinning" argument closes q = 4 (m\* ≥ 60) and q = 5 (m\* ≥ 61)
without a solver (see `MSTAR-HAND-ATTACK.md`); the machine reproduces them.

## 3. The finite model and its validation

Each rung-question is a Boolean decision: with the partition and internal
edges fixed, introduce one variable per cross-pair (present or absent) and
enforce, for every 6-set, that it spans ≥ 4 edges and ≤ 14 (K₆-freeness),
together with the absent-pair budget. The encoder is `general_rung.py`
(and the shape-specific `rung62_complete.py`, `rung_754_parallel.py`); it
is full-spec, with no lemma shortcuts in the trust base.

The model is validated three ways before any infeasibility is trusted:

1. It reproduces a known SAT value exactly: the Case-A C4 configuration of
   (6,5,5,5,5) has minimum 34 absent pairs under both an independent
   checker and the production encoder.
2. It is not vacuously infeasible: at a loose budget the model is satisfied
   and the witness passes an independent verifier.
3. The isomorphism reduction is exact. An early version keyed configuration
   deduplication on a Weisfeiler–Leman hash, which collides on
   non-isomorphic regular graphs (C₈, C₄+C₄, C₃+C₅); this was caught
   against the validated rung-62 count and corrected to an exact
   iso-class identity. Without the fix the enumeration silently merges
   configurations and could report a false closure.

The dense, high-budget configurations of q = 7 were confirmed by extended
single-instance runs (one needed ~40 minutes of solver time); all returned
infeasible, none feasible.

## 4. Status, trust base, and reproduction

**Proven, unconditional:** m\* ≥ 63.

**Trust base:** (i) Füredi 2015, Theorem 1, a published result whose
statement was checked verbatim; (ii) the full-spec finite model above,
validated as in §3. No part of the chain depends on the earlier,
never-committed "pass-1..20" reductions that an older note in this
directory imported; those are superseded.

**Reproduce:** `general_rung.py q` decides rung q over all admissible
shapes; `rung62_complete.py` and `rung_754_parallel.py` carry the q = 6, 7
shapes; results are in `artifacts/road66/`. Each is a self-contained CP-SAT
decision.

## 5. What m\* ≥ 66 would still require

The route to the full r = 5 case (m\* ≥ 66) stays open, but it is now
sharply localized. Killing rungs q = 8,9,10 reduces, after the elementary
and stability lemmas, to deciding the configurations whose internal graph
is **triangle-free and concentrated in one or two parts** (K_{2,3}, C₄,
C₅, paths). Three independent facts pin down this residue:

- the route is **alive**: the canonical hardest configuration
  (a star in the 6-part plus K_{2,3} in one 5-part, at q = 10) has minimum
  absent-pairs ≥ 27 > its cap of 20, so it is infeasible, consistent with
  the conjecture;
- the clique-core hand lemmas (Case A, the empty-4-part K₆-forcing lemma,
  and the triangle/K₄/K₅ bounds, all with machine-exact constants in
  `artifacts/road66/handlemma/`) close the configurations that carry a
  clique, and an explicit fractional K₆-packing closes the *diffuse*
  triangle-free configurations; but
- **fractional and clique methods provably cannot close the concentrated
  triangle-free residue**: its packing optimum is ≈ 13 against a cap of 20,
  and the gap is inherent (the load-bearing blocking constant
  BLOCK(3,3,3,3) = 18 is an integer fact whose linear relaxation is only 9;
  see `artifacts/road66/lpdual/`).

So m\* ≥ 66 is reachable as a hybrid — hand lemmas and the packing for the
clique-bearing and diffuse families, full-spec CP-SAT for the concentrated
triangle-free core — but that core is the genuine obstruction: each of its
configurations needs a heavy individual solver run, and no cheap closed
form exists. Proving it is a matter of compute, not of a missing idea.

---

[ErGy97] P. Erdős, A. Gyárfás, *A variant of the classical Ramsey
problem*, Combinatorica 17 (1997), 459–467.
[Fü15] Z. Füredi, *A proof of the stability of extremal graphs, Simonovits'
stability from Szemerédi's regularity*, arXiv:1501.03129; Combinatorica.
