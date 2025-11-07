# configs/pr_template.md: Default template for pull request bodies.
# This Markdown file is used as the template for creating pull requests when a
# sync conflict occurs. It includes placeholders that will be dynamically
# replaced with information about the divergence, such as the SHAs of the
# conflicting commits.

### Sealbridge Sync Conflict

This PR was automatically created by `sealbridge` because a sync conflict was detected between the personal and relay remotes for the `{repo_name}` repository. A manual review and merge are required.

**Details:**
- **Repository:** `{repo_name}`
- **Branch:** `{branch_name}`
- **Personal (Origin) Head:** `{personal_sha}`
- **Relay Head:** `{relay_sha}`

This branch contains the changes from the relay remote, rebased on top of the personal remote's branch. Please review the changes and merge if they are correct.

---
*This PR was sealed at the relay.*
