# Sealbridge Repos

Sealbridge Repos is a tool for bi-directionally syncing code between a personal, plaintext Git repository and a work, encrypted Git repository. It is designed to be run as a daemon on both your personal and work machines, ensuring that your code is always up-to-date while maintaining a strict security boundary.

## Architecture

Sealbridge operates on a two-clone model. On your home machine, the `sealbridge-bridge` process maintains two separate clones of each repository: one for your personal plaintext remote, and one for the encrypted work relay. The bridge is responsible for mirroring changes between these two clones.

On your work machine, the `sealreposd` daemon syncs only with the encrypted work relay, ensuring that your work machine never communicates with your personal GitHub account.

## Features

- **Bi-directional Sync:** Keep your personal and work repositories in sync.
- **Encrypted at Rest:** All code is encrypted at the work remote using `git-crypt`.
- **XDG Compliant:** Sealbridge respects XDG base directory specifications on both Linux and Windows.
- **Policy Enforcement:** Configure include/exclude paths to control what gets synced.
- **Secret Scanning:** Prevent secrets from being committed with `gitleaks` integration.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/sealbridge-repos.git
    cd sealbridge-repos
    ```

2.  **Run the installation script:**
    -   **Linux:** `./scripts/install.sh`
    -   **Windows (PowerShell):** `.\\scripts\\install.ps1`

## Configuration

Configuration is handled by a `policy.yaml` file located in `${XDG_CONFIG_HOME}/sealbridge/`. An example configuration is provided in `configs/policy.yaml.example`.

## Usage

The `reposctl` CLI is used to manage Sealbridge.

-   `reposctl status`: Show the status of each configured repository.
-   `reposctl sync <repo_name>`: Run a single sync cycle for a repository.
-   `reposctl unlock <repo_name>`: Unlock a `git-crypt` encrypted repository.
-   `reposctl set-profile <home|work>`: Set the active profile.
-   `reposctl pr <repo_name>`: Create a pull request for a repository with diverged changes.
