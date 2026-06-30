# Match-check packet — Erdős problem 785

Computed bucket: `hypothesis-conditional`

## Machine evidence (L1) — deterministic, no human/model judgment

- Verdict: `conditional`
- **Undischarged named assumptions** (theorem parameters — `#print axioms` cannot see these):
  - `h_hyp : Erdos785.exact_complements A B`
  → the proof is conditional on the above; it is NOT an unconditional resolution even if kernel-clean.

## 1. Upstream statement

- Boxed problem: https://www.erdosproblems.com/785
- LaTeX source: https://www.erdosproblems.com/latex/785
- Upstream state: `proved (Lean)`

## 2. FC theorem

- No Formal Conjectures file for this problem yet.

## 3. Hosted theorem signature(s)

- plby/lean-proofs — state `complete` (complete)
  - https://github.com/plby/lean-proofs/blob/main/src/v4.29.1/ErdosProblems/Erdos785.lean
- Jayyhk/erdos-lean — state `complete` (complete)
  - https://github.com/Jayyhk/erdos-lean/blob/main/problems/785/Erdos785.lean

## Decision

- [ ] faithful — the formal theorem states the boxed problem; safe to link.
- [ ] variant — proves a weaker/variant statement; do not link as complete.
- [ ] unfaithful — does not prove the boxed problem; mismatch.
