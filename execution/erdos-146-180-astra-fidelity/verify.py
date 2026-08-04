#!/usr/bin/env python3
"""Source-first mechanical qualification for the Astra Erdős 146/180 matrices."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
from typing import Any

FRONTIER_COMMIT = "3abe642436ea7692a54e1f6008d5e8b05a8c06eb"
STATEMENTS_ROOT = "sha256:dd66cd1de41db64b13d5c2d1f0e486c722924ee2a7d679af3a93bc67f3185ac4"
ASTRA_COMMIT = "29362184c2b698c1b279bc85b3957ee813646c63"
ASTRA_TREE = "730bf2c6a13dbb96606024c5fd681a48633fb393"
ERDOSPROBLEMS_COMMIT = "8138974387d9030542daabe67faaa33eff9356f8"
ERDOSPROBLEMS_TREE = "7ed44c260d7eb63a067cf5a16afdb645d494ef06"
ERDOSPROBLEMS_ROOT = "sha256:a4358d57b591fc92c75981c160a11f43a561de6b5e8478d8f9629511759a9213"
PAPER_ROOT = "sha256:64b900d5fae6fe22f2ae1b8e3b712d20055194a6c81cf343a2455e5898ac7dd6"
REPLAY_FILE_ROOT = "sha256:bc25a2bd0d410d890144a0f045330fd4649f2bfc7171242c38661b2d6a9ac8f3"
REPLAY_SELF_ROOT = "sha256:5a60c3be27036c65a6a37bf55dce71abcb024cfecece92b8e7dcaf1324b095d0"
SOLUTION_ROOT = "sha256:ed50917cd60c231551698a276efbef4161e34c8ff9ecb069f3b9c937d030a68c"

CASES = {
    146: {
        "report": "artifacts/fidelity/erdos-146-astra-fidelity.v1.json",
        "report_root": "sha256:7180b9a43e0465cce9afaad85ff40ebf1cdb91ddf536c000de6bfbbf423a98c2",
        "statement": "If $H$ is bipartite and is $r$-degenerate, that is, every induced subgraph of $H$ has minimum degree $\\leq r$, then\\[\\mathrm{ex}(n;H) \\ll n^{2-1/r}.\\]",
        "conclusion": "faithful",
        "profile_id": "J-146",
        "profile_root": "48e77981fb8a5f29e444f619cabb98d7c5df95d7150fb8808a17d94b05b38426",
        "challenge": "ComparatorChallenges/J_TwoDegenerateGraphs.lean",
        "challenge_root": "sha256:9565db54e089c8a3d5be1d463c06429283aee131f0506306bb4bfaf64dfbdf9e",
        "theorems": [
            "TwoDegenerateGraphs.twoDegenerateExtremalCounterexample",
            "TwoDegenerateGraphs.not_erdos_146",
        ],
        "assessments": {
            "definition_mapping": "match",
            "quantifiers": "match_with_explicit_domain",
            "hypotheses": "match",
            "conclusion": "match",
            "source_timing_and_disagreement": "status_lag_not_statement_mismatch",
            "unresolved_questions": "none_within_statement_fidelity",
        },
        "lean_fragments": [
            "def IsDegenerate {V : Type*} (r : ℕ) (G : SimpleGraph V) : Prop :=",
            "∀ s : Finset V, s.Nonempty →",
            "∃ v ∈ s, (neighborsWithin G s v).card ≤ r",
            "0 < r → H.IsBipartite → IsDegenerate r H →",
            "(fun n : ℕ => (n : ℝ) ^ (((2 : ℕ) : ℝ) - 1 / (r : ℝ)))",
            "H.Connected ∧",
            "H.IsBipartite ∧",
            "IsTwoDegenerate H ∧",
            "c * (n : ℝ) ^ ((3 : ℝ) / 2 + ε) ≤",
            "theorem not_erdos_146 :",
            "¬ DegeneracyConjectureStatement := by",
        ],
    },
    180: {
        "report": "artifacts/fidelity/erdos-180-astra-fidelity.v1.json",
        "report_root": "sha256:a8758344f24ad00f0bf5c4d38e77105bc8ceef25aff0c3daa36f7e6f6a9766a4",
        "statement": "If $\\mathcal{F}$ is a finite set of finite graphs then $\\mathrm{ex}(n;\\mathcal{F})$ is the maximum number of edges a graph on $n$ vertices can have without containing any subgraphs from $\\mathcal{F}$. Note that it is trivial that $\\mathrm{ex}(n;\\mathcal{F})\\leq \\mathrm{ex}(n;G)$ for every $G\\in\\mathcal{F}$. Is it true that, for every $\\mathcal{F}$, there exists $G\\in\\mathcal{F}$ such that\\[\\mathrm{ex}(n;G)\\ll_{\\mathcal{F}}\\mathrm{ex}(n;\\mathcal{F})?\\]",
        "conclusion": "qualified_mismatch",
        "profile_id": "J-180",
        "profile_root": "e9a7a93409f01b4ca611ddb21a6c69821f9fde60dd385651aa62f4ebe68ba3a6",
        "challenge": "ComparatorChallenges/J_CompactnessConjecture.lean",
        "challenge_root": "sha256:0640640051c055e453df5551696ebaa61f3fa9d647ba9ec38b1734d280898801",
        "theorems": [
            "CompactnessConjecture.quantitativeCompactnessCounterexample",
            "CompactnessConjecture.compactnessCounterexample_bigO",
            "CompactnessConjecture.not_erdos_180",
        ],
        "assessments": {
            "definition_mapping": "match",
            "quantifiers": "qualified_mismatch",
            "hypotheses": "corrected_formulation_not_literal_source",
            "conclusion": "consequence_matches_both",
            "source_timing_and_disagreement": "status_lag_plus_statement_correction",
            "unresolved_questions": "source_correction_required_before_faithful_label",
        },
        "lean_fragments": [
            "def IsCyclicFamily (family : Finset FiniteGraph) : Prop :=",
            "∀ forbidden ∈ family, ¬ forbidden.graph.IsAcyclic",
            "family.Nonempty → IsCyclicFamily family → IsCompactFamily family",
            "∀ forbidden ∈ family,",
            "forbidden.graph.Connected ∧ forbidden.graph.IsBipartite ∧",
            "¬ forbidden.graph.IsAcyclic) ∧",
            "(21 : ℝ) / 16 = (4 : ℝ) / 3 - 1 / 48 ∧",
            "¬ IsCompactFamily family ∧",
            "¬ CompactnessConjectureStatement := by",
        ],
    },
}


def root(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def git_value(repository: pathlib.Path, expression: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", expression], text=True
    ).strip()


def git_blob(repository: pathlib.Path, commit: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(repository), "show", f"{commit}:{path}"]
    )


def require_fragments(text: str, fragments: list[str], label: str) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} lost required source fragments: {missing}")


def normalized_pdf_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="strict")
    for source, replacement in {
        "ﬀ": "ff",
        "ﬁ": "fi",
        "ﬂ": "fl",
        "−": "-",
    }.items():
        text = text.replace(source, replacement)
    return re.sub(r"\s+", " ", text)


def yaml_problem_block(text: str, problem: int) -> str:
    marker = f'- number: "{problem}"'
    if marker not in text:
        raise ValueError(f"missing Erdős problem {problem} status block")
    return text.split(marker, 1)[1].split('\n- number: "', 1)[0]


def verify(args: argparse.Namespace) -> dict[str, Any]:
    frontier = args.frontier.resolve()
    astra = args.ten_proofs.resolve()
    erdosproblems = args.erdosproblems.resolve()
    vela = args.vela.resolve()
    paper = args.paper.resolve()

    if git_value(astra, "HEAD") != ASTRA_COMMIT or git_value(astra, "HEAD^{tree}") != ASTRA_TREE:
        raise ValueError("Astra source commit or tree drifted")
    if (
        git_value(erdosproblems, "HEAD") != ERDOSPROBLEMS_COMMIT
        or git_value(erdosproblems, "HEAD^{tree}") != ERDOSPROBLEMS_TREE
    ):
        raise ValueError("erdosproblems source commit or tree drifted")

    statements_raw = git_blob(frontier, FRONTIER_COMMIT, "sources/statements.v1.json")
    if root(statements_raw) != STATEMENTS_ROOT:
        raise ValueError("retained statement snapshot drifted")
    statement_snapshot = json.loads(statements_raw)
    statements = {
        int(problem): entry["statement"]
        for problem, entry in statement_snapshot["problems"].items()
    }

    status_raw = (erdosproblems / "data/problems.yaml").read_bytes()
    if root(status_raw) != ERDOSPROBLEMS_ROOT:
        raise ValueError("erdosproblems status source drifted")
    status_text = status_raw.decode()
    for problem in CASES:
        block = yaml_problem_block(status_text, problem)
        require_fragments(
            block,
            ['state: "open"', 'state: "unformalized"', 'last_update: "2025-08-31"'],
            f"erdosproblems {problem}",
        )

    paper_raw = paper.read_bytes()
    if root(paper_raw) != PAPER_ROOT:
        raise ValueError("OpenAI manuscript root drifted")
    paper_pages = subprocess.check_output(
        ["pdftotext", "-f", "237", "-l", "238", "-layout", str(paper), "-"]
    )
    paper_text = normalized_pdf_text(paper_pages)
    require_fragments(
        paper_text,
        [
            "The original formulation admits simple counterexamples",
            "The corrected form of the conjecture",
            "all of whose members contain cycles",
            "every nonempty subgraph of H has a vertex of degree at most r",
            "connected bipartite 2- degenerate graph H",
            "c n3/2+ε",
        ],
        "OpenAI manuscript pages 237-238",
    )

    solution_raw = (astra / "CompactnessAndDegeneracy.lean").read_bytes()
    if root(solution_raw) != SOLUTION_ROOT:
        raise ValueError("Astra solution module drifted")

    replay_path = vela / "paper/artifacts/astra-ten-result-map-2026-08-03/result.v1.json"
    replay_raw = replay_path.read_bytes()
    if root(replay_raw) != REPLAY_FILE_ROOT:
        raise ValueError("native replay result file drifted")
    replay = json.loads(replay_raw)
    if replay.get("self_root") != REPLAY_SELF_ROOT:
        raise ValueError("native replay self root drifted")
    profiles = {profile["id"]: profile for profile in replay.get("profiles", [])}

    checked_cases = []
    for problem, case in CASES.items():
        if statements.get(problem) != case["statement"]:
            raise ValueError(f"retained Erdős {problem} statement bytes changed")
        challenge_raw = (astra / case["challenge"]).read_bytes()
        if root(challenge_raw) != case["challenge_root"]:
            raise ValueError(f"Astra Erdős {problem} challenge drifted")
        challenge_text = challenge_raw.decode()
        require_fragments(challenge_text, case["lean_fragments"], f"Astra Erdős {problem}")

        report_raw = (frontier / case["report"]).read_bytes()
        if root(report_raw) != case["report_root"]:
            raise ValueError(f"Erdős {problem} fidelity report drifted")
        report = json.loads(report_raw)
        if report.get("conclusion") != case["conclusion"]:
            raise ValueError(f"Erdős {problem} report conclusion drifted")
        assessments = {
            field: value.get("assessment")
            for field, value in report.get("matrix", {}).items()
        }
        if assessments != case["assessments"]:
            raise ValueError(f"Erdős {problem} fidelity matrix drifted")
        if problem == 146 and report.get("discrepancies") != []:
            raise ValueError("Erdős 146 acquired an unregistered discrepancy")
        if problem == 180:
            discrepancies = report.get("discrepancies", [])
            if [entry.get("id") for entry in discrepancies] != [
                "cyclic_family_hypothesis_absent_from_retained_statement"
            ]:
                raise ValueError("Erdős 180 material discrepancy drifted")
            if report.get("next_obligation", {}).get("kind") != "source-correction-review":
                raise ValueError("Erdős 180 lost its source-correction obligation")

        profile = profiles.get(case["profile_id"])
        if profile is None:
            raise ValueError(f"native replay lost profile {case['profile_id']}")
        expected_profile = {
            "profile_sha256": case["profile_root"],
            "challenge_sha256": case["challenge_root"].removeprefix("sha256:"),
            "solution_sha256": SOLUTION_ROOT.removeprefix("sha256:"),
            "theorem_names": case["theorems"],
            "comparator": "pass",
            "nanoda_kernel": "accept",
            "lean_kernel": "accept",
            "statement_fidelity": "matrix pending",
        }
        actual_profile = {field: profile.get(field) for field in expected_profile}
        if actual_profile != expected_profile:
            raise ValueError(f"native replay profile {case['profile_id']} drifted")
        checked_cases.append(
            {
                "problem": problem,
                "report_root": case["report_root"],
                "conclusion": case["conclusion"],
                "source_status": "open_unformalized_as_of_2025-08-31",
                "mechanical_source_check": "pass",
                "native_replay": "comparator_nanoda_lean_pass",
            }
        )

    return {
        "schema": "erdos-frontier.astra-146-180-fidelity-check.v1",
        "ok": True,
        "authority": "non_authoritative",
        "claim_credit": False,
        "checked_cases": checked_cases,
        "conclusions": {
            "erdos_146": "mechanically_consistent_faithful_matrix",
            "erdos_180": "mechanically_consistent_qualified_mismatch",
        },
        "next_obligation": {
            "erdos_146": "No protocol action exists without a source-owning Target; retain at the source-local evidence ceiling.",
            "erdos_180": "Prepare a chronology-preserving source-correction packet; any correction and Standing transition require separate human authority.",
        },
        "shared_dependencies": [
            "Same human operator and machine as the producer reports and native replay.",
            "Same retained statements, OpenAI manuscript and source release, Lean kernel, Mathlib, and replay evidence.",
            "This checker validates exact sources and consequence coverage; it does not independently re-prove the mathematics.",
        ],
        "accepted_state_change": "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier", required=True, type=pathlib.Path)
    parser.add_argument("--ten-proofs", required=True, type=pathlib.Path)
    parser.add_argument("--erdosproblems", required=True, type=pathlib.Path)
    parser.add_argument("--vela", required=True, type=pathlib.Path)
    parser.add_argument("--paper", required=True, type=pathlib.Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        result = {
            "schema": "erdos-frontier.astra-146-180-fidelity-check.v1",
            "ok": False,
            "error": str(error),
            "accepted_state_change": "none",
        }
    print(json.dumps(result, sort_keys=True) if args.json else result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
