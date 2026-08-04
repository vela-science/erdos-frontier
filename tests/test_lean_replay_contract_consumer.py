from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reproductions/erdos-264/lean-replay-contract.consumer.v1.json"
HISTORICAL_VERIFIER = ROOT / "execution/erdos-264-proof-repair/verify.py"
HISTORICAL_CAPSULE = ROOT / "execution/erdos-264-proof-repair/verifier-capsule.v1.json"


def package_directory() -> Path:
    if value := os.environ.get("VELA_LEAN_REPLAY_CONTRACT"):
        return Path(value).resolve(strict=True)
    return (ROOT.parent / "vela/research/lean-replay-contract").resolve(strict=True)


class LeanReplayContractConsumerTests(unittest.TestCase):
    def test_exact_package_root_without_rewriting_historical_verifier(self) -> None:
        package = package_directory()
        sys.path.insert(0, str(package))
        try:
            from lean_replay_contract import parse_axioms, verify_package_reference
        finally:
            sys.path.pop(0)

        reference = json.loads(REFERENCE.read_bytes())
        capsule = json.loads(HISTORICAL_CAPSULE.read_bytes())
        self.assertEqual(
            verify_package_reference(package, reference),
            "sha256:5653a31b6b42a77cff91905ffa3086730e21eb6cc4105963d9d98cbcc2b2baae",
        )
        verifier_bytes = HISTORICAL_VERIFIER.read_bytes()
        self.assertEqual(len(verifier_bytes), capsule["implementation"]["size"])
        self.assertEqual(
            "sha256:" + hashlib.sha256(verifier_bytes).hexdigest(),
            capsule["implementation"]["sha256"],
        )
        declaration = "Erdos264.erdos_264.parts.i"
        output = (
            f"'{declaration}' depends on axioms: "
            "[propext, Classical.choice, Quot.sound]"
        )
        self.assertEqual(
            parse_axioms(
                output,
                declaration=declaration,
                permitted={"propext", "Classical.choice", "Quot.sound"},
            ),
            ["propext", "Classical.choice", "Quot.sound"],
        )
        self.assertEqual(reference["authority_effect"], "none")
        self.assertEqual(reference["standing_effect"], "none")


if __name__ == "__main__":
    unittest.main()
