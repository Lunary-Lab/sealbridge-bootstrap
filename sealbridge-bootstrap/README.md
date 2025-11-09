# SealBridge Bootstrap

`sealbridge-bootstrap` provides a secure, two-gate bootstrap process for provisioning a fresh workstation. It uses a combination of server-verified TOTP and a local passphrase to decrypt an SSH key, which is then used to set up the machine in a user-space, XDG-compliant manner on both Linux and Windows.

## Overview

The bootstrap process is designed to be initiated with a simple one-liner, minimizing the trust required in the initial connection. The core principles are:

- **Two-Gate Security**: A workstation is not fully trusted until it passes two independent security checks:
    1.  **Something you have**: A time-based one-time password (TOTP) from an authenticator app, verified by a trusted server (`sealbridge-otp-gate`).
    2.  **Something you know**: A local passphrase to decrypt a session-critical SSH key.
- **Zero Trust on Disk**: Plaintext secrets, especially the bootstrap SSH key, never touch the disk. They are decrypted directly into the running SSH agent's memory.
- **User-Space & XDG-Compliant**: The entire process operates within the user's home directory (`$HOME`). It strictly adheres to the XDG Base Directory Specification on both Linux and Windows, ensuring a clean, predictable, and non-invasive setup.
- **Idempotent and Atomic**: The process is safe to re-run. It detects existing setups and can re-apply dotfiles without destructive actions. Operations are designed to be atomic where possible.
- **Configuration as Code**: All tool versions, endpoints, and repository locations are defined in a central `bootstrap.yaml` file, making the process transparent and auditable.

## Usage

### Prerequisites

- A fresh user account on a Linux (POSIX shell) or Windows (PowerShell) machine.
- `curl` (on Linux) or `irm` (on Windows).
- `git` is recommended but not strictly required (the bootstrap can fetch it).
- Access to the `sealbridge-otp-gate` server from the new workstation.
- Your TOTP secret configured in an authenticator app.
- The passphrase for the encrypted SSH key.

### Bootstrap Commands

**Linux/macOS (POSIX)**:
```sh
sh -c "$(curl -fsSL https://your-dist-server.com/sealbridge/bootstrap/latest/bootstrap.sh)"
```

**Windows (PowerShell)**:
```powershell
iex (irm https://your-dist-server.com/sealbridge/bootstrap/latest/bootstrap.ps1)
```

## How It Works

1.  **Stub Execution**: The one-liner downloads a tiny, insecure bootstrap stub (`bootstrap.sh` or `.ps1`).
2.  **Payload Verification**: The stub's primary job is to download the real, versioned payload (`payload.tar.zst` or `.zip`). It contains a hardcoded SHA256 checksum that it verifies against the downloaded payload. **Execution halts if the checksum fails.**
3.  **Extraction & Execution**: The verified payload is extracted into a temporary cache directory (`${XDG_CACHE_HOME}/sealbridge/bootstrap/<version>`). The stub then executes the main Python application (`sbboot`).
4.  **Gate 1: TOTP Verification**: `sbboot` prompts for your 6-digit TOTP code and sends it to the `sealbridge-otp-gate` for verification. The process will not continue until the gate returns a success response.
5.  **Gate 2: Passphrase Decryption**: `sbboot` prompts for your local passphrase. It downloads a pinned version of the `age` decryption tool, verifies its checksum, and then uses it to decrypt the bootstrap SSH key (`assets/id_bootstrap.age`). The key is piped directly to a running `ssh-agent` and is **never written to disk**.
6.  **Dotfiles Provisioning**: With the key loaded in the agent, `sbboot` downloads a pinned version of `chezmoi`, verifies its checksum, and then uses it to clone your private `dotfiles` repository and apply a configuration profile (e.g., `work` or `home`).
7.  **Cleanup**: The script cleans up temporary files, unsets sensitive environment variables, and terminates any temporary SSH agents it may have started.

## Security and Threat Model

- **Initial Connection**: The initial `curl` or `irm` is over TLS, but the executed script is insecure. The trust is established **after** the payload's SHA256 checksum is verified locally by the stub. This mitigates a compromise of the distribution server.
- **Secrets Management**:
    - The bootstrap SSH key is encrypted at rest using `age`.
    - The key is only ever decrypted into memory. A compromised machine would require runtime inspection capabilities to steal the key.
    - The OTP gate client secret is loaded from an environment variable, not stored in the repository.
- **Binary Integrity**: All external tools (`age`, `chezmoi`, `uv`) are downloaded from pinned, versioned URLs and their SHA256 checksums are verified before execution.
- **Filesystem Policy**: The bootstrap process is strictly confined to `$HOME` and respects XDG directories. By default, it is forbidden from touching `$HOME/workspace/**`, preventing accidental modification of user code or data.

## Troubleshooting

- **OTP Gate Unreachable**: Verify network connectivity and any firewall rules blocking access to the gate's URL.
- **Checksum Mismatch**: This indicates a corrupted download or a potential MITM attack. Do not proceed.
- **Decryption Failed**: You may have entered the wrong passphrase. The script will allow a limited number of retries.
- **SSH Agent Issues**: Ensure `ssh-agent` is running (on Linux) or the "OpenSSH Authentication Agent" service is running (on Windows).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
