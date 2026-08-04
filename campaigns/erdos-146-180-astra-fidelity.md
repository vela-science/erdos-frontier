# Erdős 146 and 180 Astra statement-fidelity campaign

## Objective

Complete source-local definition, quantifier, hypothesis, conclusion,
source-timing, discrepancy, and nonclaim matrices for the two Chapter 10
Erdős-facing Astra results without converting producer analysis or kernel
passage into scientific Standing.

This campaign is complementary to the existing Erdős 183 human checkpoint.
It creates no Target, Submission, Verification, Proposal, Decision, Event, or
accepted Claim.

## Exact inputs

- Retained statement snapshot:
  `sources/statements.v1.json` at commit
  `3abe642436ea7692a54e1f6008d5e8b05a8c06eb`, root
  `sha256:dd66cd1de41db64b13d5c2d1f0e486c722924ee2a7d679af3a93bc67f3185ac4`.
- Source-status observation: `teorth/erdosproblems` commit
  `8138974387d9030542daabe67faaa33eff9356f8`, tree
  `7ed44c260d7eb63a067cf5a16afdb645d494ef06`, problems root
  `sha256:a4358d57b591fc92c75981c160a11f43a561de6b5e8478d8f9629511759a9213`.
- Astra source: `openai/ten-proofs` commit
  `29362184c2b698c1b279bc85b3957ee813646c63`, tree
  `730bf2c6a13dbb96606024c5fd681a48633fb393`.
- Manuscript root:
  `sha256:64b900d5fae6fe22f2ae1b8e3b712d20055194a6c81cf343a2455e5898ac7dd6`.
- Complete native replay root:
  `sha256:5a60c3be27036c65a6a37bf55dce71abcb024cfecece92b8e7dcaf1324b095d0`.

## Producer results

### Erdős 146

Conclusion: **faithful**, pending separately scoped Verification.

The retained induced-subgraph definition of `r`-degeneracy, the manuscript's
subgraph formulation, and Lean's finite-vertex-set definition are equivalent.
The formal conjecture quantifies over the meaningful positive-`r` domain and
uses the exact `O(n^(2-1/r))` conclusion. The retained counterexample is
stronger than required: one connected bipartite 2-degenerate graph has
eventual extremal growth at least `c n^(3/2+epsilon)`.

Report:
`artifacts/fidelity/erdos-146-astra-fidelity.v1.json`, file root
`sha256:7180b9a43e0465cce9afaad85ff40ebf1cdb91ddf536c000de6bfbbf423a98c2`.

### Erdős 180

Conclusion: **qualified mismatch**, pending separately scoped Verification and
source-correction review.

The retained statement asks the unrestricted finite-family question. The
manuscript explicitly says that this original form has simple counterexamples,
then states a corrected conjecture for nonempty families whose members all
contain cycles. Lean formalizes that corrected predicate. These predicates are
not identical.

The consequence is still strong: the formal witness is a nonempty family of
connected bipartite cyclic graphs with family extremal number
`O(n^(4/3-1/48))` while every member has extremal number
`Omega(n^(4/3))`. The same family refutes both the corrected conjecture and the
broader retained question. The mismatch concerns source/formal predicate
identity, not the validity of that consequence.

Report:
`artifacts/fidelity/erdos-180-astra-fidelity.v1.json`, file root
`sha256:a8758344f24ad00f0bf5c4d38e77105bc8ceef25aff0c3daa36f7e6f6a9766a4`.

## Next valid actions

1. Run one separately scoped, source-first Verification of both report roots,
   including the induced/subgraph equivalence for 146 and the corrected-source
   boundary for 180.
2. If that Verification passes, prepare a distinct Erdős 180 source-correction
   packet that preserves both formulations and their chronology. Do not
   overwrite the original question or infer a Decision.
3. Keep the existing Erdős 183 Proposal pending until human repository
   authority explicitly accepts, rejects, or documents deferral.
4. Feed only verified, consequence-complete conclusions into the cross-release
   Astra map. Do not create an Astra Frontier or bundle three independent
   authority choices into one Decision.

## Nonclaims

- The reports do not independently re-prove the manuscript.
- Comparator, Nanoda, and Lean passage are not statement-fidelity Decisions.
- No novelty, priority, citation completeness, community acceptance, or global
  solution status is established.
- The producer, replay, source, operator, machine lineage, Lean kernel, and
  Mathlib dependencies are shared rather than externally independent.
- This campaign document and its report files do not change Standing.
