# Human Decision inbox — 2026-08-04

## Purpose and authority boundary

This source-local checkpoint makes the current review queue inspectable without
changing scientific Standing. It is derived from `vela review list` and
`vela review show` at repository root
`sha256:821cf0d94778f647305107943572f4916a6cf63fe5ea12506a471fabc07b7474`.
The complete inbox projection root is
`sha256:a6a4c5f525333401dd34e15e7f1d657e613ad769e475acdd992172c57d40ddbd`.

Only an attributed repository-authority Decision may accept or reject a
Proposal. A general instruction to continue the campaign is not a Decision on
any assertion below. This document neither recommends scientific acceptance
nor supplies authority credentials.

Every entry must be refreshed immediately before a Decision. Repository,
Proposal, Claim, Submission, Verification-set, policy, keyset, authority-record,
or authority-event-log drift invalidates the captured entry.

## Protocol-ready entries

### Erdős 1056 range `10429601..10429800`

- Proposal: `vpr_27bce8983810f3bd`
- Claim: `vcl_4b80b2d9500a1f6dd98cf7722717e6d26d9ebd9d8edabb09f9436b9ac49a9237`
- Assertion: exhaustive search of 13 primes found no `k=15` witness; maximum
  multiplicity 11 at `p=10429717`, residue `2060465`
- Scoped Verifications: `vvr_85596c5b83104888`,
  `vvr_b879aec074e01d16`
- Entry root:
  `sha256:76a6557dc534a23b2b7640d55912c0372d135446a04a068ba011a13107c25960`
- If accepted from the captured state:
  `sha256:0257fe808e36a5910018055a02412b569b393152350a77a70c02dc2b66ac656d`
- If rejected from the captured state:
  `sha256:33e84dcd9b25c9c690bd22b8a1743685c6192fabe7c00af3de7852a775f9443b`

### Erdős 1056 range `10429801..10430000`

- Proposal: `vpr_148c88da4d5579a9`
- Claim: `vcl_9a4d0304e69426ac62623215f8b9ad7bde9381236aee223b160e92c40943ba86`
- Assertion: exhaustive search of 12 primes found no `k=15` witness; maximum
  multiplicity 11 at `p=10429973`, residue `7723031`
- Scoped Verification: `vvr_18f4862fd1a2c256`
- Entry root:
  `sha256:58f2f44b083ad2a9201bf52b5274ab6d0f87383b4c9093cc1397a1107a600a8b`
- If accepted from the captured state:
  `sha256:7a60bf2dbf5a636f520985cb7d543e9c20471a0ac415a38aac2b3bc0bcf84c00`
- If rejected from the captured state:
  `sha256:595193b98ef912ecde0a20b2bbae69d424d8daef89071533ab3060e089fddd1d`

### Erdős 1056 range `10430201..10430400`

- Proposal: `vpr_eca7e122d1ce6e52`
- Claim: `vcl_5ac4a8eb6ab179ba727ff6395abf1fd6b591137f9da73cc5c09cd41587cd7f86`
- Assertion: exhaustive search of 15 primes found no `k=15` witness; maximum
  multiplicity 11 at `p=10430281`, residue `1529895`
- Scoped Verification: `vvr_c3437dc1eed8af3c`
- Entry root:
  `sha256:bf1542a07558226d0353e0ff7f54f69d050f44dbe7535b236df6f769f0753abf`
- If accepted from the captured state:
  `sha256:3b91c05dcafe765aa116d270e8458e4ff86bec235f55c14ed453b30a1a8fa232`
- If rejected from the captured state:
  `sha256:49f5c6eb6b4c2333594dc296a288d41a148d2d27246ab2798ec1d6c33975bfe9`

### Astra / Erdős 183 statement fidelity

- Proposal: `vpr_3635f052644495be`
- Claim: `vcl_47d920289e237e9eedbba44ff247d676b8e739d7a07bf743d213d151162d7881`
- Assertion: at the retained Erdős snapshot and OpenAI ten-proofs commit
  `29362184c2b698c1b279bc85b3957ee813646c63`,
  `ErdosProblems.MulticolourTriangleRamsey.erdos_183` faithfully formalizes
  the retained Erdős 183 statement
- Scoped Verification: `vvr_bee06004b4285330`
- Entry root:
  `sha256:a8526ee5a084852eb07d4826c22622b7be33b216e437c10353c801c80ea7c1df`
- If accepted from the captured state:
  `sha256:4457f64d13cbc18ab218661cdc97d74581a4ad992d3b4cca9b5349ecee1346c6`
- If rejected from the captured state:
  `sha256:f579830c4ec27452f94def922e8413d6a429a252553da0629b2e2cae79fa777c`

The Erdős 183 assertion is source fidelity only. It does not independently
re-prove the manuscript, establish novelty or citation completeness, update
the older source registry, imply community acceptance, or establish external
independence. The manuscript and formalization share OpenAI provenance.

## Duplicate-execution blocker

Two pending Proposals bind the same exact Erdős 1056 producer execution over
`10430001..10430200`. Neither may be accepted while both are pending.

The older wording, `vpr_b4a4b9ea9c00d6e9`, says a candidate artifact was
produced but omits the bounded-negative and global-nonclaim language used by
the corrected Submission. Its Claim is
`vcl_764737221fcd251de5fcabe2836915d15160dd217976c29d30d1e641362598fe`.

The corrected wording, `vpr_96578d006119b322`, states that an exhaustive search
of the 11 primes found no `k=15` witness, with maximum multiplicity 11 at
`p=10430171`, residue `4302968`. Its Claim is
`vcl_268fd0de48f9275bfe2bfcaef6df03f851343dd81109c09d8002f64b05b7edac`
and its scoped Verification is `vvr_9e6664cad0970e67`.

A producer-owned withdrawal of the older Proposal was attempted without
authority credentials and failed closed because the currently available
signing key does not match the immutable Submission identity. No state changed.
The safe human sequence is therefore:

1. inspect both exact entries;
2. reject the older Proposal with an attributed supersession reason, unless
   the original producer identity first withdraws it;
3. refresh the queue and repository root;
4. inspect the corrected Proposal after its blocker clears; and
5. accept or reject the corrected wording on its own scientific merits.

The captured older entry root is
`sha256:a14d9ec68730d36b3d0cbd45080f9a6508ad624c81ea35a345b5ed7d8f80730f`.
The captured corrected entry root is
`sha256:98303b9f10c3ed88ad3e1d940cdac21555548c27c166e616a892d97636786a4d`.
Their projected successor roots are deliberately not used as a multi-step
plan: resolving either Proposal changes the repository root and invalidates the
other captured entry.

## Reproduction

```bash
vela replay . --json
vela review list . --json
vela review show . vpr_27bce8983810f3bd --json
vela review show . vpr_148c88da4d5579a9 --json
vela review show . vpr_eca7e122d1ce6e52 --json
vela review show . vpr_3635f052644495be --json
vela review show . vpr_b4a4b9ea9c00d6e9 --json
vela review show . vpr_96578d006119b322 --json
```

After every attributed Decision, run `vela replay . --json`, commit the exact
authority mutation, and recompute `vela review list . --json` before acting on
the next item. Do not batch Decisions against stale projected roots.
