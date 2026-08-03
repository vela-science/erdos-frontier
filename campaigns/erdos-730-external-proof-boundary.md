# Erdős 730 external-proof-boundary campaign

## Objective

Determine whether the pinned complete Lean proof establishes the exact retained
Erdős 730 statement, preserve the Lean 4.29.1/4.27.0 boundary, and carry the
bounded conclusion through scoped Verification, human Decision, replay, and
handoff.

## Frozen entry state

- Frontier commit: `ea44055f33ec04509385454228fd6cba8fcfe562`
- Target: `erdos:730:external-proof-boundary`
- Packet root:
  `sha256:36dd946797305295d127d5c6fed23ffccd76609a8705f0155c9cf2f7f1c6e370`
- Output: `artifacts/fidelity/erdos-730-proof-boundary.v1.json`
- Verifier: `execution/erdos-730-proof-boundary/verify.py`
- External terminal theorem:
  `Erdos730.FullDensityTheorem.pairSet_infinite`
- External toolchain: Lean 4.29.1
- Formal Conjectures toolchain: Lean 4.27.0

The machine-readable Target contract is
[`targets/erdos-730-external-proof-boundary.json`](../targets/erdos-730-external-proof-boundary.json).

## Decision rationale

The pinned `lean-proofs` lineage contains a complete kernel-checked theorem
proving a stronger positive-density statement about consecutive central
binomial coefficients. Formal Conjectures and the retained public source still
call problem 730 open, the proof predates this campaign, and the two source
trees use different Lean versions. The bounded work therefore had to establish
source equivalence and preserve the toolchain boundary before any local
Standing change could be considered.

Mechanical replay was required to bind both repositories, reproduce terminal-
solve ancestry and exact theorem bytes, compile the external theorem and audit
under Lean 4.29.1, confirm the Formal Conjectures bytes and 4.27.0 environment,
and validate complete report coverage. Semantic review remained separate from
mechanical checking and could conclude only `equivalent`, `not_equivalent`, or
`indeterminate`.

## Outcome — 2026-08-03

The producer report concluded `equivalent` at
`sha256:42db39dd2b51e7821e02fc1acbb3e43cde83f269a8cb491f2925ad3aa233d106`.
The source-local verifier recomputed both Git trees and source roots, proved
terminal-solve ancestry and unchanged terminal bytes, scanned all 74 retained
modules for proof escapes, and compiled the terminal theorem and audit from a
clean detached checkout under Lean 4.29.1.

Submission `vsb_46bd0d7cef0d2fa6` retained that non-authoritative producer
result. Fresh source-first review produced requirement-satisfying scoped
Verification `vvr_3b6d523c55a24dc9`. Attributed human Decision event
`vev_0ab843df6ad373ec` accepted only Claim
`vcl_8ef85fca44b8d9105e8c28b9ba702accd9365c4ff23d87466bf2b64853921345`.
Strict replay at Frontier commit
`9ecb63bc97ccb8b403b4088e15c54499ab4e95f6` reproduces repository root
`sha256:821cf0d94778f647305107943572f4916a6cf63fe5ea12506a471fabc07b7474`.
No unrelated Standing changed.

The completed Target is no longer offered by `vela next`. The exact rooted
handoff is retained at
`execution/erdos-730-proof-boundary/post-decision-handoff.v1.json`, root
`sha256:e1236ab59f36ab655dbbfdc2bc6d147554afd36040f18a7e14d7762cad5916d7`.

## Independence and nonclaims

The producer and review shared the same human operator, machine, Codex model
family, source repositories, Lean kernel, and Mathlib. No external-participant
or organizational independence is claimed.

The outcome does not establish Vela-caused discovery, novelty, global solution
status, community acceptance, external mathematical review, or a native Lean
4.27.0 port. The external source statuses remain distinct from local Frontier
Standing.
