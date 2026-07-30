#!/usr/bin/env bash
# Re-run the heavy multi-toolchain Lean audit and refresh retained source locks.
#
# Each proof repo is loaded in its own built `.lake` env at its own pinned Lean
# toolchain; the extractor reads axioms + theorem-parameter hypotheses per proof.
# This is the HEAVY step — run it explicitly when the proof corpora change.
#
# Assumes the proof repos are already cloned + built locally (the default roots, or
# the VELA_PROOF_REPO* env overrides used by extract_assumptions.py). The CI
# workflow audit-proofs.yml does the clone + build before calling this.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

echo "==> plby fork (Lean 4.29.1)"
python3 lean/extract_assumptions.py --repo plby

echo "==> alphaproof-nexus (Lean 4.27.0)"
python3 lean/extract_assumptions.py --repo alphaproof

# Jayyhk/erdos-lean is per-problem-project (each problems/<n>/ pins its own
# toolchain). Provision a toolchain group first with lean/build-jayyhk.sh; this
# audits whatever is already built and skips the rest.
echo "==> Jayyhk/erdos-lean (audits already-built problem projects)"
python3 lean/extract_assumptions.py --repo jayyhk || true

echo "==> refresh the source audit and exact source locks"
python3 erdos_frontier.py

echo "re-audit complete: audit_feed*.json + sources.lock.json refreshed."
