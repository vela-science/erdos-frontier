# Erdős ↔ Formal Conjectures sync status

*Regenerated 2026-06-26 by [`fc-sync-status.py`](fc-sync-status.py). Do not edit by hand.*

This is a **computed** view, not a hand-kept list. It joins the machine-readable sources on the problem number so the status can't drift:

- [erdosproblems.com](https://www.erdosproblems.com) status ([`problems.yaml`](https://github.com/teorth/erdosproblems/blob/main/data/problems.yaml))
- Formal Conjectures' own [`conjectures.json`](https://google-deepmind.github.io/formal-conjectures/data/conjectures.json) (has-a-file + `formalProofLink`)
- hosted proofs from [`plby/lean-proofs`](https://github.com/plby/lean-proofs/blob/main/data/sources.yaml) (ᵖ) and [`Jayyhk/erdos-lean`](https://github.com/Jayyhk/erdos-lean/blob/main/data/problems.yaml) (ʲ), with their `conditional` / `axiomatic` / `trust_extended` flags

It also folds in the live set of open FC pull requests, so it never points at in-flight work. The ᵖ / ʲ marks after each problem show which collection hosts the proof.

Reconciled **1217** problems.

| status | count | meaning |
|---|---:|---|
| `statement` | 93 | **Write the FC statement + link.** A complete hosted proof exists, FC has no file yet. The #3998 batch. |
| `link` | 3 | **Add the `formal_proof` link.** FC already has the statement; the hosted proof just isn't linked. |
| `docstring` | 11 | **Docstring note, not a `formal_proof` tag.** The hosted proof is conditional (assumes an unformalized axiom) or axiomatic / trust-extended. |
| `partial` | 8 | **Partial proof.** Proves a specific variant, not the full erdosproblems statement. May be linkable to that FC variant; needs a per-problem look (per @plby). |
| `in-pr` | 30 | **Claimed.** An open FC pull request (or a tracked issue claim) already covers this. |
| `wont-fix` | 1 | **Maintainer marked `won't fix`** (e.g. the hosted proof is not actually complete). Skip it. |
| `done` | 86 | Already linked in FC. |
| `no-proof` | 985 | No hosted Lean proof to link (nothing to do here yet). |

*A short manual list carries two maintainer calls that live in issue comments rather than the structured sources: 678 (`wont-fix`, mo271 flagged the proof as not actually complete) and 613 (`in-pr`, claimed by Paul-Lez). Everything else is computed.*


## `statement` — 93 problem(s)

**Write the FC statement + link.** A complete hosted proof exists, FC has no file yet. The #3998 batch.

[24](https://www.erdosproblems.com/24)ᵖʲ [31](https://www.erdosproblems.com/31)ᵖʲ [34](https://www.erdosproblems.com/34)ᵖʲ [45](https://www.erdosproblems.com/45)ᵖʲ [46](https://www.erdosproblems.com/46)ᵖʲ [47](https://www.erdosproblems.com/47)ᵖʲ [71](https://www.erdosproblems.com/71)ʲ [93](https://www.erdosproblems.com/93)ᵖʲ [94](https://www.erdosproblems.com/94)ᵖʲ [115](https://www.erdosproblems.com/115)ᵖʲ [150](https://www.erdosproblems.com/150)ᵖʲ [164](https://www.erdosproblems.com/164)ᵖʲ [199](https://www.erdosproblems.com/199)ᵖʲ [202](https://www.erdosproblems.com/202)ᵖʲ [205](https://www.erdosproblems.com/205)ᵖʲ [206](https://www.erdosproblems.com/206)ᵖʲ [209](https://www.erdosproblems.com/209)ʲ [214](https://www.erdosproblems.com/214)ᵖʲ [224](https://www.erdosproblems.com/224)ᵖʲ [226](https://www.erdosproblems.com/226)ᵖʲ [246](https://www.erdosproblems.com/246)ᵖʲ [280](https://www.erdosproblems.com/280)ᵖʲ [281](https://www.erdosproblems.com/281)ᵖʲ [296](https://www.erdosproblems.com/296)ᵖʲ [314](https://www.erdosproblems.com/314)ᵖʲ [315](https://www.erdosproblems.com/315)ᵖʲ [328](https://www.erdosproblems.com/328)ʲ [333](https://www.erdosproblems.com/333)ᵖʲ [337](https://www.erdosproblems.com/337)ᵖʲ [353](https://www.erdosproblems.com/353)ʲ [363](https://www.erdosproblems.com/363)ᵖʲ [369](https://www.erdosproblems.com/369)ᵖʲ [401](https://www.erdosproblems.com/401)ᵖʲ [403](https://www.erdosproblems.com/403)ʲ [419](https://www.erdosproblems.com/419)ᵖʲ [426](https://www.erdosproblems.com/426)ᵖʲ [429](https://www.erdosproblems.com/429)ᵖʲ [435](https://www.erdosproblems.com/435)ᵖʲ [443](https://www.erdosproblems.com/443)ᵖʲ [453](https://www.erdosproblems.com/453)ᵖʲ [464](https://www.erdosproblems.com/464)ʲ [476](https://www.erdosproblems.com/476)ᵖʲ [481](https://www.erdosproblems.com/481)ᵖʲ [484](https://www.erdosproblems.com/484)ᵖʲ [487](https://www.erdosproblems.com/487)ᵖʲ [497](https://www.erdosproblems.com/497)ᵖʲ [498](https://www.erdosproblems.com/498)ᵖʲ [502](https://www.erdosproblems.com/502)ᵖʲ [512](https://www.erdosproblems.com/512)ʲ [519](https://www.erdosproblems.com/519)ᵖʲ [537](https://www.erdosproblems.com/537)ᵖʲ [540](https://www.erdosproblems.com/540)ᵖʲ [582](https://www.erdosproblems.com/582)ᵖʲ [618](https://www.erdosproblems.com/618)ᵖʲ [621](https://www.erdosproblems.com/621)ᵖʲ [639](https://www.erdosproblems.com/639)ᵖʲ [646](https://www.erdosproblems.com/646)ᵖʲ [648](https://www.erdosproblems.com/648)ᵖʲ [649](https://www.erdosproblems.com/649)ᵖʲ [666](https://www.erdosproblems.com/666)ᵖʲ [674](https://www.erdosproblems.com/674)ᵖʲ [692](https://www.erdosproblems.com/692)ᵖʲ [698](https://www.erdosproblems.com/698)ᵖʲ [716](https://www.erdosproblems.com/716)ʲ [751](https://www.erdosproblems.com/751)ᵖʲ [753](https://www.erdosproblems.com/753)ᵖʲ [756](https://www.erdosproblems.com/756)ᵖʲ [760](https://www.erdosproblems.com/760)ᵖʲ [762](https://www.erdosproblems.com/762)ᵖʲ [765](https://www.erdosproblems.com/765)ʲ [775](https://www.erdosproblems.com/775)ᵖʲ [785](https://www.erdosproblems.com/785)ᵖʲ [798](https://www.erdosproblems.com/798)ᵖʲ [818](https://www.erdosproblems.com/818)ᵖʲ [844](https://www.erdosproblems.com/844)ᵖʲ [862](https://www.erdosproblems.com/862)ᵖʲ [867](https://www.erdosproblems.com/867)ᵖʲ [898](https://www.erdosproblems.com/898)ᵖʲ [905](https://www.erdosproblems.com/905)ᵖʲ [907](https://www.erdosproblems.com/907)ᵖʲ [914](https://www.erdosproblems.com/914)ᵖʲ [927](https://www.erdosproblems.com/927)ʲ [947](https://www.erdosproblems.com/947)ᵖʲ [958](https://www.erdosproblems.com/958)ᵖʲ [966](https://www.erdosproblems.com/966)ᵖʲ [967](https://www.erdosproblems.com/967)ᵖʲ [974](https://www.erdosproblems.com/974)ᵖʲ [990](https://www.erdosproblems.com/990)ᵖʲ [1134](https://www.erdosproblems.com/1134)ʲ [1136](https://www.erdosproblems.com/1136)ᵖʲ [1190](https://www.erdosproblems.com/1190)ᵖʲ [1193](https://www.erdosproblems.com/1193)ᵖʲ [1197](https://www.erdosproblems.com/1197)ᵖʲ

## `link` — 3 problem(s)

**Add the `formal_proof` link.** FC already has the statement; the hosted proof just isn't linked.

[330](https://www.erdosproblems.com/330)ʲ [351](https://www.erdosproblems.com/351)ᵖʲ [499](https://www.erdosproblems.com/499)ᵖʲ

## `docstring` — 11 problem(s)

**Docstring note, not a `formal_proof` tag.** The hosted proof is conditional (assumes an unformalized axiom) or axiomatic / trust-extended.

[192](https://www.erdosproblems.com/192)ʲ [231](https://www.erdosproblems.com/231)ʲ [237](https://www.erdosproblems.com/237)ᵖʲ [291](https://www.erdosproblems.com/291)ᵖ [490](https://www.erdosproblems.com/490)ᵖʲ [610](https://www.erdosproblems.com/610)ʲ [658](https://www.erdosproblems.com/658)ᵖʲ [659](https://www.erdosproblems.com/659)ᵖʲ [694](https://www.erdosproblems.com/694)ᵖʲ [964](https://www.erdosproblems.com/964)ᵖʲ [1148](https://www.erdosproblems.com/1148)ᵖʲ

## `partial` — 8 problem(s)

**Partial proof.** Proves a specific variant, not the full erdosproblems statement. May be linkable to that FC variant; needs a per-problem look (per @plby).

[124](https://www.erdosproblems.com/124)ᵖ [264](https://www.erdosproblems.com/264)ᵖ [368](https://www.erdosproblems.com/368)ᵖ [485](https://www.erdosproblems.com/485)ᵖ [866](https://www.erdosproblems.com/866)ᵖ [1056](https://www.erdosproblems.com/1056)ᵖ [1095](https://www.erdosproblems.com/1095)ᵖ [1187](https://www.erdosproblems.com/1187)ᵖ

## `wont-fix` — 1 problem(s)

**Maintainer marked `won't fix`** (e.g. the hosted proof is not actually complete). Skip it.

[678](https://www.erdosproblems.com/678)ᵖʲ
