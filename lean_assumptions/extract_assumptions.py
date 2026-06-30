#!/usr/bin/env python3
"""
Vela L1 assumption-extractor harness over the plby fork corpus (Lean v4.29.1).

  discover target theorem decls per Erdős problem (namespace + headline theorems)
  → generate a robust extract.lean (string-resolved decls, skips any missing)
  → run it in the fork's built env → assumptions.jsonl (one L1 record per theorem)
  → join with erdos-fc-sync status.json → audit_feed.json (one row per problem).

The machine layer (L0/L1) only. Verdicts are facts, not human judgment.
"""
import json, re, subprocess, sys, pathlib

HOME = pathlib.Path.home()
import os
FORK = pathlib.Path(os.environ.get("VELA_PROOF_REPO", str(HOME / "personal/lean-proofs-fork/src/v4.29.1")))
ERDOS = FORK / "ErdosProblems"
SP = pathlib.Path(__file__).resolve().parent
EXTRACT = SP / "extract_all.lean"
ASSUMPTIONS = SP / "assumptions.jsonl"
FEED = SP / "audit_feed.json"
STATUS = SP.parent / "status.json"

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


OLEAN_DIR = FORK / ".lake/build/lib/lean/ErdosProblems"


def discover():
    """problem_num → {module, namespace, decls, built}. Only headline theorems."""
    by_num = {}
    for f in sorted(ERDOS.glob("Erdos[0-9]*.lean")):
        m = re.match(r"Erdos(\d+)", f.stem)
        if not m:
            continue
        num = int(m.group(1))
        text = f.read_text(errors="ignore")
        nsm = re.search(r"^namespace (Erdos\d+\w*)", text, re.M)
        ns = nsm.group(1) if nsm else f.stem
        thms = re.findall(r"^theorem (\w+)", text, re.M)
        keep = [t for t in thms if t.startswith(("erdos_", "main_theorem", "not_erdos"))]
        if not keep:
            keep = thms[:2]
        if not keep:
            continue
        by_num[num] = {
            "module": f"ErdosProblems.{f.stem}",
            "decls": [f"{ns}.{t}" for t in keep],
            "built": (OLEAN_DIR / f"{f.stem}.olean").exists(),
        }
    return by_num


def gen_extract(by_num):
    """Import only BUILT modules; audit only their decls (robust to partial build)."""
    built = {n: r for n, r in by_num.items() if r["built"]}
    imports = "\n".join(f"import {r['module']}" for r in built.values())
    decls = [d for r in built.values() for d in r["decls"]]
    body = (EXTRACT_TEMPLATE
            .replace("__IMPORTS__", imports)
            .replace("__DECLS__", ",\n".join(f'  "{d}"' for d in decls)))
    EXTRACT.write_text(body)
    return len(built), len(decls)


def run_extractor():
    res = subprocess.run(
        ["lake", "env", "lean", str(EXTRACT)],
        cwd=str(FORK), capture_output=True, text=True,
    )
    lines = [l for l in res.stdout.splitlines() if l.startswith("{")]
    ASSUMPTIONS.write_text("\n".join(lines) + ("\n" if lines else ""))
    if res.returncode != 0 and not lines:
        sys.stderr.write("EXTRACTOR FAILED:\n" + res.stderr[-3000:] + "\n")
    return [json.loads(l) for l in lines]


def join_feed(records, by_num):
    """One audit row per problem; pick the headline decl (erdos_<num> if present)."""
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
        # headline = the erdos_<num> decl if audited, else the most-conditional
        headline = next((r for r in recs if r["decl"].endswith(f"erdos_{num}")), None)
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
    json.dump(feed, open(FEED, "w"), indent=2)
    return feed


def main():
    by_num = discover()
    nmods, ndecls = gen_extract(by_num)
    nbuilt = sum(1 for r in by_num.values() if r["built"])
    sys.stderr.write(
        f"discovered {len(by_num)} problems ({nbuilt} built); "
        f"auditing {ndecls} decls across {nmods} built modules\n")
    records = run_extractor()
    sys.stderr.write(f"extracted {len(records)} L1 records\n")
    feed = join_feed(records, by_num)
    # summary
    from collections import Counter
    c = Counter(r["machine_verdict"] for r in feed)
    sys.stderr.write(f"feed: {len(feed)} problems | verdicts: {dict(c)}\n")
    axiomcond = [r for r in feed if r["non_kernel_axioms"]]
    sys.stderr.write(f"axiom-conditional (#print axioms catches these): {len(axiomcond)} problems\n")
    # the headline trap class: kernel-clean + sorry-free, yet conditional on a
    # problem-defined named assumption — exactly what #print axioms cannot see.
    traps = [r for r in feed if r["machine_verdict"] == "conditional"
             and not r["non_kernel_axioms"] and r["named_assumptions"]]
    sys.stderr.write(f"AXIOM-CLEAN-BUT-CONDITIONAL (the 678 trap class): {len(traps)} problems\n")
    for r in sorted(traps, key=lambda r: r["problem"]):
        sys.stderr.write(f"  #{r['problem']:>5}  {r['headline_decl']:38} {r['named_assumptions']}\n")


if __name__ == "__main__":
    main()
