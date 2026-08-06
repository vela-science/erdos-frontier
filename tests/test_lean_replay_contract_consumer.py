from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reproductions/erdos-264/lean-replay-contract.consumer.v1.json"
HISTORICAL_VERIFIER = ROOT / "execution/erdos-264-proof-repair/verify.py"
HISTORICAL_CAPSULE = ROOT / "execution/erdos-264-proof-repair/verifier-capsule.v1.json"


def package_directory() -> Path:
    if value := os.environ.get("VELA_LEAN_REPLAY_CONTRACT"):
        return Path(value).resolve(strict=True)
    return (ROOT.parent / "vela/research/lean-replay-contract").resolve(strict=True)


def historical_verifier() -> types.ModuleType:
    """Load the accepted verifier for reading only; it is never rewritten."""
    specification = importlib.util.spec_from_file_location(
        "erdos_264_historical_verifier", HISTORICAL_VERIFIER
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class LeanReplayContractConsumerTests(unittest.TestCase):
    def test_exact_package_root_without_rewriting_historical_verifier(self) -> None:
        package = package_directory()
        sys.path.insert(0, str(package))
        try:
            from lean_replay_contract import (
                ContractError,
                parse_axioms,
                verify_package_reference,
            )
        finally:
            sys.path.pop(0)

        reference = json.loads(REFERENCE.read_bytes())
        capsule = json.loads(HISTORICAL_CAPSULE.read_bytes())
        # The root asserted here was a copy of the one this reference already
        # declares, so an honest change to the package meant hand-editing the
        # same digest in two files. The reference is the retained evidence;
        # what this consumer must show is that the package on disk verifies
        # against it and yields the root the reference names.
        self.assertEqual(
            verify_package_reference(package, reference),
            reference["package_root"],
        )
        verifier_bytes = HISTORICAL_VERIFIER.read_bytes()
        self.assertEqual(len(verifier_bytes), capsule["implementation"]["size"])
        self.assertEqual(
            "sha256:" + hashlib.sha256(verifier_bytes).hexdigest(),
            capsule["implementation"]["sha256"],
        )
        # The declaration and the permitted axioms belong to the accepted
        # verifier, whose bytes were just bound to the capsule. Restating them
        # here made the axiom check a round trip through the test's own
        # fixture: it could agree with itself while disagreeing with the
        # verifier it exists to reproduce.
        verifier = historical_verifier()
        declaration = verifier.DECLARATION
        permitted = verifier.ALLOWED_AXIOMS
        reported = sorted(permitted)
        output = f"'{declaration}' depends on axioms: [{', '.join(reported)}]"
        self.assertEqual(
            parse_axioms(
                output,
                declaration=declaration,
                permitted=permitted,
                expected=reported,
            ),
            reported,
        )
        # A parser that only agrees with a well-formed report reproduces
        # nothing: the boundary the accepted verifier enforces is that an
        # axiom outside its permitted set fails closed.
        with self.assertRaises(ContractError):
            parse_axioms(
                output.replace("]", ", sorryAx]"),
                declaration=declaration,
                permitted=permitted,
            )
        self.assertEqual(reference["authority_effect"], "none")
        self.assertEqual(reference["standing_effect"], "none")


if __name__ == "__main__":
    unittest.main()
