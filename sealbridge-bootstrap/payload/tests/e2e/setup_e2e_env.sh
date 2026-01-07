#!/bin/bash
set -e

# --- E2E Test Environment Setup ---

# 1. Install 'age' binary
AGE_VERSION="v1.3.1"
AGE_ARCH="linux-amd64"
AGE_ASSET="age-${AGE_VERSION}-${AGE_ARCH}.tar.gz"
AGE_URL="https://github.com/FiloSottile/age/releases/download/${AGE_VERSION}/${AGE_ASSET}"
CHECKSUMS_URL="https://github.com/FiloSottile/age/releases/download/${AGE_VERSION}/sha256sums.txt"

echo "Downloading age binary..."
curl -fL -o "/tmp/${AGE_ASSET}" "${AGE_URL}"

echo "Verifying age checksum..."
curl -fL -o "/tmp/sha256sums.txt" "${CHECKSUMS_URL}"
grep "${AGE_ASSET}" "/tmp/sha256sums.txt" | sha256sum -c -

echo "Installing age binary..."
tar -C /usr/local/bin -xzf "/tmp/${AGE_ASSET}" age/age --strip-components=1
rm "/tmp/${AGE_ASSET}" "/tmp/sha256sums.txt"

# 2. Create mock dotfiles git repository
echo "Creating mock dotfiles repository..."
git init --bare /tmp/dotfiles.git
git clone /tmp/dotfiles.git /tmp/dotfiles-clone
cd /tmp/dotfiles-clone
mkdir -p source
echo "sealbridge-e2e-test-successful" > source/dot_test-file
git add .
git config user.email "tester@sealbridge.dev"
git config user.name "E2E Tester"
git commit -m "Add test file for e2e verification"
git push origin main
cd /
rm -rf /tmp/dotfiles-clone

# 3. Generate and encrypt the SSH key for the test
echo "Generating and encrypting SSH key..."
ssh-keygen -t ed25519 -f /tmp/id_ed25519 -N "" -C "e2e-test-key"
# The public key needs to be authorized for the git user (tester)
cat /tmp/id_ed25519.pub >> /home/tester/.ssh/authorized_keys
# Encrypt the private key with a known passphrase for the test
echo "testpassphrase" | age -p -o /tmp/id_bootstrap.age /tmp/id_ed25519
# Remove the plaintext private key
rm /tmp/id_ed25519

echo "E2E environment setup complete."
