#!/usr/bin/env bash
# Re-run the heavy multi-toolchain Lean audit and regenerate the committed feeds.
#
# Each proof repo is loaded in its own built `.lake` env at its own pinned Lean
# toolchain; the extractor reads axioms + theorem-parameter hypotheses per proof.
# This is the HEAVY step — run it when the proof corpora change. The daily
# update-status.yml job does NOT run this; it only re-reads the committed
# audit_feed*.json and refreshes the join, which is cheap.
#
# Assumes the proof repos are already cloned + built locally (the default roots, or
# the VELA_PROOF_REPO* env overrides used by extract_assumptions.py). The CI
# workflow audit-proofs.yml does the clone + build before calling this.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

echo "==> plby fork (Lean 4.29.1)"
python3 lean_assumptions/extract_assumptions.py --repo plby

echo "==> alphaproof-nexus (Lean 4.27.0)"
python3 lean_assumptions/extract_assumptions.py --repo alphaproof

echo "==> regenerate the join (status.json + verdicts.json + STATUS.md + packets feed)"
python3 fc-sync-status.py

echo "re-audit complete: audit_feed*.json + status regenerated."
