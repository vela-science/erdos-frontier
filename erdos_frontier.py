#!/usr/bin/env python3
"""Build the Erdős frontier audit: join the proof corpora, the machine fidelity
verdicts, the frozen wiki, and the gpt-erdos claims into status.json / verdicts.json
(the public feed) and the human-readable STATUS.md / NEXT_BATCH.md."""

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
# Statement-fidelity verdicts: signed attestations that a hosted/FC theorem
# faithfully states the boxed problem. Primary read is the hub snapshot for the
# erdos-formalization frontier (vfr_0a25edabc16db143); the committed
# fidelity_cache.json is the offline fallback used until that frontier is
# published (the loader 404-falls-back, then auto-switches once it is live).
FIDELITY_URL = "https://hub.constellate.science/entries/vfr_0a25edabc16db143/snapshot"
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

SECTION_ORDER = [
    "statement",
    "link",
    "needs-statement-update",
    "needs-human-match-check",
    "mismatch",
    "hypothesis-conditional",
    "docstring",
    "partial",
    "blocked-claim",
    "wont-fix",
    "defer",
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

BUCKET_DESC = {
    "statement": "**Write the FC statement + link.** A complete hosted proof exists, FC has no file yet.",
    "link": "**Add the `formal_proof` link.** FC already has the statement; the hosted proof just is not linked.",
    "needs-statement-update": "**Not a trivial link.** FC has a file, but the statement or answer needs a human update before linking.",
    "needs-human-match-check": "**Needs match-check.** A hosted proof exists, but the proof/statement relation has not been audited.",
    "mismatch": "**Skip for now.** The hosted proof is complete, but it does not prove the boxed FC statement.",
    "hypothesis-conditional": "**Do not link as complete.** The theorem carries a non-problem hypothesis even if `#print axioms` is clean.",
    "docstring": "**Docstring note, not a `formal_proof` tag.** The hosted proof is conditional, axiomatic, or trust-extended.",
    "partial": "**Partial proof.** Proves a variant, not the full erdosproblems statement.",
    "blocked-claim": "**Claimed outside an open PR.** Skip until the claim is resolved.",
    "in-pr": "**Claimed by an open FC PR.** Skip to avoid collisions.",
    "wont-fix": "**Maintainer marked `won't fix`.** Skip.",
    "defer": "**Deferred.** A human override says to leave this out of the next batch.",
    "done": "Already linked in FC.",
    "no-proof": "No hosted Lean proof to link yet.",
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


LOCAL_FRONTIER = Path(__file__).resolve().parent / "frontier.json"


def load_fidelity(url_or_path: str | Path = FIDELITY_URL) -> dict[int, dict]:
    """Load signed statement-fidelity verdicts keyed by problem number.

    Primary read is the repo's own replayed ``frontier.json`` — the git-native
    source of truth this repo now hosts, the same state ``vela check`` verifies.
    If that is absent (a partial checkout), fall back to the hub snapshot, then to
    the committed ``fidelity_cache.json``. If all are missing, return ``{}`` so the
    column is simply empty and the run still succeeds.
    """
    # Prefer the local replayed frontier only for the default read; an explicit
    # path or URL (offline runs, tests) is honored exactly as given.
    if url_or_path == FIDELITY_URL and LOCAL_FRONTIER.exists():
        try:
            local = parse_fidelity(json.loads(LOCAL_FRONTIER.read_text()), source="local")
            if local:
                return local
        except (OSError, json.JSONDecodeError):
            pass
    target = str(url_or_path)
    if re.match(r"^https?://", target):
        try:
            return parse_fidelity(load_json_url(target), source="hub")
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
            # Fall back to the offline cache, but do not fail silently: the
            # verdicts are still shown, tagged `source: cache`, and the site can
            # say "offline snapshot". Operators see the outage in the CI log.
            import sys
            sys.stderr.write(f"WARNING: fidelity hub unreachable ({exc}); using offline cache\n")
    else:
        # An explicit local path was requested; treat it as last-known-good cache.
        cache_path = Path(target)
        if cache_path.exists():
            try:
                return parse_fidelity(json.loads(cache_path.read_text()), source="cache")
            except (OSError, json.JSONDecodeError):
                return {}
        return {}
    cache_path = Path(FIDELITY_CACHE)
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
    counts = Counter(row["bucket"] for row in rows)
    bloom_formalized = {
        problem
        for problem, data in erdos.items()
        if ((data.get("formalized") or {}).get("state") == "yes")
    }
    coverage_gap = sorted(bloom_formalized - (set(proofs) | set(fc)))
    return {
        "generated_at": generated_at,
        "claims_available": claims_available,
        "sources": {
            "formal_conjectures": CONJ_URL,
            "erdosproblems": ERDOS_URL,
            "plby": PLBY_URL,
            "jayyhk": JAYY_URL,
            "vlp": VLP_URL,
            "fidelity": FIDELITY_URL,
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


def format_problem_inline(row: dict) -> str:
    text = f"[{row['problem']}]({row['erdos_url']}){row['source_tags']}"
    if row["claims"]:
        links = ", ".join(f"[#{claim['number']}]({claim['url']})" for claim in row["claims"])
        text += f" ({links})"
    return text


def format_problem_detail(row: dict) -> str:
    parts = [format_problem_inline(row)]
    override = row.get("override")
    if override and override.get("reason"):
        parts.append(override["reason"])
    elif row["claims"]:
        parts.append("; ".join(f"#{claim['number']} {claim['title']}" for claim in row["claims"]))
    else:
        parts.append(row["recommended_action"])
    return " — ".join(parts)


def fidelity_theorem_link(row: dict) -> str:
    """Link to the FC theorem page; falls back to the erdos URL.

    Uses the exact FC ``theorem`` name captured in ``build_fc`` so the query
    resolves on the site; if no FC file is known, points at the upstream problem
    page so the link is always live.
    """
    return (row.get("fc") or {}).get("fc_url") or row["erdos_url"]


def fidelity_rows(payload: dict) -> list[dict]:
    return [row for row in payload["rows"] if row.get("fidelity")]


def render_fidelity_section(payload: dict) -> list[str]:
    rows = sorted(fidelity_rows(payload), key=lambda row: row["problem"])
    out: list[str] = []
    out.append(f"\n## statement fidelity — {len(rows)} signed verdict(s)\n")
    out.append(
        "Signed statement-fidelity verdicts: a reviewer attests whether the formal "
        "theorem faithfully states the boxed problem. A signed verdict supersedes the "
        "computed bucket and any matching `overrides.yaml` row.\n"
    )
    if not rows:
        out.append("_none_")
        return out
    out.append("| problem | verdict | source | reviewer | theorem |\n|---|---|---|---|---|")
    for row in rows:
        fidelity = row["fidelity"]
        verdict = fidelity.get("verdict") or "?"
        source = fidelity.get("source") or "?"
        reviewer = fidelity.get("reviewer") or "—"
        link = fidelity_theorem_link(row)
        out.append(
            f"| [{row['problem']}]({row['erdos_url']}) | `{verdict}` | {source} "
            f"| {reviewer} | [theorem]({link}) |"
        )
    return out


def render_status_md(payload: dict) -> str:
    out: list[str] = []
    out.append("# Erdős frontier — proof status\n")
    out.append(f"*Regenerated {payload['generated_at']} by [`erdos_frontier.py`](../erdos_frontier.py). Do not edit by hand.*\n")
    out.append(
        "This is a **computed** view, not a hand-kept list. It joins erdosproblems.com, "
        "Formal Conjectures, hosted Lean proof indexes, live open PRs, and explicit human "
        "overrides on the problem number so the status cannot drift silently.\n"
    )
    out.append(
        "Proof-source marks: ᵖ = [`plby/lean-proofs`](https://github.com/plby/lean-proofs), "
        "ʲ = [`Jayyhk/erdos-lean`](https://github.com/Jayyhk/erdos-lean), "
        "ʷ = [`williamjblair/lean-proofs`](https://github.com/williamjblair/lean-proofs).\n"
    )
    if not payload["claims_available"]:
        out.append("> ⚠️ The open-PR claims layer did not run this time, so `in-pr` may be undercounted.\n")
    if payload["coverage_gap"]:
        links = " ".join(f"[{problem}]({EPC}/{problem})" for problem in payload["coverage_gap"])
        out.append(f"> ⚠️ **Coverage gap:** investigate {links}\n")
    else:
        out.append(
            f"**Coverage:** all {payload['bloom_formalized_count']} problems Bloom marks formalized are tracked "
            "by plby ∪ Jayyhk ∪ williamjblair/lean-proofs ∪ FC. No gap.\n"
        )
    out.append(f"Reconciled **{payload['total_problems']}** problems.\n")
    out.append("| status | count | meaning |\n|---|---:|---|")
    for bucket in BUCKET_ORDER:
        out.append(f"| `{bucket}` | {payload['counts'].get(bucket, 0)} | {BUCKET_DESC[bucket]} |")
    out.append(
        "\nHuman override judgments live in [`overrides.yaml`](overrides.yaml). They encode known "
        "claims, theorem mismatches, and conditional-proof traps that are not visible in the upstream "
        "machine-readable sources.\n"
    )

    rows_by_bucket: dict[str, list[dict]] = {bucket: [] for bucket in BUCKET_ORDER}
    for row in payload["rows"]:
        rows_by_bucket.setdefault(row["bucket"], []).append(row)

    for bucket in SECTION_ORDER:
        rows = rows_by_bucket.get(bucket, [])
        out.append(f"\n## `{bucket}` — {len(rows)} problem(s)\n\n{BUCKET_DESC[bucket]}\n")
        if not rows:
            out.append("_none_")
        elif bucket in {"statement", "link", "docstring", "partial"}:
            out.append(" ".join(format_problem_inline(row) for row in rows))
        else:
            out.extend(f"- {format_problem_detail(row)}" for row in rows)
    out.extend(render_fidelity_section(payload))
    out.append("")
    return "\n".join(out)


def batch_rank(row: dict) -> tuple[int, int, int]:
    sources = set(row["proof_sources"])
    both_main_sources = "plby" in sources and "jayyhk" in sources
    return (0 if both_main_sources else 1, -len(sources), row["problem"])


def safe_statement_rows(payload: dict) -> list[dict]:
    rows = [row for row in payload["rows"] if row["bucket"] == "statement"]
    return sorted(rows, key=batch_rank)


def render_next_batch_md(payload: dict, *, top_count: int = 20, batch_size: int = 8) -> str:
    rows = safe_statement_rows(payload)
    top = rows[:top_count]
    batch = top[:batch_size]
    out: list[str] = []
    out.append("# Next Erdős FC Sync Batch\n")
    out.append(f"*Generated {payload['generated_at']} from [`status.json`](status.json).*\n")
    out.append(
        "This file lists safe `statement` candidates only: no open PR claim, no human override, "
        "and at least one complete hosted proof source.\n"
    )
    out.append(f"## Suggested Batch — {len(batch)} problem(s)\n")
    out.append(" ".join(format_problem_inline(row) for row in batch) or "_none_")
    out.append(f"\n## Top {len(top)} Safe Candidates\n")
    for row in top:
        out.append(f"### Problem {row['problem']}{row['source_tags']}\n")
        out.append(f"- Problem: {row['erdos_url']}")
        out.append(f"- LaTeX: {row['latex_url']}")
        for link in row["proof_links"]:
            out.append(f"- {link['label']}: {link['url']}")
        out.append("- Anti-collision:")
        out.append("```bash")
        out.append(
            f'gh pr list -R {FC_REPO} --search "ErdosProblems/{row["problem"]}" --state all'
        )
        out.append(f'gh issue list -R {FC_REPO} --search "{row["problem"]}"')
        out.append("```\n")
    out.append("")
    return "\n".join(out)


# Recognizable named theorems an Erdős proof may assume without proving (as an
# axiom or as a hypothesis parameter). Keyed by the axiom identifier or the
# hypothesis type-head. `family` merges different formulations of the same input
# (e.g. the Maynard–Tao axiom and its Banks–Freiberg–Turnage-Butterbaugh corollary)
# so leverage counts the distinct problems that rest on one mathematical result.
# Descriptions are kept only where confidently known; a blank one shows just the
# name. Anything not listed is treated as a problem-internal hypothesis, not a
# load-bearing external input.
CONDITION_META: dict[str, tuple[str, str | None, str]] = {
    "maynard_tao": ("Maynard–Tao theorem", "maynard-tao",
                    "Consecutive primes in arithmetic progressions (bounded gaps)."),
    "maynardTaoBFT": ("Maynard–Tao theorem", "maynard-tao",
                      "Banks–Freiberg–Turnage-Butterbaugh corollary of Maynard–Tao."),
    "tao_teravainen": ("Tao–Teräväinen theorem", None,
                       "Bound on the number of prime factors of nearby integers."),
    "Finset.add_kneser": ("Kneser's theorem", None,
                          "Lower bound for the size of a sumset."),
    "mertens_product": ("Mertens' product theorem", None, ""),
    "linnik_dvd": ("Linnik's theorem", None, "Least prime in an arithmetic progression."),
    "shiu_consecutive_primes": ("Shiu's theorem", None,
                                "Strings of consecutive primes in a progression."),
    "Pollack17.theorem_1_3": ("Pollack (2017), Theorem 1.3", None, ""),
    "golod_shafarevich_inequality": ("Golod–Shafarevich inequality", "golod-shafarevich",
                                     "Rank-of-relations bound for finitely presented groups/algebras."),
    "shafarevich_relation_rank_bound": ("Golod–Shafarevich inequality", "golod-shafarevich",
                                        "Rank-of-relations bound for finitely presented groups/algebras."),
    "bernays": ("bernays", None, ""),
    "DukeTheoremStatement": ("Duke's theorem", None, ""),
    "PNT_statement": ("Prime Number Theorem", None, ""),
    "GoldstonGrahamPintzYildirimStatement": ("Goldston–Graham–Pintz–Yıldırım", None, ""),
    "EremenkoLempertAtZeroStatement": ("Eremenko–Lempert theorem", None, ""),
}


def _assumption_head(text: str) -> str:
    """'h_duke : Erdos1148.DukeTheoremStatement x' -> 'DukeTheoremStatement'."""
    typ = text.split(" : ", 1)[-1]
    return typ.split(".")[-1].split(" ")[0].split("(")[0]


def _clean_condition_name(raw: str) -> str:
    """Strip a leading problem namespace (e.g. 'Erdos1197.') for display."""
    return re.sub(r"^Erdos_?\d+\w*\.", "", raw)


def compute_conditions(rows: list[dict]) -> list[dict]:
    """Group conditional proofs by the unproven input each one declares.

    The load-bearing map: axiom conditions (from ``#print axioms``) and the
    recognizable named-theorem hypotheses are external results the frontier rests
    on — formalizing one clears every problem that assumes it. Problem-internal
    hypotheses and ``native_decide`` trust are surfaced in their own tiers so the
    map never dresses a routine hypothesis up as a load-bearing theorem.
    """
    groups: dict[str, dict] = {}

    def bump(key: str, name: str, kind: str, tier: str, desc: str, problem: int) -> None:
        g = groups.setdefault(key, {"key": key, "name": name, "kind": kind,
                                    "tier": tier, "description": desc, "problems": set()})
        g["problems"].add(problem)

    for r in rows:
        if r["machine_verdict"] != "conditional":
            continue
        for ax in r["non_kernel_axioms"]:
            if "native_decide" in ax or "._native." in ax:
                bump("native_decide", "native_decide (trusted native evaluation)",
                     "compiler", "compiler",
                     "The proof trusts a native-compiled computation, not a kernel proof.",
                     r["problem"])
                continue
            cleaned = _clean_condition_name(ax)
            meta = CONDITION_META.get(ax) or CONDITION_META.get(cleaned)
            name, family, desc = meta if meta else (cleaned, None, "")
            bump(family or cleaned, name, "axiom", "theorem", desc, r["problem"])
        for h in r["named_assumptions"]:
            head = _assumption_head(h)
            meta = CONDITION_META.get(head)
            if meta:
                name, family, desc = meta
                bump(family or head, name, "hypothesis", "theorem", desc, r["problem"])
            else:
                bump(head, _clean_condition_name(head), "hypothesis", "hypothesis", "", r["problem"])

    tier_rank = {"theorem": 0, "hypothesis": 1, "compiler": 2}
    out = [{"key": g["key"], "name": g["name"], "kind": g["kind"], "tier": g["tier"],
            "description": g["description"], "problems": sorted(g["problems"]),
            "leverage": len(g["problems"])} for g in groups.values()]
    out.sort(key=lambda c: (tier_rank.get(c["tier"], 9), -c["leverage"], c["name"].lower()))
    return out


def render_verdicts_feed(payload: dict) -> dict:
    """The public audit feed: which formally-solved Erdős claims are actually
    unconditional. One row per problem, joining the machine L1 verdict, the FC/
    erdos L0 status, and any signed L2 fidelity verdict. The saleable artifact —
    a benchmark builder consumes this to avoid counting a conditional proof as a
    solve. Machine evidence is deterministic; signed verdicts carry a reviewer.
    """
    rows = []
    for r in payload["rows"]:
        machine = r.get("machine") or {}
        fidelity = r.get("fidelity") or {}
        wiki = r.get("wiki") or {}
        candidate = r.get("candidate_claims") or {}
        fc = r.get("fc") or {}
        rows.append({
            "problem": r["problem"],
            "erdos_url": r["erdos_url"],
            "erdos_state": r.get("erdos_state"),
            "fc_linked": bool(fc.get("linked")),
            # the FC catalog page for this problem, and whether FC marks it
            # formally proved — the claim this audit reads the proof behind.
            "fc_url": fc.get("fc_url"),
            "fc_theorem": fc.get("theorem"),
            "fc_has_proof": bool(fc.get("has_proof")),
            # the hosted proof FC links (the artifact the machine layer audited),
            # plus every indexed hosted proof for the problem.
            "proof_link": fc.get("formal_proof_link"),
            "proof_links": r.get("proof_links") or [],
            "bucket": r["bucket"],
            "machine_verdict": machine.get("verdict"),
            "machine_source": machine.get("source"),
            "named_assumptions": machine.get("named_assumptions") or [],
            "non_kernel_axioms": machine.get("non_kernel_axioms") or [],
            # the frozen-wiki claim this row is a superset of (None if absent).
            "wiki_ai_systems": wiki.get("ai_systems") or [],
            "wiki_humans": wiki.get("humans") or [],
            "wiki_outcome": wiki.get("outcome_label"),
            "wiki_color": wiki.get("claimed_color"),
            "wiki_claims_solved": bool(wiki.get("claims_full_solution")),
            "wiki_claims_lean": bool(wiki.get("claims_lean")),
            # wiki says solved; the available formal proof is conditional/incomplete.
            "discrepancy": bool(r.get("discrepancy")),
            # a flag on a celebrated proof, held for human review (not auto-published).
            "held_for_review": bool(r.get("held_for_review")),
            # independent human review of the GPT-5.2 candidate (neelsomani/gpt-erdos).
            "gpt_erdos": candidate.get("category"),
            # axis 2 — the signed statement-fidelity verdict (does the formal
            # statement faithfully state the boxed problem). Human-signed, L2.
            "signed_fidelity_verdict": fidelity.get("verdict"),
            "signed_by": fidelity.get("reviewer") if fidelity.get("signed") else None,
            "fidelity_note": fidelity.get("note"),
            "fidelity_source": fidelity.get("source"),
            "recommended_action": r.get("recommended_action"),
        })
    flagged = [r for r in rows if r["machine_verdict"] == "conditional"]
    return {
        "schema": "erdos-fidelity-audit.v1",
        "generated_at": payload["generated_at"],
        "sources": payload.get("sources"),
        "summary": {
            "problems": len(rows),
            "wiki_problems": sum(1 for r in rows if r["wiki_outcome"] is not None),
            "machine_conditional": len(flagged),
            "axiom_clean_but_conditional": [
                r["problem"] for r in flagged
                if r["named_assumptions"] and not r["non_kernel_axioms"]
            ],
            "discrepancies": [r["problem"] for r in rows if r["discrepancy"]],
            "held_for_review": [r["problem"] for r in rows if r["held_for_review"]],
            "signed_fidelity": [
                {"problem": r["problem"], "verdict": r["signed_fidelity_verdict"],
                 "reviewer": r["signed_by"]}
                for r in rows if r["signed_fidelity_verdict"] is not None
            ],
            "gpt_erdos_problems": sum(1 for r in rows if r["gpt_erdos"] is not None),
            # where an independent human review (gpt-erdos) and this proof audit both
            # speak to the same problem — they examine different artifacts (informal
            # GPT output vs the hosted Lean proof), so overlap is the interesting part.
            "cross_reference": [
                {"problem": r["problem"], "machine_verdict": r["machine_verdict"],
                 "gpt_erdos": r["gpt_erdos"]}
                for r in rows if r["gpt_erdos"] is not None and r["machine_verdict"] is not None
            ],
            # the load-bearing condition map: the unproven inputs the conditional
            # proofs declare, grouped so leverage counts the problems each unlocks.
            "conditions": compute_conditions(rows),
        },
        "rows": rows,
    }


#: The slim per-row projection the dashboard table needs. Everything else
#: (proof links, notes, full hypothesis types, provenance) lives in the
#: per-problem shard. `named` carries display names only: the full
#: "binder : Type" strings are most of verdicts.json's bulk. Empty and
#: null fields are omitted per row, and erdos_url is derived client-side,
#: so a row with no audit data is just its problem number and bucket.
TABLE_FIELDS = (
    "problem", "fc_url", "bucket", "machine_verdict",
    "named", "axioms", "signed_fidelity_verdict", "signed_by",
    "wiki_outcome", "wiki_ai_systems", "gpt_erdos", "discrepancy",
)


def _table_row(r: dict) -> dict:
    row = dict(r,
               named=[a.split(" : ")[-1] for a in r["named_assumptions"]],
               axioms=r["non_kernel_axioms"])
    return {k: row[k] for k in TABLE_FIELDS if row.get(k) not in (None, [], False, "")}


def render_site_data(feed: dict, root: Path) -> None:
    """Pre-split site feeds so no page needs the full verdicts.json.

    Additive only: verdicts.json stays the public contract, byte-for-byte.
    Shards omit generated_at (it lives in summary.json) and are written
    compact with sorted keys, so unchanged content produces no diff in the
    daily refresh commit.
    """
    data = root / "data"
    problems_dir = data / "problems"
    problems_dir.mkdir(parents=True, exist_ok=True)
    rows = feed["rows"]

    def dumps(obj: object) -> str:
        return json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n"

    summary = dict(feed["summary"])
    summary["funnel"] = {
        "problems": len(rows),
        "hosted_proof": sum(1 for r in rows if r["bucket"] != "no-proof"),
        "audited": sum(1 for r in rows if r["machine_verdict"] is not None),
        "conditional": sum(1 for r in rows if r["machine_verdict"] == "conditional"),
        "axiom_clean_but_conditional": len(summary["axiom_clean_but_conditional"]),
        "wiki": summary["wiki_problems"],
        "discrepancies": len(summary["discrepancies"]),
    }
    summary["discrepancy_rows"] = [
        {"problem": r["problem"], "wiki_outcome": r["wiki_outcome"],
         "named_assumptions": r["named_assumptions"],
         "non_kernel_axioms": r["non_kernel_axioms"],
         "axiom_invisible": bool(r["named_assumptions"] and not r["non_kernel_axioms"])}
        for r in rows if r["discrepancy"]
    ]
    summary["wiki_by_problem"] = {
        str(r["problem"]): r["wiki_outcome"]
        for r in rows if r["wiki_outcome"] is not None
    }
    (data / "summary.json").write_text(dumps({
        "schema": feed["schema"],
        "generated_at": feed["generated_at"],
        "summary": summary,
    }))

    (data / "table.json").write_text(dumps({
        "schema": feed["schema"],
        "rows": [_table_row(r) for r in rows],
    }))

    live = set()
    for r in rows:
        name = f"{r['problem']}.json"
        live.add(name)
        (problems_dir / name).write_text(dumps(r))
    for stale in problems_dir.glob("*.json"):
        if stale.name not in live:
            stale.unlink()


def write_outputs(payload: dict, root: str | Path = ".") -> None:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "STATUS.md").write_text(render_status_md(payload))
    (root / "NEXT_BATCH.md").write_text(render_next_batch_md(payload))
    (root / "status.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    feed = render_verdicts_feed(payload)
    (root / "verdicts.json").write_text(json.dumps(feed, indent=2, sort_keys=True) + "\n")
    render_site_data(feed, root)


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
    fidelity = load_fidelity(FIDELITY_URL)
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
    registry = (yaml.safe_load((root / "sources.yaml").read_text()) or {}).get("sources", {})
    headers = claims_headers()
    locked: dict[str, dict] = {}
    for name, spec in registry.items():
        entry: dict = {"kind": spec.get("kind")}
        if spec.get("repo"):
            entry["repo"] = spec["repo"]
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
            elif spec.get("kind") == "statement_attestations" and (root / "frontier.json").exists():
                entry["home"] = "self (.vela/ -> frontier.json)"
                entry["sha256"] = "sha256:" + hashlib.sha256(
                    (root / "frontier.json").read_bytes()).hexdigest()
            elif spec.get("path") and (root / spec["path"]).exists():
                entry["path"] = spec["path"]
                entry["sha256"] = "sha256:" + hashlib.sha256(
                    (root / spec["path"]).read_bytes()).hexdigest()
        except (urllib.error.URLError, OSError) as exc:
            entry["error"] = str(exc)
        locked[name] = entry
    stamp = _datetime.datetime.now(_datetime.timezone.utc).replace(microsecond=0).isoformat()
    out = {"generated_at": stamp, "sources": locked}
    (root / "sources.lock.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def main() -> int:
    payload = load_live_status()
    write_outputs(payload, "site")
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
    print("wrote STATUS.md, status.json, NEXT_BATCH.md, verdicts.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

