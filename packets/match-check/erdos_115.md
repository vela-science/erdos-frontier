# Match-check packet — Erdős problem 115

Computed bucket: `hypothesis-conditional`

## Machine evidence (L1) — deterministic, no human/model judgment

- Verdict: `conditional`
- **Undischarged named assumptions** (theorem parameters — `#print axioms` cannot see these):
  - `a : Erdos115.EremenkoLempertAtZeroStatement n`
  → the proof is conditional on the above; it is NOT an unconditional resolution even if kernel-clean.

## 1. Upstream statement

- Boxed problem: https://www.erdosproblems.com/115
- LaTeX source: https://www.erdosproblems.com/latex/115
- Upstream state: `proved (Lean)`

## 2. FC theorem

- No Formal Conjectures file for this problem yet.

## 3. Hosted theorem signature(s)

- plby/lean-proofs — state `complete` (complete)
  - https://github.com/plby/lean-proofs/blob/main/src/v4.29.1/ErdosProblems/Erdos115.lean
- Jayyhk/erdos-lean — state `complete` (complete)
  - https://github.com/Jayyhk/erdos-lean/blob/main/problems/115/Erdos115.lean

## Decision

- [ ] faithful — the formal theorem states the boxed problem; safe to link.
- [ ] variant — proves a weaker/variant statement; do not link as complete.
- [ ] unfaithful — does not prove the boxed problem; mismatch.
