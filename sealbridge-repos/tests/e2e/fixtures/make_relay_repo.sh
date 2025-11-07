#!/bin/bash
# tests/e2e/fixtures/make_relay_repo.sh: Creates a bare relay repo with git-crypt.
# This script initializes a bare git repository and then configures it for
# git-crypt encryption, adding a specified GPG user.

set -e
set -x # Enable debug output

REPO_PATH="$1"
GPG_FPR="$2"

if [ -z "$REPO_PATH" ] || [ -z "$GPG_FPR" ]; then
    echo "Usage: $0 <path_to_repo> <gpg_fingerprint>"
    exit 1
fi

# Create a temporary directory to initialize the repo
TMP_INIT_DIR=$(mktemp -d)
cd "$TMP_INIT_DIR"

git init
git config user.name "E2E Test"
git config user.email "test@example.com"
git checkout -b main

git-crypt init
git-crypt add-gpg-user "$GPG_FPR"

# Use the encrypt-all template
echo '* filter=git-crypt diff=git-crypt' > .gitattributes
echo '.gitattributes !filter !diff' >> .gitattributes

git add .gitattributes
git commit -m "Initialize git-crypt"

# Create the bare repo and push to it
git init --bare "$REPO_PATH"
git remote add origin "$REPO_PATH"
git push -u origin main

cd / && rm -rf "$TMP_INIT_DIR"
