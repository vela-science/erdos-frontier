# Imported attack records (617 / 686 / 993)

The `617/`, `686/`, and `993/` subdirectories are the **authored attack records**
for Erdős problems #617, #686, and #993, consolidated here from the public
`verified-combinatorics` mirror (`github.com/willblair0708/verified-combinatorics`)
so the research record lives with the canonical Vela state rather than stranded
in a separate single-purpose repo.

What was brought in: the prose notes (`NOTES`, `RESULT`, `STATUS`, structural
case analyses, `LEMMAS`, session reports), the method source (`.py`/`.c`/`.sh`
search, verify, and certificate scripts), the written-up note (`617/note/`
LaTeX + PDF), and the key result/witness JSON. What was left in the mirror:
regenerable run-output (`.log`/`.err`/`.out`, `.cnf.gz`, `.npz`, `.pkl`,
`.jsonl` sweep logs, compiled binaries, `__pycache__`) and scratch prompt drafts.

The frozen, kernel-checked status of these problems is the canonical record:
the `vela-verify` Erdős certificate family and the Lean proofs
(`lean/Vela/Erdos/`) are the trust; these directories are the supporting attack
scaffolding, not accepted state. The `verified-combinatorics` mirror remains in
place as the stable `%H` publication surface that the accepted OEIS comments
link to.
