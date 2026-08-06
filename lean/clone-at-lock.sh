#!/usr/bin/env bash
# Check out a declared source at the commit `sources.lock.json` records for it.
#
# The audit workflows used to `git clone --depth 1` a default branch, so every
# run read whatever `main` was at that moment — and the plby clone read
# `williamjblair/lean-proofs-fork`, a repository `sources.yaml` does not name at
# all. Those are one fault wearing two faces: evidence built from bytes the
# inventory did not pin. So both the repository and the commit are read from the
# lock, here, at run time. Neither is written into a workflow: a commit pasted
# into YAML is a second pin, and a second pin is a thing that can disagree with
# the first while both look authoritative.
#
# `git clone --depth 1` takes a branch or tag, never an arbitrary commit, which
# is why this is the long form instead. GitHub serves any reachable commit to
# `git fetch`, so a one-commit fetch costs what the old shallow clone cost.
#
# The check-out is then held to the lock. A fetch that silently landed on
# something else — a moved ref, a proxy, a typo in the key — would otherwise
# produce an audit that looks exactly like a correct one, which is the failure
# this script exists to make impossible.
#
#   lean/clone-at-lock.sh <source-key> <destination>
set -euo pipefail

KEY="${1:?usage: clone-at-lock.sh <source-key> <destination>}"
DEST="${2:?usage: clone-at-lock.sh <source-key> <destination>}"
LOCK="$(cd "$(dirname "$0")/.." && pwd)/sources.lock.json"

# Read `repo` and `commit` together, so a key that is declared but unpinnable
# fails here with the reason rather than half-way through a clone.
SPEC="$(python3 - "$LOCK" "$KEY" <<'PY'
import json
import sys

lock_path, key = sys.argv[1], sys.argv[2]
with open(lock_path, encoding="utf-8") as handle:
    entry = json.load(handle)["sources"].get(key)
if entry is None:
    sys.exit(
        f"{lock_path} has no source {key!r}. A repository the audit reads must be "
        "declared in sources.yaml first, then pinned by regenerating the lock."
    )
repo, commit = entry.get("repo"), entry.get("commit")
if not repo or not commit:
    sys.exit(
        f"{key}: the lock records repo={repo!r} commit={commit!r}, and checking out "
        "the acquired bytes needs both. Declare the missing one and regenerate."
    )
print(repo, commit)
PY
)"
read -r REPO COMMIT <<<"$SPEC"

echo "==> $KEY: $REPO @ $COMMIT -> $DEST"
mkdir -p "$DEST"
git -C "$DEST" init -q
git -C "$DEST" remote add origin "https://github.com/$REPO.git"
git -C "$DEST" fetch -q --depth 1 origin "$COMMIT"
git -C "$DEST" checkout -q FETCH_HEAD

HEAD="$(git -C "$DEST" rev-parse HEAD)"
if [ "$HEAD" != "$COMMIT" ]; then
  echo "FATAL: $KEY checked out $HEAD, but sources.lock.json pins $COMMIT" >&2
  exit 1
fi
echo "    HEAD $HEAD matches the lock"
