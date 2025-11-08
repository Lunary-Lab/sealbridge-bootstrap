#!/bin/bash
set -e

# Create a bare git repository to act as the dotfiles remote
git init --bare /tmp/dotfiles.git

# Clone the bare repo to a temporary location to add files
git clone /tmp/dotfiles.git /tmp/dotfiles-clone

cd /tmp/dotfiles-clone

# Create a file that chezmoi can apply.
# The `dot_` prefix tells chezmoi to create this file as `.test-file` in the home directory.
mkdir -p source
echo "sealbridge-e2e-test" > source/dot_test-file

# Add and commit the file
git add .
git commit -m "Add test file for e2e verification"

# Push the changes back to the bare repository
git push origin main

# Clean up the temporary clone
rm -rf /tmp/dotfiles-clone
