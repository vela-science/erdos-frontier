# Erdős Frontier

> [!IMPORTANT]
> **Archived.** This repository is preserved exactly as signed and is no longer
> developed. Its history, records and authority events stay readable here.
>
> Vela's authority boundary was renamed and consolidated in
> [ADR 0039](https://github.com/vela-science/vela/blob/main/docs/adr/0039-repository-authority-and-derived-frontiers.md).
> `Frontier` was doing three jobs at once — authority boundary, topic boundary
> and product slice — and four repositories existed because there were four
> topics, not four authorities. They named one maintainer and one decision
> model between them, so four trust roots bought four Standing universes that
> could not see each other.
>
> A repository now exists because there is a new **authority**, never because
> there is a new topic. Current mathematical work lives in one repository under
> one authority. Nothing here was migrated into it: Claims are re-admitted
> deliberately through Submission, Verification and Decision, and these roots
> remain as their provenance.
>
> Tooling from `vela 0.967` onward does not read this repository. The last
> release that does is `0.966.4`.

The canonical Git repository for Vela’s Erdős research portfolio and
formalization-fidelity audit. The bounded question is stated in
[STATEMENT.md](STATEMENT.md) and declared in `frontier.toml`, which
`profile_root` commits to.

[Open in Vela Observatory](https://app.vela.space/frontiers/erdos) or verify
the exact repository state locally:

```bash
git clone https://github.com/vela-science/erdos-frontier
cd erdos-frontier
vela replay . --json
vela status . --json
vela next . --json
```

Human-readable target plans and completed campaign summaries live in
[`campaigns/`](campaigns/). Exact Target packets, retained scientific objects,
artifacts, and replay state in this repository remain authoritative over those
summaries.

## What this repository establishes

The source audit asks two separate questions:

1. Does a hosted Lean proof establish its theorem unconditionally?
2. Does the formal theorem faithfully state the informal Erdős problem?

The first is reproducible machine evidence. The second is scientific judgment.
Vela keeps them separate: a passing Verification is evidence, not acceptance,
and only repository authority can change accepted Standing.

## Repository model

The active repository is intentionally compact:

- [`.vela/repository.json`](.vela/repository.json) indexes the current objects.
- [`.vela/origin.json`](.vela/origin.json) binds the compacted predecessor.
- [`.vela/authority/`](.vela/authority/) contains repository-authority records.
- [`records/`](records/) contains immutable Claims, Submissions, Verifications,
  Proposals, artifacts, and related canonical objects.
- [`targets.json`](targets.json) is the current Target Index.
- [`targets/closures/`](targets/closures/) contains exact closure evidence for
  ranked work.
- [`sources/`](sources/) and [`sources.lock.json`](sources.lock.json) retain
  external source evidence and exact source identities.
- [`artifacts/`](artifacts/) and [`witnesses/`](witnesses/) retain scientific
  evidence.

Historical runtime formats remain reachable through the signed predecessor tag
`pre-compaction/fc7b922e54e4`; they are not duplicated in the active tree. The
Observatory derives its read-only view from the canonical repository and
retained source snapshots.
There is no second site or graph authority surface in this repository.

## Research loop

```text
map → target → work → submit → verify → decide → remap
```

```bash
vela status . --json
vela next . --json
vela start <target> --frontier . --json
vela submit --frontier . \
  --claim "<bounded result>" \
  --type theoretical \
  --replayability exact \
  --artifact <path>:<kind> \
  --caveat "<what this does not establish>" \
  --packet-root <packet_sha256> \
  --profile-root <profile_sha256> \
  --verifier-capsule-root <capsule_sha256> \
  --result-contract-root <contract_sha256> \
  --as agent:<name> --json
```

`vela start` is a write-free briefing and prints the exact Submission binding
values; it creates no Attempt, lease, or approval step. Agents and producers
stop after registering a Submission. Verification and repository-authority
Decisions are separate records. Git transports the bytes; it does not create
scientific acceptance.

## Source audit

[`erdos_frontier.py`](erdos_frontier.py) joins the Erdős catalogue, Formal
Conjectures, hosted proof manifests, retained machine-audit evidence, and
reviewed source classifications. It returns an in-memory audit payload and
refreshes exact source hashes in `sources.lock.json`; it does not publish a
parallel status snapshot.

The principal inputs are:

| source | contribution |
|---|---|
| [erdosproblems.com](https://www.erdosproblems.com) | problem statements and upstream status |
| [formal-conjectures](https://github.com/google-deepmind/formal-conjectures) | formal statements and proof links |
| [plby/lean-proofs](https://github.com/plby/lean-proofs), [Jayyhk/erdos-lean](https://github.com/Jayyhk/erdos-lean), [williamjblair/lean-proofs](https://github.com/williamjblair/lean-proofs) | hosted Lean proofs and condition metadata |
| [`lean/audit_feed*.json`](lean/) | retained multi-toolchain machine evidence |
| [`sources/wiki/`](sources/wiki/) and [`sources/gpt_erdos/`](sources/gpt_erdos/) | frozen external claim snapshots |
| [`overrides.yaml`](overrides.yaml) | explicit source-classification facts not available upstream |

Run the focused source audit and tests:

```bash
uv sync --all-groups
uv run pytest -q
GH_TOKEN=$(gh auth token) uv run python erdos_frontier.py
```

The token is used only to read public Formal Conjectures pull requests and
issues. Heavy Lean extraction remains an explicit manual workflow under
[`lean/`](lean/).

## Boundaries

- A `sorry`-free, axiom-clean theorem can still depend on an unproved theorem
  supplied as a hypothesis.
- Verification never implies that the formal statement is the intended
  scientific claim.
- Agents cannot accept their own Submissions or access repository authority.
- Canonical records are immutable; corrections append.
- Generated indexes and readers are replaceable and confer no authority.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution mechanics and
[AGENTS.md](AGENTS.md) for the canonical agent guide.
