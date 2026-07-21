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


def test_frontier_workflow_uses_the_lock_matching_released_vela():
    workflow = yaml.load(
        (ROOT / ".github" / "workflows" / "vela-frontier.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    lock = (ROOT / "vela.lock").read_text()
    lock_version = re.search(r"^vela_version:\s*(\S+)$", lock, re.MULTILINE)

    assert lock_version is not None
    assert workflow["env"]["VELA_VERSION"] == f"v{lock_version.group(1)}"
    assert workflow["env"]["VELA_LINUX_ARCHIVE_SHA256"] == (
        "29ff6001374196a24fba3766462474f09fc197721cc38e353dabca01eecad2fa"
    )
    assert workflow["env"]["VELA_LINUX_SHA256"] == (
        "cf30a1dc5f575e74055396a9afde59f9b64fb82fc01e58a3e1863a5e36d6444e"
    )


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
