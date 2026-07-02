"""The split site feeds are additive: verdicts.json is a public contract and
must not change shape or bytes when render_site_data is introduced; the
summary/table/shard trio must stay consistent with it."""

import json
from pathlib import Path

import pytest

import erdos_frontier as ef

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"


@pytest.fixture(scope="module")
def payload():
    return json.loads((SITE / "status.json").read_text())


@pytest.fixture(scope="module")
def feed(payload):
    return ef.render_verdicts_feed(payload)


def test_verdicts_feed_unchanged_by_site_data(payload, feed, tmp_path_factory):
    """Regenerating from the committed payload reproduces the committed
    verdicts.json byte-for-byte: render_site_data added nothing to it."""
    rendered = json.dumps(feed, indent=2, sort_keys=True) + "\n"
    assert rendered == (SITE / "verdicts.json").read_text()


def test_site_data_consistent(feed, tmp_path):
    ef.render_site_data(feed, tmp_path)
    data = tmp_path / "data"

    summary = json.loads((data / "summary.json").read_text())
    table = json.loads((data / "table.json").read_text())
    rows = feed["rows"]

    # summary carries the timestamp; shards must not (daily-commit churn).
    assert summary["generated_at"] == feed["generated_at"]
    funnel = summary["summary"]["funnel"]
    assert funnel["problems"] == len(rows)
    assert funnel["discrepancies"] == len(summary["summary"]["discrepancy_rows"])
    assert funnel["conditional"] == sum(
        1 for r in rows if r["machine_verdict"] == "conditional")

    # table: one slim row per problem; empty fields omitted, nothing
    # outside the projection.
    assert len(table["rows"]) == len(rows)
    for t in table["rows"][:50]:
        assert "problem" in t
        assert set(t) <= set(ef.TABLE_FIELDS)

    # shards: one per problem, no generated_at, content matches the feed row.
    shards = sorted((data / "problems").glob("*.json"))
    assert len(shards) == len(rows)
    by_problem = {r["problem"]: r for r in rows}
    sample = json.loads(shards[0].read_text())
    assert "generated_at" not in sample
    assert sample == by_problem[sample["problem"]]


def test_discrepancy_rows_match_feed(feed, tmp_path):
    ef.render_site_data(feed, tmp_path)
    summary = json.loads((tmp_path / "data" / "summary.json").read_text())
    listed = {d["problem"] for d in summary["summary"]["discrepancy_rows"]}
    assert listed == {r["problem"] for r in feed["rows"] if r["discrepancy"]}
