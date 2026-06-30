#!/usr/bin/env python3
"""Emit human-review match-check packets for problems needing a statement audit.

A packet is a markdown artifact with three panels for a reviewer to compare:

  1. Upstream statement   — the boxed problem on erdosproblems.com (LaTeX view).
  2. FC theorem           — the Formal Conjectures file for this problem.
  3. Hosted theorem(s)    — the hosted Lean proof source(s) and their state.

The reviewer reads all three and decides whether the formal theorem faithfully
states the boxed problem. Packets are written to packets/match-check/erdos_<n>.md.

Reuses the dashboard's own row builders (row_for_problem / build_fc /
build_proofs / proof_url) so the packet never drifts from the computed status.

Usage:
    python match_packet.py 214            # one problem
    python match_packet.py                # all rows needing a match-check
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

from fc_sync_status import (
    SOURCE_LABEL,
    load_live_status,
)


# Buckets whose statement/theorem relation has not been settled and so benefit
# from a human-readable comparison packet.
PACKET_BUCKETS = {
    "needs-human-match-check",
    "mismatch",
    "hypothesis-conditional",
}

PACKET_DIR = Path("packets/match-check")


def render_packet(row: dict) -> str:
    problem = row["problem"]
    out: list[str] = []
    out.append(f"# Match-check packet — Erdős problem {problem}\n")
    out.append(f"Computed bucket: `{row['bucket']}`")
    fidelity = row.get("fidelity")
    if fidelity:
        out.append(
            f"Signed verdict: `{fidelity.get('verdict')}` "
            f"({fidelity.get('source')}, {fidelity.get('reviewer') or 'unknown'})"
        )
    override = row.get("override")
    if override and override.get("reason"):
        out.append(f"Override note: {override['reason']}")
    out.append("")

    machine = row.get("machine")
    if machine:
        out.append("## Machine evidence (L1) — deterministic, no human/model judgment\n")
        out.append(f"- Verdict: `{machine.get('verdict')}`")
        if machine.get("non_kernel_axioms"):
            out.append(f"- Non-kernel axioms: `{', '.join(machine['non_kernel_axioms'])}` "
                       "(visible to `#print axioms`)")
        if machine.get("named_assumptions"):
            out.append("- **Undischarged named assumptions** (theorem parameters — "
                       "`#print axioms` cannot see these):")
            for a in machine["named_assumptions"]:
                out.append(f"  - `{a}`")
            out.append("  → the proof is conditional on the above; it is NOT an "
                       "unconditional resolution even if kernel-clean.")
        out.append("")

    out.append("## 1. Upstream statement\n")
    out.append(f"- Boxed problem: {row['erdos_url']}")
    out.append(f"- LaTeX source: {row['latex_url']}")
    out.append(f"- Upstream state: `{row['erdos_state']}`\n")

    out.append("## 2. FC theorem\n")
    fc = row.get("fc") or {}
    if fc.get("path"):
        out.append(f"- File: `{fc['path']}`")
        out.append(
            "- View: "
            f"https://github.com/google-deepmind/formal-conjectures/blob/main/{fc['path']}"
        )
        out.append(f"- Linked formal_proof: {'yes' if fc.get('linked') else 'no'}")
    else:
        out.append("- No Formal Conjectures file for this problem yet.")
    out.append("")

    out.append("## 3. Hosted theorem signature(s)\n")
    if row["proof_links"]:
        for link in row["proof_links"]:
            label = SOURCE_LABEL.get(link["source"], link["source"])
            flags = []
            if link.get("complete"):
                flags.append("complete")
            if link.get("conditional"):
                flags.append("conditional")
            if link.get("partial"):
                flags.append("partial")
            state = link.get("state") or "?"
            out.append(f"- {label} — state `{state}` ({', '.join(flags) or 'unflagged'})")
            out.append(f"  - {link['url']}")
    else:
        out.append("- No hosted Lean proof source for this problem.")
    out.append("")

    out.append("## Decision\n")
    out.append(
        "- [ ] faithful — the formal theorem states the boxed problem; safe to link.\n"
        "- [ ] variant — proves a weaker/variant statement; do not link as complete.\n"
        "- [ ] unfaithful — does not prove the boxed problem; mismatch.\n"
    )
    return "\n".join(out)


def write_packet(row: dict, root: str | Path = ".") -> Path:
    out_dir = Path(root) / PACKET_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"erdos_{row['problem']}.md"
    path.write_text(render_packet(row))
    return path


def select_rows(payload: dict, problem: int | None) -> list[dict]:
    if problem is not None:
        return [row for row in payload["rows"] if row["problem"] == problem]
    return [row for row in payload["rows"] if row["bucket"] in PACKET_BUCKETS]


def verdict_stub(row: dict) -> dict:
    """A pre-filled row for `vela attest --batch`. The reviewer fills `verdict`
    (faithful/variant/unfaithful) and `target` (the finding id) after reading the
    packet; everything else is derived. `note` carries the machine hint, not a
    judgment. Statement-faithfulness stays a human verdict signed under one key."""
    fc = row.get("fc") or {}
    machine = row.get("machine") or {}
    hint = ""
    if machine.get("named_assumptions"):
        hint = ("machine: kernel-clean but conditional on "
                + ", ".join(machine["named_assumptions"]))
    elif machine.get("non_kernel_axioms"):
        hint = "machine: conditional on axioms " + ", ".join(machine["non_kernel_axioms"])
    return {
        "target": None,
        "verdict": "",
        "informal_ref": f"erdosproblems.com/{row['problem']}",
        "formal_ref": (f"google-deepmind/formal-conjectures@HEAD:{fc['path']}"
                       if fc.get("path") else None),
        "formal_statement_hash": None,
        "note": hint,
    }


def main(argv: list[str]) -> int:
    problem = int(argv[1]) if len(argv) > 1 else None
    payload = load_live_status()
    rows = select_rows(payload, problem)
    if not rows:
        target = f"problem {problem}" if problem is not None else "the match-check buckets"
        print(f"No rows found for {target}.")
        return 0
    stubs = []
    for row in rows:
        path = write_packet(row)
        stubs.append(verdict_stub(row))
        print(f"wrote {path}")
    stub_path = Path(PACKET_DIR) / "verdicts_stub.jsonl"
    stub_path.write_text("\n".join(json.dumps(s) for s in stubs) + "\n")
    print(f"wrote {stub_path} ({len(stubs)} rows) — fill verdict+target, then "
          "`vela attest <frontier> --batch verdicts_stub.jsonl --as reviewer:will-blair --key <key>`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
