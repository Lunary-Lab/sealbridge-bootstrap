# Assets

This directory contains encrypted assets required for the bootstrap process.

## `id_bootstrap.age`

This is the `age`-encrypted SSH private key used for the initial bootstrap. It should be encrypted with a strong passphrase.

### Key Rotation

To rotate the key:

1.  **Generate a new SSH key pair**:
    ```sh
    ssh-keygen -t ed25519 -C "sealbridge-bootstrap-key-$(date +'%Y-%m-%d')" -f id_bootstrap_new
    ```
    **Do not use a passphrase for the key itself.** The encryption will be handled by `age`.

2.  **Encrypt the private key with `age`**:
    ```sh
    age -p id_bootstrap_new > id_bootstrap.age
    ```
    You will be prompted to enter a strong passphrase. This is the passphrase users will need to enter during the bootstrap process.

3.  **Update the public key**: The corresponding public key (`id_bootstrap_new.pub`) needs to be added as a deploy key to any private Git repositories that the bootstrap process needs to clone (e.g., your `dotfiles` repository).

4.  **Replace the old key**: Overwrite the old `id_bootstrap.age` in this directory with the new one.

5.  **Cleanup**: Securely delete the plaintext private key (`id_bootstrap_new`) and the public key file.
    ```sh
    shred -u id_bootstrap_new id_bootstrap_new.pub
    ```

**Warning**: Never commit the plaintext private key to this repository. The CI pipeline includes a plaintext guard to prevent this.
