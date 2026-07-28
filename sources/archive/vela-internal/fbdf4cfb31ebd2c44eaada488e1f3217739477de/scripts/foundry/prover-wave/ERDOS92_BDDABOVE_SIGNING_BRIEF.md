# Erdos92 possible_f_values_BddAbove signing brief

Status: pending human review only. Do not sign from an agent session.

## Claim

`Erdos92.possible_f_values_BddAbove` closes the formal-conjectures `sorry`:

```lean
theorem possible_f_values_BddAbove (n : Nat) : BddAbove (possible_f_values n)
```

The proof shows the concrete bound `n - 1`. Given any witness set of `n` points
with the minimum equidistant property, choose a point in the nonempty set. Every
distance class around that point is a subset of `points.erase x`, whose cardinality
is `n - 1`, so the supremum defining `maxEquidistantPointsAt x points` is at most
`n - 1`.

## Source And Replay

Source corpus: `google-deepmind/formal-conjectures`, detached at
`upstream/main` commit `9b619575`.

Patch:

```bash
git -C /tmp/fc-prover-1074 apply /Users/williamblair/personal/vela/scripts/foundry/prover-wave/erdos92-possible-f-values-bddabove.patch
```

Kernel replay:

```bash
cd /Users/williamblair/personal/vela
target/release/vela foundry lean-run \
  --lean-dir /tmp/fc-prover-1074 \
  --module FormalConjectures/ErdosProblems/92.lean \
  --decl Erdos92.possible_f_values_BddAbove \
  --json
```

Observed result:

- `status`: `verified`
- `vlv`: `vlv_265c710fef7812b5`
- `vla`: `vla_710f20af5a8c9be4`
- axioms: `Classical.choice`, `Quot.sound`, `propext`
- `sorryAx`: absent

## Audit

Static scan over the closed proof body found no `sorry`, `native_decide`,
`decide +kernel`, `stop`, `axiom`, `unsafe`, or sole `rfl` proof.

Self-reference and vacuity check: the theorem target is `BddAbove
(possible_f_values n)`, not `True` or an `answer(sorry)` placeholder. The proof
uses the provided witness set, its nonemptiness, the cardinality hypothesis, and
the `sSup` bound on finite distance-class cardinalities.

Independent arithmetic check: no computed arithmetic step is part of this proof.
The only numeric reduction is the symbolic `points.card = n` rewrite into
`(points.erase x).card = n - 1`.

## Pending Proposal

Proposal id: `vpr_013d603c9b6044af`

Preview:

```bash
target/release/vela diff --frontier examples/prover-lane vpr_013d603c9b6044af
```

Current preview delta:

- kind: `finding.add`
- proposes finding: `vf_4a4537e9e5818ac6`
- shape if accepted: findings `7 -> 8`, events `7 -> 8`
- review warnings if accepted:
  - `condition.comparator_or_baseline@vf_4a4537e9e5818ac6`
  - `condition.endpoint@vf_4a4537e9e5818ac6`
  - `evidence.span_presence@vf_4a4537e9e5818ac6`

## Human Signing Command

If, and only if, Will accepts this pending finding:

```bash
target/release/vela sign --frontier examples/prover-lane vpr_013d603c9b6044af --yes \
  --reason "accept kernel-clean Erdos92 possible_f_values_BddAbove closure"
```

What remains pending or open after acceptance: the asymptotic Erdős #92 weak and
strong variants remain open. This proposal only closes the boundedness sanity
lemma.
