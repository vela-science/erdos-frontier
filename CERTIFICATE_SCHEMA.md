# Historical certificate projections

The JSON files under [`certificates/`](certificates/) are retained historical
projections from the predecessor epoch. They document the useful distinction
between:

- machine evidence about a proof’s axioms and hypothesis parameters; and
- accountable judgment about statement fidelity.

The old certificate generator and generated site feed have been retired. These
JSON files are not an active schema, authority surface, or current Vela object.
Current scientific identity and Standing are represented by immutable Claims,
Submissions, Verification Records, Proposals, and Decisions under `records/`,
indexed by `.vela/repository.json`.

To inspect current state:

```bash
vela replay . --json
vela status . --json
vela show . <object_id> --json
vela why . <claim_id> --json
```

The historical projections remain in Git because they are evidence of earlier
analysis. New integrations should consume current Vela records rather than
reviving this format.
