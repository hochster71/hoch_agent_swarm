#!/bin/bash
# Generate the founder approval signing key (Ed25519, passphrase-protected).
# Private key lives OUTSIDE the repo so agents never touch it.
# Only the public key + allowed_signers file are committed.
set -euo pipefail
KEYDIR="$HOME/.has_founder"
KEY="$KEYDIR/founder_signing_key"
REPO="$HOME/hoch_agent_swarm"
mkdir -p "$KEYDIR" && chmod 700 "$KEYDIR"
[ -f "$KEY" ] && { echo "Key already exists at $KEY — refusing to overwrite."; exit 1; }
echo "Choose a strong passphrase — it is the founder authorization factor."
ssh-keygen -t ed25519 -C "founder@hoch-has" -f "$KEY"   # prompts for passphrase
chmod 600 "$KEY"
PUB=$(cat "$KEY.pub")
echo "founder@hoch-has namespaces=\"has-approval\" ${PUB% founder@hoch-has}" > "$REPO/config/founder_allowed_signers"
echo "Wrote $REPO/config/founder_allowed_signers — commit this file."
echo "NEVER commit $KEY."
