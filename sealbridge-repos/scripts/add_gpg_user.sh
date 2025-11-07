#!/bin/bash
# scripts/add_gpg_user.sh: Helper to add a GPG user to a relay repo.
# This script simplifies the process of granting a new user access to a
# git-crypt-encrypted relay repository. It takes the repository path and the
# user's GPG fingerprint as arguments.

set -e

REPO_PATH="$1"
GPG_USER="$2"

if [ -z "$REPO_PATH" ] || [ -z "$GPG_USER" ]; then
    echo "Usage: $0 <path_to_repo> <gpg_fingerprint>"
    exit 1
fi

cd "$REPO_PATH"
git-crypt add-gpg-user "$GPG_USER"

echo "GPG user $GPG_USER added successfully to $REPO_PATH"
echo "Commit the .git-crypt directory changes to update access."
