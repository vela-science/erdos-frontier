# The screening check, adapted to statements

Nat Sothanaphan screens claimed solutions at
[erdosproblems.com](https://www.erdosproblems.com/forum) with a structured,
model-assisted read: the transcript is always published, and the result is
reported as a screening, never a verdict. This page writes that procedure
down and adapts it to a different target: whether a formal Lean statement
faithfully states the problem it names.

The procedure is reconstructed from his forum posts, so details may be off;
corrections welcome.

## Why statements need it

The Lean kernel guarantees a proof, not a meaning. A statement can elaborate,
pass every linter, and still say something other than the problem; when the
miniF2F benchmark was re-audited
([arXiv:2511.03108](https://arxiv.org/abs/2511.03108)), over half of its
type-checking statements disagreed with their informal originals. For
solution claims the screening runs in front of a human referee. For
statements it runs in front of nothing: there is no kernel for faithfulness.
That argues for more structure, not less.

## The procedure

| step | rule | why |
|---|---|---|
| 1 | fresh model session, every time | a model sharing context with whoever produced the statement is convinced by its own reading |
| 2 | overview → rank the riskiest spots (quantifier order, hypothesis strength, definitional unfolding) → audit each → one full pass | ranking risks produces careful scrutiny; a "be adversarial" instruction produces hallucinated errors |
| 3 | per-clause table: every quantifier, hypothesis, and conclusion mapped to source text, one verdict per clause | mismatches hide in single clauses; after correcting any misreading, re-verify **every** clause |
| 4 | say the check "**found** no mismatch" or "**claimed** a mismatch in clause X", never "the statement is faithful" | positive error reports are themselves unverified claims |
| 5 | publish the transcript, with the standing disclaimer: a screening, not comprehensive, not a confirmation stamp | anyone can audit the prompt and the reasoning behind a verdict |

Statements are better targets for this than papers in one respect: they are
short and their clauses are enumerable, so the per-clause table can be
complete, and the length-dependent reliability decay that limits screening on
long writeups mostly disappears.

Two probes complement the read, because acting on a statement catches more
than reading it (LLM judges caught 63% of statement drift in the
[Faithfulness Gap](https://arxiv.org/abs/2606.16541) measurements; behavioral
probes about 90%):

- run a prover briefly against the statement *and its negation*: a genuinely
  open problem survives both, and a missing hypothesis usually doesn't.
  Boris Alexeev
  [ran Aristotle against Erdős 56](https://xenaproject.wordpress.com/2025/12/05/formalization-of-erdos-problems/)
  and a size-2 counterexample exposed the missing hypothesis;
- have a fresh model back-translate the Lean into English *without seeing
  the informal original*, then compare the two English statements.

## Running one

1. Open a fresh session with a capable model. Paste the problem's source
   text (from erdosproblems.com or the cited paper, not the repo's
   docstring) and the formal statement. Nothing else; no PR discussion, no
   author notes.
2. Ask for an overview: what each side says, in the model's own words,
   before any comparison.
3. Ask it to rank the places most worth scrutinizing, then work through
   them one at a time.
4. Ask for the per-clause table and check it yourself as it fills in:

   | clause | source says | formal statement says | verdict |
   |---|---|---|---|
   | *each quantifier* | *quoted source text* | *the formal counterpart* | *found no mismatch, or claimed: …* |
   | *each hypothesis* | *…* | *…* | *…* |
   | *the conclusion* | *…* | *…* | *…* |

   If any clause gets corrected along the way, re-run the whole table.
5. One full pass over both texts, then write the result in found/claimed
   language and link the transcript.

A screening on a statement takes minutes, not hours; the artifact is short
and the clauses run out.

## Known failure modes

| failure mode | evidence | guard |
|---|---|---|
| the model confirms whatever artifact is in front of it | [BrokenMath](https://arxiv.org/abs/2510.04721): 29% sycophantic-proof rate, best model tested | ask what does *not* match, never "verify this is right" |
| independent runs share blind spots | [FrontierMath v2 audit](https://epoch.ai/frontiermath/the-benchmark): errors in 42% of problems that had passed human review | take the union of flags and have a human adjudicate each; no majority voting |
| circularity | models citing a site's own status as evidence a problem is open | the check reads the original source, never the repo's docstring |
| one clause corrected, the rest assumed fine | a screening that fixed one misread condition and never re-checked the condition it had already passed | step 3's re-verify-all rule |

## What a screening never does

A screening informs; it does not decide. In
[formal-conjectures](https://github.com/google-deepmind/formal-conjectures),
maintainer approval merges a statement. On
[erdos-frontier](https://erdos.constellate.science/method.html), a
statement-fidelity verdict exists only as a named reviewer's signed event.
The screening's output is provenance for those decisions, nothing more.

First runs of this format: self-reviews on my own open formal-conjectures
statement PRs. The broader review-process context lives in
[STANDARD_CHECK.md](STANDARD_CHECK.md).
