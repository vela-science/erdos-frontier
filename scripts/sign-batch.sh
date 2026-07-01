#!/usr/bin/env bash
# Sign a reviewed campaign batch in one pass, under YOUR key.
#
#   bash scripts/sign-batch.sh --review     # the full session: shows each packet
#                                           # in the terminal, takes your verdict
#                                           # inline, then signs everything
#   bash scripts/sign-batch.sh [stub-file]  # sign a stub you filled by hand
#   (default stub: packets/draft-review/verdicts_stub.json)
#
# Either way the judgment is yours: for every VERDICT-FILLED row the script
# creates the campaign finding (`vela finding add --apply`), fills the row's
# `target` with the vf_ id, and signs ALL rows in one `vela attest --batch`
# (one key read), then re-materializes the frontier.
#
# KEY CUSTODY: the attest verdicts are reserved for reviewer: actors by the
# substrate; an agent cannot run this to any effect. Rows with an empty verdict
# are refused — the judgment is yours, not defaultable.
#
# Env: VELA (default vela), REVIEWER (default reviewer:will-blair).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
VELA="${VELA:-vela}"
REVIEWER="${REVIEWER:-reviewer:will-blair}"

REVIEW=0; STUB=""
for a in "$@"; do
  case "$a" in
    --review) REVIEW=1 ;;
    *) STUB="$a" ;;
  esac
done
STUB="${STUB:-packets/draft-review/verdicts_stub.json}"

[ -f "$STUB" ] || { echo "no stub at $STUB (run match_packet.py --draft first)"; exit 1; }

# --review: walk each unfilled row — show the packet, take the verdict inline.
# The judgment stays yours; this only removes the file-editing friction.
if [ "$REVIEW" = "1" ]; then
  python3 - "$STUB" <<'EOF'
import json, sys, pathlib
stub = pathlib.Path(sys.argv[1])
rows = json.load(stub.open())
valid = {"f": "faithful", "v": "variant", "u": "unfaithful"}
for r in rows:
    if r.get("verdict") in ("faithful", "variant", "unfaithful"):
        continue
    n = r["problem"]
    packet = pathlib.Path(f"packets/draft-review/erdos_{n}.md")
    print("\n" + "=" * 72)
    print(packet.read_text() if packet.exists() else f"(no packet for {n})")
    print("=" * 72)
    while True:
        ans = input(f"verdict for {n} — [f]aithful / [v]ariant / [u]nfaithful "
                    f"/ [s]kip / [q]uit: ").strip().lower()
        if ans in ("q", "quit"):
            json.dump(rows, stub.open("w"), indent=2)
            print("saved partial progress; re-run to continue.")
            sys.exit(2)
        if ans in ("s", "skip", ""):
            break
        if ans in valid or ans in valid.values():
            r["verdict"] = valid.get(ans, ans)
            break
        print("  (f, v, u, s, or q)")
json.dump(rows, stub.open("w"), indent=2)
print("\nverdicts saved.")
EOF
fi

# refuse empty verdicts + validate values, BEFORE creating anything
python3 - "$STUB" <<'EOF'
import json, sys
rows = json.load(open(sys.argv[1]))
bad = [r["problem"] for r in rows if r.get("verdict") not in ("faithful","variant","unfaithful")]
if bad:
    sys.exit(f"unfilled/invalid verdict for problems {bad} — read the packets and "
             f"fill each \"verdict\" (faithful/variant/unfaithful) first.")
print(f"{len(rows)} rows, all verdicts filled.")
EOF

# create one finding per row, fill targets, emit the vela-shaped bare array
FINAL="packets/draft-review/verdicts_signed_input.json"
python3 - "$STUB" "$FINAL" "$VELA" "$REVIEWER" <<'EOF'
import json, re, subprocess, sys
stub, final, vela, reviewer = sys.argv[1:5]
rows = json.load(open(stub))
out = []
for r in rows:
    n = r["problem"]
    res = subprocess.run(
        [vela, "finding", "add", ".",
         "--assertion",
         f"The Formal Conjectures statement drafted for Erdős problem {n} "
         f"faithfully represents the informal problem.",
         "--type", "theoretical", "--source", "erdos-frontier campaign",
         "--author", reviewer, "--apply", "--json"],
        capture_output=True, text=True)
    m = re.search(r"vf_[0-9a-f]+", res.stdout + res.stderr)
    if not m:
        sys.exit(f"finding add failed for {n}: {res.stderr[-300:]}")
    out.append({"target": m.group(0), "verdict": r["verdict"],
                "informal_ref": r.get("informal_ref",""),
                "formal_ref": r.get("formal_ref",""),
                "formal_statement_hash": r.get("formal_statement_hash",""),
                "note": r.get("note","")})
    print(f"  {n}: finding {m.group(0)} ({r['verdict']})")
json.dump(out, open(final, "w"), indent=2)
print(f"wrote {final}")
EOF

"$VELA" attest . --batch "$FINAL" --as "$REVIEWER"
"$VELA" frontier materialize .
echo
echo "signed + materialized. next:"
echo "  git add .vela/ frontier.json frontier.yaml vela.lock proof/ && git commit -m 'Sign batch fidelity verdicts' && git push"
echo "  python scripts/submit_batch.py assemble batch-3"
