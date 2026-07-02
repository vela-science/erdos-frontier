# A standard check for statement review

**Status: proposal.** Written 2026-07-02, seeking feedback from the
formal-conjectures maintainers before any of it is built. Discussion:
[leanprover Zulip, #Formal conjectures](https://leanprover.zulipchat.com/#narrow/channel/524981-Formal-conjectures).

## The problem

Merging a conjecture statement into
[formal-conjectures](https://github.com/google-deepmind/formal-conjectures)
requires a maintainer to read it carefully against the source. Yaël Dillies
put numbers on it: roughly ten minutes per problem, a ~200-hour lower bound
for the Erdős corpus alone. The variable worth optimizing is **maintainer
review cycles per merged statement**: every round trip a reviewer spends on
something a machine or the author could have caught is a round trip not spent
on the one judgment that needs them, whether the formal statement faithfully
states the problem.

Two facts shape the design. First, most review comments are repetitive;
Moritz Firsching: "pretty much what we write during review is repetitive and
should just be in a checklist for the Author or their agents to tick off."
Second, faithfulness is exactly the property the toolchain does not check: a
statement can elaborate, pass every linter, and be wrong by meaning. The
miniF2F re-audit ([arXiv:2511.03108](https://arxiv.org/abs/2511.03108)) found
informal/formal discrepancies in over half of a benchmark's type-checking
statements.

## Principles

1. **Mechanical checks may gate; model output never does.** No LLM judgment
   becomes repo state, blocks a merge, or is reported as a verdict. This
   matches how every mature review bot converged (advisory commentary,
   deterministic gates) and how this repo's signed frontier already works:
   machines report facts, a named human signs judgment.
2. **One sticky comment per PR, edited in place.** The mathlib
   `PR_summary` pattern. Never comment-per-run; noise is why AI review
   workflows get disabled.
3. **Evidence or silence.** A claimed issue names the clause, the line, and
   the source text it conflicts with, or it is not posted.
4. **Checks earn their noise or get removed.** Rule-hit counts and review
   cycles are measured; anything that flags without changing outcomes is
   deleted.

## The layers

### L0. Author checklist

A "Before requesting review" section in
`FormalConjectures/ErdosProblems/README.md`, distilled from corrections that
actually recur in review (each line traces to a real review comment on a
merged PR):

- Quote erdosproblems.com verbatim in docstrings; do not paraphrase unless
  fixing a genuine error in the original.
- For solved problems, also quote the attribution sentence below the box
  (who solved it, where) verbatim.
- Search `FormalConjecturesForMathlib` and neighboring problem files before
  defining anything; notation and API often already exist.
- Meta-commentary belongs in the PR description, not the Lean file.
- New attribute or utility behavior needs demo tests in
  `FormalConjecturesTest`.

Zero infrastructure. The welcome bot already points contributors at this
README.

### L1. Statement facts

A deterministic sticky comment on ErdosProblems PRs, computed in CI, facts
only:

- per declaration: `@[category]`, `@[AMS]`, docstring presence (the existing
  linters already enforce these; the comment surfaces them per-PR);
- agreement between the file's category and erdosproblems.com's live status
  (the logic already exists in `scripts/check_erdos_status.py`);
- for any `formal_proof` link: the linked proof's axiom set, `sorry` state,
  and the Prop hypotheses it takes as parameters, from the same extractor
  behind this repository's audit and
  [FC#4368](https://github.com/google-deepmind/formal-conjectures/pull/4368).

This is the mechanical half of a review, precomputed. A reviewer opens the
PR and the facts are already on the table.

### L2. Behavioral probes

The strongest known fidelity checks act on the statement rather than reading
it ([Faithfulness Gap, arXiv:2606.16541](https://arxiv.org/abs/2606.16541):
LLM judges detected statement drift at 63%, behavioral probing at ~90%):

- **Trivial proof/disproof attempt.** Run a prover briefly against the
  statement and its negation. A genuinely open problem should survive both;
  a missing hypothesis usually does not. Precedent: Boris Alexeev's
  [Aristotle run on Erdős 56](https://xenaproject.wordpress.com/2025/12/05/formalization-of-erdos-problems/),
  where a size-2 counterexample exposed a missing hypothesis instantly.
- **Suspicious-pattern linters.** Vacuous hypotheses, trivially-true shapes,
  inconsistent hypothesis sets, in the mold of the repo's existing
  `ExistsImplicationLinter` and `AnswerLinter`. These are the only two
  semantic misformalization linters deployed anywhere in the Lean ecosystem;
  the pattern is proven and extensible.

Probe results are flags in the L1 comment for the human reviewer. A flag is
a reason to look, never a verdict.

### L3. The screening check

For contested or high-stakes statements: a curated, model-assisted check in
the format Nat Sothanaphan developed for solution claims on
erdosproblems.com, adapted to statement fidelity. The procedure, with his
hygiene imported wholesale:

1. **Fresh session, always.** The checking model never shares context with
   whoever produced the statement; a model re-reading its own work is
   convinced by it.
2. **Triage, then audit.** Overview of the statement and source; rank the
   places most worth scrutinizing (quantifier order, hypothesis strength,
   definitional unfoldings, domain conventions); audit each; one full pass.
   No "be adversarial" instruction; demanding errors exist produces
   hallucinated ones.
3. **Per-clause correspondence table.** Every quantifier, hypothesis, and
   conclusion of the formal statement mapped to the source text, one verdict
   per clause. After correcting any misreading, re-verify all clauses, not
   just the corrected one.
4. **Verdict lexicon.** "Check **found** no mismatch" (absence of findings)
   vs "check **claimed** a mismatch in clause X" (positive reports are
   themselves unverified claims). Never "the statement is faithful."
5. **Transcript published** with every result, plus the fixed disclaimer:
   this is a screening, not comprehensive, and not a confirmation stamp.

Anyone can run one; documenting the format is what makes results comparable
across people and time. Known failure modes to design against: sycophancy
toward the artifact ([BrokenMath, arXiv:2510.04721](https://arxiv.org/abs/2510.04721));
correlated errors across model runs, so prefer flag-union with human
adjudication over majority voting (the FrontierMath v2 audit found errors in
42% of problems that had already passed human review); and circularity, the
check must read the original source, not the repo's own docstring.

### L4. The human signature

Unchanged, and the point. Maintainer approval remains the only thing that
merges a statement. In this repository's terms: the machine tier reports
facts, and a statement-fidelity verdict exists only as a named reviewer's
signed event. Nothing in L0–L3 signs anything.

## Rollout

**Phase 1, no infrastructure.** The L0 checklist as a small PR to the
ErdosProblems README, plus L3-format self-reviews posted on my own open
batch PRs so maintainers can judge from real artifacts whether the format
saves cycles. Costs the maintainers nothing but a read.

**Phase 2, if Phase 1 reads as useful.** The L1 workflow behind a
`statement-check` label, run on ~10 PRs. Measure review cycles per merged
PR against the recent baseline. Adopt, adjust, or delete on the numbers.

**Phase 3, if Phase 2 pays.** L2 probes, added one at a time, each with its
own hit-rate ledger.

Kill criterion at every phase: anything that adds noise instead of removing
cycles goes.

## What this is not

- Not an AI reviewer. No model approves, requests changes, or gates.
- Not comment automation. One sticky comment, severity-floored, or nothing.
- Not a replacement for reading the mathematics. It clears the mechanical
  underbrush so the ten human minutes land on the judgment only a human can
  sign.

## Sources

Nat Sothanaphan's standard-check posts on the
[erdosproblems.com forum](https://www.erdosproblems.com/forum) (method,
verdict lexicon, calibration retrospectives) ·
[mathlib PR_summary workflow](https://github.com/leanprover-community/mathlib4/blob/master/.github/workflows/PR_summary.yml) ·
[FC's linter framework](https://github.com/google-deepmind/formal-conjectures/tree/main/FormalConjectures/Util/Linters) ·
[Alexeev, "Formalization of Erdős problems"](https://xenaproject.wordpress.com/2025/12/05/formalization-of-erdos-problems/) ·
[miniF2F-Lean Revisited](https://arxiv.org/abs/2511.03108) ·
[The Faithfulness Gap](https://arxiv.org/abs/2606.16541) ·
[BrokenMath](https://arxiv.org/abs/2510.04721) ·
[FormalAlign](https://arxiv.org/abs/2410.10135) ·
[Epoch AI, FrontierMath v2 audit](https://epoch.ai/frontiermath/the-benchmark) ·
[leanprover-community/intentions](https://github.com/leanprover-community/intentions)
(the claim/queue primitive, if review ever becomes a claimable task board).
