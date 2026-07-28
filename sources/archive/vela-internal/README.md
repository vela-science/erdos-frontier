# Vela internal source archive

This directory preserves the exact historical source bytes referenced by
recovered Erdős attempt records.

The original source repository was a private integration workspace. Keeping
its URLs as the provenance identity is correct, but relying on it for public
retrieval is not. `manifest.json` binds every original
`repository@commit:path` identity to a byte-exact path in this public
Frontier.

These files are historical evidence only. Mirroring them:

- does not rewrite their original identity;
- does not promote a draft or machine check to accepted scientific state;
- does not alter a Claim, Verification Record, Proposal, Decision, Event, or
  Standing; and
- does not make the archived transition repository a current dependency.

Verify every mirror from the repository root:

```bash
bun scripts/verify-source-archive.ts
```
