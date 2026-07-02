#!/usr/bin/env bash
# The policy-signing ceremony: ONE signature activates policy-bound
# auto-admission for the mechanical exact lane on this frontier
# (.vela/policies/active.json, sealed vap_…). The policy can only TIGHTEN
# the frozen floor; truth-bearing claims stay human-keyed regardless.
#
# Run as yourself. Writes .vela/policies/active.sig.json; commit + push
# afterward (git push is publication).
set -euo pipefail
cd "$(dirname "$0")/.."

KEY="${VELA_KEY_PATH:-$HOME/.vela/keys/will-blair/private.key}"
POLICY=".vela/policies/active.json"
[ -f "$POLICY" ] || { echo "no sealed policy at $POLICY"; exit 1; }
[ -f "$KEY" ] || { echo "no key at $KEY (set VELA_KEY_PATH)"; exit 1; }

python3 - "$POLICY" "$KEY" <<'PY'
import sys, json, hashlib, datetime
from pathlib import Path
policy_path, key_path = sys.argv[1], sys.argv[2]
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
except ImportError:
    sys.exit("pip install cryptography")

policy = json.loads(Path(policy_path).read_text())
pid = policy["id"]
assert pid.startswith("vap_"), "policy not sealed"

def canonical(v):
    # RFC-8785-lite for this shape: sorted keys, no whitespace
    return json.dumps(v, sort_keys=True, separators=(",", ":")).encode()

body = canonical(policy)
seed = bytes.fromhex(Path(key_path).read_text().strip())
k = Ed25519PrivateKey.from_private_bytes(seed)
sig = k.sign(body)
pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
rec = {
    "policy_id": pid,
    "signer_pubkey_hex": pub.hex(),
    "signature": sig.hex(),
    "signed_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
}
out = Path(policy_path).with_name("active.sig.json")
out.write_text(json.dumps(rec, indent=2) + "\n")
print(f"signed {pid} -> {out}")
print("verify + commit:")
print("  vela status . --json | jq .policy")
print("  git add .vela/policies && git commit -m 'governance: activate mechanical acceptance policy' && git push")
PY
