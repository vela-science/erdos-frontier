# Erdős Frontier — formal-proof fidelity audit

## Register

product

## Product purpose

A public audit over the Erdős problem corpus: which "formally solved" problems rest on an unconditional Lean proof, and which silently assume an unproven result. The successor to the erdosproblems wiki's AI-contributions page (frozen June 30, 2026). The machine layer extracts axioms and hypothesis parameters deterministically; the human layer is signed statement-fidelity verdicts by named reviewers on a Vela frontier (vfr_0a25edabc16db143). The site is a materialized view of that signed state.

## Users

Skeptical mathematicians and Lean contributors arriving from Formal Conjectures PR reviews and the leanprover Zulip; secondarily benchmark builders deciding whether a claimed solve can enter an eval set. They want the evidence chain fast, they distrust decoration, and they will check the reproduce command.

## Brand and tone

Part of the Constellate ecosystem (constellate.science). Calm scientific record: legibility, trust, provenance, quiet control. Wabi-sabi restraint; kintsugi gold marks human-signed acts only; ma (negative space) at section boundaries. The page is the artifact: it should print well. Understate, never oversell; the numbers carry the argument.

## Anti-references

SaaS dashboards with hero-metric cards and gradient accents; crypto-dark landing pages; emoji traffic lights; shields and checkmark badges; anything that reads as marketing rather than a record.

## Strategic principles

- Trust tiers are the visual vocabulary: signed (gold), machine (moss), recorded (brass), declared (stone), contradiction (cinnabar).
- The 9 discrepancies are the reason the site exists; they lead.
- Public feeds (verdicts.json, graph.json, status.json) are contracts; the UI never requires reshaping them.
- Zero build step; static files on GitHub Pages; evergreen-browser oklch is fine.
