# Match-check packet — Erdős problem 94

Computed bucket: `hypothesis-conditional`

## Machine evidence (L1) — deterministic, no human/model judgment

- Verdict: `conditional`
- **Undischarged named assumptions** (theorem parameters — `#print axioms` cannot see these):
  - `hconv : Erdos94.ConvexPosition P`
  → the proof is conditional on the above; it is NOT an unconditional resolution even if kernel-clean.

## 1. Upstream statement

- Boxed problem: https://www.erdosproblems.com/94
- LaTeX source: https://www.erdosproblems.com/latex/94
- Upstream state: `proved (Lean)`

## 2. FC theorem

- No Formal Conjectures file for this problem yet.

## 3. Hosted theorem signature(s)

- plby/lean-proofs — state `complete` (complete)
  - https://github.com/plby/lean-proofs/blob/main/src/v4.29.1/ErdosProblems/Erdos94.lean
- Jayyhk/erdos-lean — state `complete` (complete)
  - https://github.com/Jayyhk/erdos-lean/blob/main/problems/94/Erdos94.lean

## Decision

- [ ] faithful — the formal theorem states the boxed problem; safe to link.
- [ ] variant — proves a weaker/variant statement; do not link as complete.
- [ ] unfaithful — does not prove the boxed problem; mismatch.
