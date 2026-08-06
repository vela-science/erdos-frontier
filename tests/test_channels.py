"""Hold the channel taxonomy to the shape its `schema:` key claims.

`campaigns/channels.yaml` is curation, not configuration: no Vela command reads
it and it adjudicates nothing. What it does carry is two cross-references that
fail silently. A `reduces_to` naming a core that is not declared reads exactly
like one that is, and the briefing that consumes the file by eye would report
a channel as cold against a wall nobody wrote down. A channel id duplicated
across two problems is the same defect wearing a different hat. Neither shows
up as a parse error, so this file is what notices.

This is also the only thing standing behind the `schema:` key. An identifier no
reader validates is a promise nobody keeps, and the alternative to checking it
was deleting it.
"""

from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
CHANNELS = ROOT / "campaigns" / "channels.yaml"

SCHEMA = "erdos-frontier.channels.v0.1"


def load():
    return yaml.safe_load(CHANNELS.read_text(encoding="utf-8"))


def iter_channels(document):
    for problem, channels in document["problems"].items():
        for channel in channels:
            yield problem, channel


def test_taxonomy_declares_the_schema_this_file_checks():
    assert load()["schema"] == SCHEMA


def test_every_reduction_names_a_declared_core():
    document = load()
    cores = {core["id"] for core in document["cores"]}
    for _problem, channel in iter_channels(document):
        if "reduces_to" in channel:
            assert channel["reduces_to"] in cores, (
                f"{channel['id']} reduces to {channel['reduces_to']}, "
                f"which is not a declared core"
            )


def test_channel_and_core_identifiers_are_unique():
    document = load()
    core_ids = [core["id"] for core in document["cores"]]
    assert len(core_ids) == len(set(core_ids))

    channel_ids = [channel["id"] for _problem, channel in iter_channels(document)]
    assert len(channel_ids) == len(set(channel_ids))


def test_each_channel_identifier_names_the_problem_it_sits_under():
    # The id carries the problem number, so a channel filed under the wrong key
    # is a fold key pointing at another problem's work.
    for problem, channel in iter_channels(load()):
        assert channel["id"].startswith(f"erdos{problem}:"), (
            f"{channel['id']} is filed under problem {problem}"
        )


def test_every_channel_carries_a_title():
    for _problem, channel in iter_channels(load()):
        assert channel["title"].strip()
