# LocalCurator Prime - Release Guide

This document describes the code signing infrastructure and release workflow for Windows and macOS.

## Code Signing Infrastructure

Without code signing, Windows SmartScreen blocks the installer, and macOS Gatekeeper rejects the app. Code signing is integrated directly into our GitHub Actions release workflow.

### Obtaining Certificates

**For Dev / Testing:**

- Self-signed certificates can be generated, but they will still show warnings to end users on Windows, and will not pass macOS notarization constraints.

**For Production:**

1. **Windows**: Purchase a standard or EV Code Signing Certificate (e.g., from SSL.com, DigiCert). Export it as a Base64 encoded PFX file (`.pfx`).
2. **macOS**: Enroll in the Apple Developer Program. Create a "Developer ID Application" certificate via the Apple Developer console.

### GitHub Secrets Setup Checklist

Configure the following secrets in the GitHub repository (`Settings -> Secrets and variables -> Actions`):

#### Updater Configuration and Secrets

Tauri requires an Ed25519 keypair for securely delivering auto-updates.

**To generate a new Updater Keypair:**

1. Run `powershell ./scripts/generate_updater_key.ps1`
   - Alternatively, use the Tauri CLI: `cargo tauri signer generate -w ~/.tauri/localcurator.key`
2. Open the generated `~/.tauri/localcurator.key.pub` and copy the public key string.
3. Paste the string into `src-tauri/tauri.conf.json` -> `plugins.updater.pubkey`.

**GitHub Secrets for the Updater:**

- `TAURI_PRIVATE_KEY`: Private Ed25519 key (contents of `~/.tauri/localcurator.key`).
- `TAURI_KEY_PASSWORD`: Password you set during generation (if any).

### Content Security Policy (CSP)

Our application enforces a strict Content Security Policy defined in `tauri.conf.json`.

- `default-src 'self' tauri: https://tauri.localhost`: Default context restricting to local and Tauri protocol.
- `style-src 'self' 'unsafe-inline'`: Allows Tailwind CSS runtime injection.
- `connect-src 'self' http://localhost:* https://tauri.localhost tauri:`: Allows frontend connections to the Python backend on localhost ports.
- `img-src 'self' blob: data: http://localhost:* https://tauri.localhost`: Allows data URIs, blob URLs (for dynamically loaded images), and backend image serving.
- `font-src 'self' data:`: Local font loading.
- `script-src 'self' 'unsafe-inline'`: Required for React execution via Next.js exports.

#### Windows Authenticode

- `WINDOWS_CERTIFICATE`: The Base64 encoded `.pfx` certificate file.
- `WINDOWS_CERTIFICATE_PASSWORD`: The password for the `.pfx` file.

#### macOS Notarization & Signing

- `APPLE_CERTIFICATE`: The Base64 encoded `.p12` file of your Developer ID Application certificate.
- `APPLE_CERTIFICATE_PASSWORD`: The password for the `.p12` file.
- `APPLE_SIGNING_IDENTITY`: The exact string name of the certificate identity.
- `APPLE_ID`: Your Apple ID email address.
- `APPLE_PASSWORD`: App-specific password for the Apple ID.
- `APPLE_TEAM_ID`: Your 10-character Apple Team ID.

## Release Procedure

1. **Bump Version**: Update the version number in `src-tauri/tauri.conf.json`, `web/package.json`, and `pyproject.toml` (if available).
2. **Push Tag**: Create and push a Git tag formatted as `vX.Y.Z` (e.g., `v1.0.0`).

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **Workflow Dispatch (Alternative)**: Trigger the `.github/workflows/release.yml` manually from the Actions tab and specify the version.
4. **Draft Release**: The CI will create a *draft* on GitHub Releases with uploaded `.msi`, `.dmg`, and `.AppImage` files. Review the assets, fill in any patch notes, and publish the release.

## Updating the App

Our application pulls updates using the embedded Tauri Updater plugin. Ensure that the latest compiled `.json` manifest from your CI is hosted on `endpoints` described within `tauri.conf.json`.
