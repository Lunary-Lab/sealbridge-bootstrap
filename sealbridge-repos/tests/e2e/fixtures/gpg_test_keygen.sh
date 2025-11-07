#!/bin/bash
# tests/e2e/fixtures/gpg_test_keygen.sh: Generates ephemeral GPG keys for CI.
# This script creates a temporary GPG home directory and generates a new GPG key
# without a passphrase, suitable for use in automated tests. It then exports
# the home directory path and the key's fingerprint.

set -e

GPG_HOME=$(mktemp -d)
export GNUPGHOME="$GPG_HOME"

echo "$GPG_HOME"

# Generate a key without a passphrase
cat >/tmp/gpg-batch <<EOF
%no-protection
Key-Type: 1
Key-Length: 2048
Subkey-Type: 1
Subkey-Length: 2048
Name-Real: E2E Test Key
Name-Email: test@example.com
Expire-Date: 0
EOF

gpg --batch --gen-key /tmp/gpg-batch > /dev/null 2>&1

# Export the fingerprint
gpg --list-keys --with-colons | grep "^fpr" | cut -d: -f10
