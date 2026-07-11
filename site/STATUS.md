# Erdős frontier — proof status

*Regenerated 2026-07-11 by [`erdos_frontier.py`](../erdos_frontier.py). Do not edit by hand.*

This is a **computed** view, not a hand-kept list. It joins erdosproblems.com, Formal Conjectures, hosted Lean proof indexes, live open PRs, and explicit human overrides on the problem number so the status cannot drift silently.

Proof-source marks: ᵖ = [`plby/lean-proofs`](https://github.com/plby/lean-proofs), ʲ = [`Jayyhk/erdos-lean`](https://github.com/Jayyhk/erdos-lean), ʷ = [`williamjblair/lean-proofs`](https://github.com/williamjblair/lean-proofs).

**Coverage:** all 496 problems Bloom marks formalized are tracked by plby ∪ Jayyhk ∪ williamjblair/lean-proofs ∪ FC. No gap.

Reconciled **1217** problems.

| status | count | meaning |
|---|---:|---|
| `statement` | 66 | **Write the FC statement + link.** A complete hosted proof exists, FC has no file yet. |
| `link` | 1 | **Add the `formal_proof` link.** FC already has the statement; the hosted proof just is not linked. |
| `needs-statement-update` | 1 | **Not a trivial link.** FC has a file, but the statement or answer needs a human update before linking. |
| `needs-human-match-check` | 2 | **Needs match-check.** A hosted proof exists, but the proof/statement relation has not been audited. |
| `mismatch` | 2 | **Skip for now.** The hosted proof is complete, but it does not prove the boxed FC statement. |
| `hypothesis-conditional` | 7 | **Do not link as complete.** The theorem carries a non-problem hypothesis even if `#print axioms` is clean. |
| `docstring` | 8 | **Docstring note, not a `formal_proof` tag.** The hosted proof is conditional, axiomatic, or trust-extended. |
| `partial` | 6 | **Partial proof.** Proves a variant, not the full erdosproblems statement. |
| `blocked-claim` | 3 | **Claimed outside an open PR.** Skip until the claim is resolved. |
| `in-pr` | 304 | **Claimed by an open FC PR.** Skip to avoid collisions. |
| `wont-fix` | 1 | **Maintainer marked `won't fix`.** Skip. |
| `defer` | 0 | **Deferred.** A human override says to leave this out of the next batch. |
| `done` | 109 | Already linked in FC. |
| `no-proof` | 707 | No hosted Lean proof to link yet. |

Human override judgments live in [`overrides.yaml`](overrides.yaml). They encode known claims, theorem mismatches, and conditional-proof traps that are not visible in the upstream machine-readable sources.


## `statement` — 66 problem(s)

**Write the FC statement + link.** A complete hosted proof exists, FC has no file yet.

[24](https://www.erdosproblems.com/24)ᵖʲ ([#4369](https://github.com/google-deepmind/formal-conjectures/pull/4369)) [71](https://www.erdosproblems.com/71)ʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [93](https://www.erdosproblems.com/93)ᵖʲ ([#4369](https://github.com/google-deepmind/formal-conjectures/pull/4369)) [164](https://www.erdosproblems.com/164)ᵖʲ ([#4369](https://github.com/google-deepmind/formal-conjectures/pull/4369)) [206](https://www.erdosproblems.com/206)ᵖʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [209](https://www.erdosproblems.com/209)ʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [314](https://www.erdosproblems.com/314)ᵖʲ ([#4369](https://github.com/google-deepmind/formal-conjectures/pull/4369)) [315](https://www.erdosproblems.com/315)ᵖʲ ([#4369](https://github.com/google-deepmind/formal-conjectures/pull/4369)) [328](https://www.erdosproblems.com/328)ʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [333](https://www.erdosproblems.com/333)ᵖʲ ([#4369](https://github.com/google-deepmind/formal-conjectures/pull/4369)) [353](https://www.erdosproblems.com/353)ʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [369](https://www.erdosproblems.com/369)ᵖʲ ([#4369](https://github.com/google-deepmind/formal-conjectures/pull/4369)) [401](https://www.erdosproblems.com/401)ᵖʲ ([#4369](https://github.com/google-deepmind/formal-conjectures/pull/4369)) [403](https://www.erdosproblems.com/403)ʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [426](https://www.erdosproblems.com/426)ᵖʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [429](https://www.erdosproblems.com/429)ᵖʲ ([#4369](https://github.com/google-deepmind/formal-conjectures/pull/4369)) [435](https://www.erdosproblems.com/435)ᵖʲ ([#4369](https://github.com/google-deepmind/formal-conjectures/pull/4369)) [443](https://www.erdosproblems.com/443)ᵖʲ ([#4371](https://github.com/google-deepmind/formal-conjectures/pull/4371)) [464](https://www.erdosproblems.com/464)ʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [484](https://www.erdosproblems.com/484)ᵖʲ ([#4371](https://github.com/google-deepmind/formal-conjectures/pull/4371)) [487](https://www.erdosproblems.com/487)ᵖʲ ([#4371](https://github.com/google-deepmind/formal-conjectures/pull/4371)) [497](https://www.erdosproblems.com/497)ᵖʲ ([#4371](https://github.com/google-deepmind/formal-conjectures/pull/4371)) [498](https://www.erdosproblems.com/498)ᵖʲ ([#4371](https://github.com/google-deepmind/formal-conjectures/pull/4371)) [502](https://www.erdosproblems.com/502)ᵖʲ ([#4371](https://github.com/google-deepmind/formal-conjectures/pull/4371)) [512](https://www.erdosproblems.com/512)ʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [537](https://www.erdosproblems.com/537)ᵖʲ ([#4371](https://github.com/google-deepmind/formal-conjectures/pull/4371)) [582](https://www.erdosproblems.com/582)ᵖʲ ([#4371](https://github.com/google-deepmind/formal-conjectures/pull/4371)) [618](https://www.erdosproblems.com/618)ᵖʲ ([#4371](https://github.com/google-deepmind/formal-conjectures/pull/4371)) [621](https://www.erdosproblems.com/621)ᵖʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [639](https://www.erdosproblems.com/639)ᵖʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [646](https://www.erdosproblems.com/646)ᵖʲ ([#4371](https://github.com/google-deepmind/formal-conjectures/pull/4371)) [648](https://www.erdosproblems.com/648)ᵖʲ ([#4385](https://github.com/google-deepmind/formal-conjectures/pull/4385)) [649](https://www.erdosproblems.com/649)ᵖʲ [658](https://www.erdosproblems.com/658)ᵖʲ [666](https://www.erdosproblems.com/666)ᵖʲ [674](https://www.erdosproblems.com/674)ᵖʲ [692](https://www.erdosproblems.com/692)ᵖʲ [698](https://www.erdosproblems.com/698)ᵖʲ [716](https://www.erdosproblems.com/716)ʲ [751](https://www.erdosproblems.com/751)ᵖʲ [753](https://www.erdosproblems.com/753)ᵖʲ [756](https://www.erdosproblems.com/756)ᵖʲ [760](https://www.erdosproblems.com/760)ᵖʲ [762](https://www.erdosproblems.com/762)ᵖʲ [765](https://www.erdosproblems.com/765)ʲ [775](https://www.erdosproblems.com/775)ᵖʲ [798](https://www.erdosproblems.com/798)ᵖʲ [818](https://www.erdosproblems.com/818)ᵖʲ [844](https://www.erdosproblems.com/844)ᵖʲ [862](https://www.erdosproblems.com/862)ᵖʲ [867](https://www.erdosproblems.com/867)ᵖʲ [898](https://www.erdosproblems.com/898)ᵖʲ [905](https://www.erdosproblems.com/905)ᵖʲ [907](https://www.erdosproblems.com/907)ᵖʲ [914](https://www.erdosproblems.com/914)ᵖʲ [927](https://www.erdosproblems.com/927)ʲ [947](https://www.erdosproblems.com/947)ᵖʲ [958](https://www.erdosproblems.com/958)ᵖʲ [966](https://www.erdosproblems.com/966)ᵖʲ [967](https://www.erdosproblems.com/967)ᵖʲ [974](https://www.erdosproblems.com/974)ᵖʲ [990](https://www.erdosproblems.com/990)ᵖʲ [1134](https://www.erdosproblems.com/1134)ʲ [1136](https://www.erdosproblems.com/1136)ᵖʲ [1190](https://www.erdosproblems.com/1190)ᵖʲ [1193](https://www.erdosproblems.com/1193)ᵖʲ

## `link` — 1 problem(s)

**Add the `formal_proof` link.** FC already has the statement; the hosted proof just is not linked.

[617](https://www.erdosproblems.com/617)ʷ

## `needs-statement-update` — 1 problem(s)

**Not a trivial link.** FC has a file, but the statement or answer needs a human update before linking.

- [330](https://www.erdosproblems.com/330)ʲ ([#4367](https://github.com/google-deepmind/formal-conjectures/pull/4367)) — FC already has an open answer-shaped statement; resolving this is not a trivial link-only update.

## `needs-human-match-check` — 2 problem(s)

**Needs match-check.** A hosted proof exists, but the proof/statement relation has not been audited.

- [150](https://www.erdosproblems.com/150)ᵖʲ — Previously dropped from a batch because no hosted proof cleanly matched the boxed statement.
- [202](https://www.erdosproblems.com/202)ᵖʲ — Previously dropped from a batch because no hosted proof cleanly matched the boxed statement.

## `mismatch` — 2 problem(s)

**Skip for now.** The hosted proof is complete, but it does not prove the boxed FC statement.

- [214](https://www.erdosproblems.com/214)ᵖʲ — Skip until a hosted proof matches the boxed FC statement.
- [337](https://www.erdosproblems.com/337)ᵖʲ — Skip until a hosted proof matches the boxed FC statement.

## `hypothesis-conditional` — 7 problem(s)

**Do not link as complete.** The theorem carries a non-problem hypothesis even if `#print axioms` is clean.

- [94](https://www.erdosproblems.com/94)ᵖʲ — Do not add a formal_proof link; document or wait for an unconditional theorem.
- [115](https://www.erdosproblems.com/115)ᵖʲ — Do not add a formal_proof link; document or wait for an unconditional theorem.
- [205](https://www.erdosproblems.com/205)ᵖʲ — Do not add a formal_proof link; document or wait for an unconditional theorem.
- [785](https://www.erdosproblems.com/785)ᵖʲ — Do not add a formal_proof link; document or wait for an unconditional theorem.
- [964](https://www.erdosproblems.com/964)ᵖʲ — Do not add a formal_proof link; document or wait for an unconditional theorem.
- [1148](https://www.erdosproblems.com/1148)ᵖʲ — Do not add a formal_proof link; document or wait for an unconditional theorem.
- [1187](https://www.erdosproblems.com/1187)ᵖ — Do not add a formal_proof link; document or wait for an unconditional theorem.

## `docstring` — 8 problem(s)

**Docstring note, not a `formal_proof` tag.** The hosted proof is conditional, axiomatic, or trust-extended.

[192](https://www.erdosproblems.com/192)ʲ [231](https://www.erdosproblems.com/231)ʲ [237](https://www.erdosproblems.com/237)ᵖʲ [490](https://www.erdosproblems.com/490)ᵖʲ [610](https://www.erdosproblems.com/610)ʲ [659](https://www.erdosproblems.com/659)ᵖʲ [694](https://www.erdosproblems.com/694)ᵖʲ [1197](https://www.erdosproblems.com/1197)ᵖʲ

## `partial` — 6 problem(s)

**Partial proof.** Proves a variant, not the full erdosproblems statement.

[264](https://www.erdosproblems.com/264)ᵖ [368](https://www.erdosproblems.com/368)ᵖ [485](https://www.erdosproblems.com/485)ᵖ [866](https://www.erdosproblems.com/866)ᵖ [1056](https://www.erdosproblems.com/1056)ᵖ [1095](https://www.erdosproblems.com/1095)ᵖ

## `blocked-claim` — 3 problem(s)

**Claimed outside an open PR.** Skip until the claim is resolved.

- [45](https://www.erdosproblems.com/45)ᵖʲ — Claimed by a human in the FC issue thread; skip to avoid collision.
- [46](https://www.erdosproblems.com/46)ᵖʲ — Claimed by a human in the FC issue thread; skip to avoid collision.
- [613](https://www.erdosproblems.com/613)ᵖʲ ([#4354](https://github.com/google-deepmind/formal-conjectures/pull/4354)) — Claimed by Paul-Lez in an FC issue comment.

## `wont-fix` — 1 problem(s)

**Maintainer marked `won't fix`.** Skip.

- [678](https://www.erdosproblems.com/678)ᵖʲ — Maintainer flagged the hosted proof as not actually complete.

## `defer` — 0 problem(s)

**Deferred.** A human override says to leave this out of the next batch.

_none_

## statement fidelity — 64 signed verdict(s)

Signed statement-fidelity verdicts: a reviewer attests whether the formal theorem faithfully states the boxed problem. A signed verdict supersedes the computed bucket and any matching `overrides.yaml` row.

| problem | verdict | source | reviewer | theorem |
|---|---|---|---|---|
| [24](https://www.erdosproblems.com/24) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/24) |
| [31](https://www.erdosproblems.com/31) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos31.erdos_31) |
| [34](https://www.erdosproblems.com/34) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos34.erdos_34) |
| [47](https://www.erdosproblems.com/47) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos47.erdos_47) |
| [71](https://www.erdosproblems.com/71) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/71) |
| [93](https://www.erdosproblems.com/93) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/93) |
| [134](https://www.erdosproblems.com/134) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos134.erdos_134) |
| [164](https://www.erdosproblems.com/164) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/164) |
| [178](https://www.erdosproblems.com/178) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos178.erdos_178) |
| [199](https://www.erdosproblems.com/199) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos199.erdos_199) |
| [205](https://www.erdosproblems.com/205) | `variant` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/205) |
| [206](https://www.erdosproblems.com/206) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/206) |
| [209](https://www.erdosproblems.com/209) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/209) |
| [214](https://www.erdosproblems.com/214) | `unfaithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/214) |
| [224](https://www.erdosproblems.com/224) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos224.erdos_224) |
| [226](https://www.erdosproblems.com/226) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos226.erdos_226) |
| [246](https://www.erdosproblems.com/246) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos246.erdos_246) |
| [258](https://www.erdosproblems.com/258) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos258.erdos_258) |
| [280](https://www.erdosproblems.com/280) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos280.erdos_280) |
| [281](https://www.erdosproblems.com/281) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos281.erdos_281) |
| [296](https://www.erdosproblems.com/296) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos296.erdos_296) |
| [314](https://www.erdosproblems.com/314) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/314) |
| [315](https://www.erdosproblems.com/315) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/315) |
| [328](https://www.erdosproblems.com/328) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/328) |
| [333](https://www.erdosproblems.com/333) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/333) |
| [337](https://www.erdosproblems.com/337) | `unfaithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/337) |
| [353](https://www.erdosproblems.com/353) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/353) |
| [363](https://www.erdosproblems.com/363) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos363.erdos_363) |
| [369](https://www.erdosproblems.com/369) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/369) |
| [401](https://www.erdosproblems.com/401) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/401) |
| [403](https://www.erdosproblems.com/403) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/403) |
| [419](https://www.erdosproblems.com/419) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos419.erdos_419) |
| [426](https://www.erdosproblems.com/426) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/426) |
| [429](https://www.erdosproblems.com/429) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/429) |
| [435](https://www.erdosproblems.com/435) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/435) |
| [443](https://www.erdosproblems.com/443) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/443) |
| [453](https://www.erdosproblems.com/453) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos453.erdos_453) |
| [464](https://www.erdosproblems.com/464) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/464) |
| [476](https://www.erdosproblems.com/476) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos476.erdos_476) |
| [484](https://www.erdosproblems.com/484) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/484) |
| [487](https://www.erdosproblems.com/487) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/487) |
| [493](https://www.erdosproblems.com/493) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos493.erdos_493) |
| [497](https://www.erdosproblems.com/497) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/497) |
| [498](https://www.erdosproblems.com/498) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/498) |
| [502](https://www.erdosproblems.com/502) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/502) |
| [512](https://www.erdosproblems.com/512) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/512) |
| [519](https://www.erdosproblems.com/519) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos519.erdos_519) |
| [532](https://www.erdosproblems.com/532) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos532.erdos_532) |
| [537](https://www.erdosproblems.com/537) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/537) |
| [540](https://www.erdosproblems.com/540) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos540.erdos_540) |
| [582](https://www.erdosproblems.com/582) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/582) |
| [618](https://www.erdosproblems.com/618) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/618) |
| [621](https://www.erdosproblems.com/621) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/621) |
| [639](https://www.erdosproblems.com/639) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/639) |
| [646](https://www.erdosproblems.com/646) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/646) |
| [648](https://www.erdosproblems.com/648) | `faithful` | local | reviewer:will-blair | [theorem](https://www.erdosproblems.com/648) |
| [729](https://www.erdosproblems.com/729) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos729.erdos_729) |
| [871](https://www.erdosproblems.com/871) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos871.erdos_871) |
| [904](https://www.erdosproblems.com/904) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos904.erdos_904) |
| [923](https://www.erdosproblems.com/923) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos923.erdos_923) |
| [1090](https://www.erdosproblems.com/1090) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos1090.erdos_1090) |
| [1125](https://www.erdosproblems.com/1125) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos1125.erdos_1125) |
| [1126](https://www.erdosproblems.com/1126) | `faithful` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos1126.erdos_1126) |
| [1148](https://www.erdosproblems.com/1148) | `variant` | local | reviewer:will-blair | [theorem](https://google-deepmind.github.io/formal-conjectures/theorem/?name=Erdos1148.erdos_1148) |
