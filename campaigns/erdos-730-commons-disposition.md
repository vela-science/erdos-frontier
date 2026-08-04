# Erdős 730 frontier-to-commons disposition

## Disposition

**Retain the accepted external-proof boundary in the Erdős Frontier. Do not
classify the Formal Conjectures problem as solved or submit a proof link until
the native maintainer accepts the mathematical-status and toolchain boundary.**

This is the third explicit frontier-to-commons disposition. The evidence is
strong enough to establish the exact local Claim and strong enough to prepare
a small future `formal_proof` link. It is not strong enough to make the two
remaining native decisions on behalf of Formal Conjectures: whether the result
should be classified `research solved`, and whether a Lean 4.29.1 proof in an
external repository is acceptable evidence for a Lean 4.27.0 statement.

If those decisions are positive, the correct contribution is a small
statement-and-link change in Formal Conjectures. It is not a copy of the
74-module proof and not a Mathlib extraction.

## Exact contribution boundary

- Intended native owner: `google-deepmind/formal-conjectures`
- Current native path: `FormalConjectures/ErdosProblems/730.lean`
- Current declaration: `Erdos730.erdos_730`
- Current statement root:
  `sha256:c8e532aa2916312501375df4e30ca4770fdeb3968d39622dda5cdfc5f9fa26e7`
- Current native state: `answer(sorry) ↔ Erdos730.S.Infinite`, category
  `research open`, theorem proof `by sorry`
- External proof commit: `4f915a323443bfb1709a6805a013812016dca88a`
- External terminal theorem:
  `Erdos730.FullDensityTheorem.pairSet_infinite`
- External terminal root:
  `sha256:7f341400b34cd3241007dce7365aa84c367546ffda0acf164d7a32e003f98ba0`
- External Lean: `leanprover/lean4:v4.29.1`
- External Mathlib: `5e932f97dd25535344f80f9dd8da3aab83df0fe6`
- Native Lean at qualification: `leanprover/lean4:v4.27.0`
- Native Mathlib at qualification:
  `a3a10db0e9d66acbebf76c5e6a135066525ac900`
- External proof closure: 74 retained Lean modules
- Axioms: `propext`, `Classical.choice`, and `Quot.sound`

The accepted local Claim is
`vcl_8ef85fca44b8d9105e8c28b9ba702accd9365c4ff23d87466bf2b64853921345`.
Verification `vvr_3b6d523c55a24dc9` binds both source trees, terminal
ancestry, the 74-module escape scan, native external build, axiom audit, and
six-dimensional source-equivalence review. Decision
`vev_0ab843df6ad373ec` accepts only the bounded external-proof Claim while
preserving the non-port boundary.

## Existing upstream work

Formal Conjectures PR 3525 remains open and conflicting. Its Erdős 730 change
only proves `erdos_730.variants.explicit_pairs`; it does not fill the main
`erdos_730` declaration or link the external infinitude theorem. The explicit-
pairs proof was independently merged later in PR 4121. PR 3525 is therefore
not an upstream path for this external proof.

The current main statement still contains the answer and theorem placeholders
and no `formal_proof` link. The future candidate should be prepared against
current main after the two native decisions below, not rebased from PR 3525.

## Evidence supporting a future link

- The external theorem proves a stronger consecutive-pair family for the same
  natural-pair predicate retained as `Erdos730.S`.
- The source-first review checked domain and pair order, central-binomial
  definition, prime-support equality, conclusion strength, proof assumptions,
  and the toolchain/import boundary.
- The complete retained external closure has no proof escape and the terminal
  theorem compiles with the exact allowed axiom set.
- The proof predates this campaign; the disposition claims neither discovery
  nor priority.

## Native decisions still needed

1. Does Formal Conjectures treat the accepted equivalence plus external proof
   as enough to change `answer(sorry)` to `answer(True)` and category
   `research open` to `research solved` while the public source remains open?
2. Is a pinned Lean 4.29.1 external link acceptable without a direct Lean
   4.27.0 port or cross-repository import?

Until both decisions are explicit, retaining the evidence source-local is the
honest maintenance boundary.

## Nonclaims

- This disposition does not change Formal Conjectures or Erdős Problems.
- It does not claim a globally accepted solution, novelty, priority, or
  external mathematical review.
- It does not establish a Lean 4.27.0 port.
- A local accepted Claim is not upstream acceptance.
- The shared operator, machine, model family, source repositories, Lean
  kernel, and Mathlib dependencies remain explicit.
- It does not establish general Vela productivity or reviewer-efficiency.

## Reproduction

```bash
python3 execution/erdos-730-proof-boundary/verify.py \
  --report artifacts/fidelity/erdos-730-proof-boundary.v1.json

vela why . \
  vcl_8ef85fca44b8d9105e8c28b9ba702accd9365c4ff23d87466bf2b64853921345 \
  --json
```

This document is a source-local reuse disposition. It creates no Claim,
Verification, Decision, external review state, or authority effect.
