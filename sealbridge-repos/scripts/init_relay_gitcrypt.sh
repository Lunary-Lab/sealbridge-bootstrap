#!/bin/bash
# scripts/init_relay_gitcrypt.sh: Helper to initialize a git-crypt relay repo.
# This script automates the process of setting up a new relay repository with
# git-crypt. It initializes the repo, copies the .gitattributes template to
# encrypt all files, and adds the initial GPG users who are authorized to
# access the repository's content.

set -e

REPO_PATH="$1"
shift
GPG_USERS=("$@")

if [ -z "$REPO_PATH" ] || [ ${#GPG_USERS[@]} -eq 0 ]; then
    echo "Usage: $0 <path_to_repo> <gpg_fingerprint_1> [gpg_fingerprint_2]..."
    exit 1
fi

cd "$REPO_PATH"
git-crypt init

# Add GPG users
for user in "${GPG_USERS[@]}"; do
    git-crypt add-gpg-user "$user"
done

# Copy the .gitattributes file
cp ../configs/gitattributes.gitcrypt .gitattributes

echo "git-crypt relay initialized successfully at $REPO_PATH"
echo "Commit the .gitattributes file to apply encryption."
