#!/usr/bin/env python3
"""
erdos-fc-sync — a computed source of truth for the Erdős proof-sync effort.

The problem this solves is drift. A problem's "status" is stored in several places
that update independently:

  * erdosproblems.com (Bloom's upstream status)
  * the Formal Conjectures repo (each file's @[category ...] annotation + formal_proof)
  * the proof collections that host Lean proofs of solved problems
    (plby/lean-proofs and Jayyhk/erdos-lean), and whether each proof is conditional

Reconciling those by hand is what drifts. This script computes the status instead, by
joining the machine-readable sources on the problem number, plus the live set of open
FC pull requests so it never points anyone at in-flight work. It writes STATUS.md.

Sources (all fetched fresh):
  fc      https://google-deepmind.github.io/formal-conjectures/data/conjectures.json
  erdos   https://raw.githubusercontent.com/teorth/erdosproblems/main/data/problems.yaml
  plby    https://raw.githubusercontent.com/plby/lean-proofs/main/data/sources.yaml
  jayyhk  https://raw.githubusercontent.com/Jayyhk/erdos-lean/main/data/problems.yaml
  claims  github.com/google-deepmind/formal-conjectures open PRs (REST API)

Run: python fc-sync-status.py            (writes STATUS.md, prints the summary)
A GitHub token in GH_TOKEN / GITHUB_TOKEN lets the open-PR (claims) layer run.
"""
import json, re, os, urllib.request, urllib.error, datetime
import yaml

UA = {"User-Agent": "erdos-fc-sync"}
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

CONJ_URL = "https://google-deepmind.github.io/formal-conjectures/data/conjectures.json"
ERDOS_URL = "https://raw.githubusercontent.com/teorth/erdosproblems/main/data/problems.yaml"
PLBY_URL = "https://raw.githubusercontent.com/plby/lean-proofs/main/data/sources.yaml"
JAYY_URL = "https://raw.githubusercontent.com/Jayyhk/erdos-lean/main/data/problems.yaml"
REPO = "google-deepmind/formal-conjectures"
SRC_TAG = {"plby": "ᵖ", "jayyhk": "ʲ"}


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


# --- erdos upstream status ------------------------------------------------
erdos = {int(p["number"]): p for p in yaml.safe_load(fetch(ERDOS_URL))}

# --- hosted proofs: union of plby and Jayyhk ------------------------------
# presence => a proof is hosted; only a non-conditional / `complete` proof counts
# as complete (an axiomatic / trust-extended / partial proof is not).
proofs = {}  # n -> {"complete", "conditional", "partial": bool, "sources": set}


def add_proof(n, complete, conditional, partial, source):
    rec = proofs.setdefault(n, {"complete": False, "conditional": False,
                                "partial": False, "sources": set()})
    rec["complete"] |= complete
    rec["conditional"] |= conditional
    rec["partial"] |= partial
    rec["sources"].add(source)


for e in yaml.safe_load(fetch(PLBY_URL)):
    m = re.search(r"Erdos(\d+)", e.get("key", ""))
    if not m:
        continue
    # key PRESENCE is the flag; `conditional:` is often null-valued (axiom omitted).
    # plby's distinction: `conditional` assumes an axiom; `partial` proves a variant.
    cond = "conditional" in e
    part = "partial" in e
    add_proof(int(m.group(1)), not (cond or part), cond, part, "plby")

for e in yaml.safe_load(fetch(JAYY_URL)):
    try:
        n = int(e["number"])
    except (KeyError, ValueError, TypeError):
        continue
    state = (e.get("proof") or {}).get("state")
    # Jayyhk: `complete` is clean; `axiomatic` / `trust_extended` are not axiom-clean.
    add_proof(n, state == "complete", state in ("axiomatic", "trust_extended"), False, "jayyhk")

# --- FC view: has a file? has a formal_proof link? ------------------------
conj = json.loads(fetch(CONJ_URL))
entries = []
for v in conj.values():
    entries.extend(v if isinstance(v, list) else [v])
fc = {}
for e in entries:
    if not isinstance(e, dict):
        continue
    m = re.search(r"ErdosProblems/(\d+)\.lean", e.get("githubPath") or "")
    if not m:
        continue
    rec = fc.setdefault(int(m.group(1)), {"has_file": True, "linked": False})
    if e.get("hasFormalProof") and e.get("formalProofLink"):
        rec["linked"] = True


# --- claims: numbers touched by an open FC pull request -------------------
def get_claims():
    claimed, available = set(), False
    hdr = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    try:
        prs, page = [], 1
        while True:
            batch = json.loads(fetch(
                f"https://api.github.com/repos/{REPO}/pulls?state=open&per_page=100&page={page}", hdr))
            prs += batch
            if len(batch) < 100:
                break
            page += 1
        for pr in prs:
            files = json.loads(fetch(
                f"https://api.github.com/repos/{REPO}/pulls/{pr['number']}/files?per_page=100", hdr))
            for f in files:
                m = re.search(r"ErdosProblems/(\d+)\.lean", f.get("filename", ""))
                if m:
                    claimed.add(int(m.group(1)))
        available = True
    except (urllib.error.HTTPError, urllib.error.URLError):
        pass  # rate-limited / no token: degrade, note it in the output
    return claimed, available


claimed, claims_available = get_claims()


def get_wontfix():
    """FC issues the maintainers labelled `won't fix` are explicit do-not-link calls
    (e.g. 678, where the hosted proof is not actually complete). Respect them."""
    import urllib.parse
    s = set()
    hdr = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    try:
        page = 1
        while True:
            url = (f"https://api.github.com/repos/{REPO}/issues?state=all&labels="
                   + urllib.parse.quote("won't fix") + f"&per_page=100&page={page}")
            batch = json.loads(fetch(url, hdr))
            if not batch:
                break
            for it in batch:
                if it.get("pull_request"):
                    continue
                m = re.search(r"Problem (\d+)", it.get("title", ""))
                if m:
                    s.add(int(m.group(1)))
            if len(batch) < 100:
                break
            page += 1
    except (urllib.error.HTTPError, urllib.error.URLError):
        pass
    return s


wontfix = get_wontfix()

# Maintainer judgments that live in an issue comment, not in a label or the structured
# data, so the join can't infer them. Kept short and transparent; prune as the data
# catches up.
MANUAL_SKIP = {678}    # mo271: the hosted proof "is not actually complete" (FC#4051)
MANUAL_CLAIMS = {613}  # Paul-Lez claimed it on FC#3965 (an issue comment, not a PR)
wontfix |= MANUAL_SKIP
claimed |= MANUAL_CLAIMS


def action(n):
    f = fc.get(n, {"has_file": False, "linked": False})
    p = proofs.get(n)
    if f["linked"]:
        return "done"
    if not p:
        return "no-proof"
    if n in wontfix:
        return "wont-fix"
    if n in claimed:
        return "in-pr"
    if p["complete"]:
        return "link" if f["has_file"] else "statement"
    if p["conditional"]:
        return "docstring"
    return "partial"


def srcs(n):
    s = proofs.get(n, {}).get("sources", set())
    return "".join(SRC_TAG[k] for k in ("plby", "jayyhk") if k in s)


rows = [(n, action(n), erdos[n].get("status", {}).get("state", "?")) for n in sorted(erdos)]

from collections import Counter
counts = Counter(a for _, a, _ in rows)
ORDER = ["statement", "link", "docstring", "partial", "in-pr", "wont-fix", "done", "no-proof"]
DESC = {
    "statement": "**Write the FC statement + link.** A complete hosted proof exists, FC has no file yet. The #3998 batch.",
    "link":      "**Add the `formal_proof` link.** FC already has the statement; the hosted proof just isn't linked.",
    "docstring": "**Docstring note, not a `formal_proof` tag.** The hosted proof is conditional (assumes an unformalized axiom) or axiomatic / trust-extended.",
    "partial":   "**Partial proof.** Proves a specific variant, not the full erdosproblems statement. May be linkable to that FC variant; needs a per-problem look (per @plby).",
    "in-pr":     "**Claimed.** An open FC pull request (or a tracked issue claim) already covers this.",
    "wont-fix":  "**Maintainer marked `won't fix`** (e.g. the hosted proof is not actually complete). Skip it.",
    "done":      "Already linked in FC.",
    "no-proof":  "No hosted Lean proof to link (nothing to do here yet).",
}
EPC = "https://www.erdosproblems.com"


def md():
    today = datetime.date.today().isoformat()
    out = []
    out.append("# Erdős ↔ Formal Conjectures sync status\n")
    out.append(f"*Regenerated {today} by [`fc-sync-status.py`](fc-sync-status.py). "
               "Do not edit by hand.*\n")
    out.append(
        "This is a **computed** view, not a hand-kept list. It joins the machine-readable "
        "sources on the problem number so the status can't drift:\n\n"
        "- [erdosproblems.com](https://www.erdosproblems.com) status "
        "([`problems.yaml`](https://github.com/teorth/erdosproblems/blob/main/data/problems.yaml))\n"
        "- Formal Conjectures' own [`conjectures.json`](https://google-deepmind.github.io/formal-conjectures/data/conjectures.json) "
        "(has-a-file + `formalProofLink`)\n"
        "- hosted proofs from [`plby/lean-proofs`](https://github.com/plby/lean-proofs/blob/main/data/sources.yaml) (ᵖ) "
        "and [`Jayyhk/erdos-lean`](https://github.com/Jayyhk/erdos-lean/blob/main/data/problems.yaml) (ʲ), "
        "with their `conditional` / `axiomatic` / `trust_extended` flags\n\n"
        "It also folds in the live set of open FC pull requests, so it never points at in-flight work. "
        "The ᵖ / ʲ marks after each problem show which collection hosts the proof.\n")
    if not claims_available:
        out.append("> ⚠️ The open-PR (claims) layer did not run this time (no token / rate limit), "
                   "so `in-pr` may be undercounted.\n")
    out.append(f"Reconciled **{len(rows)}** problems.\n")
    out.append("| status | count | meaning |\n|---|---:|---|")
    for a in ORDER:
        out.append(f"| `{a}` | {counts.get(a,0)} | {DESC[a]} |")
    out.append("\n*A short manual list carries two maintainer calls that live in issue "
               "comments rather than the structured sources: 678 (`wont-fix`, mo271 flagged the "
               "proof as not actually complete) and 613 (`in-pr`, claimed by Paul-Lez). "
               "Everything else is computed.*\n")
    for a in ("statement", "link", "docstring", "partial", "wont-fix"):
        ns = [n for n, x, _ in rows if x == a]
        out.append(f"\n## `{a}` — {len(ns)} problem(s)\n\n{DESC[a]}\n")
        out.append(" ".join(f"[{n}]({EPC}/{n}){srcs(n)}" for n in ns) or "_none_")
    out.append("")
    return "\n".join(out)


with open("STATUS.md", "w") as f:
    f.write(md())

print(f"reconciled {len(rows)} problems; claims_available={claims_available}; "
      f"hosted proofs tracked: {len(proofs)}")
for a in ORDER:
    print(f"  {a:>10}: {counts.get(a,0)}")
print("wrote STATUS.md")
