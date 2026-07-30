#!/usr/bin/env python3
"""Statement-facts report for a formal-conjectures pull request.

Usage:
    python fc_pr_audit.py <pr-number> [--repo google-deepmind/formal-conjectures]

Reads the PR's changed ErdosProblems files at the PR head, parses each
declaration textually (no Lean build), joins each problem against the current
source audit, and prints a markdown facts report suitable for a PR comment.

Facts only, no judgments. A flag is a reason for a human to look, never a
verdict. This implements the L1 layer of STANDARD_CHECK.md.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys

from erdos_frontier import load_live_status

DEFAULT_REPO = "google-deepmind/formal-conjectures"
ERDOS_FILE = re.compile(r"FormalConjectures/ErdosProblems/(\d+)\.lean$")
DECL = re.compile(r"^\s*(?:noncomputable\s+)?(theorem|lemma|def|abbrev)\s+([\w.«»]+)")
CATEGORY = re.compile(r"category\s+([^,\]]+)")
AMS = re.compile(r"AMS\s+([\d\s,]+)")
FORMAL_PROOF = re.compile(r'formal_proof[^\]]*?"(https?://[^"]+)"')
ERDOS_REF = re.compile(r"erdosproblems\.com/(\d+)")


def gh_json(args: list[str]):
    out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def fetch_file(repo: str, path: str, ref: str) -> str | None:
    try:
        data = gh_json(["api", f"repos/{repo}/contents/{path}?ref={ref}"])
    except subprocess.CalledProcessError:
        return None
    if data.get("encoding") == "base64":
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    return None


def parse_lean(text: str) -> dict:
    """Textual parse: declarations with their attribute block and docstring."""
    lines = text.splitlines()
    decls = []
    pending_attr: list[str] = []
    has_docstring = False
    in_docstring = False
    in_attr = False
    for line in lines:
        stripped = line.strip()
        if in_docstring:
            if "-/" in stripped:
                in_docstring = False
                has_docstring = True
            continue
        if stripped.startswith("/--"):
            if "-/" in stripped[3:]:
                has_docstring = True
            else:
                in_docstring = True
            continue
        if stripped.startswith("@[") or in_attr:
            pending_attr.append(stripped)
            in_attr = "]" not in stripped
            continue
        m = DECL.match(line)
        if m:
            attr = " ".join(pending_attr)
            cat = CATEGORY.search(attr)
            ams = AMS.search(attr)
            decls.append({
                "kind": m.group(1),
                "name": m.group(2),
                "category": cat.group(1).strip() if cat else None,
                "ams": ams.group(1).strip().rstrip(",") if ams else None,
                "docstring": has_docstring,
                "formal_proof": FORMAL_PROOF.findall(attr),
            })
            pending_attr, has_docstring = [], False
        elif stripped and not stripped.startswith("--"):
            # any other code line breaks docstring/attr adjacency
            if not stripped.startswith(("import", "open", "namespace", "end",
                                        "set_option", "section", "variable")):
                pending_attr, has_docstring = [], False
    return {"decls": decls, "erdos_refs": sorted(set(ERDOS_REF.findall(text)))}


def load_feed() -> dict[str, dict]:
    """Build the small PR-audit view directly from retained source evidence."""
    rows = {}
    for source in load_live_status()["rows"]:
        machine = source.get("machine") or {}
        wiki = source.get("wiki") or {}
        fidelity = source.get("fidelity") or {}
        rows[str(source["problem"])] = {
            "problem": source["problem"],
            "erdos_state": source.get("erdos_state"),
            "proof_links": source.get("proof_links") or [],
            "machine_verdict": machine.get("verdict"),
            "named_assumptions": machine.get("named_assumptions") or [],
            "wiki_outcome": wiki.get("outcome_label"),
            "signed_fidelity_verdict": fidelity.get("verdict"),
            "signed_by": fidelity.get("reviewer"),
        }
    return rows


def facts_for_file(path: str, text: str, feed: dict[str, dict]) -> list[str]:
    n = ERDOS_FILE.search(path).group(1)
    parsed = parse_lean(text)
    row = feed.get(n)
    out = [f"#### `{path}` (Erdős {n})", ""]

    if parsed["decls"]:
        out += ["| declaration | category | AMS | docstring |", "|---|---|---|---|"]
        for d in parsed["decls"]:
            # category/AMS are required on theorems and lemmas; defs are exempt
            required = d["kind"] in ("theorem", "lemma")
            miss = "**not detected**" if required else "—"
            out.append(
                f"| `{d['name']}` | {d['category'] or miss} "
                f"| {d['ams'] or miss} "
                f"| {'yes' if d['docstring'] else miss} |")
        out.append("")
        if any(not (d["category"] and d["ams"]) and d["kind"] in ("theorem", "lemma")
               for d in parsed["decls"]):
            out.append("*\"not detected\" is a textual parse result; unusually "
                       "formatted attributes can be missed. The build linters are "
                       "authoritative.*")
            out.append("")

    flags = []
    if n not in parsed["erdos_refs"]:
        flags.append(f"no reference link to erdosproblems.com/{n} found in the file")

    if row:
        out.append(f"- erdosproblems.com status: **{row.get('erdos_state') or 'unknown'}**")
        cats = {d["category"] for d in parsed["decls"] if d["category"]}
        state = (row.get("erdos_state") or "").lower()
        if any(c.startswith("research solved") for c in cats) and state == "open":
            flags.append("file says `research solved`; erdosproblems.com says open")
        if any(c.startswith("research open") for c in cats) and (
                state.startswith("proved") or state.startswith("solved")):
            flags.append(f"file says `research open`; erdosproblems.com says {row.get('erdos_state')}")
        if row.get("wiki_outcome"):
            out.append(f"- AI-contributions wiki (recorded, not verified): {row['wiki_outcome']}")
        hosted = row.get("proof_links") or []
        for p in hosted:
            bits = [k for k in ("conditional", "partial") if p.get(k)]
            out.append(f"- hosted proof known to the audit: {p.get('label')}"
                       + (f" ({', '.join(bits)})" if bits else " (complete)"))
        if row.get("machine_verdict"):
            out.append(f"- audit verdict on the strongest hosted proof: "
                       f"**{row['machine_verdict']}**"
                       + (f", assuming {', '.join(row['named_assumptions'])}"
                          if row.get("named_assumptions") else ""))
            if row["machine_verdict"] == "conditional":
                flags.append("the hosted proof the audit knows is conditional; "
                             "a `formal_proof` link to it would need the conditional modifier")
        if row.get("signed_fidelity_verdict"):
            out.append(f"- signed statement-fidelity verdict: {row['signed_fidelity_verdict']} "
                       f"(reviewer: {row.get('signed_by')})")
        else:
            out.append("- signed statement-fidelity verdict: none yet")
    else:
        out.append(f"- Erdős {n} is not in the audit feed (new problem number)")

    for d in parsed["decls"]:
        for url in d["formal_proof"]:
            out.append(f"- `formal_proof` link on `{d['name']}`: {url}")

    if flags:
        out.append("")
        out.append("**Worth a look** (facts that may disagree, not verdicts):")
        out += [f"- {f}" for f in flags]
    out.append("")
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", type=int)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    args = ap.parse_args(argv)

    pr = gh_json(["pr", "view", str(args.pr), "-R", args.repo,
                  "--json", "number,title,headRefOid,files,headRepository,headRepositoryOwner"])
    head_repo = f"{pr['headRepositoryOwner']['login']}/{pr['headRepository']['name']}"
    ref = pr["headRefOid"]
    targets = [f["path"] for f in pr["files"] if ERDOS_FILE.search(f["path"])]

    print(f"### Statement facts: PR #{pr['number']} — {pr['title']}")
    print(
        "*Mechanical report from the source audit in "
        "[erdos-frontier](https://github.com/vela-science/erdos-frontier); "
        "facts only, no judgments.*\n"
    )
    if not targets:
        print("No `FormalConjectures/ErdosProblems/*.lean` files changed in this PR.")
        return 0

    feed = load_feed()
    for path in targets:
        text = fetch_file(head_repo, path, ref) or fetch_file(args.repo, path, ref)
        if text is None:
            print(f"#### `{path}`\n\n- could not fetch file at PR head\n")
            continue
        print("\n".join(facts_for_file(path, text, feed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
