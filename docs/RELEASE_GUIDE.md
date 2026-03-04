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

#### Updater Secrets (Tauri v1/v2)

- `TAURI_PRIVATE_KEY`: Private Ed25519 key for the Tauri updater signing.
- `TAURI_KEY_PASSWORD`: Password for the updater private key (if it's encrypted).

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
