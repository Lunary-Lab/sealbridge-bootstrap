#!/bin/bash
# tests/e2e/fixtures/make_personal_repo.sh: Creates a bare personal origin repo.
# This script initializes a bare git repository and populates it with some
# initial content to simulate a user's personal repository.

set -e
set -x # Enable debug output

REPO_PATH="$1"
if [ -z "$REPO_PATH" ]; then
    echo "Usage: $0 <path_to_repo>"
    exit 1
fi

# Create a temporary directory to initialize the repo
TMP_INIT_DIR=$(mktemp -d)
cd "$TMP_INIT_DIR"

git init
git config user.name "E2E Test"
git config user.email "test@example.com"
git checkout -b main

echo "Initial content" > README.md
git add README.md
git commit -m "Initial commit"

# Create the bare repo and push to it
git init --bare "$REPO_PATH"
git remote add origin "$REPO_PATH"
git push -u origin main

cd / && rm -rf "$TMP_INIT_DIR"
