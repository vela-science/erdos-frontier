"""Contracts that keep expensive external audits outside routine automation."""

from pathlib import Path
import re
import subprocess

import yaml


ROOT = Path(__file__).parents[1]


def test_heavy_lean_reaudit_is_manual_only():
    workflow = yaml.load(
        (ROOT / ".github" / "workflows" / "audit-proofs.yml").read_text(),
        Loader=yaml.BaseLoader,
    )

    assert workflow["on"] == {"workflow_dispatch": {}}


# The pin this asserted used to be a literal SHA, which went stale on the first
# release after it was written and reddened this Frontier for a reason that had
# nothing to do with the Frontier. Nothing in this repository declares which
# Vela release it expects: `frontier.toml` carries no version, `.vela/` records
# roots rather than a toolchain, and the action resolves its own release at run
# time. The only declaration is the `# vX.Y.Z` comment beside each pin. So the
# test holds what it can actually read — that every use of the action is pinned
# to a full commit SHA rather than a movable tag, that each pin says which
# release it is, and that the repository never disagrees with itself about
# which release that is. A bump stays green as long as it is a real bump.

VELA_ACTION_PIN = re.compile(
    r"^\s*-?\s*uses:\s*vela-science/vela@(?P<sha>\S+)\s*#\s*(?P<version>v\S+)\s*$",
    re.MULTILINE,
)


def _vela_action_pins():
    pins = {}
    for workflow in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for match in VELA_ACTION_PIN.finditer(workflow.read_text()):
            pins.setdefault(workflow.name, []).append(
                (match.group("sha"), match.group("version"))
            )
    return pins


def test_frontier_workflow_pins_current_released_vela_action():
    workflow = yaml.load(
        (ROOT / ".github" / "workflows" / "vela-frontier.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    checkout = workflow["jobs"]["verify"]["steps"][0]
    assert checkout["with"]["fetch-depth"] == "0"
    vela = workflow["jobs"]["verify"]["steps"][1]
    assert vela["uses"].startswith("vela-science/vela@")
    assert vela["with"] == {"frontier": "."}

    pins = _vela_action_pins()
    assert "vela-frontier.yml" in pins, (
        "vela-frontier.yml must pin vela-science/vela by SHA with a "
        "`# vX.Y.Z` comment naming the release"
    )

    seen = {pin for file_pins in pins.values() for pin in file_pins}
    for sha, version in seen:
        assert re.fullmatch(r"[0-9a-f]{40}", sha), (
            f"vela-science/vela must be pinned to a full commit SHA, got {sha!r}"
        )
        assert re.fullmatch(r"v\d+\.\d+\.\d+", version), (
            f"the pin comment must name a released version, got {version!r}"
        )
    assert len(seen) == 1, (
        f"every workflow must pin the same Vela release, found {sorted(seen)}"
    )
    assert vela["uses"] == f"vela-science/vela@{next(iter(seen))[0]}"


def test_artifact_hash_cannot_depend_on_ignored_workspace_files():
    ignored = subprocess.run(
        [
            "git",
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "artifacts",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()

    assert ignored == []
