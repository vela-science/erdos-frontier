#!/usr/bin/env python3
"""S4: turn signed campaign drafts into a ready-to-push FC branch. Never pushes.

Two subcommands, because the signed vsa_ hash-binds the exact draft bytes so
the formal_proof link must be present BEFORE the fidelity review:

  prepare <batch>   for each gated draft with link_allowed, insert the
                    `formal_proof using lean4 at "<pinned-url>"` attribute
                    (URL pinned to the source repo's current commit SHA, never
                    a floating main). Idempotent. Then re-gate + packet + sign.

  assemble <batch>  verify EVERY draft in the batch has a signed faithful vsa_
                    whose formal_statement_hash matches the current bytes, then
                    create the FC branch, copy the files, and write the PR body
                    (the #4319 format). Stops there — Will pushes + opens the PR.

Env: FC_DIR (default ~/personal/formal-conjectures).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import json
import pathlib
import re
import subprocess
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent.parent
STAGING = HERE / "statements"
CAMPAIGN = HERE / "campaign.yaml"
FRONTIER_JSON = HERE / "frontier.json"
FC_DIR = pathlib.Path(__import__("os").environ.get("FC_DIR",
                      str(pathlib.Path.home() / "personal/formal-conjectures")))

# proof-source GitHub repos, for SHA pinning
SOURCE_REPOS = {"plby": "plby/lean-proofs", "jayyhk": "Jayyhk/erdos-lean",
                "vlp": "williamjblair/lean-proofs"}


def batch_problems(name: str) -> list[int]:
    camp = yaml.safe_load(CAMPAIGN.read_text())
    batch = next((b for b in camp.get("batches", []) if b["name"] == name), None)
    if not batch:
        sys.exit(f"batch {name!r} not in campaign.yaml")
    return batch["problems"]


def head_sha(repo: str) -> str:
    return subprocess.run(
        ["gh", "api", f"repos/{repo}/commits/HEAD", "--jq", ".sha"],
        capture_output=True, text=True, check=True).stdout.strip()


def pin_url(url: str, shas: dict) -> str:
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/blob/main/(.+)", url)
    if not m:
        return url
    repo, path = m.group(1), m.group(2)
    if repo not in shas:
        shas[repo] = head_sha(repo)
    return f"https://github.com/{repo}/blob/{shas[repo]}/{path}"


def prepare(name: str) -> int:
    shas: dict = {}
    for n in batch_problems(name):
        ddir = STAGING / str(n)
        meta = json.loads((ddir / "draft.json").read_text())
        lean_path = ddir / f"{n}.lean"
        if not meta.get("link_allowed"):
            print(f"  -- {n}: link not allowed (machine verdict "
                  f"{meta.get('machine_verdict')}); statement-only")
            continue
        text = lean_path.read_text()
        if "formal_proof" in text:
            print(f"  ok {n}: formal_proof already present")
            continue
        # the machine-audited source is the one we link
        hosted = next((h for h in meta.get("hosted", [])
                       if h.get("source") == meta.get("machine_source")), None)
        if not hosted:
            print(f"  !! {n}: no hosted entry for machine source; skipping link")
            continue
        pinned = pin_url(hosted["url"], shas)
        new, count = re.subn(
            r"@\[category ([^\]]+?)\]",
            lambda m: f'@[category {m.group(1)},\n  formal_proof using lean4 at "{pinned}"]',
            text, count=1)
        if not count:
            print(f"  !! {n}: no @[category ...] attribute found")
            continue
        lean_path.write_text(new)
        print(f"  ok {n}: linked {pinned[:90]}…")
    print("\nnow: re-run scripts/gate_draft.sh <problems>, review each statements/<n>/inputs.md"
          " against its .lean, fill statements/<batch>-verdicts.json, then"
          " `vela review . --batch statements/<batch>-verdicts.json` and re-run assemble.")
    return 0


def signed_hashes() -> dict[str, dict]:
    """formal_statement_hash -> attestation, from the replayed frontier."""
    doc = json.loads(FRONTIER_JSON.read_text())
    out = {}
    for att in doc.get("statement_attestations", []) or []:
        h = att.get("formal_statement_hash")
        if h:
            out[h] = att
    return out


def assemble(name: str) -> int:
    problems = batch_problems(name)
    signed = signed_hashes()
    branch = f"erdos-campaign-{name}"
    ready, table = [], []
    for n in problems:
        ddir = STAGING / str(n)
        meta = json.loads((ddir / "draft.json").read_text())
        data = (ddir / f"{n}.lean").read_bytes()
        h = hashlib.sha256(data).hexdigest()
        att = signed.get(h)
        if not att or att.get("verdict") != "faithful":
            print(f"  !! {n}: NO signed faithful vsa_ for current bytes "
                  f"({'stale hash' if not att else att.get('verdict')}) — excluded")
            continue
        gates = json.loads((ddir / "gates.json").read_text())
        if not gates.get("passed"):
            print(f"  !! {n}: gates not green — excluded")
            continue
        ready.append(n)
        linked = "yes" if b"formal_proof" in data else "no (statement only)"
        div = "; ".join(meta.get("divergence_notes") or []) or "none recorded"
        table.append(f"| {n} | {meta.get('upstream_state')} | {linked} | {div[:220]} |")

    if not ready:
        sys.exit("nothing signed+gated to assemble")

    subprocess.run(["git", "-C", str(FC_DIR), "checkout", "main"], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", str(FC_DIR), "pull", "--ff-only", "origin", "main"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(FC_DIR), "checkout", "-B", branch], check=True,
                   capture_output=True)
    for n in ready:
        dst = FC_DIR / "FormalConjectures" / "ErdosProblems" / f"{n}.lean"
        dst.write_bytes((STAGING / str(n) / f"{n}.lean").read_bytes())
        subprocess.run(["git", "-C", str(FC_DIR), "add", str(dst)], check=True)

    body = "\n".join([
        f"Adds Formal Conjectures statements for Erdős problems "
        f"{', '.join(str(n) for n in ready)}.",
        "",
        "Each statement was drafted from the boxed problem text on "
        "erdosproblems.com (docstrings verbatim), cross-checked against two "
        "independently hosted Lean proofs, and reviewed for statement fidelity "
        "before submission. `formal_proof` links (pinned to a commit) are "
        "included only where the hosted proof is unconditional under an axiom "
        "and hypothesis audit; divergences from the hosted formalizations are "
        "noted below.",
        "",
        "| problem | upstream state | proof linked | divergence notes |",
        "|---|---|---|---|",
        *table,
        "",
        "Part of #3998.",
    ])
    body_path = STAGING / f"_batch-{name}-pr-body.md"
    body_path.write_text(body + "\n")
    print(f"\nassembled {len(ready)}/{len(problems)} on branch {branch!r} in {FC_DIR}")
    print(f"PR body: {body_path}")
    print("\nWILL, from the FC checkout:")
    print(f"  git commit -m 'ErdosProblems: add {', '.join(str(n) for n in ready)} (#3998 sync)'")
    print(f"  git push -u fork {branch}")
    print(f"  gh pr create -R google-deepmind/formal-conjectures --head williamjblair:{branch} "
          f"--title 'ErdosProblems: add {', '.join(str(n) for n in ready)} (#3998 sync)' "
          f"--body-file {body_path}")
    return 0


def lean_review_view(path: pathlib.Path) -> str:
    """The judgment surface: the module from `/-!` onward — verbatim
    informal text, encoding notes, and the theorem. The license header
    carries no signal for a fidelity call."""
    text = path.read_text()
    i = text.find("/-!")
    return text[i:] if i >= 0 else text


def build_rows(name: str) -> list[dict]:
    """Pre-fill everything mechanical: the accepted finding id per
    problem, refs, and the sha256 of the exact draft bytes the vsa_ will
    bind. verdict + note stay empty — they are the human judgment."""
    problems = batch_problems(name)
    sha = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    doc = json.loads(FRONTIER_JSON.read_text())
    targets: dict[int, str] = {}
    for f in doc.get("findings", []):
        fd = f.get("finding", f)
        text = (fd.get("assertion") or {}).get("text") or ""
        for n in problems:
            if text.startswith(f"FC statement draft for Erd\u0151s #{n}:") or \
               text.startswith(f"FC statement draft for Erdős #{n}:"):
                targets[n] = fd["id"]
    missing = [n for n in problems if n not in targets]
    if missing:
        sys.exit(f"no accepted draft finding for {missing}; accept the batch proposals first")
    rows = []
    for n in problems:
        data = (STAGING / str(n) / f"{n}.lean").read_bytes()
        rows.append({
            "target": targets[n],
            "verdict": "",
            "informal_ref": f"erdosproblems.com/{n}",
            "formal_ref": f"williamjblair/erdos-frontier@{sha}:statements/{n}/{n}.lean",
            "formal_statement_hash": hashlib.sha256(data).hexdigest(),
            "note": "",
        })
    return rows


VERDICT_KEYS = {"f": "faithful", "v": "variant", "u": "unfaithful"}


def review(name: str) -> int:
    """The whole human session, one command: show each draft, take the
    verdict + note, sign everything in ONE key read, assemble the FC
    branch. Resume-safe (answers are saved as you go); skipped problems
    are excluded from signing and from the PR."""
    problems = batch_problems(name)
    vpath = STAGING / f"{name}-verdicts.json"
    if vpath.exists():
        rows = json.loads(vpath.read_text())["verdicts"]
    else:
        rows = build_rows(name)
        vpath.write_text(json.dumps({"verdicts": rows}, indent=2) + "\n")

    def prob(row):
        return int(row["informal_ref"].rsplit("/", 1)[1])

    pending = [r for r in rows if not r["verdict"]]
    session_note = ""
    if pending:
        print(f"{len(rows) - len(pending)}/{len(rows)} already answered; "
              f"{len(pending)} to review. [f]aithful [v]ariant [u]nfaithful [s]kip [q]uit\n")
        # The method is one review, applied twelve times: capture it once.
        # Per problem, Enter reuses it; typing replaces it for that problem
        # (divergent cases deserve their own words).
        default_method = ("Read the draft docstring (verbatim boxed problem text) and "
                          "encoding notes against the theorem statement; gates green.")
        session_note = input(f"method note for this session\n  [Enter = \"{default_method}\"]: ").strip() \
            or default_method
    for row in rows:
        if row["verdict"]:
            continue
        n = prob(row)
        gates = json.loads((STAGING / str(n) / "gates.json").read_text())
        print("─" * 72)
        print(f"Erdős {n}   https://www.erdosproblems.com/{n}   "
              f"gates: {'green' if gates.get('passed') else 'RED'}")
        print("─" * 72)
        print(lean_review_view(STAGING / str(n) / f"{n}.lean"))
        while True:
            ans = input(f"[{n}] verdict f/v/u/s/q: ").strip().lower()
            if ans in ("q", "quit"):
                vpath.write_text(json.dumps({"verdicts": rows}, indent=2) + "\n")
                print("saved; re-run to resume.")
                return 0
            if ans in ("s", "skip"):
                break
            if ans in VERDICT_KEYS:
                note = input(f"[{n}] note [Enter = method note]: ").strip() or session_note
                row["verdict"] = VERDICT_KEYS[ans]
                row["note"] = note
                break
            print("  f=faithful v=variant u=unfaithful s=skip q=save+quit")
        vpath.write_text(json.dumps({"verdicts": rows}, indent=2) + "\n")

    filled = [r for r in rows if r["verdict"]]
    skipped = [prob(r) for r in rows if not r["verdict"]]
    print("\n" + "═" * 72)
    for r in filled:
        print(f"  {prob(r):>5}  {r['verdict']:<11} {r['note'][:70]}")
    if skipped:
        print(f"  skipped (not signed, not shipped): {skipped}")
    if not filled:
        sys.exit("no verdicts to sign")

    yn = input(f"\nSign {len(filled)} verdict(s) as your key-custody act "
               f"(one key read, self-publishes)? [y/N] ").strip().lower()
    if yn != "y":
        print(f"not signed; answers saved in {vpath}. Re-run to sign.")
        return 0
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump({"verdicts": filled}, tf)
        sign_path = tf.name
    rc = subprocess.run([os.environ.get("VELA", "vela"), "review", str(HERE),
                         "--batch", sign_path]).returncode
    os.unlink(sign_path)
    if rc != 0:
        sys.exit(f"vela review failed (exit {rc}); nothing assembled")
    print()
    return assemble(name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "review", "assemble"])
    ap.add_argument("batch")
    args = ap.parse_args()
    if args.cmd == "prepare":
        return prepare(args.batch)
    if args.cmd == "review":
        return review(args.batch)
    return assemble(args.batch)


if __name__ == "__main__":
    sys.exit(main())
