#!/usr/bin/env bash
# The frontier graph, one verb per intention:
#
#   bash scripts/graph.sh build            rebuild the corpus graph from sources
#   bash scripts/graph.sh blast <node>     dependency-impact of retracting a node
#                                          (e.g. cond:maynard-tao, erdos:997,
#                                           proof:plby:258)
#   bash scripts/graph.sh serve [port]     the frontier over HTTP (default MCP
#                                          stdio config is .mcp.json — any MCP
#                                          client opening this repo gets the
#                                          read-only tool set)
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

# `vela` is often a shell alias (which scripts don't expand) and a stale conda
# shim can shadow the real binary: resolve the first candidate that actually runs.
resolve_vela() {
  # newest-first: the workspace wrapper carries the full command surface
  # (`atlas`, `serve`); older release builds on PATH may lack them.
  for c in "${VELA:-}" "$HOME/personal/vela/scripts/vela" \
           "$HOME/.cargo/bin/vela" "$(command -v vela || true)" \
           "$HOME/.local/bin/vela"; do
    [ -n "$c" ] && "$c" help advanced 2>/dev/null | grep -q "atlas" \
      && { echo "$c"; return; }
  done
  echo "no vela with the atlas/serve surface found (set VELA=/path/to/vela)" >&2
  exit 1
}
VELA_BIN="$(resolve_vela)"

case "${1:-}" in
  build)
    python3 scripts/build_graph.py
    ;;
  blast)
    [ -n "${2:-}" ] || { echo "usage: graph.sh blast <node-id>"; exit 2; }
    [ -f graph/corpus-edges.jsonl ] || python3 scripts/build_graph.py >/dev/null
    "$VELA_BIN" atlas decl-blast --edges graph/corpus-edges.jsonl --decl "$2"
    ;;
  serve)
    "$VELA_BIN" serve . --http "${2:-8787}"
    ;;
  *)
    sed -n '2,12p' "$0"; exit 2
    ;;
esac
