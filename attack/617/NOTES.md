# Provenance, imported claims, and verification notes

## 1. Unconditional elementary facts (verified here, trivial)

For a 5-colouring of K_26, *balanced* means every 6-set sees all 5 colours.
Writing G_c for the colour-c graph:

* balanced ⟺ α(G_c) ≤ 5 for every colour c (every 6-set has a c-edge);
* hence every 6-set S has e_c(S) ≤ 15 − 4 = 11 for every c;
* hence (complement of G_c is K₆-free, Turán) |G_c| ≥ 325 − T(26,5)
  = 325 − 270 = **55**, unconditionally, for every colour.

## 2. Imported claims (NOT verified in this repository)

The following are quoted from ~20 earlier working passes whose artifacts
were never committed anywhere; they could not be re-verified here and every
"conditional" statement below depends on them:

* (P1) |G_c| ≥ 61 for every colour, and |G_c − v| ≥ 55 for every vertex.
* (P2) if |G_c| = 61 then G_c has a vertex v of degree 6; with A = N(v)
  (|A|=6), B = rest (|B|=19): e(G_c[B]) = 40 is forced.
* (P3) G[A] ≅ K₄⊔2K₁ (Case I) or K₄⊔K₂ (Case II); the A→B edges split as
  |N_B(p)|=4, |N_B(q)|=5 (Case I) resp. 4,4 (Case II) over the two
  non-K₄ vertices p,q, and the four K₄-vertices of A have **no**
  B-neighbours.
* (P4) Δ(B) ≤ 6, τ₃(B) ≥ 9.
* (P5) complement(B) is K₅-saturated and not 4-partite; τ₄(B) = 4.

Internal consistency checks that pass: e(A)+e(A,B)+e(B) = 6+9+40 = 55
(Case I) and 7+8+40 = 55 (Case II). ✓

## 3. The §3 hitset-pair derivations (re-derived independently — correct
**given** P2–P4)

All six-sets below must carry a colour-c edge (balancedness); u denotes any
K₄-vertex of A, which by (P3) has no B-neighbour and is non-adjacent to p
and q in G_c.

* **α(B) ≤ 4**: for a 5-set I ⊆ B, the 6-set {v}∪I has no c-edge at v
  (B = non-neighbours of v), so I contains an edge.
* **P hits every independent 4-set F of B** (both cases): the 6-set
  {p,u}∪F has c-edges only inside p→F = p→(F∩P); so F∩P ≠ ∅.  Symmetric
  for Q.
* **Case I, P∪Q hits every independent 3-set T of B**: the 6-set
  {p,q,u}∪T has c-edges only in p→(T∩P) ∪ q→(T∩Q) (p,q non-adjacent in
  Case I), so T∩(P∪Q) ≠ ∅.
* **Case I, P∩Q = ∅**: P∪Q is a τ₃-hitting set, |P∪Q| ≥ τ₃(B) ≥ 9 = |P|+|Q|.
  (Uses imported τ₃ bound (P4).)
* **Case I, e_B(Q) ≤ 6**: 6-set {q}∪Q carries 5 + e_B(Q) ≤ 11 c-edges.
* **Case II, e_B(P) + |P∩Q| ≤ 6**: 6-set {p,q}∪P carries
  1 (pq) + 4 (p→P) + |P∩Q| (q→P) + e_B(P) ≤ 11.  Symmetric for Q.
* τ₄(B) ≤ 4 is implied by P being a hitting 4-set, so (P5)'s τ₄(B)=4
  reduces to τ₄(B) ≥ 4.

WLOG canonical placement of (P,Q) used by the solver is sound: every
constraint of the spec is invariant under relabelling vertices of B, and in
Case II the sub-cases k = |P∩Q| = 0..4 are exhaustive.

## 4. Encoding soundness notes (solve_hitset_pair.py)

* Eagerly encoded: e(B)=40 (totalizer), Δ≤6 (seq. counters), α≤4
  (one clause per 5-set), hitting conditions (one clause per relevant
  4-/3-set), e_B(P)/e_B(Q) caps, K₅-saturation of the complement
  (per-pair existential gadgets, implication only in the sound direction),
  τ₄ ≥ 4 (per-3-set existential gadgets, sound direction).
* Lazily encoded (CEGAR, each added constraint individually implied by the
  spec): e_B(S) ≤ 11 per violated 6-set; "this particular partition of V
  into 4 parts is not a B-clique cover" per discovered cover.
* Termination: UNSAT, or a witness with no violated lazy condition; every
  SAT witness is re-verified by `check_witness.py` against the *entire*
  spec from scratch.

## 4b. Structural lemmas proved here (unconditional consequences of the spec)

* **Lemma 1** (Case I): e(B−P) ≥ 31 — `case1_structure.md`.
* **Lemma 2** (Case I): e(B−Q) ≥ 27 — `case1_structure.md`.
* **Lemma 3** (Case II): e(B−P) ≥ 31 and e(B−Q) ≥ 31 — `case2_structure.md`.
* **Restricted-T saturation**: every saturation witness T for a B-edge uv
  satisfies T∩P ≠ ∅ (unless u,v ∈ P) and T∩Q ≠ ∅ (unless u,v ∈ Q), because
  T∪{u}, T∪{v} are independent 4-sets which P,Q must hit.  Used to shrink
  the saturation gadgets ~3x in both solvers, soundly.

## 5. RESULTS — the hitset-pair finite problem is UNSAT in all cases

**Theorem (computational; conditional only on the encoding arguments in
§3–§4b, all of which are written out and independently re-derived here).**
There is **no** graph B on 19 vertices satisfying the section-6 spec —
in Case I or in any Case II sub-case k = 0..4.

**Conditional corollary** (additionally assuming the imported pass-1..20
claims of §2, which are NOT verified in this repository): in any balanced
5-colouring of K₂₆, every colour class has at least **62** edges; the
61-edge colour-class boundary is closed.

Erdős #617 itself remains open: this closes one control point of one
route.  It is neither a proof that balanced colourings of K₂₆ do not
exist, nor a counterexample.

### Verdict matrix

Four encoding variants per case (main = Lemma cuts + restricted-T;
ablations remove the hand-proved lemmas and/or the T-restriction; *pure* =
neither, i.e. the minimal trust base: direct spec constraints + lex-leader
symmetry breaking only).  All 24 CDCL runs returned UNSAT on the first
solver call — the lazy constraint families (6-set bounds, 4-partiteness)
were never needed.

Run `python3 collect_results.py` for the generated table with timings.
Summary: **24/24 CDCL UNSAT** (CaDiCaL 1.9.5); **6/6 DRAT certificates**
produced by Glucose 4.2 (independent second solver) and machine-verified
by drat-trim (`s VERIFIED`; see artifacts/certs_summary.txt — total
verification ~4 CPU-hours, largest proof 2.7 GB); CP-SAT third-engine
INFEASIBLE confirmation on II.k0.

### Trust base for the UNSAT claim

1. The constraint-to-CNF encoding (`solve_hitset_pair.py`), validated
   end-to-end: a model of the relaxed instance (cap removed) produced
   under the exact production encoding passes every spec condition under
   independently written semantics (including unrestricted saturation).
2. Lex-leader symmetry breaking over adjacent transpositions within the
   interchangeable vertex classes (textbook-sound; bubble-sort argument;
   regression-tested to preserve satisfiability of the relaxed instance).
3. The solvers, cross-checked three ways: CaDiCaL (via PySAT), Glucose
   4.2 with DRAT proof logging, drat-trim proof verification, and
   OR-Tools CP-SAT with a *different* encoding (native linear
   cardinalities, eager 6-set bounds, degree-sort instead of lex).
4. The hand-proved Lemmas 1–3 and the restricted-T argument are NOT in
   the trust base: the ablation and pure runs are UNSAT without them.

### Diagnostics that locate the contradiction

* Relaxing only e_B(Q) ≤ 6 in Case I makes the instance SAT instantly
  (the model is the pass-20 near-miss family: P=K₄, Q=K₅, dense R, no
  cross edges).  The cap is the heart of Case I.
* In Case II.k0 the caps are vacuous; infeasibility there is purely
  "two disjoint hitting 4-sets cannot coexist" under L1–L3, L5, τ₄ ≥ 4.
* K₅-saturation of the complement is the binding global constraint: the
  v1 lazy runs (saturation enforced only by counterexample) freely found
  models satisfying everything else.
