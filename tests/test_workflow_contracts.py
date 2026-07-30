"""Contracts that keep expensive external audits outside routine automation."""

from pathlib import Path
import subprocess

import yaml


ROOT = Path(__file__).parents[1]


def test_heavy_lean_reaudit_is_manual_only():
    workflow = yaml.load(
        (ROOT / ".github" / "workflows" / "audit-proofs.yml").read_text(),
        Loader=yaml.BaseLoader,
    )

    assert workflow["on"] == {"workflow_dispatch": {}}


def test_frontier_workflow_pins_current_released_vela_action():
    workflow = yaml.load(
        (ROOT / ".github" / "workflows" / "vela-frontier.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    checkout = workflow["jobs"]["verify"]["steps"][0]
    assert checkout["with"]["fetch-depth"] == "0"
    vela = workflow["jobs"]["verify"]["steps"][1]
    assert vela["uses"] == (
        "vela-science/vela@2fafd652c501cfd6be16f24cc13d6e173eccd58a"
    )
    assert vela["with"] == {"frontier": ".", "vela-version": "v0.950.1"}


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
