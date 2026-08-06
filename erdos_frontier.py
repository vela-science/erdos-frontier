#!/usr/bin/env python3
"""Reconcile retained Erdős source evidence into one in-memory audit payload.

The canonical scientific and authority state lives in the compact Vela epoch.
This module only joins external source indexes for focused audits and refreshes
their exact content hashes in ``sources.lock.json``; it does not publish a
parallel site, graph, or status snapshot.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import datetime as _datetime
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

import yaml


UA = {"User-Agent": "erdos-frontier"}
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

CONJ_URL = "https://google-deepmind.github.io/formal-conjectures/data/conjectures.json"
ERDOS_URL = "https://raw.githubusercontent.com/teorth/erdosproblems/main/data/problems.yaml"
PLBY_URL = "https://raw.githubusercontent.com/plby/lean-proofs/main/data/sources.yaml"
JAYY_URL = "https://raw.githubusercontent.com/Jayyhk/erdos-lean/main/data/problems.yaml"
VLP_URL = "https://raw.githubusercontent.com/williamjblair/lean-proofs/main/proofs.yaml"
# Historical statement-fidelity attestations retained as source evidence. The
# current accepted Claims and Decisions live in Vela records; this frozen input
# remains useful only for source-audit classification.
FIDELITY_CACHE = "sources/fidelity_cache.json"
FC_REPO = "google-deepmind/formal-conjectures"
EPC = "https://www.erdosproblems.com"

FIDELITY_VERDICTS = {"faithful", "variant", "unfaithful"}

SOURCE_ORDER = ("plby", "jayyhk", "vlp")
SRC_TAG = {"plby": "ᵖ", "jayyhk": "ʲ", "vlp": "ʷ"}
SOURCE_LABEL = {
    "plby": "plby/lean-proofs",
    "jayyhk": "Jayyhk/erdos-lean",
    "vlp": "williamjblair/lean-proofs",
}

BUCKET_ORDER = [
    "statement",
    "link",
    "needs-statement-update",
    "needs-human-match-check",
    "mismatch",
    "hypothesis-conditional",
    "docstring",
    "partial",
    "blocked-claim",
    "in-pr",
    "wont-fix",
    "defer",
    "done",
    "no-proof",
]

OVERRIDE_BUCKETS = {
    "blocked-claim",
    "wont-fix",
    "mismatch",
    "hypothesis-conditional",
    "needs-human-match-check",
    "needs-statement-update",
    "defer",
}

RECOMMENDED_ACTION = {
    "statement": "Write the FC statement and link the matching hosted proof.",
    "link": "Check theorem match, then add the formal_proof link.",
    "needs-statement-update": "Review and update the FC statement before adding any link.",
    "needs-human-match-check": "Read the hosted theorem and boxed problem before deciding whether to link.",
    "mismatch": "Skip until a hosted proof matches the boxed FC statement.",
    "hypothesis-conditional": "Do not add a formal_proof link; document or wait for an unconditional theorem.",
    "docstring": "Add only a docstring note if useful; do not add formal_proof.",
    "partial": "Only link a correctly stated variant after a per-problem review.",
    "blocked-claim": "Skip because a human claim exists outside an open PR.",
    "in-pr": "Skip because an open PR already touches this problem.",
    "wont-fix": "Skip.",
    "defer": "Skip this batch.",
    "done": "No action.",
    "no-proof": "No action until a hosted proof appears.",
}


@dataclass(frozen=True)
class Claim:
    number: int
    title: str
    url: str
    head_ref: str


def fetch(url: str, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


def load_yaml_url(url: str):
    return yaml.safe_load(fetch(url))


def load_json_url(url: str):
    return json.loads(fetch(url))


def proof_url(source: str, problem: int, entry: dict | None = None) -> str:
    if source == "plby":
        return f"https://github.com/plby/lean-proofs/blob/main/src/v4.29.1/ErdosProblems/Erdos{problem}.lean"
    if source == "jayyhk":
        return f"https://github.com/Jayyhk/erdos-lean/blob/main/problems/{problem}/Erdos{problem}.lean"
    if source == "vlp":
        file = (entry or {}).get("file") or f"ErdosProblems/Erdos{problem}.lean"
        return f"https://github.com/williamjblair/lean-proofs/blob/main/{file}"
    raise ValueError(f"unknown proof source: {source}")


def add_proof(
    proofs: dict[int, dict],
    problem: int,
    *,
    complete: bool,
    conditional: bool,
    partial: bool,
    source: str,
    url: str,
    state: str | None = None,
) -> None:
    rec = proofs.setdefault(
        problem,
        {"complete": False, "conditional": False, "partial": False, "sources": {}},
    )
    rec["complete"] |= complete
    rec["conditional"] |= conditional
    rec["partial"] |= partial
    rec["sources"][source] = {
        "complete": complete,
        "conditional": conditional,
        "partial": partial,
        "url": url,
        "state": state,
    }


def build_proofs(
    plby_items: list[dict] | None,
    jayyhk_items: list[dict] | None,
    vlp_doc: dict | None,
) -> dict[int, dict]:
    proofs: dict[int, dict] = {}
    for entry in plby_items or []:
        match = re.search(r"Erdos(\d+)", entry.get("key", ""))
        if not match:
            continue
        problem = int(match.group(1))
        conditional = "conditional" in entry
        partial = "partial" in entry
        add_proof(
            proofs,
            problem,
            complete=not (conditional or partial),
            conditional=conditional,
            partial=partial,
            source="plby",
            url=proof_url("plby", problem, entry),
            state="partial" if partial else "conditional" if conditional else "complete",
        )

    for entry in jayyhk_items or []:
        try:
            problem = int(entry["number"])
        except (KeyError, TypeError, ValueError):
            continue
        state = (entry.get("proof") or {}).get("state")
        add_proof(
            proofs,
            problem,
            complete=state == "complete",
            conditional=state in ("axiomatic", "trust_extended"),
            partial=False,
            source="jayyhk",
            url=proof_url("jayyhk", problem, entry),
            state=state,
        )

    for entry in (vlp_doc or {}).get("proofs", []):
        try:
            problem = int(entry["problem"])
        except (KeyError, TypeError, ValueError):
            continue
        clean = bool(entry.get("axioms_clean"))
        add_proof(
            proofs,
            problem,
            complete=clean,
            conditional=not clean,
            partial=False,
            source="vlp",
            url=proof_url("vlp", problem, entry),
            state="axioms_clean" if clean else "not_clean",
        )
    return proofs


LEAN_AUDIT_DIR = Path(__file__).resolve().parent / "lean"
_VERDICT_RANK = {"unconditional": 2, "conditional": 1, "incomplete": 0}


def _audit_tag(path: Path) -> str:
    """audit_feed_<tag>.json -> <tag>; the legacy audit_feed.json -> plby."""
    stem = path.stem
    return stem[len("audit_feed_"):] if stem.startswith("audit_feed_") else "plby"


def load_machine_audit(audit_dir: Path = LEAN_AUDIT_DIR) -> dict[int, dict]:
    """Merge every ``audit_feed*.json`` (one per proof repo) keyed by problem.

    Each repo's harness writes ``audit_feed_<tag>.json`` — the deterministic result
    of loading its hosted proofs and reading their axioms + theorem-parameter
    hypotheses, not a flag the author declared. A problem can be proven in more than
    one repo; we keep the STRONGEST verdict (unconditional > conditional > incomplete)
    so an unconditional proof in any audited repo settles it, and record which feed
    it came from. Empty if no audit has been generated.
    """
    merged: dict[int, dict] = {}
    for path in sorted(Path(audit_dir).glob("audit_feed*.json")):
        tag = _audit_tag(path)
        try:
            rows = json.load(open(path))
        except (OSError, ValueError):
            continue
        for raw in rows:
            if "problem" not in raw:
                continue
            problem = int(raw["problem"])
            rec = {**raw, "source": tag}
            cur = merged.get(problem)
            if cur is None or (_VERDICT_RANK.get(rec.get("machine_verdict"), -1)
                               > _VERDICT_RANK.get(cur.get("machine_verdict"), -1)):
                merged[problem] = rec
    return merged


def apply_machine_audit(proofs: dict[int, dict], audit: dict[int, dict]) -> None:
    """Fold the machine verdict over the producer-declared flags, in place.

    The machine ran the proof, so its verdict is authoritative for any problem it
    audited. A non-empty ``named_assumptions`` (a problem-defined Prop assumed as a
    hypothesis — e.g. ``DukeTheoremStatement``) is the ``#print axioms``-invisible
    conditionality the raw ``conditional``/``partial`` flags systematically miss.
    """
    for problem, feed in audit.items():
        rec = proofs.get(problem)
        if rec is None:
            continue
        verdict = feed.get("machine_verdict")
        rec["machine_verdict"] = verdict
        rec["machine_source"] = feed.get("source")
        rec["machine_named_assumptions"] = feed.get("named_assumptions") or []
        rec["machine_non_kernel_axioms"] = feed.get("non_kernel_axioms") or []
        if verdict == "conditional":
            rec["conditional"] = True
            rec["complete"] = False
        elif verdict == "unconditional":
            rec["conditional"] = False
            rec["complete"] = not rec.get("partial")


WIKI_REGISTRY_PATH = Path(__file__).resolve().parent / "sources/wiki/registry.json"
WIKI_SOURCE = ("https://github.com/teorth/erdosproblems/wiki/"
               "AI-contributions-to-Erd%C5%91s-problems")

_COLOR_RANK = {"green": 3, "yellow": 2, "white": 1, "red": 0}


def _wiki_is_full(entry: dict) -> bool:
    """A green entry asserting the boxed problem itself is resolved (or beaten)."""
    outcome = entry.get("outcome") or {}
    label = (outcome.get("label") or "").lower()
    return outcome.get("color") == "green" and (
        "full solution" in label or "stronger" in label or "solved" in label
    )


def _wiki_summary(entries: list[dict]) -> dict:
    """Collapse a problem's wiki entries into one per-problem claim view."""
    ai = sorted({s for e in entries for s in e.get("ai_systems", [])})
    humans = sorted({h for e in entries for h in e.get("humans", [])})
    best = max(
        (e for e in entries if (e.get("outcome") or {}).get("color") != "red"),
        key=lambda e: _COLOR_RANK.get((e.get("outcome") or {}).get("color"), 0),
        default=None,
    )
    best_outcome = (best or {}).get("outcome") or {}
    return {
        "ai_systems": ai,
        "humans": humans,
        "claimed_color": best_outcome.get("color"),
        "outcome_label": best_outcome.get("label"),
        "claims_full_solution": any(_wiki_is_full(e) for e in entries),
        "claims_lean": any((e.get("outcome") or {}).get("lean") for e in entries),
        "has_incorrect": any(
            (e.get("outcome") or {}).get("color") == "red" for e in entries),
        "entries": entries,
    }


def load_wiki_registry(path: Path = WIKI_REGISTRY_PATH) -> dict[int, dict]:
    """Per-problem view of the frozen teorth AI-contributions wiki (2026-06-30).

    The wiki is the registry this audit is a superset of: it carries the claim
    (which AI, which humans, what outcome colour) but never the conditionality of
    the underlying proof — the column this audit adds. Re-derived offline from the
    committed ``sources/wiki/`` markdown by ``sources/wiki/snapshot.py``; this reads
    only the resulting ``sources/wiki/registry.json``. Empty if the snapshot is absent.
    """
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[int, dict] = {}
    for key, entries in (doc.get("problems") or {}).items():
        try:
            problem = int(key)
        except (TypeError, ValueError):
            continue
        out[problem] = _wiki_summary(entries)
    return out


CANDIDATE_CLAIMS_PATH = Path(__file__).resolve().parent / "sources/gpt_erdos/registry.json"
CANDIDATE_SOURCE = "https://github.com/neelsomani/gpt-erdos"

def load_candidate_claims(path: Path = CANDIDATE_CLAIMS_PATH) -> dict[int, dict]:
    """Independent human classification of GPT-5.2-Pro candidate solutions
    (neelsomani/gpt-erdos), keyed by problem.

    A CLAIMS source for cross-reference, not a proof corpus: it reviews informal GPT
    output, while this audit reads hosted Lean proofs. Where the two overlap they
    often differ (different artifacts), which is the point of carrying it. Empty if
    the snapshot is absent.
    """
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[int, dict] = {}
    for key, rec in (doc.get("problems") or {}).items():
        try:
            problem = int(key)
        except (TypeError, ValueError):
            continue
        out[problem] = {"category": rec.get("category"),
                        "category_label": rec.get("category_label"),
                        "source": "gpt-erdos"}
    return out


def fc_theorem_url(theorem: str | None) -> str | None:
    """The Formal Conjectures per-theorem page for a declaration name.

    The site keys its theorem view on the exact ``theorem`` field from
    ``conjectures.json`` (e.g. ``Erdos258.erdos_258``), so pass that value
    verbatim rather than reconstructing a name.
    """
    if not theorem:
        return None
    return ("https://google-deepmind.github.io/formal-conjectures/theorem/?name="
            + urllib.parse.quote(theorem))


def build_fc(conjectures: dict) -> dict[int, dict]:
    entries = []
    for value in conjectures.values():
        entries.extend(value if isinstance(value, list) else [value])
    fc: dict[int, dict] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = entry.get("githubPath") or ""
        match = re.search(r"ErdosProblems/(\d+)\.lean", path)
        if not match:
            continue
        problem = int(match.group(1))
        rec = fc.setdefault(problem, {
            "has_file": True, "linked": False, "path": path,
            "formal_proof_link": None, "theorem": None, "has_proof": False,
        })
        rec["has_file"] = True
        rec["path"] = rec.get("path") or path
        theorem = entry.get("theorem")
        base = f"Erdos{problem}.erdos_{problem}"
        # Pick the FC theorem the row should link to: the one that carries the
        # formal proof wins, else the base `erdos_<n>` statement, else the first
        # seen. `.variants.*` are secondary framings of the same problem.
        if entry.get("hasFormalProof"):
            rec["has_proof"] = True
            if entry.get("formalProofLink"):
                rec["linked"] = True
                rec["formal_proof_link"] = entry.get("formalProofLink")
            rec["theorem"] = theorem or rec["theorem"]
        elif rec["theorem"] is None or theorem == base:
            if not rec.get("has_proof"):
                rec["theorem"] = theorem or rec["theorem"]
    for rec in fc.values():
        rec["fc_url"] = fc_theorem_url(rec.get("theorem"))
    return fc


def _attestation_problem(attestation: dict) -> int | None:
    """Derive the Erdős problem number from an attestation.

    Prefer the trailing integer of ``informal_ref`` (e.g. ``erdosproblems.com/214``);
    fall back to a trailing integer in ``target`` (e.g. ``vf_erdos_214``).
    """
    for field in ("informal_ref", "target"):
        text = attestation.get(field) or ""
        match = re.search(r"(\d+)\s*$", str(text))
        if match:
            return int(match.group(1))
    return None


def parse_fidelity(doc: dict | None, *, source: str) -> dict[int, dict]:
    """Project a ``statement_attestations[]`` document onto problem number.

    Returns ``{problem: {verdict, reviewer, formal_ref, formal_statement_hash,
    note, signed, stale, source}}``. ``signed`` is True for real attestations;
    ``source`` records hub-vs-cache provenance. ``stale`` is left ``None`` here
    and resolved per-row once an FC theorem hash is available.
    """
    out: dict[int, dict] = {}
    for attestation in (doc or {}).get("statement_attestations", []) or []:
        if not isinstance(attestation, dict):
            continue
        verdict = attestation.get("verdict")
        if verdict not in FIDELITY_VERDICTS:
            continue
        problem = _attestation_problem(attestation)
        if problem is None:
            continue
        out[problem] = {
            "verdict": verdict,
            "reviewer": attestation.get("attested_by"),
            "formal_ref": attestation.get("formal_ref"),
            "formal_statement_hash": attestation.get("formal_statement_hash"),
            "note": attestation.get("note"),
            "signed": True,
            "stale": None,
            "source": source,
        }
    return out


def load_fidelity(url_or_path: str | Path = FIDELITY_CACHE) -> dict[int, dict]:
    """Load retained statement-fidelity source evidence keyed by problem."""
    target = str(url_or_path)
    if re.match(r"^https?://", target):
        try:
            return parse_fidelity(load_json_url(target), source="hub")
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
            import sys
            sys.stderr.write(f"WARNING: fidelity source unreachable ({exc})\n")
            return {}
    cache_path = Path(target)
    if cache_path.exists():
        try:
            return parse_fidelity(json.loads(cache_path.read_text()), source="cache")
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def claims_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}


def fetch_claims() -> tuple[dict[int, list[Claim]], bool]:
    claims_by_problem: dict[int, list[Claim]] = {}
    headers = claims_headers()
    try:
        page = 1
        prs = []
        while True:
            batch = json.loads(
                fetch(f"https://api.github.com/repos/{FC_REPO}/pulls?state=open&per_page=100&page={page}", headers)
            )
            prs.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        for pr in prs:
            files = json.loads(fetch(pr["url"] + "/files?per_page=100", headers))
            claim = Claim(
                number=int(pr["number"]),
                title=pr.get("title") or "",
                url=pr.get("html_url") or "",
                head_ref=(pr.get("head") or {}).get("ref") or "",
            )
            for file in files:
                match = re.search(r"ErdosProblems/(\d+)\.lean", file.get("filename", ""))
                if match:
                    claims_by_problem.setdefault(int(match.group(1)), []).append(claim)
        return claims_by_problem, True
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError, json.JSONDecodeError):
        return {}, False


def fetch_wontfix() -> set[int]:
    problems: set[int] = set()
    headers = claims_headers()
    try:
        page = 1
        while True:
            url = (
                f"https://api.github.com/repos/{FC_REPO}/issues?state=all&labels="
                + urllib.parse.quote("won't fix")
                + f"&per_page=100&page={page}"
            )
            batch = json.loads(fetch(url, headers))
            if not batch:
                break
            for issue in batch:
                if issue.get("pull_request"):
                    continue
                match = re.search(r"Problem (\d+)", issue.get("title", ""))
                if match:
                    problems.add(int(match.group(1)))
            if len(batch) < 100:
                break
            page += 1
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        pass
    return problems


def load_overrides(path: str | Path = "overrides.yaml") -> dict[int, dict]:
    override_path = Path(path)
    if not override_path.exists():
        return {}
    raw = yaml.safe_load(override_path.read_text()) or {}
    overrides: dict[int, dict] = {}
    for key, value in raw.items():
        try:
            problem = int(key)
        except (TypeError, ValueError):
            continue
        if not isinstance(value, dict):
            continue
        bucket = value.get("bucket")
        if bucket and bucket not in OVERRIDE_BUCKETS:
            raise ValueError(f"unknown override bucket for {problem}: {bucket}")
        overrides[problem] = value
    return overrides


# High-profile, widely-cited AI-solved proofs (DeepMind AlphaProof's set + the
# Aristotle/GPT trio). A mechanical conditional/incomplete flag on one of these is
# either a real and important catch or a false positive that would be costly to
# publish wrong — so it is HELD for a human to confirm before it reaches the public
# feed, rather than auto-published. Verified-clear problems live in staging_cleared.yaml.
CELEBRATED_PROBLEMS = frozenset({12, 26, 125, 138, 152, 741, 846, 397, 728, 729})


def load_staging_cleared(path: str | Path = "staging_cleared.yaml") -> set[int]:
    """Problem numbers whose celebrated-proof flag a human has hand-verified, so it
    may publish. Empty (every celebrated flag held) if the file is absent."""
    p = Path(path)
    if not p.exists():
        return set()
    raw = yaml.safe_load(p.read_text()) or {}
    return {int(x) for x in (raw.get("cleared") or [])}


def apply_staging_gate(rows: list[dict], cleared: set[int]) -> list[int]:
    """Hold any conditional/incomplete flag on a celebrated proof until cleared.

    Sets ``held_for_review`` on every row and suppresses ``discrepancy`` for a held
    one, so a false positive on a Tao-accepted proof never auto-publishes. Returns
    the sorted list of held problem numbers.
    """
    held: list[int] = []
    for row in rows:
        verdict = (row.get("machine") or {}).get("verdict")
        gated = (row["problem"] in CELEBRATED_PROBLEMS
                 and verdict in ("conditional", "incomplete")
                 and row["problem"] not in cleared)
        row["held_for_review"] = gated
        if gated:
            row["discrepancy"] = False
            held.append(row["problem"])
    return sorted(held)


def source_names(proof: dict | None) -> list[str]:
    if not proof:
        return []
    sources = proof.get("sources", {})
    return [source for source in SOURCE_ORDER if source in sources]


def source_tags(proof: dict | None) -> str:
    return "".join(SRC_TAG[source] for source in source_names(proof))


def verdict_bucket(fidelity: dict | None, fc: dict) -> str | None:
    """Map a signed statement-fidelity verdict to a bucket, or None.

    Priority sits below ``fc.linked`` and above ``in-pr``/override/computed:
    a signed verdict is direct human review of the statement match, so it
    supersedes a machine-inferred bucket and a matching ``overrides.yaml`` row.
    """
    if not fidelity or not fidelity.get("signed"):
        return None
    verdict = fidelity.get("verdict")
    note = (fidelity.get("note") or "").lower()
    if verdict == "unfaithful":
        return "mismatch"
    if verdict == "variant":
        if "variant" in note or "weaker" in note:
            return "partial"
        return "hypothesis-conditional"
    if verdict == "faithful":
        # The statement matches; the only remaining work is wiring the link.
        return "link" if fc.get("has_file") else "statement"
    return None


def classify(
    problem: int,
    fc: dict,
    proof: dict | None,
    claims: list[Claim],
    override: dict | None,
    fidelity: dict | None = None,
) -> str:
    if fc.get("linked"):
        return "done"
    verdict = verdict_bucket(fidelity, fc)
    if verdict:
        return verdict
    if override and override.get("bucket") in OVERRIDE_BUCKETS:
        return override["bucket"]
    if claims:
        return "in-pr"
    if not proof:
        return "no-proof"
    if proof.get("complete"):
        return "link" if fc.get("has_file") else "statement"
    if proof.get("machine_named_assumptions"):
        # the machine found a problem-defined named Prop assumed as a hypothesis —
        # kernel-clean but conditional, exactly what #print axioms cannot see.
        return "hypothesis-conditional"
    if proof.get("conditional"):
        return "docstring"
    if proof.get("partial"):
        return "partial"
    return "needs-human-match-check"


def fidelity_field(fidelity: dict | None, fc_data: dict) -> dict | None:
    """Project the per-row ``fidelity`` view, computing staleness if possible."""
    if not fidelity:
        return None
    stale = fidelity.get("stale")
    expected = fidelity.get("formal_statement_hash")
    # TODO: derive the current FC theorem hash to confirm staleness. The FC
    # conjectures feed does not expose a per-theorem statement hash cheaply, so
    # leave stale=None rather than guessing whether the statement drifted.
    if expected is not None:
        stale = None
    return {
        "verdict": fidelity.get("verdict"),
        "reviewer": fidelity.get("reviewer"),
        "signed": fidelity.get("signed"),
        "note": fidelity.get("note"),
        "formal_ref": fidelity.get("formal_ref"),
        "source": fidelity.get("source"),
        "stale": stale,
    }


def wiki_field(wiki: dict | None) -> dict | None:
    """Project the per-row wiki claim view (everything but the raw entry list)."""
    if not wiki:
        return None
    return {key: wiki[key] for key in (
        "ai_systems", "humans", "claimed_color", "outcome_label",
        "claims_full_solution", "claims_lean", "has_incorrect")}


def row_for_problem(
    problem: int,
    erdos_record: dict,
    fc_record: dict | None,
    proof: dict | None,
    claims: list[Claim],
    override: dict | None,
    fidelity: dict | None = None,
    wiki: dict | None = None,
    candidate: dict | None = None,
) -> dict:
    fc_data = fc_record or {"has_file": False, "linked": False, "path": None, "formal_proof_link": None}
    bucket = classify(problem, fc_data, proof, claims, override, fidelity)
    machine_verdict = proof.get("machine_verdict") if proof else None
    # The wedge made visible: the wiki records the boxed problem as fully solved,
    # yet the formal proof we can actually load is conditional or incomplete. A
    # machine fact about the available proof, not a verdict on the wiki's claim.
    discrepancy = bool(
        wiki and wiki.get("claims_full_solution")
        and machine_verdict in ("conditional", "incomplete"))
    sources = source_names(proof)
    proof_links = []
    if proof:
        for source in sources:
            data = proof["sources"][source]
            proof_links.append(
                {
                    "source": source,
                    "label": SOURCE_LABEL[source],
                    "url": data["url"],
                    "state": data.get("state"),
                    "complete": data["complete"],
                    "conditional": data["conditional"],
                    "partial": data["partial"],
                }
            )
    return {
        "problem": problem,
        "bucket": bucket,
        "erdos_url": f"{EPC}/{problem}",
        "latex_url": f"{EPC}/latex/{problem}",
        "erdos_state": ((erdos_record.get("status") or {}).get("state") or "?"),
        "proof_sources": sources,
        "proof_links": proof_links,
        "source_tags": source_tags(proof),
        "fc": {
            "has_file": bool(fc_data.get("has_file")),
            "linked": bool(fc_data.get("linked")),
            "path": fc_data.get("path"),
            "formal_proof_link": fc_data.get("formal_proof_link"),
            "theorem": fc_data.get("theorem"),
            "has_proof": bool(fc_data.get("has_proof")),
            "fc_url": fc_data.get("fc_url"),
        },
        "claims": [asdict(claim) for claim in claims],
        "override": override or None,
        "wiki": wiki_field(wiki),
        "discrepancy": discrepancy,
        "candidate_claims": candidate,
        "fidelity": fidelity_field(fidelity, fc_data),
        "machine": (
            {
                "verdict": proof.get("machine_verdict"),
                "source": proof.get("machine_source"),
                "named_assumptions": proof.get("machine_named_assumptions") or [],
                "non_kernel_axioms": proof.get("machine_non_kernel_axioms") or [],
            }
            if proof and proof.get("machine_verdict")
            else None
        ),
        "recommended_action": (override or {}).get("recommended_action") or RECOMMENDED_ACTION[bucket],
    }


def build_status(
    *,
    erdos: dict[int, dict],
    fc: dict[int, dict],
    proofs: dict[int, dict],
    claims_by_problem: dict[int, list[Claim]],
    claims_available: bool,
    overrides: dict[int, dict],
    fidelity: dict[int, dict] | None = None,
    wiki: dict[int, dict] | None = None,
    candidate_claims: dict[int, dict] | None = None,
    cleared: set[int] | None = None,
    generated_at: str | None = None,
) -> dict:
    generated_at = generated_at or _datetime.date.today().isoformat()
    fidelity = fidelity or {}
    wiki = wiki or {}
    candidate_claims = candidate_claims or {}
    rows = [
        row_for_problem(
            problem,
            erdos[problem],
            fc.get(problem),
            proofs.get(problem),
            claims_by_problem.get(problem, []),
            overrides.get(problem),
            fidelity.get(problem),
            wiki.get(problem),
            candidate_claims.get(problem),
        )
        for problem in sorted(erdos)
    ]
    held_for_review = apply_staging_gate(rows, cleared or set())
    # Row hygiene for the override side-channel: a signed verdict
    # structurally supersedes any overrides.yaml row (see classify), so a
    # shadowed row is dead weight that misleads the next editor. Surface
    # them; the fix is deleting the row, never touching the verdict.
    shadowed = sorted(
        row["problem"]
        for row in rows
        if row.get("override") and verdict_bucket(fidelity.get(row["problem"]), row["fc"])
    )
    if shadowed:
        import sys as _sys

        print(
            f"overrides.yaml: {len(shadowed)} row(s) shadowed by a signed verdict "
            f"(delete them): {shadowed}",
            file=_sys.stderr,
        )
    counts = Counter(row["bucket"] for row in rows)
    bloom_formalized = {
        problem
        for problem, data in erdos.items()
        if ((data.get("formalized") or {}).get("state") == "yes")
    }
    coverage_gap = sorted(bloom_formalized - (set(proofs) | set(fc)))
    return {
        "generated_at": generated_at,
        "shadowed_overrides": shadowed,
        "claims_available": claims_available,
        "sources": {
            "formal_conjectures": CONJ_URL,
            "erdosproblems": ERDOS_URL,
            "plby": PLBY_URL,
            "jayyhk": JAYY_URL,
            "vlp": VLP_URL,
            "fidelity": FIDELITY_CACHE,
            "wiki": WIKI_SOURCE,
            "gpt_erdos": CANDIDATE_SOURCE,
            "fc_repo": FC_REPO,
        },
        "counts": {bucket: counts.get(bucket, 0) for bucket in BUCKET_ORDER},
        "total_problems": len(rows),
        "hosted_proofs_tracked": len(proofs),
        "wiki_problems_tracked": len(wiki),
        "discrepancies": sorted(r["problem"] for r in rows if r.get("discrepancy")),
        "held_for_review": held_for_review,
        "bloom_formalized_count": len(bloom_formalized),
        "coverage_gap": coverage_gap,
        "rows": rows,
    }


def load_live_status(overrides_path: str | Path = "overrides.yaml") -> dict:
    erdos = {int(problem["number"]): problem for problem in load_yaml_url(ERDOS_URL)}
    plby_items = load_yaml_url(PLBY_URL)
    jayyhk_items = load_yaml_url(JAYY_URL)
    try:
        vlp_doc = load_yaml_url(VLP_URL) or {}
    except (urllib.error.HTTPError, urllib.error.URLError):
        vlp_doc = {}
    proofs = build_proofs(plby_items, jayyhk_items, vlp_doc)
    apply_machine_audit(proofs, load_machine_audit())
    fc = build_fc(load_json_url(CONJ_URL))
    claims_by_problem, claims_available = fetch_claims()
    overrides = load_overrides(overrides_path)
    fidelity = load_fidelity()
    wiki = load_wiki_registry()
    candidate_claims = load_candidate_claims()
    cleared = load_staging_cleared()
    for problem in fetch_wontfix():
        overrides.setdefault(
            problem,
            {
                "bucket": "wont-fix",
                "reason": "Formal Conjectures issue is labelled won't fix.",
                "source": f"https://github.com/{FC_REPO}/issues?q={problem}+label%3A%22won%27t+fix%22",
            },
        )
    return build_status(
        erdos=erdos,
        fc=fc,
        proofs=proofs,
        claims_by_problem=claims_by_problem,
        claims_available=claims_available,
        overrides=overrides,
        fidelity=fidelity,
        wiki=wiki,
        candidate_claims=candidate_claims,
        cleared=cleared,
    )


def write_sources_lock(root: str | Path = ".") -> dict:
    """Record the exact content hash (+ GitHub commit, where resolvable) of every
    live source into ``sources.lock.json``, so the materialized state is traceable
    to fixed snapshots rather than a floating ``main``. Network failures degrade to
    a recorded error rather than aborting the run.
    """
    import hashlib
    root = Path(root)
    lock_path = root / "sources.lock.json"
    registry = (yaml.safe_load((root / "sources.yaml").read_text()) or {}).get("sources", {})
    headers = claims_headers()
    locked: dict[str, dict] = {}
    for name, spec in registry.items():
        entry: dict = {"kind": spec.get("kind")}
        # Repository identity and selected paths are part of the lock even for
        # URL-backed inputs. Keeping them outside the fetch branches prevents a
        # routine status refresh from erasing the exact inventory provenance.
        for field in ("repo", "ref", "path", "paths", "commit", "tree", "home"):
            if spec.get(field) is not None:
                entry[field] = spec[field]
        if spec.get("acquired_by"):
            # A cited entry names a corpus another Frontier acquires, and its url
            # is the repository landing page rather than a content locator.
            # Fetching it would hash rendered HTML and record that as the content
            # root, so the declared commit and tree are the whole of this entry.
            entry["acquired_by"] = spec["acquired_by"]
            if spec.get("url") is not None:
                entry["url"] = spec["url"]
            locked[name] = entry
            continue
        try:
            if spec.get("url"):
                data = fetch(spec["url"])
                entry["url"] = spec["url"]
                entry["sha256"] = "sha256:" + hashlib.sha256(data).hexdigest()
                if spec.get("repo") and spec.get("ref"):
                    try:
                        commit = json.loads(fetch(
                            f"https://api.github.com/repos/{spec['repo']}/commits/{spec['ref']}",
                            headers))
                        entry["ref"] = spec["ref"]
                        entry["commit"] = commit.get("sha")
                    except (urllib.error.URLError, json.JSONDecodeError):
                        pass
            elif spec.get("path") and (root / spec["path"]).exists():
                entry["sha256"] = "sha256:" + hashlib.sha256(
                    (root / spec["path"]).read_bytes()).hexdigest()
        except (urllib.error.URLError, OSError) as exc:
            entry["error"] = str(exc)
        locked[name] = entry
    stamp = _datetime.datetime.now(_datetime.timezone.utc).replace(microsecond=0).isoformat()
    out = {"generated_at": stamp, "sources": locked}
    lock_path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def main() -> int:
    payload = load_live_status()
    try:
        write_sources_lock(".")
    except OSError as exc:
        import sys
        sys.stderr.write(f"WARNING: could not write sources.lock.json ({exc})\n")
    print(
        f"reconciled {payload['total_problems']} problems; "
        f"claims_available={payload['claims_available']}; "
        f"hosted proofs tracked={payload['hosted_proofs_tracked']}"
    )
    for bucket in BUCKET_ORDER:
        print(f"  {bucket:>24}: {payload['counts'].get(bucket, 0)}")
    print("refreshed sources.lock.json; canonical state remains in Vela records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
