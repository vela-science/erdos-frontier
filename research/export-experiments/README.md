# Export experiments

Status: no supported export profile or live protocol edge.

This is the only place for unpromoted MCP, RO-Crate, PROV-O, Frictionless,
registry, or report experiments. An experiment is a removable projection over
exact Frontier state. It creates no Vela object, carries no repository
authority, and cannot change Standing.

Promotion requires a generated artifact with:

- generator name and exact version;
- source commit, tree, and repository root;
- declared output schema, media type, or profile;
- exact output root and deterministic regeneration command;
- transformation and semantic-loss report;
- `authority_effect: none`;
- validation or conformance command;
- supported transport and protocol version, if any;
- at least two maintained consumers or one measured task not served by the
  existing CLI/HTTP read surface; and
- a deletion plan if the experiment fails.

Until those gates pass, this repository does not claim MCP, A2A, RO-Crate,
PROV-O, Frictionless, registry, or generated-report support.
