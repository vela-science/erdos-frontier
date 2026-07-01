#!/usr/bin/env python3
"""
Vela L1 assumption-extractor harness, multi-repo / multi-toolchain.

  discover target theorem decls per Erdős problem (namespace + headline theorems)
  → generate a robust extract.lean (string-resolved decls, skips any missing)
  → run it in the repo's own built env → assumptions_<tag>.jsonl (one L1 record/thm)
  → join with erdos-frontier status.json → audit_feed[_<tag>].json (one row/problem).

Each proof repo pins its own Lean toolchain and lives at its own root; the same
metaprogram runs against each (it operates on decl-name strings, not Lean versions).
A repo's feed is tagged so erdos_frontier can merge feeds and keep the strongest
verdict per problem. The machine layer (L0/L1) only — verdicts are facts, not human
judgment.

  python extract_assumptions.py --repo plby         # default; writes audit_feed.json
  python extract_assumptions.py --repo alphaproof    # writes audit_feed_alphaproof.json
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
from collections import Counter

HOME = pathlib.Path.home()
SP = pathlib.Path(__file__).resolve().parent
STATUS = SP.parent / "site" / "status.json"

# Per-repo config. `root` is the lake project (where `lake env lean` runs and
# `.lake/build` lives); override with the env var for CI checkouts. `glob` finds
# the Erdős problem files under it; `num_re` reads the problem number from the file
# name; `keep` selects the headline theorem(s) in each file.
# `headline_override` pins the boxed theorem for a problem the name heuristic
# mis-selects. Hand-verified, one entry per correction, kept explicit so the choice
# is auditable rather than emergent.
#
# #997: the file names its boxed result `erdos997` (no underscore, so the `erdos_`
# keep-prefix misses it) at the end of the file, past the `thms[:2]` fallback window,
# so the heuristic picked the helper `not_wellDistributed_of_clustering`, which is
# conditional on a `HasClustering` hypothesis the boxed theorem discharges. The boxed
# theorem's own `#print axioms erdos997` attests the real dependency: the visible
# `maynardTaoBFT` axiom. Verdict stays conditional (still a discrepancy) but now
# reports a visible axiom instead of an invisible hypothesis.
#
# #347: the heuristic picked the helper `main_theorem`, which is conditional on an
# `is_cofinite_subsequence` hypothesis. The file's actual boxed answer is
# `answer_is_yes` (it constructs the sequence, discharges the hypothesis, and
# `#print axioms answer_is_yes` is kernel-clean). Pinning it flips 347 to
# unconditional: it was a FALSE positive in the discrepancy view, not a conditional
# proof. The keep-prefix missed `answer_is_yes` (no `erdos_`/`main_theorem` prefix).
#
# #164, #296: same shape as #347, found by the mispick sweep. The boxed answers
# `erdos164` and `erdos296` are closed, argument-free, kernel-clean theorems (the
# file's own `#print axioms` targets) — genuinely unconditional. The heuristic
# instead picked a conditional helper (`erdos_strong_on_pRough…`, `erdos296_upper_bound`)
# because the boxed names have no underscore after `erdos`, so the `erdos_` keep-prefix
# misses them. Hand-verified: each boxed theorem states the full problem with no
# hypothesis parameter. (Not fixed here: #94/#785 whose boxed answers still carry a
# problem hypothesis, so `conditional` is correct; #1080 whose answer is a negation
# the extractor's forallTelescope cannot read cleanly.)
REPOS = {
    "plby": {
        "root_env": "VELA_PROOF_REPO",
        "root": HOME / "personal/lean-proofs-fork/src/v4.29.1",
        "glob": "ErdosProblems/Erdos[0-9]*.lean",
        "num_re": r"Erdos(\d+)",
        "keep": ("erdos_", "main_theorem", "not_erdos"),
        "headline_override": {997: "erdos997", 347: "answer_is_yes",
                              164: "erdos164", 296: "erdos296"},
    },
    "alphaproof": {
        "root_env": "VELA_PROOF_REPO_ALPHAPROOF",
        "root": HOME / "personal/alphaproof-nexus-results",
        "glob": "APNOutputs/ErdosProblems/erdos_[0-9]*.lean",
        "num_re": r"erdos_(\d+)",
        "keep": ("target_theorem", "erdos_"),
        "headline_override": {},
    },
    # Jayyhk/erdos-lean is a per-problem-project repo: each `problems/<n>/` is its
    # own lake project pinned to its own toolchain + mathlib revision (so it cannot
    # be one built env like plby). The driver audits every problem whose project is
    # already built and records the machine verdict beside the producer's declared
    # `state`, so a `complete` claim over a conditional proof shows up as an overclaim.
    "jayyhk": {
        "root_env": "VELA_PROOF_REPO_JAYYHK",
        "root": HOME / "personal/erdos-lean",
        "mode": "per_problem_project",
        "manifest": "data/problems.yaml",
        "headline_override": {},
    },
}

EXTRACT_TEMPLATE = r'''__IMPORTS__
open Lean Elab Command Meta
def declNames : List String := [
__DECLS__
]
def kernelAxioms : List Name := [``propext, ``Classical.choice, ``Quot.sound]
run_cmd do
  let env ← getEnv
  for s in declNames do
    let declName := s.toName
    if (env.find? declName).isNone then continue
    let axs ← liftCoreM (Lean.collectAxioms declName)
    let axList := axs.toList
    let sorryFree := !axList.contains ``sorryAx
    let nonKernel := axList.filter (fun a => !kernelAxioms.contains a && a != ``sorryAx)
    let (named, preconds) ← liftTermElabM do
      let info ← getConstInfo declName
      forallTelescope info.type fun xs _ => do
        let mut named : Array String := #[]
        let mut preconds : Array String := #[]
        for x in xs do
          let ld ← x.fvarId!.getDecl
          if (← Meta.isProp ld.type) && ld.binderInfo != BinderInfo.instImplicit then
            let nm := ld.userName.eraseMacroScopes
            let nmStr := if nm.isInternal || nm.hasMacroScopes then "_" else nm.toString
            let entry := s!"{nmStr} : {(← ppExpr ld.type).pretty.replace "\n" " "}"
            -- a problem-defined named Prop (head const in an Erdos* namespace)
            -- is a candidate smuggled assumption; everything else is a routine
            -- precondition (an inequality, membership, quantified formula, or a
            -- standard Mathlib property of the theorem's own variables).
            let isNamed := match ld.type.getAppFn with
              | .const hn _ => "Erdos".isPrefixOf hn.toString
              | _ => false
            if isNamed then named := named.push entry else preconds := preconds.push entry
        return (named, preconds)
    let verdict := if !sorryFree then "incomplete"
                   else if !named.isEmpty || !nonKernel.isEmpty then "conditional"
                   else "unconditional"
    let record : Json := Json.mkObj [
      ("schema", Json.str "vela.lean_assumption.v0.1"),
      ("decl", Json.str declName.toString),
      ("sorry_free", Json.bool sorryFree),
      ("axioms", Json.arr (axList.map (fun a => Json.str a.toString)).toArray),
      ("axiom_verdict", Json.str (if nonKernel.isEmpty then "kernel_clean" else "non_kernel_axioms")),
      ("named_assumptions", Json.arr (named.map Json.str)),
      ("preconditions", Json.arr (preconds.map Json.str)),
      ("verdict", Json.str verdict) ]
    IO.println record.compress
'''


def module_of(file: pathlib.Path, root: pathlib.Path) -> str:
    """Lean module name from the file's path relative to the lake root.

    A path component that itself contains a dot (alphaproof names files like
    ``erdos_12.parts.ii.lean``) must be guillemet-quoted, or Lean reads the dots as
    module separators and looks for a nested ``erdos_12/parts/ii.olean`` that does
    not exist.
    """
    parts = [f"«{p}»" if "." in p else p
             for p in file.relative_to(root).with_suffix("").parts]
    return ".".join(parts)


def olean_of(file: pathlib.Path, root: pathlib.Path) -> pathlib.Path:
    rel = file.relative_to(root).with_suffix(".olean")
    return root / ".lake/build/lib/lean" / rel


def discover(cfg: dict, root: pathlib.Path) -> dict:
    """problem_num → {module, decls, built}. Only headline theorems."""
    num_re = re.compile(cfg["num_re"])
    by_num: dict[int, dict] = {}
    for f in sorted(root.glob(cfg["glob"])):
        m = num_re.search(f.name)
        if not m:
            continue
        num = int(m.group(1))
        text = f.read_text(errors="ignore")
        nsm = re.search(r"^namespace (Erdos\d+\w*)", text, re.M)
        ns = nsm.group(1) if nsm else f.stem
        thms = re.findall(r"^theorem (\w+)", text, re.M)
        keep = [t for t in thms if t.startswith(cfg["keep"])]
        if not keep:
            keep = thms[:2]
        # a hand-verified headline pin overrides the heuristic: audit that boxed
        # theorem and force it as the reported decl in join_feed (see REPOS).
        override = cfg.get("headline_override", {}).get(num)
        forced = None
        if override and override in thms:
            if override not in keep:
                keep = [override, *keep]
            forced = f"{ns}.{override}"
        if not keep:
            continue
        # last file per problem number wins (e.g. Erdos1100b over Erdos1100), as
        # before; cross-repo strongest-verdict merge lives in erdos_frontier.
        by_num[num] = {
            "module": [module_of(f, root)],
            "decls": [f"{ns}.{t}" for t in keep],
            "built": olean_of(f, root).exists(),
            "headline": forced,
        }
    return by_num


def gen_extract(by_num: dict, extract_path: pathlib.Path):
    """Import only BUILT modules; audit only their decls (robust to partial build)."""
    built = {n: r for n, r in by_num.items() if r["built"]}
    modules = sorted({m for r in built.values() for m in r["module"]})
    imports = "\n".join(f"import {m}" for m in modules)
    decls = [d for r in built.values() for d in r["decls"]]
    body = (EXTRACT_TEMPLATE
            .replace("__IMPORTS__", imports)
            .replace("__DECLS__", ",\n".join(f'  "{d}"' for d in decls)))
    extract_path.write_text(body)
    return len(modules), len(decls)


def run_extractor(root: pathlib.Path, extract_path: pathlib.Path, out_jsonl: pathlib.Path):
    res = subprocess.run(
        ["lake", "env", "lean", str(extract_path)],
        cwd=str(root), capture_output=True, text=True,
    )
    lines = [l for l in res.stdout.splitlines() if l.startswith("{")]
    out_jsonl.write_text("\n".join(lines) + ("\n" if lines else ""))
    if res.returncode != 0 and not lines:
        sys.stderr.write("EXTRACTOR FAILED:\n" + res.stderr[-3000:] + "\n")
    return [json.loads(l) for l in lines]


def join_feed(records: list, by_num: dict, out_feed: pathlib.Path):
    """One audit row per problem; pick the headline decl (erdos_<num> or target_theorem)."""
    status_rows = {}
    if STATUS.exists():
        s = json.load(open(STATUS))
        for r in s.get("rows", []):
            status_rows[r.get("problem")] = r
    by_decl = {r["decl"]: r for r in records}
    feed = []
    for num, info in sorted(by_num.items()):
        recs = [by_decl[d] for d in info["decls"] if d in by_decl]
        if not recs:
            continue
        # a hand-verified pin wins; else the problem-numbered boxed name; else the
        # most-conditional decl among those audited.
        forced = info.get("headline")
        headline = next((r for r in recs if r["decl"] == forced), None) if forced else None
        if headline is None:
            headline = next(
                (r for r in recs if r["decl"].endswith((f"erdos_{num}", "target_theorem_0"))), None)
        order = {"incomplete": 0, "conditional": 1, "unconditional": 2}
        if headline is None:
            headline = min(recs, key=lambda r: order.get(r["verdict"], 9))
        st = status_rows.get(num, {})
        feed.append({
            "problem": num,
            "erdos_url": f"https://www.erdosproblems.com/{num}",
            "fc_status": st.get("erdos_state"),
            "fc_bucket": st.get("bucket"),
            "headline_decl": headline["decl"],
            "machine_verdict": headline["verdict"],
            "axiom_verdict": headline["axiom_verdict"],
            "non_kernel_axioms": [a for a in headline["axioms"]
                                  if a not in ("propext", "Classical.choice", "Quot.sound")],
            "named_assumptions": headline["named_assumptions"],
            "preconditions": headline["preconditions"],
            "all_decls": {r["decl"]: r["verdict"] for r in recs},
        })
    json.dump(feed, open(out_feed, "w"), indent=2)
    return feed


def audit_jayyhk(cfg: dict, root: pathlib.Path, out_feed: pathlib.Path):
    """Per-problem-project audit. Each `problems/<n>/` is its own built lake project;
    run the same metaprogram on its boxed theorem and record the verdict beside the
    producer-declared `state`. Only already-built projects are audited (building the
    12 pinned toolchains is the CI job); the rest are skipped and reported."""
    import yaml
    manifest = yaml.safe_load((root / cfg["manifest"]).read_text())
    feed, counts = [], Counter()
    built = skipped = 0
    for entry in manifest:
        try:
            num = int(entry["number"])
        except (KeyError, ValueError, TypeError):
            continue
        proof = entry.get("proof") or {}
        theorem = proof.get("theorem")            # e.g. Erdos45.erdos_45
        pdir = root / (proof.get("path") or f"problems/{num}/")
        if not theorem or not (pdir / ".lake" / "build").exists():
            skipped += 1
            continue
        module = theorem.split(".")[0]            # Erdos45
        extract_path = pdir / "extract_jayyhk.lean"
        extract_path.write_text(
            EXTRACT_TEMPLATE.replace("__IMPORTS__", f"import {module}")
                            .replace("__DECLS__", f'  "{theorem}"'))
        res = subprocess.run(["lake", "env", "lean", extract_path.name],
                             cwd=str(pdir), capture_output=True, text=True)
        recs = [json.loads(l) for l in res.stdout.splitlines() if l.startswith("{")]
        rec = next((r for r in recs if r["decl"] == theorem), recs[0] if recs else None)
        if rec is None:
            sys.stderr.write(f"[jayyhk] #{num}: no record ({res.stderr[-160:].strip()})\n")
            continue
        built += 1
        counts[rec["verdict"]] += 1
        feed.append({
            "problem": num,
            "erdos_url": f"https://www.erdosproblems.com/{num}",
            "headline_decl": rec["decl"],
            "machine_verdict": rec["verdict"],
            "axiom_verdict": rec["axiom_verdict"],
            "non_kernel_axioms": [a for a in rec["axioms"]
                                  if a not in ("propext", "Classical.choice", "Quot.sound")],
            "named_assumptions": rec["named_assumptions"],
            "preconditions": rec["preconditions"],
            "declared_state": proof.get("state"),
            "all_decls": {rec["decl"]: rec["verdict"]},
        })
    json.dump(feed, open(out_feed, "w"), indent=2)
    sys.stderr.write(f"[jayyhk] audited {built} built projects ({skipped} unbuilt/skipped); "
                     f"verdicts {dict(counts)} -> {out_feed.name}\n")
    over = [r["problem"] for r in feed
            if r.get("declared_state") == "complete" and r["machine_verdict"] == "conditional"]
    if over:
        sys.stderr.write(f"[jayyhk] PRODUCER OVERCLAIM (declared complete, machine conditional): {over}\n")
    return feed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", choices=sorted(REPOS), default="plby")
    ap.add_argument("--root", help="override the lake project root (else env/default)")
    args = ap.parse_args()
    cfg = REPOS[args.repo]
    root = pathlib.Path(args.root or os.environ.get(cfg["root_env"], str(cfg["root"])))

    # plby keeps the legacy output names so the committed feed is unchanged.
    suffix = "" if args.repo == "plby" else f"_{args.repo}"
    extract_path = SP / f"extract{suffix or '_all'}.lean"
    out_jsonl = SP / f"assumptions{suffix}.jsonl"
    out_feed = SP / f"audit_feed{suffix}.json"

    if not root.exists():
        sys.stderr.write(f"[{args.repo}] root not found: {root} — skipping\n")
        return
    if cfg.get("mode") == "per_problem_project":
        audit_jayyhk(cfg, root, out_feed)
        return
    by_num = discover(cfg, root)
    nmods, ndecls = gen_extract(by_num, extract_path)
    nbuilt = sum(1 for r in by_num.values() if r["built"])
    sys.stderr.write(
        f"[{args.repo}] root={root}\n"
        f"[{args.repo}] discovered {len(by_num)} problems ({nbuilt} built); "
        f"auditing {ndecls} decls across {nmods} built modules\n")
    records = run_extractor(root, extract_path, out_jsonl)
    sys.stderr.write(f"[{args.repo}] extracted {len(records)} L1 records\n")
    feed = join_feed(records, by_num, out_feed)
    c = Counter(r["machine_verdict"] for r in feed)
    sys.stderr.write(f"[{args.repo}] feed: {len(feed)} problems | verdicts: {dict(c)} -> {out_feed.name}\n")
    traps = [r for r in feed if r["machine_verdict"] == "conditional"
             and not r["non_kernel_axioms"] and r["named_assumptions"]]
    sys.stderr.write(f"[{args.repo}] axiom-clean-but-conditional (678 trap class): {len(traps)}\n")
    for r in sorted(traps, key=lambda r: r["problem"]):
        sys.stderr.write(f"  #{r['problem']:>5}  {r['headline_decl']:38} {r['named_assumptions']}\n")


if __name__ == "__main__":
    main()
